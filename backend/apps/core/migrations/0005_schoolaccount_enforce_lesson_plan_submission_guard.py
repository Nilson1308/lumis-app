from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_schoolaccount_non_teaching_event_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolaccount',
            name='enforce_lesson_plan_submission_guard',
            field=models.BooleanField(
                default=False,
                help_text='Quando ativo, professores com planejamento semanal em atraso ficam bloqueados até liberação da coordenação/admin.',
                verbose_name='Bloquear envio de planejamento por atraso',
            ),
        ),
    ]
