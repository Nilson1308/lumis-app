from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0019_student_authorizations'),
    ]

    operations = [
        migrations.AddField(
            model_name='lessonplan',
            name='attachment_link',
            field=models.CharField(blank=True, max_length=500, verbose_name='Link para Download (arquivo > 5MB)'),
        ),
    ]
