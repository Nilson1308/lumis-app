from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from django.db.models import F, Sum
from django.utils import timezone

from .models import AccountsPayable, BankEntry, BudgetLine, FinancialCategory, IsaacTransaction

DEFAULT_RECONCILIATION_TOLERANCE = Decimal('0.01')


@dataclass
class ReconciliationMatch:
    isaac_transaction_id: int
    bank_entry_id: int
    expected_amount: Decimal
    bank_amount: Decimal
    settlement_date: str


@dataclass
class ReconciliationDivergence:
    isaac_transaction_id: int | None
    bank_entry_id: int | None
    expected_amount: Decimal | None
    bank_amount: Decimal | None
    divergence_amount: Decimal
    reason: str


@dataclass
class ReconciliationReport:
    reconciled: list[ReconciliationMatch] = field(default_factory=list)
    divergences: list[ReconciliationDivergence] = field(default_factory=list)
    unmatched_isaac_transactions: list[int] = field(default_factory=list)
    unmatched_bank_entries: list[int] = field(default_factory=list)


@dataclass
class CashIsolationLine:
    transaction_id: int
    competence_date: str
    settlement_date: str
    is_anticipation: bool
    operational_revenue: Decimal
    anticipation_cash_in: Decimal
    anticipation_fee: Decimal


@dataclass
class CashIsolationReport:
    receitas_normais: Decimal
    antecipacoes_entrada: Decimal
    taxas_antecipacao: Decimal
    saldo_projetado: Decimal
    despesas_consideradas: Decimal
    linhas: list[CashIsolationLine] = field(default_factory=list)


def _amounts_match(expected: Decimal, actual: Decimal, tolerance: Decimal) -> bool:
    return abs(expected - actual) <= tolerance


def _mark_reconciled(isaac_tx: IsaacTransaction, bank_entry: BankEntry) -> None:
    now = timezone.now()
    isaac_tx.reconciliation_status = IsaacTransaction.RECONCILIATION_RECONCILED
    isaac_tx.divergence_amount = None
    isaac_tx.divergence_notes = ''
    isaac_tx.reconciled_at = now
    isaac_tx.save(update_fields=[
        'reconciliation_status',
        'divergence_amount',
        'divergence_notes',
        'reconciled_at',
        'updated_at',
    ])
    bank_entry.isaac_transaction = isaac_tx
    bank_entry.save(update_fields=['isaac_transaction', 'updated_at'])


def _mark_divergence(
    isaac_tx: IsaacTransaction | None,
    *,
    bank_entry: BankEntry | None = None,
    expected_amount: Decimal | None = None,
    bank_amount: Decimal | None = None,
    reason: str,
) -> ReconciliationDivergence:
    divergence_amount = Decimal('0.00')
    if expected_amount is not None and bank_amount is not None:
        divergence_amount = bank_amount - expected_amount

    if isaac_tx is not None:
        isaac_tx.reconciliation_status = IsaacTransaction.RECONCILIATION_DIVERGENCE
        isaac_tx.divergence_amount = divergence_amount
        isaac_tx.divergence_notes = reason
        isaac_tx.reconciled_at = None
        isaac_tx.save(update_fields=[
            'reconciliation_status',
            'divergence_amount',
            'divergence_notes',
            'reconciled_at',
            'updated_at',
        ])

    return ReconciliationDivergence(
        isaac_transaction_id=isaac_tx.pk if isaac_tx else None,
        bank_entry_id=bank_entry.pk if bank_entry else None,
        expected_amount=expected_amount,
        bank_amount=bank_amount,
        divergence_amount=divergence_amount,
        reason=reason,
    )


@transaction.atomic
def reconcile_isaac_with_bank_entries(
    bank_entries: Iterable[BankEntry] | None = None,
    *,
    settlement_date_from=None,
    settlement_date_to=None,
    tolerance: Decimal = DEFAULT_RECONCILIATION_TOLERANCE,
) -> ReconciliationReport:
    """
    Confronta repasses Isaac com entradas bancárias reais.

    Critério de pareamento: mesma data (liquidação x entrada) e valor líquido
    dentro da tolerância. Atualiza status para 'Conciliado' ou registra divergência.
    """
    report = ReconciliationReport()

    isaac_qs = IsaacTransaction.objects.filter(
        reconciliation_status__in=[
            IsaacTransaction.RECONCILIATION_PENDING,
            IsaacTransaction.RECONCILIATION_DIVERGENCE,
        ]
    ).order_by('settlement_date', 'id')

    if settlement_date_from:
        isaac_qs = isaac_qs.filter(settlement_date__gte=settlement_date_from)
    if settlement_date_to:
        isaac_qs = isaac_qs.filter(settlement_date__lte=settlement_date_to)

    if bank_entries is None:
        bank_qs = BankEntry.objects.filter(isaac_transaction__isnull=True).order_by('entry_date', 'id')
    else:
        bank_qs = sorted(bank_entries, key=lambda entry: (entry.entry_date, entry.pk or 0))

    isaac_by_date: dict = {}
    for isaac_tx in isaac_qs:
        isaac_by_date.setdefault(isaac_tx.settlement_date, []).append(isaac_tx)

    used_isaac_ids: set[int] = set()

    for bank_entry in bank_qs:
        candidates = [
            tx for tx in isaac_by_date.get(bank_entry.entry_date, [])
            if tx.pk not in used_isaac_ids
        ]

        if not candidates:
            report.unmatched_bank_entries.append(bank_entry.pk)
            report.divergences.append(_mark_divergence(
                None,
                bank_entry=bank_entry,
                bank_amount=bank_entry.amount,
                reason='Entrada bancária sem repasse Isaac correspondente na mesma data.',
            ))
            continue

        matched_tx = None
        for candidate in candidates:
            if _amounts_match(candidate.valor_liquido, bank_entry.amount, tolerance):
                matched_tx = candidate
                break

        if matched_tx is None:
            closest = min(
                candidates,
                key=lambda tx: abs(tx.valor_liquido - bank_entry.amount),
            )
            used_isaac_ids.add(closest.pk)
            report.divergences.append(_mark_divergence(
                closest,
                bank_entry=bank_entry,
                expected_amount=closest.valor_liquido,
                bank_amount=bank_entry.amount,
                reason=(
                    'Valor da entrada bancária difere do repasse Isaac esperado '
                    f'(esperado R$ {closest.valor_liquido}, recebido R$ {bank_entry.amount}).'
                ),
            ))
            continue

        used_isaac_ids.add(matched_tx.pk)
        _mark_reconciled(matched_tx, bank_entry)
        report.reconciled.append(ReconciliationMatch(
            isaac_transaction_id=matched_tx.pk,
            bank_entry_id=bank_entry.pk,
            expected_amount=matched_tx.valor_liquido,
            bank_amount=bank_entry.amount,
            settlement_date=str(matched_tx.settlement_date),
        ))

    for isaac_tx in isaac_qs:
        if isaac_tx.pk in used_isaac_ids:
            continue
        report.unmatched_isaac_transactions.append(isaac_tx.pk)
        report.divergences.append(_mark_divergence(
            isaac_tx,
            expected_amount=isaac_tx.valor_liquido,
            reason='Repasse Isaac sem entrada bancária correspondente na data de liquidação.',
        ))

    return report


@dataclass
class CashFlowConsolidatedReport:
    saldo_bancario: Decimal
    previsoes_isaac_liquidas: Decimal
    contas_a_pagar: Decimal
    saldo_consolidado: Decimal
    antecipacoes_isoladas: Decimal
    taxas_antecipacao: Decimal
    reference_date: str


@dataclass
class DRECategoryLine:
    category_id: int
    category_code: str
    category_name: str
    category_type: str
    orcado: Decimal
    realizado: Decimal
    variacao: Decimal


@dataclass
class DREReport:
    competence_date_from: str
    competence_date_to: str
    lines: list[DRECategoryLine]
    receitas_orcado: Decimal
    receitas_realizado: Decimal
    despesas_orcado: Decimal
    despesas_realizado: Decimal
    resultado_orcado: Decimal
    resultado_realizado: Decimal


def _sum_decimal(values) -> Decimal:
    return values or Decimal('0.00')


def consolidate_cash_flow(*, reference_date=None) -> CashFlowConsolidatedReport:
    """
    Consolida saldo bancário, previsões líquidas Isaac pendentes e deduz contas a pagar.
    """
    ref = reference_date or timezone.localdate()

    saldo_bancario = _sum_decimal(
        BankEntry.objects.aggregate(total=Sum('amount'))['total']
    )

    previsoes_isaac_liquidas = _sum_decimal(
        IsaacTransaction.objects.filter(
            reconciliation_status__in=[
                IsaacTransaction.RECONCILIATION_PENDING,
                IsaacTransaction.RECONCILIATION_DIVERGENCE,
            ],
            settlement_date__gte=ref,
        ).aggregate(total=Sum('valor_liquido'))['total']
    )

    contas_a_pagar = _sum_decimal(
        AccountsPayable.objects.filter(
            approval_status__in=[
                AccountsPayable.APPROVAL_PENDING,
                AccountsPayable.APPROVAL_APPROVED,
            ],
            due_date__gte=ref,
        ).aggregate(total=Sum('amount'))['total']
    )

    isolation = isolate_cash_flow(
        competence_date_from=ref.replace(day=1),
        competence_date_to=ref,
        include_approved_payables=False,
    )

    saldo_consolidado = saldo_bancario + previsoes_isaac_liquidas - contas_a_pagar

    return CashFlowConsolidatedReport(
        saldo_bancario=saldo_bancario,
        previsoes_isaac_liquidas=previsoes_isaac_liquidas,
        contas_a_pagar=contas_a_pagar,
        saldo_consolidado=saldo_consolidado,
        antecipacoes_isoladas=isolation.antecipacoes_entrada,
        taxas_antecipacao=isolation.taxas_antecipacao,
        reference_date=str(ref),
    )


def build_dre_report(*, competence_date_from, competence_date_to) -> DREReport:
    """
    DRE Orçado vs. Realizado estritamente por competence_date.
    """
    budget_lines = (
        BudgetLine.objects.filter(
            competence_date__gte=competence_date_from,
            competence_date__lte=competence_date_to,
        )
        .select_related('category', 'cost_center')
        .order_by('category__category_type', 'category__name')
    )

    orcado_by_category: dict[int, Decimal] = {}
    category_meta: dict[int, FinancialCategory] = {}
    for line in budget_lines:
        orcado_by_category[line.category_id] = (
            orcado_by_category.get(line.category_id, Decimal('0.00')) + line.amount
        )
        category_meta[line.category_id] = line.category

    receitas_realizado_total = _sum_decimal(
        IsaacTransaction.objects.filter(
            competence_date__gte=competence_date_from,
            competence_date__lte=competence_date_to,
        ).aggregate(total=Sum(F('valor_liquido') + F('taxa_antecipacao')))['total']
    )

    despesas_realizado_by_category: dict[int, Decimal] = {}
    for payable in AccountsPayable.objects.filter(
        competence_date__gte=competence_date_from,
        competence_date__lte=competence_date_to,
        approval_status=AccountsPayable.APPROVAL_APPROVED,
        category_id__isnull=False,
    ):
        despesas_realizado_by_category[payable.category_id] = (
            despesas_realizado_by_category.get(payable.category_id, Decimal('0.00'))
            + payable.amount
        )

    income_orcado_total = Decimal('0.00')
    for category_id, orcado in orcado_by_category.items():
        if category_meta[category_id].category_type == FinancialCategory.TYPE_INCOME:
            income_orcado_total += orcado

    lines: list[DRECategoryLine] = []
    receitas_orcado = Decimal('0.00')
    despesas_orcado = Decimal('0.00')
    receitas_realizado = Decimal('0.00')
    despesas_realizado = Decimal('0.00')

    for category_id, orcado in sorted(
        orcado_by_category.items(),
        key=lambda item: (category_meta[item[0]].category_type, category_meta[item[0]].name),
    ):
        category = category_meta[category_id]
        if category.category_type == FinancialCategory.TYPE_INCOME:
            if income_orcado_total > 0:
                realizado = (
                    receitas_realizado_total * orcado / income_orcado_total
                ).quantize(Decimal('0.01'))
            else:
                realizado = Decimal('0.00')
            receitas_orcado += orcado
            receitas_realizado += realizado
        else:
            realizado = despesas_realizado_by_category.get(category_id, Decimal('0.00'))
            despesas_orcado += orcado
            despesas_realizado += realizado

        lines.append(DRECategoryLine(
            category_id=category_id,
            category_code=category.code,
            category_name=category.name,
            category_type=category.category_type,
            orcado=orcado,
            realizado=realizado,
            variacao=realizado - orcado,
        ))

    return DREReport(
        competence_date_from=str(competence_date_from),
        competence_date_to=str(competence_date_to),
        lines=lines,
        receitas_orcado=receitas_orcado,
        receitas_realizado=receitas_realizado,
        despesas_orcado=despesas_orcado,
        despesas_realizado=despesas_realizado,
        resultado_orcado=receitas_orcado - despesas_orcado,
        resultado_realizado=receitas_realizado - despesas_realizado,
    )


def isolate_cash_flow(
    *,
    competence_date_from=None,
    competence_date_to=None,
    include_approved_payables: bool = True,
) -> CashIsolationReport:
    """
    Isola contabilmente antecipações das receitas normais.

    Receitas normais usam a receita operacional equivalente (valor_liquido + taxa_antecipacao).
    Entradas antecipadas e taxas ficam em buckets separados para não distorcer
    o saldo projetado com efeito de timing de caixa.
    """
    tx_qs = IsaacTransaction.objects.all().order_by('competence_date', 'id')
    if competence_date_from:
        tx_qs = tx_qs.filter(competence_date__gte=competence_date_from)
    if competence_date_to:
        tx_qs = tx_qs.filter(competence_date__lte=competence_date_to)

    receitas_normais = Decimal('0.00')
    antecipacoes_entrada = Decimal('0.00')
    taxas_antecipacao = Decimal('0.00')
    linhas: list[CashIsolationLine] = []

    for isaac_tx in tx_qs:
        operational = isaac_tx.operational_revenue
        receitas_normais += operational

        anticipation_cash_in = Decimal('0.00')
        anticipation_fee = Decimal('0.00')
        if isaac_tx.is_anticipation:
            anticipation_cash_in = isaac_tx.valor_liquido
            anticipation_fee = isaac_tx.taxa_antecipacao
            antecipacoes_entrada += anticipation_cash_in
            taxas_antecipacao += anticipation_fee

        linhas.append(CashIsolationLine(
            transaction_id=isaac_tx.pk,
            competence_date=str(isaac_tx.competence_date),
            settlement_date=str(isaac_tx.settlement_date),
            is_anticipation=isaac_tx.is_anticipation,
            operational_revenue=operational,
            anticipation_cash_in=anticipation_cash_in,
            anticipation_fee=anticipation_fee,
        ))

    despesas_consideradas = Decimal('0.00')
    if include_approved_payables:
        payables_qs = AccountsPayable.objects.filter(
            approval_status=AccountsPayable.APPROVAL_APPROVED,
        )
        if competence_date_from:
            payables_qs = payables_qs.filter(competence_date__gte=competence_date_from)
        if competence_date_to:
            payables_qs = payables_qs.filter(competence_date__lte=competence_date_to)
        despesas_consideradas = _sum_decimal(
            payables_qs.aggregate(total=Sum('amount'))['total']
        )

    # Saldo projetado: receita operacional recorrente menos despesas,
    # sem somar novamente o caixa antecipado (evita dupla contagem de timing).
    saldo_projetado = receitas_normais - despesas_consideradas - taxas_antecipacao

    return CashIsolationReport(
        receitas_normais=receitas_normais,
        antecipacoes_entrada=antecipacoes_entrada,
        taxas_antecipacao=taxas_antecipacao,
        saldo_projetado=saldo_projetado,
        despesas_consideradas=despesas_consideradas,
        linhas=linhas,
    )
