import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='isaactransaction',
            name='divergence_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Valor da divergência'),
        ),
        migrations.AddField(
            model_name='isaactransaction',
            name='divergence_notes',
            field=models.TextField(blank=True, verbose_name='Observações da divergência'),
        ),
        migrations.AddField(
            model_name='isaactransaction',
            name='reconciled_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Conciliado em'),
        ),
        migrations.AddField(
            model_name='isaactransaction',
            name='reconciliation_status',
            field=models.CharField(
                choices=[('PENDING', 'Pendente'), ('RECONCILED', 'Conciliado'), ('DIVERGENCE', 'Divergência')],
                default='PENDING',
                max_length=20,
                verbose_name='Status de conciliação',
            ),
        ),
        migrations.CreateModel(
            name='BankEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_date', models.DateField(verbose_name='Data da entrada')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Valor')),
                ('description', models.CharField(blank=True, max_length=255, verbose_name='Descrição')),
                ('reference', models.CharField(blank=True, max_length=100, verbose_name='Referência bancária')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('isaac_transaction', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='bank_entry',
                    to='finance.isaactransaction',
                    verbose_name='Transação Isaac vinculada',
                )),
            ],
            options={
                'verbose_name': 'Entrada bancária',
                'verbose_name_plural': 'Entradas bancárias',
                'ordering': ['-entry_date', '-id'],
            },
        ),
    ]
