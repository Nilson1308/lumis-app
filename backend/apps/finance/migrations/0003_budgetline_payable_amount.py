import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_bankentry_isaac_reconciliation'),
    ]

    operations = [
        migrations.AddField(
            model_name='accountspayable',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Valor'),
        ),
        migrations.AddField(
            model_name='accountspayable',
            name='category',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='accounts_payable',
                to='finance.financialcategory',
                verbose_name='Categoria financeira',
            ),
        ),
        migrations.CreateModel(
            name='BudgetLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('competence_date', models.DateField(verbose_name='Data de competência')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Valor orçado')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='budget_lines',
                    to='finance.financialcategory',
                    verbose_name='Categoria financeira',
                )),
                ('cost_center', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='budget_lines',
                    to='finance.costcenter',
                    verbose_name='Centro de custo',
                )),
            ],
            options={
                'verbose_name': 'Linha orçamentária',
                'verbose_name_plural': 'Linhas orçamentárias',
                'ordering': ['competence_date', 'category__name'],
            },
        ),
        migrations.AddConstraint(
            model_name='budgetline',
            constraint=models.UniqueConstraint(
                fields=('category', 'cost_center', 'competence_date'),
                name='finance_budgetline_unique_category_center_competence',
            ),
        ),
    ]
