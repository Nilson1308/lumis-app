# Generated manually - Contraturno models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0016_extraactivity_restructure'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContraturnoClassroom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contraturno_period', models.CharField(choices=[('MORNING', 'Manhã'), ('AFTERNOON', 'Tarde')], help_text='Período oposto ao período principal da turma', max_length=20, verbose_name='Período do Contraturno')),
                ('active', models.BooleanField(default=True, verbose_name='Ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contraturnos', to='academic.classroom', verbose_name='Turma Principal')),
                ('teacher', models.ForeignKey(help_text='Professor responsável pelo controle de frequência do contraturno', limit_choices_to={'groups__name': 'Professores'}, on_delete=django.db.models.deletion.CASCADE, related_name='contraturno_responsibilities', to=settings.AUTH_USER_MODEL, verbose_name='Professor Responsável')),
            ],
            options={
                'verbose_name': 'Contraturno de Turma',
                'verbose_name_plural': 'Contraturnos de Turmas',
                'ordering': ['classroom__name'],
                'unique_together': {('classroom', 'contraturno_period')},
            },
        ),
        migrations.CreateModel(
            name='ContraturnoAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Data')),
                ('present', models.BooleanField(default=True, verbose_name='Presente')),
                ('justified', models.BooleanField(default=False, verbose_name='Falta Justificada')),
                ('observation', models.TextField(blank=True, verbose_name='Observação')),
                ('enrollment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contraturno_attendances', to='academic.enrollment', verbose_name='Matrícula')),
            ],
            options={
                'verbose_name': 'Frequência do Contraturno',
                'verbose_name_plural': 'Frequências do Contraturno',
                'ordering': ['-date'],
                'unique_together': {('enrollment', 'date')},
            },
        ),
    ]
