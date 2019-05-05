from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Payment, Option
from utils.admin._created import _CreatedAdmin
from utils.admin.utils import get_admin_url_4_model
from organizations.admin import InstitutionAdminMixin


class FeeAdmin(_CreatedAdmin):
    list_display = ("name", "event", "price")
    fieldsets = (
        (None, {
            'fields': (
                "event",
                "name",
                "participant_group",
                "price",
            )
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.event.status != 1:
            return ("event", "name", "participant_group", "price")
        else:
            return ("event", )

    def get_queryset(self, request):
        """Limit Pages to those that belong to the request's user."""
        qs = super(FeeAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            # It is mine, all mine. Just return everything.
            # TODO add permission for edu prog manager
            return qs
        return qs.filter(event__manager=request.user)

    def save_model(self, request, obj, form, change):
        # import ipdb; ipdb.set_trace()
        if getattr(obj, 'created_by', None) is None:
            obj.created_by_id = request.user.id
        obj.save()


class OptionInlineAdmin(admin.StackedInline):
    model = Option


class PaymentAdmin(admin.ModelAdmin, InstitutionAdminMixin):
    list_display = ("created", 'content_type', 'show_cause', "amount", 'frm', 'status')
    raw_id_fields = ("frm", )
    # readonly_fields = ("transaction_id", "token", 'content_type', 'object_id',)
    search_fields = ('frm__email', "token", 'billing_email', "billing_last_name" )
    date_herarchy = 'created'
    list_filter = ('status',)

    fieldsets = (
        (None, {
            'fields': (
                ("frm", "to"),
                'cause',
                ('content_type', 'object_id'),
                ("option", 'status'),
                ("amount", "currency"),
                ("created", "modified"),
                ("transaction_id", "token"),
            )
        }),
        ('customer', {
            'fields': (
                ("billing_first_name", "billing_last_name"),
                'billing_email',
                'document_id',
                'message',
            )
        }),
        ('billing adddress', {
            'fields': (
                ("billing_address_1", "billing_address_2"),
                ('billing_postcode', "billing_city"),
                ("billing_country_code", 'billing_country_area')
            )
        }),
        ('extra', {
            'fields': (
                'extra_data',
            )
        }),
    )

    def show_cause(self, obj):
        if hasattr(obj, 'cause'):
            return  format_html('<a href="{}">{}</a>', get_admin_url_4_model(obj.cause), obj.cause)
        else: 
            return ''
    show_cause.short_description = 'Cause'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("created", "modified", "frm", "to", "amount", "currency", 'content_type', 'object_id', 'cause')
        else:
            return ("created", "modified", 'cause')

    def save_model(self, request, obj, form, change):
        # import ipdb; ipdb.set_trace()
        if getattr(obj, 'created_by', None) is None:
            obj.created_by_id = request.user.id
            obj.date = timezone.now()
        obj.save()


class OptionAdmin(admin.ModelAdmin):
    list_display = ("institution", "provider", 'destination')


admin.site.register(Payment, PaymentAdmin)
admin.site.register(Option, OptionAdmin)
