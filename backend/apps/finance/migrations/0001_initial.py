import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CostCenter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nome')),
                ('code', models.CharField(max_length=20, unique=True, verbose_name='Código')),
                ('description', models.TextField(blank=True, verbose_name='Descrição')),
                ('is_active', models.BooleanField(default=True, verbose_name='Ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Centro de custo',
                'verbose_name_plural': 'Centros de custo',
                'ordering': ['name', 'code'],
            },
        ),
        migrations.CreateModel(
            name='FinancialCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nome')),
                ('code', models.CharField(max_length=20, unique=True, verbose_name='Código')),
                ('category_type', models.CharField(choices=[('INCOME', 'Receita'), ('EXPENSE', 'Despesa')], default='EXPENSE', max_length=10, verbose_name='Tipo')),
                ('is_active', models.BooleanField(default=True, verbose_name='Ativa')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='finance.financialcategory', verbose_name='Categoria pai')),
            ],
            options={
                'verbose_name': 'Categoria financeira',
                'verbose_name_plural': 'Categorias financeiras',
                'ordering': ['name', 'code'],
            },
        ),
        migrations.CreateModel(
            name='IsaacTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bruto', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Valor bruto')),
                ('descontos', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Descontos')),
                ('bolsas', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Bolsas')),
                ('taxas_isaac', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Taxas Isaac')),
                ('taxa_antecipacao', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Taxa de antecipação')),
                ('outros_abatimentos', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Outros abatimentos')),
                ('estornos', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Estornos')),
                ('ajustes', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Ajustes')),
                ('valor_liquido', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Valor líquido')),
                ('competence_date', models.DateField(verbose_name='Data de competência')),
                ('settlement_date', models.DateField(verbose_name='Data de liquidação')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Transação Isaac',
                'verbose_name_plural': 'Transações Isaac',
                'ordering': ['-competence_date', '-settlement_date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='AccountsPayable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('supplier', models.CharField(max_length=200, verbose_name='Fornecedor')),
                ('competence_date', models.DateField(verbose_name='Data de competência')),
                ('due_date', models.DateField(verbose_name='Data de vencimento')),
                ('approval_status', models.CharField(choices=[('PENDING', 'Pendente'), ('APPROVED', 'Aprovado'), ('REJECTED', 'Rejeitado')], default='PENDING', max_length=20, verbose_name='Status de aprovação')),
                ('is_recurring', models.BooleanField(default=False, verbose_name='Recorrente')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cost_center', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='accounts_payable', to='finance.costcenter', verbose_name='Centro de custo')),
            ],
            options={
                'verbose_name': 'Conta a pagar',
                'verbose_name_plural': 'Contas a pagar',
                'ordering': ['due_date', '-competence_date', '-id'],
            },
        ),
    ]
