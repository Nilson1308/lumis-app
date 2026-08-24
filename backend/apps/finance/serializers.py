from rest_framework import serializers

from .models import AccountsPayable, CostCenter, FinancialCategory, IsaacTransaction


def _decimal_field():
    return serializers.DecimalField(max_digits=12, decimal_places=2)


class CostCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCenter
        fields = [
            'id',
            'name',
            'code',
            'description',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        cleaned = (value or '').strip()
        if not cleaned:
            raise serializers.ValidationError('Informe o nome do centro de custo.')
        return cleaned

    def validate_code(self, value):
        cleaned = (value or '').strip().upper()
        if not cleaned:
            raise serializers.ValidationError('Informe o código do centro de custo.')
        return cleaned


class FinancialCategorySerializer(serializers.ModelSerializer):
    category_type_label = serializers.CharField(source='get_category_type_display', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)

    class Meta:
        model = FinancialCategory
        fields = [
            'id',
            'name',
            'code',
            'category_type',
            'category_type_label',
            'parent',
            'parent_name',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'category_type_label', 'parent_name', 'created_at', 'updated_at']

    def validate_name(self, value):
        cleaned = (value or '').strip()
        if not cleaned:
            raise serializers.ValidationError('Informe o nome da categoria.')
        return cleaned

    def validate_code(self, value):
        cleaned = (value or '').strip().upper()
        if not cleaned:
            raise serializers.ValidationError('Informe o código da categoria.')
        return cleaned

    def validate(self, attrs):
        parent = attrs.get('parent', getattr(self.instance, 'parent', None))
        if self.instance and parent and parent.pk == self.instance.pk:
            raise serializers.ValidationError({'parent': 'A categoria não pode ser pai dela mesma.'})
        return attrs


class IsaacTransactionSerializer(serializers.ModelSerializer):
    reconciliation_status_label = serializers.CharField(
        source='get_reconciliation_status_display',
        read_only=True,
    )
    operational_revenue = serializers.SerializerMethodField()

    class Meta:
        model = IsaacTransaction
        fields = [
            'id',
            'bruto',
            'descontos',
            'bolsas',
            'taxas_isaac',
            'taxa_antecipacao',
            'outros_abatimentos',
            'estornos',
            'ajustes',
            'valor_liquido',
            'competence_date',
            'settlement_date',
            'reconciliation_status',
            'reconciliation_status_label',
            'divergence_amount',
            'divergence_notes',
            'reconciled_at',
            'operational_revenue',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'reconciliation_status_label',
            'operational_revenue',
            'reconciled_at',
            'created_at',
            'updated_at',
        ]

    def get_operational_revenue(self, obj):
        return obj.operational_revenue


class AccountsPayableSerializer(serializers.ModelSerializer):
    approval_status_label = serializers.CharField(source='get_approval_status_display', read_only=True)
    cost_center_name = serializers.CharField(source='cost_center.name', read_only=True)
    cost_center_code = serializers.CharField(source='cost_center.code', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)

    class Meta:
        model = AccountsPayable
        fields = [
            'id',
            'supplier',
            'cost_center',
            'cost_center_name',
            'cost_center_code',
            'category',
            'category_name',
            'amount',
            'competence_date',
            'due_date',
            'approval_status',
            'approval_status_label',
            'is_recurring',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'cost_center_name',
            'cost_center_code',
            'category_name',
            'approval_status_label',
            'created_at',
            'updated_at',
        ]

    def validate_supplier(self, value):
        cleaned = (value or '').strip()
        if not cleaned:
            raise serializers.ValidationError('Informe o fornecedor.')
        return cleaned

    def validate(self, attrs):
        competence_date = attrs.get(
            'competence_date',
            getattr(self.instance, 'competence_date', None),
        )
        due_date = attrs.get(
            'due_date',
            getattr(self.instance, 'due_date', None),
        )
        if competence_date and due_date and due_date < competence_date:
            raise serializers.ValidationError({
                'due_date': 'A data de vencimento deve ser igual ou posterior à data de competência.',
            })
        return attrs


class CashFlowQuerySerializer(serializers.Serializer):
    reference_date = serializers.DateField(required=False)


class CashFlowReportSerializer(serializers.Serializer):
    reference_date = serializers.DateField()
    saldo_bancario = _decimal_field()
    previsoes_isaac_liquidas = _decimal_field()
    contas_a_pagar = _decimal_field()
    saldo_consolidado = _decimal_field()
    antecipacoes_isoladas = _decimal_field()
    taxas_antecipacao = _decimal_field()


class DREReportQuerySerializer(serializers.Serializer):
    competence_date_from = serializers.DateField(required=True)
    competence_date_to = serializers.DateField(required=True)

    def validate(self, attrs):
        if attrs['competence_date_to'] < attrs['competence_date_from']:
            raise serializers.ValidationError({
                'competence_date_to': 'Deve ser igual ou posterior à data inicial de competência.',
            })
        return attrs


class DRECategoryLineSerializer(serializers.Serializer):
    category_id = serializers.IntegerField()
    category_code = serializers.CharField()
    category_name = serializers.CharField()
    category_type = serializers.CharField()
    orcado = _decimal_field()
    realizado = _decimal_field()
    variacao = _decimal_field()


class DREReportTotalsSerializer(serializers.Serializer):
    receitas_orcado = _decimal_field()
    receitas_realizado = _decimal_field()
    despesas_orcado = _decimal_field()
    despesas_realizado = _decimal_field()
    resultado_orcado = _decimal_field()
    resultado_realizado = _decimal_field()


class DREReportSerializer(serializers.Serializer):
    competence_date_from = serializers.DateField()
    competence_date_to = serializers.DateField()
    lines = DRECategoryLineSerializer(many=True)
    totals = DREReportTotalsSerializer()
