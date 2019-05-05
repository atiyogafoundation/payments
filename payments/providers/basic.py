from django.shortcuts import render
from django.utils.translation import ugettext as _

from utils.email import send_mail_tmpl

from ._abstract_provider import AbstrtactProvider

DON_DETAILS = _("Bank Transfer Payment to %s")


class Cash(AbstrtactProvider):
    def execute(self, request, data=None):
        return render(request, 
            "payments/cash.html", 
            dict(payment=self.payment, settings=self.settings))


class SWIFTTransfer(AbstrtactProvider):
    required_params = {
        'bank': str, 
        'address': str, 
        'IBAN': str, 
        'BIC': str, 
        'SWIFT': str, 
        # 'cause': str, 
    }

    def execute(self, request, data=None):
        param = dict(payment=self.payment, settings=self.settings)
        cause = getattr(self.payment.cause, 'name', str(self.payment.cause))
        send_mail_tmpl(
            DON_DETAILS % cause,
            'payments/emails/swift_data.txt',
            self.payment.to.contact_email,
            [self.payment.billing_email],
            param)

        return render(request, 
            "payments/bank_trasfer.html", param)


class BankTransfer(AbstrtactProvider):
    required_params = {
        'bank': str, 
        'address': str, 
        'account_nr': str, 
        # 'cause': str, 
    }

    def execute(self, request, data=None):
        param = dict(payment=self.payment, settings=self.settings)
        cause = getattr(self.payment.cause, 'name', str(self.payment.cause))
        send_mail_tmpl(
            DON_DETAILS % cause,
            'payments/emails/transfer_data.txt',
            self.payment.to.contact_email,
            [self.payment.billing_email],
            param)

        return render(request, 
            "payments/bank_trasfer.html", param)