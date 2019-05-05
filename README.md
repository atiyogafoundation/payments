payments
=================================

Payment module providing convinient abstraction over diferent payment methods and gateways
Tested with django 2.1

Features:
* traditional payment methods: cash, bank transfer
* Paypal payment gateway with sandbox for testing
* Easly extendable to provide more payment gateways


Installing
----------
Assuming that you got virtualenv (python virtual envirement) created and activated.

Install via pip:

    pip install -e git+https://github.com/atiyogafoundation/payments/.git#egg=payments

Add to "INSTALLED_APPS" in settings.py file:
    
    'payments',

Add to 'urlpatterns' (at the end) urls.py file:
    
    (r'registration', include('payments.urls')),
    
Create tables etc.:

    python manage.py syncdb

Config
------
At settings.py file must be set:
    
    'PAYEMNT_HOST = "https://domain.com"'


Licence
-------
