# Generated migration - Add guests field to MeetingMinute

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coordination', '0005_weeklyreport_recipients_attachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='meetingminute',
            name='guests',
            field=models.TextField(blank=True, help_text='Convidados externos à instituição', verbose_name='Convidados'),
        ),
    ]
