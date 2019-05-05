import braintree

from django.shortcuts import render
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from ._abstract_provider import AbstrtactProvider
from ..models import PaymentStatus


class CheckoutForm(forms.Form):
    payment_method_nonce = forms.CharField(
        max_length=1000,
        widget=forms.widgets.HiddenInput,
        # require=False,  # In the end it's a required field, but I wanted to provide a custom exception message
    )
    
    def clean(self):
        self.cleaned_data = super(CheckoutForm, self).clean()
        # Braintree nonce is missing
        if not self.cleaned_data.get('payment_method_nonce'):
            raise forms.ValidationError(_(
                'We couldn\'t verify your payment. Please try again.'))
        return self.cleaned_data


# https://blog.bitlabstudio.com/a-guide-for-using-braintree-in-django-53e99d677f71
# http://my-django-python.blogspot.it/2015/11/braintree-payment-gateway-with-django.html
class Braintree(AbstrtactProvider):
    def __init__(self, settings, payment):
        self.braintree = braintree
        # self.braintree.Configuration.configure(braintree.Environment.Sandbox, 
        #     merchant_id=settings['merchant_id'],
        #     public_key=settings['public_key'],
        #     private_key=settings['private_key']
        # )
        self.braintree.Configuration.configure(braintree.Environment.Sandbox, 
            merchant_id='ccysy6tp48qxmjdn',
            public_key='grmsjnn9gsbvzfrf',
            private_key='35d61a8fcfcf0ee072e3e371781de696'
        )
        
    def execute(self, request):
        if not self.payment.token:
            return self.prepare(self.payment, request)
        else:
            return self.dispatch(self.payment, request)
    
    def prepare(self, payment, request):
        result = self.braintree.Customer.create({
            "first_name": payment.billing_first_name,
            "last_name": payment.billing_last_name,
            # "country_code": payment.billing_country_code,
            "email": payment.billing_email,
        })
        # import ipdb; ipdb.set_trace()
        if result.is_success:
            payment.customer_id = result.customer.id
            payment.change_status(PaymentStatus.PREAUTH)
        else:
            payment.change_status(PaymentStatus.ERROR)
        payment.save()

        if not payment.token:
            token = self.braintree.ClientToken.generate({
               "customer_id": result.customer.id
            })
            payment.token = token
            payment.save()
        return render(request, 'payments/braintree/checkout.html', dict(payment=payment))


    def dispatch(self, request, payment):
        if request.POST:
            if request.POST.get('amount') != payment.amount:
                raise 
            nonce_from_the_client =  request.POST.get("payment_method_nonce")
            result = self.braintree.Transaction.sale({
                "amount": payment.amount,
                "payment_method_nonce": nonce_from_the_client
            })
            transaction_id =  result.transaction.id
            payment.transaction_id = result.transaction.id
            if result.is_success:
                payment.change_status(PaymentStatus.CONFIRMED)
            else:
                payment.change_status(PaymentStatus.ERROR)
            payment.save()
        return render(request, 'payments/braintree/checkout.html', dict(payment=payment))
    

    def get_success_url(self):
        # Add your preferred success url
        return reverse('foo')