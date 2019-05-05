from django.conf.urls import url

from .views import result, cancel, status, user_payment


urlpatterns = [
    url(r'^result/(?P<payment_code>.+)/$', result, name="payment_result"),
    url(r'^cancel/(?P<payment_code>.+)/$', cancel, name="payment_cancel"),
    url(r'^status/(?P<payment_code>.+)/$', status, name="payment_status"),
    url(r'^$', user_payment, name="user_payment"),
]
