# Generated manually - Autorização de imagem, saída e contatos próximos

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0018_student_checklist'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='image_authorization',
            field=models.BooleanField(blank=True, help_text='Autoriza uso de imagem do aluno em fotos/vídeos', null=True, verbose_name='Autorização de Imagem'),
        ),
        migrations.AddField(
            model_name='student',
            name='exit_authorization',
            field=models.TextField(blank=True, help_text='Quem está autorizado a retirar o aluno', verbose_name='Autorização de Saída'),
        ),
        migrations.AddField(
            model_name='student',
            name='close_contacts',
            field=models.TextField(blank=True, help_text='Pessoas de confiança / contatos próximos', verbose_name='Contatos Próximos'),
        ),
    ]
