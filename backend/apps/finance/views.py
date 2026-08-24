from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AccountsPayable, CostCenter, FinancialCategory, IsaacTransaction
from .permissions import IsFinanceUser
from .serializers import (
    AccountsPayableSerializer,
    CashFlowQuerySerializer,
    CashFlowReportSerializer,
    CostCenterSerializer,
    DREReportQuerySerializer,
    DREReportSerializer,
    FinancialCategorySerializer,
    IsaacTransactionSerializer,
)
from .services import build_dre_report, consolidate_cash_flow


class CostCenterViewSet(viewsets.ModelViewSet):
    queryset = CostCenter.objects.all()
    serializer_class = CostCenterSerializer
    permission_classes = [IsFinanceUser]
    filterset_fields = ['is_active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at', 'updated_at']


class FinancialCategoryViewSet(viewsets.ModelViewSet):
    queryset = FinancialCategory.objects.select_related('parent')
    serializer_class = FinancialCategorySerializer
    permission_classes = [IsFinanceUser]
    filterset_fields = ['category_type', 'is_active', 'parent']
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'code', 'created_at', 'updated_at']


class IsaacTransactionViewSet(viewsets.ModelViewSet):
    queryset = IsaacTransaction.objects.all()
    serializer_class = IsaacTransactionSerializer
    permission_classes = [IsFinanceUser]
    filterset_fields = ['competence_date', 'settlement_date', 'reconciliation_status']
    ordering_fields = ['competence_date', 'settlement_date', 'valor_liquido', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        competence_from = params.get('competence_from')
        competence_to = params.get('competence_to')
        settlement_from = params.get('settlement_from')
        settlement_to = params.get('settlement_to')

        if competence_from:
            queryset = queryset.filter(competence_date__gte=competence_from)
        if competence_to:
            queryset = queryset.filter(competence_date__lte=competence_to)
        if settlement_from:
            queryset = queryset.filter(settlement_date__gte=settlement_from)
        if settlement_to:
            queryset = queryset.filter(settlement_date__lte=settlement_to)
        return queryset


class AccountsPayableViewSet(viewsets.ModelViewSet):
    queryset = AccountsPayable.objects.select_related('cost_center', 'category')
    serializer_class = AccountsPayableSerializer
    permission_classes = [IsFinanceUser]
    filterset_fields = ['approval_status', 'is_recurring', 'cost_center', 'category']
    search_fields = ['supplier', 'cost_center__name', 'cost_center__code']
    ordering_fields = ['due_date', 'competence_date', 'amount', 'created_at', 'updated_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        approval_status = (params.get('approval_status') or '').strip()
        is_recurring = params.get('is_recurring')
        due_from = params.get('due_from')
        due_to = params.get('due_to')
        search = (params.get('search') or '').strip()

        if approval_status:
            queryset = queryset.filter(approval_status=approval_status)
        if is_recurring in ('true', 'false'):
            queryset = queryset.filter(is_recurring=(is_recurring == 'true'))
        if due_from:
            queryset = queryset.filter(due_date__gte=due_from)
        if due_to:
            queryset = queryset.filter(due_date__lte=due_to)
        if search:
            queryset = queryset.filter(
                Q(supplier__icontains=search)
                | Q(cost_center__name__icontains=search)
                | Q(cost_center__code__icontains=search)
            )
        return queryset


class FinanceReportViewSet(viewsets.ViewSet):
    permission_classes = [IsFinanceUser]

    @action(detail=False, methods=['get'], url_path='cash-flow')
    def cash_flow(self, request):
        query = CashFlowQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        report = consolidate_cash_flow(
            reference_date=query.validated_data.get('reference_date'),
        )
        payload = {
            'reference_date': report.reference_date,
            'saldo_bancario': report.saldo_bancario,
            'previsoes_isaac_liquidas': report.previsoes_isaac_liquidas,
            'contas_a_pagar': report.contas_a_pagar,
            'saldo_consolidado': report.saldo_consolidado,
            'antecipacoes_isoladas': report.antecipacoes_isoladas,
            'taxas_antecipacao': report.taxas_antecipacao,
        }
        return Response(CashFlowReportSerializer(payload).data)

    @action(detail=False, methods=['get'], url_path='dre-report')
    def dre_report(self, request):
        query = DREReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        report = build_dre_report(
            competence_date_from=query.validated_data['competence_date_from'],
            competence_date_to=query.validated_data['competence_date_to'],
        )
        payload = {
            'competence_date_from': report.competence_date_from,
            'competence_date_to': report.competence_date_to,
            'lines': [
                {
                    'category_id': line.category_id,
                    'category_code': line.category_code,
                    'category_name': line.category_name,
                    'category_type': line.category_type,
                    'orcado': line.orcado,
                    'realizado': line.realizado,
                    'variacao': line.variacao,
                }
                for line in report.lines
            ],
            'totals': {
                'receitas_orcado': report.receitas_orcado,
                'receitas_realizado': report.receitas_realizado,
                'despesas_orcado': report.despesas_orcado,
                'despesas_realizado': report.despesas_realizado,
                'resultado_orcado': report.resultado_orcado,
                'resultado_realizado': report.resultado_realizado,
            },
        }
        return Response(DREReportSerializer(payload).data, status=status.HTTP_200_OK)
