payments
=================================

Payment module providing convinient abstraction over different payment methods and gateways
Features traditional payment methods: cash, bank transfer and Paypal payment gateway. 
Easly extendable to provide more payment gateways
Tested with Django 1.11.15

Supported payment methods:
* cash
* SWIFT bank transfer
* non SWIFT bank transfer for countries like Venezuela
* Paypal email
* Credit card via Paypal using Paypal REST SDK (with snadbox for testing)


Dependencies
------------

external:
* yamlfield
* oauthlib (for Paypal)
* requests_oauthlib (for Paypal)
* paypalrestsdk

interanal:
* Institution
* locations


Installing
----------
Assuming that you got virtualenv (python virtual envirement) created and activated.

Install via pip:

    pip install -e git+https://github.com/atiyogafoundation/payments.git#egg=payments

Add to "INSTALLED_APPS" in settings.py file:
    
    'payments',

Add to 'urlpatterns' (at the end) urls.py file:
    
    (r'payments', include('payments.urls')),
    
Create tables etc.:

    python manage.py syncdb

Config
------
At settings.py file must be set:
    
    PAYEMNT_HOST = "https://domain.com"

```python
PAYMENT_PROVIDERS = {
    'cash': ('payments.providers.basic.Cash', {}),
    'bank_transfer': ('payments.providers.basic.BankTransfer', {}),
    'SWIFT_transfer': ('payments.providers.basic.SWIFTTransfer', {}),
    'creadit_card_via_paypal': ('payments.providers.paypal.PaypalCard', {}),
    'paypal': ('payments.providers.paypal.Paypal', {}),
    'paypal_sandbox': ('payments.providers.paypal.PaypalSandbox', {}),
}
```

Extending
---------

Other payment methods / paymenet gateways can be easly added by subclassing `AbstrtactProvider` and overiding methods `execute`, `on_return`, `on_cancel` and setting `required_params`.


```python
from ._abstract_provider import AbstrtactProvider

class YourGateway(AbstrtactProvider):
    required_params = {
        'client_id' : str, # Edit this to your API user name
        'secret' : str, # Edit this to your API password
    }
    def execute(self, request, data):
        ...
     
    def on_return(self, request):
        ...
     
    def on_cancel(self, request):
        ...
```

Path to the file with custom payment method should be added to `PAYMENT_PROVIDERS` at `settings.py` (look config)

Licence
-------
[GPL](LICENSE)
