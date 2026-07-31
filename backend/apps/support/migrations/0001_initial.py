import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SupportTicket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('occurred_date', models.DateField(verbose_name='Data da ocorrência')),
                ('occurred_time', models.TimeField(verbose_name='Hora da ocorrência')),
                ('description', models.TextField(verbose_name='Descrição')),
                ('attachment', models.FileField(blank=True, null=True, upload_to='support/tickets/%Y/%m/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png'])], verbose_name='Anexo')),
                ('status', models.CharField(choices=[('OPEN', 'Aberto'), ('IN_PROGRESS', 'Em atendimento'), ('RESOLVED', 'Resolvido'), ('CANCELLED', 'Cancelado')], default='OPEN', max_length=20, verbose_name='Status')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='support_tickets', to=settings.AUTH_USER_MODEL, verbose_name='Solicitante')),
            ],
            options={
                'verbose_name': 'Chamado de suporte',
                'verbose_name_plural': 'Chamados de suporte',
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='SupportTicketReply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(verbose_name='Mensagem')),
                ('is_internal', models.BooleanField(default=False, verbose_name='Nota interna (não visível ao solicitante)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='support_ticket_replies', to=settings.AUTH_USER_MODEL, verbose_name='Autor')),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='support.supportticket', verbose_name='Chamado')),
            ],
            options={
                'verbose_name': 'Resposta do chamado',
                'verbose_name_plural': 'Respostas do chamado',
                'ordering': ['created_at', 'id'],
            },
        ),
    ]
