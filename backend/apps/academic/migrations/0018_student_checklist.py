# Generated manually - Student Checklist models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0017_contraturno_models'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentChecklistConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requires_checklist', models.BooleanField(default=False, verbose_name='Requer Checklist Diário?')),
                ('requires_lunch', models.BooleanField(default=False, verbose_name='Requer Almoço?')),
                ('requires_snack', models.BooleanField(default=False, verbose_name='Requer Lanche?')),
                ('requires_checkin', models.BooleanField(default=False, verbose_name='Requer Check-in (Entrada)?')),
                ('requires_checkout', models.BooleanField(default=False, verbose_name='Requer Check-out (Saída)?')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('segment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='checklist_config', to='academic.segment', verbose_name='Segmento')),
            ],
            options={
                'verbose_name': 'Configuração de Checklist',
                'verbose_name_plural': 'Configurações de Checklist',
            },
        ),
        migrations.CreateModel(
            name='StudentDailyChecklist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Data')),
                ('had_lunch', models.BooleanField(blank=True, default=False, null=True, verbose_name='Comeu Almoço?')),
                ('had_snack', models.BooleanField(blank=True, default=False, null=True, verbose_name='Comeu Lanche?')),
                ('checkin_time', models.TimeField(blank=True, null=True, verbose_name='Hora de Entrada')),
                ('checkout_time', models.TimeField(blank=True, null=True, verbose_name='Hora de Saída')),
                ('observation', models.TextField(blank=True, verbose_name='Observação')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('enrollment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_checklists', to='academic.enrollment', verbose_name='Matrícula')),
                ('registered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registered_checklists', to=settings.AUTH_USER_MODEL, verbose_name='Registrado por')),
            ],
            options={
                'verbose_name': 'Checklist Diário',
                'verbose_name_plural': 'Checklists Diários',
                'ordering': ['-date'],
                'unique_together': {('enrollment', 'date')},
            },
        ),
    ]
