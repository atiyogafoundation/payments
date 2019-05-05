from django import forms

from courses.models import CoursePayment
from .models import Payment, Option, PaymentStatus


class PaymentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)
        # there's a `fields` property now
        self.fields['billing_first_name'].required = True
        self.fields['billing_last_name'].required = True
        self.fields['billing_email'].required = True
        self.fields['billing_address_1'].required = True
        self.fields['billing_city'].required = True
        self.fields['billing_country_code'].required = True
        self.fields['billing_tin'].required = True
        # if type(cause).__name__ == 'Event':
        #     payment_options = cause.finance.payment_methods.values_list(
        #         'id', flat=True)
        #     self.fields['amount'].label = "amount %s" % cause.finance.currency
        # else:
        #     payment_options = Option.objects.filter(
        #         institution=self.initial['to']).values_list('id', flat=True)
        # payment_options = Option.objects.filter(
        #     institution=self.initial['to']).values_list('id', flat=True)
        self.fields['option'].queryset = self.initial['payment_methods']
        # self.fields['option'].queryset = Option.objects.filter(
        #     id__in=payment_options)
        self.fields['option'].label = "payment method"

    class Meta():
        model = Payment
        fields = (
            'option',
            'billing_first_name', 'billing_last_name', 'billing_tin',
            'billing_email', 'billing_address_1', 'billing_city', 'billing_country_code')


class DonationFormMethods(PaymentForm):
    class Meta():
        model = Payment
        fields = (
            'amount', 'option',
            'billing_first_name', 'billing_last_name', 'billing_tin',
            'billing_email', 'billing_address_1', 'billing_city', 'billing_country_code')


class DonationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(DonationForm, self).__init__(*args, **kwargs)
        # there's a `fields` property now
        self.fields['billing_first_name'].required = True
        self.fields['billing_last_name'].required = True
        self.fields['billing_email'].required = True
        self.fields['billing_address_1'].required = True
        self.fields['billing_city'].required = True
        self.fields['billing_country_code'].required = True
        self.fields['billing_tin'].required = True
        # if type(cause).__name__ == 'Event':
        #     payment_options = cause.finance.payment_methods.values_list(
        #         'id', flat=True)
        #     self.fields['amount'].label = "amount %s" % cause.finance.currency
        # else:
        #     payment_options = Option.objects.filter(
        #         institution=self.initial['to']).values_list('id', flat=True)
        # payment_options = Option.objects.filter(
        #     institution=self.initial['to']).values_list('id', flat=True)
        # self.fields['option'].queryset = Option.objects.filter(
        #     id__in=payment_options)

    class Meta():
        model = Payment
        fields = (
            'amount',
            'billing_first_name', 'billing_last_name', 'billing_tin',
            'billing_email', 'billing_address_1', 'billing_city', 'billing_country_code')


class PayedForm(forms.ModelForm):
    class Meta:
        model = CoursePayment
        fields = ("frm", "amount", "option", "status")
        field_order = ("frm", "amount", "option", "status")

    def __init__(self, *args, **kwargs):
        super(PayedForm, self).__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, "option"):
            if self.instance.option.provider in ("cash", "bank_transfer", 'SWIFT_transfer', 'paypal'):
                if self.instance.status == PaymentStatus.CONFIRMED:
                    self.fields['status'].choices = PaymentStatus.CONFIRMED_CHOICES
                else:
                    self.fields['status'].choices = PaymentStatus.WAITING_CHOICES
            else:
                self.fields['status'].widget = forms.TextInput(
                    attrs={'readonly': 'readonly'})
