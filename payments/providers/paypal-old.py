import requests
import json

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from django.shortcuts import render
from django.core.urlresolvers import reverse

from ..models import PaymentStatus
from ._abstract_provider import AbstrtactProvider


class Paypal(AbstrtactProvider):
    PAYPAL_REST_API = 'https://api.paypal.com/v1/%s'

    #https://micropyramid.com/blog/e-commerce-paypal-integration-with-django/
    SUPPORTED_CURRENCIES = ('AUD', 'BRL', 'CAD', 'CZK', 'DKK', 
        'EUR', 'HKD', 'HUF', 'ILS', 'JPY', 'MYR', 'MXN', 'TWD', 
        'NZD', 'NOK', 'PHP', 'PLN', 'GBP', 'RUB', 'SGD', 'SEK', 
        'CHF', 'THB', 'USD')

    required_params = {
        'client_id' : str, # Edit this to your API user name
        'secret' : str, # Edit this to your API password
    }
    
    def __init__(self, settings, payment):
        super(Paypal, self).__init__(settings, payment)
        respond = self.get_access_token(
            settings['client_id'], settings['secret'])
        self.settings['access_token'] = respond['access_token']
        
    def get_access_token(self, client_id, secret):
        # http://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html#backend-application-flow
        client = BackendApplicationClient(client_id=client_id)
        oauth = OAuth2Session(client=client)
        # import ipdb; ipdb.set_trace()
        respond = oauth.fetch_token(self.PAYPAL_REST_API % 'oauth2/token',
            client_id=client_id,
            client_secret=secret)
        return respond

    def execute(self, request):
        # https://developer.paypal.com/docs/integration/direct/express-checkout/integration-jsv4/advanced-payments-api/create-express-checkout-payments/
        params = self.settings
        headers={'Accept':'application/json',
            'Authorization':'Bearer %s' % params['access_token']}
        payload = {
            "intent": "sale",
            # "experience_profile_id":"experience_profile_id",
            "redirect_urls": {"return_url": params['returnUrl'], 
                "cancel_url": params['cancelUrl']},
            "payer": {"payment_method": "paypal"},
            "transactions": [
                {
                    "amount": {
                        "total": str(self.payment.amount), 
                        "currency": self.payment.currency},
                    "description": "The payment transaction description.",
                    "invoice_number": "merchant invoice",
                    "custom":  self.payment.id
                }
            ]
        }
        respond = requests.post(
            self.PAYPAL_REST_API % 'payments/payment', 
            headers=headers, json=payload)
        # https://developer.paypal.com/docs/integration/direct/express-checkout/integration-jsv4/server-side-REST-integration/
        # import ipdb; ipdb.set_trace()
        respond_dict = respond.json()
        self.payment.payment_id = respond_dict['id']
        self.payment.change_status(PaymentStatus.WAITING)
        self.payment.save()
        return render(request, 
            "payments/paypal.html", 
            dict(payment=self.payment, client_id=params['client_id']))

    def on_return(self, request):

        params = self.settings
        params['SUBJECT'] = 'FACILITATOR_EMAIL'
        params['METHOD'] = 'GetExpressCheckoutDetails'
        params['TOKEN'] = self.payment.token
        # get customer_id
        response = requests.post(self.PAYPAL_API, params=params)
        customer_id = dict(parse_qsl(response.text))['PAYERID']
        self.payment.customer_id = customer_id
        self.payment.save()
        # execute payment 
        # https://developer.paypal.com/docs/integration/direct/express-checkout/integration-jsv4/advanced-payments-api/execute-payments/
        params['METHOD'] = 'DoExpressCheckoutPayment'
        params['PAYERID'] = customer_id
        params['PAYMENTREQUEST_0_PAYMENTACTION'] = 'SALE'
        params['PAYMENTREQUEST_0_AMT'] = self.payment.amount
        params['PAYMENTREQUEST_0_CURRENCYCODE'] = self.payment.currency
        response = requests.post(PAYPAL_API, data=data)  
        result = dict(parse_qsl(response.text))
        state = result['state']
        if state == "approved":
            self.payment.status = PaymentStatus.CONFIRMED
        else:
            self.payment.status = PaymentStatus.ERROR
        
        self.payment.log_data('payment_respond', self.payment.status, result)
        self.payment.save()
        return render(request, "payments/result.html", context)

    def on_cancel(self, request):
        self.payment.change_status(PaymentStatus.CANCELLED)
        self.payment.save()
        return render(request, "payments/canceled.html", context)


class PaypalSandbox(Paypal):
    PAYPAL_REST_API = 'https://api.sandbox.paypal.com/v1/%s'
    

# class PaypalOLD(AbstrtactProvider):
#     #https://micropyramid.com/blog/e-commerce-paypal-integration-with-django/
#     SUPPORTED_CURRENCIES = ('AUD', 'BRL', 'CAD', 'CZK', 'DKK', 
#         'EUR', 'HKD', 'HUF', 'ILS', 'JPY', 'MYR', 'MXN', 'TWD', 
#         'NZD', 'NOK', 'PHP', 'PLN', 'GBP', 'RUB', 'SGD', 'SEK', 
#         'CHF', 'THB', 'USD')

#     settings = {
#         'METHOD':'SetExpressCheckout',
#         'VERSION':124.0, 
#         'PAYMENTREQUEST_0_PAYMENTACTION': 'Sale',
#     }

#     required_params = {
#         'USER' : str, # Edit this to your API user name
#         'PWD' : str, # Edit this to your API password
#         'SIGNATURE' : str, 
#         # 'PAYMENTREQUEST_0_PAYMENTACTION':str,     # type of payment
#         # 'PAYMENTREQUEST_0_AMT': int,              # amount of transaction
#         # 'PAYMENTREQUEST_0_CURRENCYCODE': str,   
#     }

#     # def check_settings(self, settings):
#     #     valid = True
#     #     for key, setting_type in self.required_params:
#     #         try:
#     #             setting = settings[key]
#     #         except:
#     #             raise ValidationError(_('this payment option requires "%s" setting' % key))
#     #         else:
#     #             if not (type(setting) != setting_type):
#     #                 raise ValidationError(_('"%s" setting should be %s' % (key, str(setting_type)))
    
#     def __init__(self, settings, payment):
#         # self.check_settings(settings)
#         host = "https://dev.shangshungfoundation.org%s"
#         self.settings.update(settings)
#         self.settings['returnUrl'] = host % reverse("payment_success", kwargs={'payment_id': payment.id})
#         self.settings['cancelUrl'] = host % reverse("payment_cancell", kwargs={'payment_id': payment.id})
#         import ipdb; ipdb.set_trace()
#         self.payment = payment

#     def get_access_token(self, client_id, secret):
#         headers={'Accept':'application/json', 'Accept-Language':'en_US'}
#         response = requests.post(PAYPAL_REST_API % '/v1/oauth2/token', headers=headers, params=params)

#     def execute(self, request):
#         params = self.settings
#         params['PAYMENTREQUEST_0_AMT'] = self.payment.amount
#         params['PAYMENTREQUEST_0_CURRENCYCODE'] = self.payment.currency
#         # get paypal token
#         response = requests.post(PAYPAL_API, params=params)
#         response_dict = dict(parse_qsl(response.text))
#         token = response_dict['TOKEN']
#         self.payment.token = token
#         self.payment.change_status(PaymentStatus.PREAUTH)
#         self.payment.save()
#         return redirect(PAYPAL_URL % token)

#     def on_respond(self, request):
#         params = self.settings
#         params['SUBJECT'] = 'FACILITATOR_EMAIL'
#         params['METHOD'] = 'GetExpressCheckoutDetails'
#         params['TOKEN'] = self.payment.token
#         # get customer_id
#         response = requests.post(PAYPAL_API, params=params)
#         customer_id = dict(parse_qsl(response.text))['PAYERID']
#         self.payment.customer_id = customer_id
#         self.payment.save()
#         # execute payment
#         params['METHOD'] = 'DoExpressCheckoutPayment'
#         params['PAYERID'] = customer_id
#         params['PAYMENTREQUEST_0_PAYMENTACTION'] = 'SALE'
#         params['PAYMENTREQUEST_0_AMT'] = self.payment.amount
#         params['PAYMENTREQUEST_0_CURRENCYCODE'] = self.payment.currency
#         response = requests.post(PAYPAL_API, data=data)  
#         result = dict(parse_qsl(response.text))
#         ack = result['ACK']
#         if ack in ['Success', 'SuccessWithWarning']:
#             self.payment.change_status(PaymentStatus.CONFIRMED)
#         else:
#             self.payment.change_status(PaymentStatus.ERROR)
#         self.payment.save()
#         return render(request, "payments/result.html", context)

# def paypal(request, participant_id):
#     participant = Participant.objects.get(pk=participant_id)
#     # What you want the button to do.
#     paypal_dict = {
#         "business": participant.course.educational_programme.institution.paypal_email,
#         "amount": participant.calculate_due,
#         "item_name": participant.course,
#         "invoice": participant.id,
#         "currency_code": participant.course.currency,
#         "notify_url": "http://education.shangshungfoundation.org" + reverse('paypal-ipn'),
#         "return_url": "http://education.shangshungfoundation.org",
#         "cancel_return": "http://education.shangshungfoundation.org/cancel/",
#         "landing_page": "Billing",
#         "lc": participant.course.main_language,
#         "custom": "update_income",  # Custom command to correlate to some function later (optional)
#     }

#     # Create the instance.
#     form = PayPalPaymentsForm(initial=paypal_dict)
#     context = {"form": form, "participant": participant}
#     return render(request, "courses/payment.html", context)


# class PaypalExpressCheckout(AbstrtactProvider):
#     #https://micropyramid.com/blog/e-commerce-paypal-integration-with-django/
#     SUPPORTED_CURRENCIES = ('AUD', 'BRL', 'CAD', 'CZK', 'DKK', 
#         'EUR', 'HKD', 'HUF', 'ILS', 'JPY', 'MYR', 'MXN', 'TWD', 
#         'NZD', 'NOK', 'PHP', 'PLN', 'GBP', 'RUB', 'SGD', 'SEK', 
#         'CHF', 'THB', 'USD')

#     params = {
#         'METHOD':'SetExpressCheckout',
#         'VERSION':86, 
#         'cancelUrl':"xxxxxxxxxxxxx",    #For use if the consumer decides not to proceed with payment 
#         'returnUrl':"xxxxxxxxxxxx"   #For use if the consumer proceeds with payment
#     }


#     required_params = {
#         'USER' : str, # Edit this to your API user name
#         'PWD' : str, # Edit this to your API password
#         'SIGNATURE' : str, 
#         'PAYMENTREQUEST_0_PAYMENTACTION':str,     # type of payment
#         'PAYMENTREQUEST_0_AMT': int,              # amount of transaction
#         'PAYMENTREQUEST_0_CURRENCYCODE': str,   
#     }

#     def get_paypal_token(self, params):
#         response = requests.get('https://api-3t.sandbox.paypal.com/nvp', params=params)


    # def execute(self):


# from models import Participant, Payment


# def paypal(request, participant_id):
#     participant = Participant.objects.get(pk=participant_id)
#     # What you want the button to do.
#     paypal_dict = {
#         "business": participant.course.educational_programme.institution.paypal_email,
#         "amount": participant.calculate_due,
#         "item_name": participant.course,
#         "invoice": participant.id,
#         "currency_code": participant.course.currency,
#         "notify_url": "http://education.shangshungfoundation.org" + reverse('paypal-ipn'),
#         "return_url": "http://education.shangshungfoundation.org",
#         "cancel_return": "http://education.shangshungfoundation.org/cancel/",
#         "landing_page": "Billing",
#         "lc": participant.course.main_language,
#         "custom": "update_income",  # Custom command to correlate to some function later (optional)
#     }

#     # Create the instance.
#     form = PayPalPaymentsForm(initial=paypal_dict)
#     context = {"form": form, "participant": participant}
#     return render(request, "courses/payment.html", context)


# def update_participant(sender, **kwargs):
#     ipn_obj = sender
#     if ipn_obj.payment_status == ST_PP_COMPLETED:

#         # WARNING !
#         # Check that the receiver email is the same we previously
#         # set on the business field request. (The user could tamper
#         # with those fields on payment form before send it to PayPal)

#         participant = Participant.objects.get(pk=ipn_obj.invoice)
#         paypal_email = participant.course.educational_programme.institution.paypal_email

#         if ipn_obj.receiver_email != paypal_email:
#             # Not a valid payment
#             return
#         # Undertake some action depending upon `ipn_obj`.
#         if ipn_obj.custom == "update_income":
#             payment = Payment.objects.create(
#                 participant=participant,
#                 amount=ipn_obj.amount,
#                 method=2,
#             )


# valid_ipn_received.connect(update_participant)