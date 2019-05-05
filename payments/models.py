try:
    from urllib.parse import urljoin, urlencode
except ImportError:
    from urllib import urlencode
    from urlparse import urljoin

import datetime
import base64
import hashlib

from django.dispatch import Signal
from django.db import models
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import JSONField
from django.utils import timezone

from yamlfield.fields import YAMLField

from locations.models import COUNTRIES, CURRENCIES
from organizations.models import Institution

PROVIDER_CACHE = {}
status_changed = Signal()


def provider_factory(provider):
    '''
    Return the provider instance based on variant
    '''
    providers = getattr(settings, 'PAYMENT_PROVIDERS', None)
    handler, config = providers.get(provider, (None, None))
    if not handler:
        raise ValueError('Payment provider does not exist: %s' %
                         (provider,))
    if provider not in PROVIDER_CACHE:
        module_path, class_name = handler.rsplit('.', 1)
        module = __import__(
            str(module_path), globals(), locals(), [str(class_name)])
        PROVIDER_CACHE[provider] = getattr(module, class_name)
    return PROVIDER_CACHE[provider]


def get_providers_choices():
    providers = getattr(settings, 'PAYMENT_PROVIDERS').keys()
    return zip(providers, providers)

def get_providers_settings():
    provider_names = getattr(settings, 'PAYMENT_PROVIDERS').keys()
    provider_settings = {}
    for provider_name in provider_names:
        provider = provider_factory(provider_name)
        provider_settings[provider_name] = show_provider_settings(provider.required_params.keys())
    return provider_settings

def show_provider_settings(settings):
    text = ''
    for setting in settings:
        text += "%s: \n" % setting
    return text


class Option(models.Model):
    DESTINATIONS = (
        (1, 'payment'),
        (2, 'donation'),
        (3, 'payment & donation'),
    )
    name = models.CharField(max_length=255,
        help_text=_('userfriendly name of the payment option'))
    institution = models.ForeignKey(Institution)
    provider = models.CharField(
        max_length=255, choices=get_providers_choices())
    currency = models.CharField(max_length=3, choices=CURRENCIES)
    # description = models.TextField()
    settings = YAMLField(
        blank=True, null=True,
        help_text="check settings for each provider")
    destination = models.PositiveIntegerField(choices=DESTINATIONS)

    def get_provider(self, payment):
        Provider = provider_factory(self.provider)
        provider = Provider(dict(self.settings or {}), payment)
        return provider

    @property
    def has_automatic_provider(self):
        return self.provider in ['cash', 'bank_transfer']

    def check_settings(self):
        Provider = provider_factory(self.provider)
        return Provider.check_settings(self.settings)

    def clean(self):
        settings_errors = self.check_settings()
        if settings_errors:
            raise ValidationError(
                _('There errors in settings: %s' % ", ".join(settings_errors)))

    def __str__(self):
        return "%s" % self.name


class PaymentStatus:
    WAITING = 'waiting'
    PREAUTH = 'preauth'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'
    REFUNDED = 'refunded'
    ERROR = 'error'
    INPUT = 'input'
    CANCELLED = 'cancelled'

    CHOICES = [
        (WAITING, _('Waiting for confirmation')),
        (PREAUTH, _('Pre-authorized')),
        (CONFIRMED, _('Confirmed')),
        (REJECTED, _('Rejected')),
        (REFUNDED, _('Refunded')),
        (ERROR, _('Error')),
        (CANCELLED, _('Cancelled')),
        (INPUT, _('Input'))]

    MANUAL_STATUS = (WAITING, CONFIRMED)
    WAITING_CHOICES = [
        (WAITING, _('Waiting for confirmation')),
        (CONFIRMED, _('Confirmed')),
        (CANCELLED, _('Cancelled')),]
    CONFIRMED_CHOICES = [
        (CONFIRMED, _('Confirmed')),
        (REFUNDED, _('Refunded')),]


class PaymentQuerySet(models.QuerySet):
    def confirmed(self):
        return self.filter(status=PaymentStatus.CONFIRMED)
    def toward(self, toward):
        return self.filter(to=toward)
    def confirmed_toward(self, toward):
        return self.filter(status=PaymentStatus.CONFIRMED, to=toward)
    def confirmed_with_cause(self, cause):
        cause = getattr(cause, 'course', cause)
        content_type_id = ContentType.objects.get_for_model(cause).id
        # import ipdb; ipdb.set_trace()
        return self.filter(
            status=PaymentStatus.CONFIRMED,
            content_type_id=content_type_id,
            object_id=cause.id
        )


class PaymentManager(models.Manager):
    def get_queryset(self):
        return PaymentQuerySet(self.model, using=self._db)
    def confirmed(self):
        return self.get_queryset().confirmed()
    def toward(self, toward):
        return self.get_queryset().toward(toward)
    def confirmed_toward(self, toward):
        return self.get_queryset().confirmed_toward(toward)
    def confirmed_with_cause(self, cause):
        return self.get_queryset().confirmed_with_cause(cause)


class Payment(models.Model):
    __prev_status = None

    code = models.CharField(max_length=36, blank=True, default='')
    status = models.CharField(
        max_length=10, choices=PaymentStatus.CHOICES,
        default=PaymentStatus.WAITING)

    frm = models.ForeignKey(
        User, verbose_name=_("from"),
        blank=True, null=True)
    to = models.ForeignKey(
        Institution, verbose_name=_("to"))

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    cause = GenericForeignKey('content_type', 'object_id')

    amount = models.DecimalField(max_digits=5, decimal_places=2)
    currency = models.CharField(max_length=10, choices=CURRENCIES)
    tax = models.DecimalField(max_digits=9, decimal_places=2, default='0.0')

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User, related_name="payments_modified",
        blank=True, null=True)
    payed_at = models.DateTimeField(blank=True, null=True)

    option = models.ForeignKey(Option)
    transaction_id = models.CharField(
        max_length=200, blank=True, null=True)
    token = models.CharField(max_length=36, blank=True, default='')

    billing_first_name = models.CharField(
        _('first name'), max_length=256, blank=True)
    billing_last_name = models.CharField(
        _('last name'), max_length=256, blank=True)
    billing_tin = models.CharField(
        _('TIN'), max_length=256, blank=True,
        help_text = _("""Taxpayer Identification Number. Italian Fiscal Code, Spanish NIF.
        , or if your country does not provide it, Passport number"""))
    billing_address_1 = models.CharField(max_length=256, blank=True)
    billing_address_2 = models.CharField(max_length=256, blank=True)
    billing_city = models.CharField(max_length=256, blank=True)
    billing_postcode = models.CharField(max_length=256, blank=True)
    customer_id = models.CharField(max_length=256, blank=True)
    billing_country_code = models.CharField(
        _('country'),
        choices=COUNTRIES,
        max_length=2, blank=True)
    billing_country_area = models.CharField(max_length=256, blank=True)
    billing_email = models.EmailField(_('email'), blank=True)
    customer_ip_address = models.GenericIPAddressField(blank=True, null=True)
    extra_data = JSONField(blank=True, null=True)
    message = models.TextField(_('message'), blank=True, default='')
    document_id = models.CharField(max_length=256, blank=True)
    log = JSONField(blank=True, null=True)

    objects = PaymentManager()

    def __init__(self, *args, **kwargs):
        super(Payment, self).__init__(*args, **kwargs)
        self.__prev_status = self.status

    def create_hash(self, seed):
        hasher = hashlib.sha1(seed.encode('utf-8'))
        return base64.urlsafe_b64encode(hasher.digest()[0:12])

    @property
    def is_automatic(self):
        return self.option.provider not in ("cash", "bank_transfer")
    
    def log_data(self, log_type, type, message, date = None):
        log = self.log or []
        if not date:
            date = str(datetime.datetime.now())
        log.append(
            [log_type, type, date, message]
        )
        self.log = log
        return log

    def clear(self):
        if not self.is_automatic and self.status in PaymentStatus.MANUAL_STATUS:
            raise ValidationError(
                _("%s does not accept '%s' status") % (
                    self.option.provider, self.status))

    def valid_billing_data(self):
        return self.billing_first_name and self.billing_last_name and \
            self.billing_city and self.billing_address_1 and \
            self.billing_postcode and \
            self.billing_country_code and self.billing_email

    def show_amount(self):
        return "%s%s" % (self.amount, self.currency)

    # def clean(self):
    #     if self.currency != self.option.currency:
    #         raise ValidationError(_("Payment currency must match payment option currency"))
    #     if not self.frm and not self.valid_billing_data():
    #         raise ValidationError("You must provide customer data")

    #     cleaned_data = self.cleaned_data
    #     if (not self.billing_first_name and not self.billing_last_name and not self.billing_email) and not self.frm:
    #         raise ValidationError(_("You must set 'from' or fill in all billing information"))

    def status_change(self):
        return (self.__prev_status, self.status)

    def status_changed(self):
        return self.__prev_status != self.status

    def change_status(self, status, message=''):
        '''
        Updates the Payment status and sends the status_changed signal.
        '''
        # from .signals import status_changed
        self.status = status
        self.message = message
        status_changed.send(sender=type(self), instance=self)

    def got_confiremed(self):
        return self.__prev_status == PaymentStatus.WAITING and self.status == PaymentStatus.CONFIRMED

    def save(self, *args, **kwargs):
        if self.got_confiremed():
            self.payed_at = timezone.now()
        if not self.id:
            self.code = self.create_hash(str(datetime.datetime.now()))
        if not self.billing_first_name and self.frm:
            self.billing_first_name = self.frm.first_name
        if not self.billing_last_name and self.frm:
            self.billing_last_name = self.frm.last_name
        if not self.billing_email and self.frm:
            self.billing_email = self.frm.email
        if self.frm and self.frm.student:
            self.billing_billing_city = self.frm.student.city
            self.billing_address_1 = self.frm.student.address
            self.billing_billing_postcode = self.frm.student.postcode
            self.billing_country_code = self.frm.student.country

        super(Payment, self).save(*args, **kwargs)
        
        # if self.status_changed():
        #     self.change_status(self.status)
        # self.__prev_status = self.status
    
    def __str__(self):
        return "%s - %s from %s %s" % (
            self.created .strftime('%d %b %Y %H:%M') if self.created else 'to be charged',
            self.show_amount(), self.billing_first_name, self.billing_last_name,)


