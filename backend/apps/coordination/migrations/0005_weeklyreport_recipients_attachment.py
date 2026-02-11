# Generated manually on 2026-02-10

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('coordination', '0004_studentreport_report_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='weeklyreport',
            name='attachment',
            field=models.FileField(blank=True, help_text='Arquivo anexo ao relatório (máximo 2MB)', null=True, upload_to='weekly_reports/%Y/%m/', verbose_name='Anexo'),
        ),
        migrations.AddField(
            model_name='weeklyreport',
            name='recipients',
            field=models.ManyToManyField(help_text='Selecione pelo menos um coordenador', related_name='received_weekly_reports', to=settings.AUTH_USER_MODEL, verbose_name='Enviar para Coordenadores'),
        ),
    ]
