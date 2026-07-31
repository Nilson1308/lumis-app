import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('academic', '0021_lessonplansubmissionblock'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SharedDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Título')),
                ('description', models.TextField(blank=True, verbose_name='Descrição')),
                ('category', models.CharField(
                    choices=[
                        ('GENERAL', 'Geral'),
                        ('PEDAGOGICAL', 'Pedagógico'),
                        ('ADMINISTRATIVE', 'Administrativo'),
                        ('FINANCIAL', 'Financeiro'),
                        ('EVENTS', 'Eventos'),
                    ],
                    default='GENERAL',
                    max_length=20,
                    verbose_name='Categoria',
                )),
                ('target_audience', models.CharField(
                    choices=[
                        ('ALL', 'Todos (professores e responsáveis)'),
                        ('TEACHERS', 'Professores'),
                        ('GUARDIANS', 'Responsáveis / Pais'),
                        ('CLASSROOM', 'Turma específica'),
                    ],
                    default='ALL',
                    max_length=20,
                    verbose_name='Público-alvo',
                )),
                ('file', models.FileField(
                    blank=True,
                    null=True,
                    upload_to='documents/%Y/%m/',
                    validators=[django.core.validators.FileExtensionValidator(
                        allowed_extensions=[
                            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                            'jpg', 'jpeg', 'png', 'zip',
                        ],
                    )],
                    verbose_name='Arquivo',
                )),
                ('external_link', models.URLField(blank=True, verbose_name='Link externo')),
                ('is_active', models.BooleanField(default=True, verbose_name='Ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('classroom', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='shared_documents',
                    to='academic.classroom',
                    verbose_name='Turma',
                )),
                ('uploaded_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='uploaded_documents',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Enviado por',
                )),
            ],
            options={
                'verbose_name': 'Documento compartilhado',
                'verbose_name_plural': 'Documentos compartilhados',
                'ordering': ['-created_at', '-id'],
            },
        ),
    ]
