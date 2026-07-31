from django.contrib import admin
from django.utils.html import format_html

from .models import SupportTicket, SupportTicketReply


class SupportTicketReplyInline(admin.TabularInline):
    model = SupportTicketReply
    extra = 1
    fields = ('author', 'message', 'is_internal', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'requester',
        'occurred_date',
        'occurred_time',
        'status',
        'has_attachment_display',
        'created_at',
    )
    list_filter = ('status', 'occurred_date', 'created_at')
    search_fields = (
        'description',
        'requester__username',
        'requester__first_name',
        'requester__last_name',
    )
    readonly_fields = ('requester', 'created_at', 'updated_at')
    inlines = [SupportTicketReplyInline]
    fieldsets = (
        (None, {
            'fields': (
                'requester',
                'status',
                ('occurred_date', 'occurred_time'),
                'description',
                'attachment',
            ),
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @admin.display(boolean=True, description='Anexo')
    def has_attachment_display(self, obj):
        return bool(obj.attachment)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        ticket = form.instance
        for instance in instances:
            if isinstance(instance, SupportTicketReply):
                if not instance.author_id:
                    instance.author = request.user
                instance.ticket = ticket
                instance.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()
        if (
            ticket.pk
            and ticket.status == SupportTicket.STATUS_OPEN
            and ticket.replies.filter(is_internal=False).exists()
        ):
            SupportTicket.objects.filter(pk=ticket.pk).update(
                status=SupportTicket.STATUS_IN_PROGRESS
            )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.requester = request.user
        super().save_model(request, obj, form, change)


@admin.register(SupportTicketReply)
class SupportTicketReplyAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'author', 'is_internal', 'created_at', 'preview')
    list_filter = ('is_internal', 'created_at')
    search_fields = ('message', 'ticket__id', 'author__username')
    readonly_fields = ('created_at',)

    @admin.display(description='Mensagem')
    def preview(self, obj):
        text = obj.message[:80] + ('…' if len(obj.message) > 80 else '')
        return format_html('<span>{}</span>', text)

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)
        ticket = obj.ticket
        if not obj.is_internal and ticket.status == SupportTicket.STATUS_OPEN:
            ticket.status = SupportTicket.STATUS_IN_PROGRESS
            ticket.save(update_fields=['status', 'updated_at'])
