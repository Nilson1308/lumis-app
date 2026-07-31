from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_schoolaccount_enforce_lesson_plan_submission_guard'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='must_change_password',
            field=models.BooleanField(default=False),
        ),
    ]

