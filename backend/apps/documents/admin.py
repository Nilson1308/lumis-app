from django.contrib import admin

from .models import SharedDocument, SharedDocumentReadStatus


class SharedDocumentReadStatusInline(admin.TabularInline):
    model = SharedDocumentReadStatus
    extra = 0
    readonly_fields = ('user', 'read_at')


@admin.register(SharedDocument)
class SharedDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'target_audience', 'classroom', 'segment', 'is_active', 'created_at')
    list_filter = ('category', 'target_audience', 'is_active', 'segment')
    search_fields = ('title', 'description')
    readonly_fields = ('uploaded_by', 'created_at', 'updated_at')
    inlines = [SharedDocumentReadStatusInline]
