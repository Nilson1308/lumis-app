from django.db import migrations, models


def default_non_teaching_event_types():
    return ['HOLIDAY']


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_accessauditlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolaccount',
            name='non_teaching_event_types',
            field=models.JSONField(
                blank=True,
                default=default_non_teaching_event_types,
                help_text="Tipos de evento do calendário que NÃO exigem chamada. Ex: ['HOLIDAY', 'MEETING']",
                verbose_name='Tipos não letivos no calendário',
            ),
        ),
    ]
