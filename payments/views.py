from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _
from django.http.response import Http404

from organizations.models import Organization
from payments.models import Option

from utils.misc import get_client_ip

from .forms import PaymentForm, DonationForm
from .models import Payment


def place_payment(request, destination_id, cause, ammount, currency):
    cause_content_type = ContentType.objects.get_for_model(cause)
    cause_id = cause.id
    #  stores payment data in session 
    request.session['payment'] = dict(
        destination_id=destination_id,
        cause=cause_content_type.id,
        cause_id=cause_id,
        ammount=str(ammount),
        currency=currency)


def user_payment(request):
    initial = {}
    user = request.user
    payment_data = request.session.get('payment')

    if not payment_data:
        return render(
        request, "payments/error.html",
        dict(error=_("Order data not found")))

    cause = ContentType.objects.get(pk=payment_data['cause'])
    cause_instance = cause.get_object_for_this_type(pk=payment_data['cause_id'])
    destination_org = Organization.objects.get(pk=payment_data['destination_id'])
    if user:
        initial = dict(
            to=destination_org,
            billing_first_name=user.first_name,
            billing_last_name=user.last_name,
            billing_email=user.email)
        if user.student:
            initial['billing_address_1'] = user.student.address
            initial['billing_city'] = user.student.city
            initial['billing_country_code'] = user.student.country
    
    if cause.app_label == 'event_registrations':
        payment_methods = cause_instance.event.finance.payment_methods.all()
    else:
        payment_methods = Option.objects.filter(institution_id=destination_org.id)
    initial['payment_methods'] = payment_methods

    payment_form = PaymentForm(request.POST or None, initial=initial)
    if payment_form.is_valid():
        payment = payment_form.save(commit=False)
        payment.amount = payment_data['ammount']
        payment.currency = payment_data['currency']
        payment.content_type_id = payment_data['cause']
        
        payment.object_id = payment_data['cause_id']
        payment.to = destination_org
        payment.status = 'waiting'
        if user:
            payment.frm = user
        payment.customer_ip_address = get_client_ip(request)
        # import ipdb; ipdb.set_trace()
        payment.save()
        
        provider = payment.option.get_provider(payment)
        return provider.execute(request, {})
    return render(
        request, "payments/payment.html",
        dict(cause=cause,
            institution=destination_org,
            payment_form=payment_form, payment_data=payment_data))


def result(request, payment_code):
    payment = Payment.objects.get(code=payment_code)
    provider = payment.option.get_provider(payment)
    return provider.on_return(request)


def cancel(request, payment_code):
    payment = Payment.objects.get(code=payment_code)
    provider = payment.option.get_provider(payment)
    cancelled = provider.on_cancel(request)
    return render(request, 'payments/cancel.html', dict(payment=payment))


def status(request, payment_code):
    payment = Payment.objects.get(code=payment_code)
    return render(request, 'payments/status.html', dict(payment=payment))
