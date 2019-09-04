import requests
import json
import paypalrestsdk

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from utils.email import send_mail_tmpl

from ..models import PaymentStatus
from ._abstract_provider import AbstrtactProvider


class PaypalCard(AbstrtactProvider):
    MODE = 'live'

    required_params = {
        'client_id' : str, # Edit this to your API user name
        'secret' : str, # Edit this to your API password
    }
    
    def __init__(self, settings, payment):
        super(PaypalCard, self).__init__(settings, payment)
        api = paypalrestsdk.configure({
            'mode': self.MODE, #sandbox or live
            'client_id': settings['client_id'],
            'client_secret': settings['secret']})
        respond = api.get_token_hash()
        self.settings.update(respond)

    def execute(self, request, data):
        from paypalrestsdk import Payment
        # https://developer.paypal.com/docs/api/quickstart/payments/#initialize-the-payment-and-redirect-the-user
        params = self.settings
        payment = Payment( {
            "intent": "sale",
            # "experience_profile_id":"experience_profile_id",
            "redirect_urls": {"return_url": params['returnUrl'], "cancel_url": params['cancelUrl']},
            "payer": {"payment_method": "paypal"},
            "transactions": [
                {
                    "amount": {
                        "total": str(self.payment.amount), 
                        "currency": self.payment.currency},
                    "description": str(self.payment.cause),
                    # "invoice_number": "merchant invoice",
                    # "custom":  self.payment.id
                }
            ]
        })
        if payment.create():
            self.payment.payment_id = payment.id
            self.payment.change_status(PaymentStatus.WAITING)
            self.payment.save()
            for link in payment.links:
                if link.method == "REDIRECT":
                    # Capture redirect url
                    redirect_url = link.href
                    # REDIRECT USER to redirect_url
            else:
                print("Error while creating payment:")
                print(payment.error)

        return redirect(redirect_url)
        # return render(request, 
        #     "payments/paypal.html", 
        #     dict(payment=self.payment, redirect_url=redirect_url))

    def on_return(self, request):
        from paypalrestsdk import Payment
        params = self.settings
        
        payment_id = request.GET.get('paymentId')
        payment = Payment.find(payment_id)
        payer_id = request.GET.get('PayerID')
        self.payment.customer_id = payer_id
        if payment.execute({"payer_id": payer_id}):
            self.payment.status = PaymentStatus.CONFIRMED
            print("Payment[%s] execute successfully" % (payment.id))
        elif self.payment.status != PaymentStatus.CONFIRMED:
            self.payment.status = PaymentStatus.ERROR
            print(payment.error)
        # TODO FIX IT
        # self.payment.log_data('payment_respond', self.payment.status, payment)
        try:
            self.payment.save()
        except:
            pass
            # import ipdb; ipdb.set_trace()
        return render(request, "payments/status.html", dict(payment=self.payment))

    def on_cancel(self, request):
        self.payment.change_status(PaymentStatus.CANCELLED)
        # self.payment.log_data('payment_respond', self.payment.status, payment)
        self.payment.save()
        return render(request, "payments/cancel.html", dict(payment=self.payment))


class PaypalSandbox(PaypalCard):
    MODE = 'sandbox'


DON_DETAILS = _("Awaiting Paypal Payment to %s")

class Paypal(AbstrtactProvider):
    required_params = {
        'paypal_email': str, 
        # 'cause': str, 
    }

    def execute(self, request, data=None):
        param = dict(payment=self.payment, settings=self.settings)
        cause = getattr(self.payment.cause, 'name', str(self.payment.cause))
        send_mail_tmpl(
            DON_DETAILS % cause,
            'payments/emails/paypal_data.txt',
            self.payment.to.contact_email,
            [self.payment.billing_email],
            param)

        return render(request, 
            "payments/paypal.html", param)
