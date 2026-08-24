from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.finance.models import (
    AccountsPayable,
    CostCenter,
    FinancialCategory,
    IsaacTransaction,
)


class Command(BaseCommand):
    help = 'Popula dados de teste do módulo financeiro sem alterar dados acadêmicos.'

    def handle(self, *args, **options):
        if IsaacTransaction.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    'Abortado: já existem registros financeiros (IsaacTransaction). '
                    'Nenhum dado foi criado para evitar duplicidade.'
                )
            )
            return

        self.stdout.write('Iniciando seed do módulo financeiro...')

        with transaction.atomic():
            cost_centers = self._seed_cost_centers()
            categories = self._seed_categories()
            isaac_count = self._seed_isaac_transactions()
            payables_count = self._seed_accounts_payable(cost_centers, categories)

        self.stdout.write(
            self.style.SUCCESS(
                f'Seed financeiro concluído: '
                f'{len(cost_centers)} centros de custo, '
                f'{len(categories)} categorias, '
                f'{isaac_count} repasses Isaac, '
                f'{payables_count} contas a pagar.'
            )
        )

    def _seed_cost_centers(self):
        specs = [
            {'code': 'INF', 'name': 'Ensino Infantil', 'description': 'Centro de custo — Educação Infantil'},
            {'code': 'FUND1', 'name': 'Fundamental I', 'description': 'Centro de custo — Ensino Fundamental I'},
            {'code': 'ADM', 'name': 'Administrativo', 'description': 'Centro de custo — Área administrativa'},
        ]
        created = {}
        for spec in specs:
            obj, was_created = CostCenter.objects.get_or_create(
                code=spec['code'],
                defaults={
                    'name': spec['name'],
                    'description': spec['description'],
                    'is_active': True,
                },
            )
            created[spec['code']] = obj
            action = 'criado' if was_created else 'já existia'
            self.stdout.write(f'  Centro de custo [{spec["code"]}]: {action}')
        return created

    def _seed_categories(self):
        specs = [
            {
                'code': 'ISAAC_REC',
                'name': 'Receita Isaac',
                'category_type': FinancialCategory.TYPE_INCOME,
            },
            {
                'code': 'TAXAS_FIN',
                'name': 'Taxas Financeiras',
                'category_type': FinancialCategory.TYPE_EXPENSE,
            },
            {
                'code': 'DESP_OP',
                'name': 'Despesas Operacionais',
                'category_type': FinancialCategory.TYPE_EXPENSE,
            },
        ]
        created = {}
        for spec in specs:
            obj, was_created = FinancialCategory.objects.get_or_create(
                code=spec['code'],
                defaults={
                    'name': spec['name'],
                    'category_type': spec['category_type'],
                    'is_active': True,
                },
            )
            created[spec['code']] = obj
            action = 'criada' if was_created else 'já existia'
            self.stdout.write(f'  Categoria [{spec["code"]}]: {action}')
        return created

    def _seed_isaac_transactions(self):
        transactions = [
            {
                'bruto': Decimal('42000.00'),
                'taxas_isaac': Decimal('3200.00'),
                'taxa_antecipacao': Decimal('0.00'),
                'valor_liquido': Decimal('38800.00'),
                'competence_date': date(2026, 8, 20),
                'settlement_date': date(2026, 8, 20),
                'reconciliation_status': IsaacTransaction.RECONCILIATION_PENDING,
                'divergence_amount': None,
                'divergence_notes': '',
            },
            {
                'bruto': Decimal('28000.00'),
                'taxas_isaac': Decimal('600.00'),
                'taxa_antecipacao': Decimal('1500.00'),
                'valor_liquido': Decimal('25900.00'),
                'competence_date': date(2026, 8, 25),
                'settlement_date': date(2026, 8, 25),
                'reconciliation_status': IsaacTransaction.RECONCILIATION_PENDING,
                'divergence_amount': None,
                'divergence_notes': '',
            },
            {
                'bruto': Decimal('35000.00'),
                'taxas_isaac': Decimal('2700.00'),
                'taxa_antecipacao': Decimal('0.00'),
                'valor_liquido': Decimal('32300.00'),
                'competence_date': date(2026, 8, 30),
                'settlement_date': date(2026, 8, 30),
                'reconciliation_status': IsaacTransaction.RECONCILIATION_DIVERGENCE,
                'divergence_amount': Decimal('500.00'),
                'divergence_notes': 'Valor creditado no banco difere do repasse Isaac esperado.',
            },
        ]

        for index, data in enumerate(transactions, start=1):
            IsaacTransaction.objects.create(**data)
            self.stdout.write(
                f'  Repasse Isaac #{index} ({data["settlement_date"]:%d/%m/%Y}): criado'
            )

        return len(transactions)

    def _seed_accounts_payable(self, cost_centers, categories):
        payables = [
            {
                'supplier': 'Conta de Luz',
                'cost_center': cost_centers['ADM'],
                'category': categories['DESP_OP'],
                'amount': Decimal('4500.00'),
                'competence_date': date(2026, 8, 1),
                'due_date': date(2026, 8, 15),
                'approval_status': AccountsPayable.APPROVAL_APPROVED,
                'is_recurring': True,
            },
            {
                'supplier': 'Material de Limpeza',
                'cost_center': cost_centers['INF'],
                'category': categories['DESP_OP'],
                'amount': Decimal('1200.00'),
                'competence_date': date(2026, 8, 1),
                'due_date': date(2026, 8, 20),
                'approval_status': AccountsPayable.APPROVAL_PENDING,
                'is_recurring': False,
            },
            {
                'supplier': 'Internet',
                'cost_center': cost_centers['FUND1'],
                'category': categories['DESP_OP'],
                'amount': Decimal('890.00'),
                'competence_date': date(2026, 9, 1),
                'due_date': date(2026, 9, 10),
                'approval_status': AccountsPayable.APPROVAL_APPROVED,
                'is_recurring': True,
            },
        ]

        created_count = 0
        for data in payables:
            _, was_created = AccountsPayable.objects.get_or_create(
                supplier=data['supplier'],
                due_date=data['due_date'],
                defaults=data,
            )
            if was_created:
                created_count += 1
                self.stdout.write(
                    f'  Conta a pagar [{data["supplier"]} — venc. {data["due_date"]:%d/%m/%Y}]: criada'
                )
            else:
                self.stdout.write(
                    f'  Conta a pagar [{data["supplier"]} — venc. {data["due_date"]:%d/%m/%Y}]: já existia'
                )

        return created_count
