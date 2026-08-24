from django.contrib import admin

from .models import AccountsPayable, BankEntry, CostCenter, FinancialCategory, IsaacTransaction


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FinancialCategory)
class FinancialCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category_type', 'parent', 'is_active', 'updated_at')
    list_filter = ('category_type', 'is_active')
    search_fields = ('code', 'name')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('parent',)


@admin.register(IsaacTransaction)
class IsaacTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'competence_date',
        'settlement_date',
        'bruto',
        'valor_liquido',
        'reconciliation_status',
        'updated_at',
    )
    list_filter = ('competence_date', 'settlement_date', 'reconciliation_status')
    search_fields = ('id',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'competence_date'
    fieldsets = (
        ('Datas', {
            'fields': ('competence_date', 'settlement_date'),
        }),
        ('Valores', {
            'fields': (
                'bruto',
                'descontos',
                'bolsas',
                'taxas_isaac',
                'taxa_antecipacao',
                'outros_abatimentos',
                'estornos',
                'ajustes',
                'valor_liquido',
            ),
        }),
        ('Conciliação', {
            'fields': (
                'reconciliation_status',
                'divergence_amount',
                'divergence_notes',
                'reconciled_at',
            ),
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


@admin.register(AccountsPayable)
class AccountsPayableAdmin(admin.ModelAdmin):
    list_display = (
        'supplier',
        'cost_center',
        'competence_date',
        'due_date',
        'approval_status',
        'is_recurring',
        'updated_at',
    )
    list_filter = ('approval_status', 'is_recurring', 'due_date', 'competence_date')
    search_fields = ('supplier', 'cost_center__name', 'cost_center__code')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('cost_center',)
    date_hierarchy = 'due_date'


@admin.register(BankEntry)
class BankEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_date', 'amount', 'description', 'reference', 'isaac_transaction', 'updated_at')
    list_filter = ('entry_date',)
    search_fields = ('description', 'reference')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('isaac_transaction',)
    date_hierarchy = 'entry_date'
