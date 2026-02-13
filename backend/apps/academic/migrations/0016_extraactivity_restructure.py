# Atividades extracurriculares: activity_type, matrícula e presença

from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def migrate_extra_activities_to_enrollments(apps, schema_editor):
    """Migra dados do ManyToMany extra_activities para ExtraActivityEnrollment."""
    Student = apps.get_model('academic', 'Student')
    ExtraActivityEnrollment = apps.get_model('academic', 'ExtraActivityEnrollment')

    today = timezone.now().date()
    for student in Student.objects.all():
        # O campo extra_activities existe na versão antiga do modelo durante a migração
        for activity in student.extra_activities.all():
            ExtraActivityEnrollment.objects.get_or_create(
                student=student,
                activity=activity,
                defaults={'start_date': today, 'active': True}
            )


def reverse_migrate(apps, schema_editor):
    """Reversão: não recriamos o ManyToMany com os dados (perda de end_date)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0015_student_ra'),
    ]

    operations = [
        # 1. Adiciona activity_type em ExtraActivity
        migrations.AddField(
            model_name='extraactivity',
            name='activity_type',
            field=models.CharField(
                choices=[('INCLUDED', 'Incluída no Período Integral'), ('PAID', 'Atividade Paga')],
                default='PAID',
                help_text='INCLUDED = incluída no pacote integral | PAID = cobrança separada',
                max_length=20,
                verbose_name='Tipo'
            ),
        ),
        # 2. Cria ExtraActivityEnrollment
        migrations.CreateModel(
            name='ExtraActivityEnrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(verbose_name='Data de Início da Matrícula')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='Data de Término')),
                ('active', models.BooleanField(default=True, verbose_name='Ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrollments', to='academic.extraactivity', verbose_name='Atividade')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='extra_activity_enrollments', to='academic.student', verbose_name='Aluno')),
            ],
            options={
                'verbose_name': 'Matrícula em Atividade Extra',
                'verbose_name_plural': 'Matrículas em Atividades Extras',
                'ordering': ['-start_date'],
                'unique_together': {('student', 'activity')},
            },
        ),
        # 3. Cria ExtraActivityAttendance
        migrations.CreateModel(
            name='ExtraActivityAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Data')),
                ('present', models.BooleanField(default=True, verbose_name='Presente')),
                ('observation', models.TextField(blank=True, verbose_name='Observação')),
                ('enrollment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendances', to='academic.extraactivityenrollment', verbose_name='Matrícula')),
            ],
            options={
                'verbose_name': 'Presença em Atividade Extra',
                'verbose_name_plural': 'Presenças em Atividades Extras',
                'ordering': ['-date'],
                'unique_together': {('enrollment', 'date')},
            },
        ),
        # 4. Migra dados
        migrations.RunPython(migrate_extra_activities_to_enrollments, reverse_migrate),
        # 5. Remove extra_activities do Student
        migrations.RemoveField(
            model_name='student',
            name='extra_activities',
        ),
    ]
