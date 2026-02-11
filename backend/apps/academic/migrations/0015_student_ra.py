# Generated manually on 2026-02-10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0014_lessonplanfile'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='ra',
            field=models.CharField(blank=True, help_text='Registro Acadêmico do aluno', max_length=20, null=True, verbose_name='RA (Registro do Aluno)'),
        ),
    ]
