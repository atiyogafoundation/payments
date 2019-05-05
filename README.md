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


Licence
-------
[GPL](LICENSE)
