from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

HOST = "https://atiyogafoundation.net"


class AbstrtactProvider(object):
    required_params = {}
    settings = {}
    
    @classmethod
    def check_settings(cls, settings):
        errors = []
        for key, setting_type in cls.required_params.items():
            try:
                setting = settings[key]
            except:
                errors.append(_('this payment option requires "%s" setting' % key))
                # /raise ValidationError(_('this payment option requires "%s" setting' % key))
            else:
                if type(setting) != setting_type:
                    # import ipdb; ipdb.set_trace()
                    errors.append('"%s" setting should be %s' % (key, type(setting_type)))
                    # raise ValidationError(_(
                    #     '"%s" setting should be %s' % (key, str(setting_type))))
        return errors

    def __init__(self, settings, payment):
        errors = self.check_settings(settings)
        if errors:
            raise ValidationError(_('There errors in settings: %s' % ", ".join(errors)))
        self.payment = payment
        settings['returnUrl'] = "%s%s" % (HOST, reverse(
            "payment_result", kwargs={'payment_code': payment.code}))
        settings['cancelUrl'] = "%s%s" % (HOST, reverse(
            "payment_cancel", kwargs={'payment_code': payment.code}))
        self.settings.update(settings)

    def excecute(self, request):
        raise NotImplementedError()

    def on_return(self, request):
        pass

    def on_cancel(self, request):
        pass

    # def get_return_url(self, payment, extra_data=None):
    #     payment_link = payment.get_process_url()
    #     url = urljoin(get_base_url(), payment_link)
    #     if extra_data:
    #         qs = urlencode(extra_data)
    #         return url + '?' + qs
    #     return url