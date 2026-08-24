from django.db import models


class CostCenter(models.Model):
    name = models.CharField('Nome', max_length=100)
    code = models.CharField('Código', max_length=20, unique=True)
    description = models.TextField('Descrição', blank=True)
    is_active = models.BooleanField('Ativo', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'code']
        verbose_name = 'Centro de custo'
        verbose_name_plural = 'Centros de custo'

    def __str__(self):
        return f'{self.code} — {self.name}'


class FinancialCategory(models.Model):
    TYPE_INCOME = 'INCOME'
    TYPE_EXPENSE = 'EXPENSE'

    TYPE_CHOICES = [
        (TYPE_INCOME, 'Receita'),
        (TYPE_EXPENSE, 'Despesa'),
    ]

    name = models.CharField('Nome', max_length=100)
    code = models.CharField('Código', max_length=20, unique=True)
    category_type = models.CharField(
        'Tipo',
        max_length=10,
        choices=TYPE_CHOICES,
        default=TYPE_EXPENSE,
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Categoria pai',
    )
    is_active = models.BooleanField('Ativa', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'code']
        verbose_name = 'Categoria financeira'
        verbose_name_plural = 'Categorias financeiras'

    def __str__(self):
        return f'{self.code} — {self.name}'


class IsaacTransaction(models.Model):
    RECONCILIATION_PENDING = 'PENDING'
    RECONCILIATION_RECONCILED = 'RECONCILED'
    RECONCILIATION_DIVERGENCE = 'DIVERGENCE'

    RECONCILIATION_STATUS_CHOICES = [
        (RECONCILIATION_PENDING, 'Pendente'),
        (RECONCILIATION_RECONCILED, 'Conciliado'),
        (RECONCILIATION_DIVERGENCE, 'Divergência'),
    ]

    bruto = models.DecimalField('Valor bruto', max_digits=12, decimal_places=2, default=0)
    descontos = models.DecimalField('Descontos', max_digits=12, decimal_places=2, default=0)
    bolsas = models.DecimalField('Bolsas', max_digits=12, decimal_places=2, default=0)
    taxas_isaac = models.DecimalField('Taxas Isaac', max_digits=12, decimal_places=2, default=0)
    taxa_antecipacao = models.DecimalField(
        'Taxa de antecipação',
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    outros_abatimentos = models.DecimalField(
        'Outros abatimentos',
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    estornos = models.DecimalField('Estornos', max_digits=12, decimal_places=2, default=0)
    ajustes = models.DecimalField('Ajustes', max_digits=12, decimal_places=2, default=0)
    valor_liquido = models.DecimalField('Valor líquido', max_digits=12, decimal_places=2, default=0)
    competence_date = models.DateField('Data de competência')
    settlement_date = models.DateField('Data de liquidação')
    reconciliation_status = models.CharField(
        'Status de conciliação',
        max_length=20,
        choices=RECONCILIATION_STATUS_CHOICES,
        default=RECONCILIATION_PENDING,
    )
    divergence_amount = models.DecimalField(
        'Valor da divergência',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    divergence_notes = models.TextField('Observações da divergência', blank=True)
    reconciled_at = models.DateTimeField('Conciliado em', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-competence_date', '-settlement_date', '-id']
        verbose_name = 'Transação Isaac'
        verbose_name_plural = 'Transações Isaac'

    def __str__(self):
        return f'Isaac #{self.pk} — {self.competence_date:%d/%m/%Y} — R$ {self.valor_liquido}'

    @property
    def is_anticipation(self):
        return self.taxa_antecipacao > 0

    @property
    def operational_revenue(self):
        """Receita operacional equivalente, antes do custo de antecipação."""
        return self.valor_liquido + self.taxa_antecipacao


class BankEntry(models.Model):
    entry_date = models.DateField('Data da entrada')
    amount = models.DecimalField('Valor', max_digits=12, decimal_places=2)
    description = models.CharField('Descrição', max_length=255, blank=True)
    reference = models.CharField('Referência bancária', max_length=100, blank=True)
    isaac_transaction = models.OneToOneField(
        IsaacTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bank_entry',
        verbose_name='Transação Isaac vinculada',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-entry_date', '-id']
        verbose_name = 'Entrada bancária'
        verbose_name_plural = 'Entradas bancárias'

    def __str__(self):
        return f'Entrada {self.entry_date:%d/%m/%Y} — R$ {self.amount}'


class AccountsPayable(models.Model):
    APPROVAL_PENDING = 'PENDING'
    APPROVAL_APPROVED = 'APPROVED'
    APPROVAL_REJECTED = 'REJECTED'

    APPROVAL_STATUS_CHOICES = [
        (APPROVAL_PENDING, 'Pendente'),
        (APPROVAL_APPROVED, 'Aprovado'),
        (APPROVAL_REJECTED, 'Rejeitado'),
    ]

    supplier = models.CharField('Fornecedor', max_length=200)
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.PROTECT,
        related_name='accounts_payable',
        verbose_name='Centro de custo',
    )
    competence_date = models.DateField('Data de competência')
    due_date = models.DateField('Data de vencimento')
    approval_status = models.CharField(
        'Status de aprovação',
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default=APPROVAL_PENDING,
    )
    is_recurring = models.BooleanField('Recorrente', default=False)
    amount = models.DecimalField('Valor', max_digits=12, decimal_places=2, default=0)
    category = models.ForeignKey(
        FinancialCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='accounts_payable',
        verbose_name='Categoria financeira',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', '-competence_date', '-id']
        verbose_name = 'Conta a pagar'
        verbose_name_plural = 'Contas a pagar'

    def __str__(self):
        return f'{self.supplier} — venc. {self.due_date:%d/%m/%Y} ({self.get_approval_status_display()})'


class BudgetLine(models.Model):
    category = models.ForeignKey(
        FinancialCategory,
        on_delete=models.PROTECT,
        related_name='budget_lines',
        verbose_name='Categoria financeira',
    )
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='budget_lines',
        verbose_name='Centro de custo',
    )
    competence_date = models.DateField('Data de competência')
    amount = models.DecimalField('Valor orçado', max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['competence_date', 'category__name']
        verbose_name = 'Linha orçamentária'
        verbose_name_plural = 'Linhas orçamentárias'
        constraints = [
            models.UniqueConstraint(
                fields=['category', 'cost_center', 'competence_date'],
                name='finance_budgetline_unique_category_center_competence',
            ),
        ]

    def __str__(self):
        return f'{self.category.code} — {self.competence_date:%m/%Y} — R$ {self.amount}'
