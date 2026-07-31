import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0021_lessonplansubmissionblock'),
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='shareddocument',
            name='segment',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='shared_documents',
                to='academic.segment',
                verbose_name='Segmento',
            ),
        ),
        migrations.AlterField(
            model_name='shareddocument',
            name='target_audience',
            field=models.CharField(
                choices=[
                    ('ALL', 'Todos (professores e responsáveis)'),
                    ('TEACHERS', 'Professores'),
                    ('GUARDIANS', 'Responsáveis / Pais'),
                    ('CLASSROOM', 'Turma específica'),
                    ('SEGMENT', 'Segmento / série'),
                ],
                default='ALL',
                max_length=20,
                verbose_name='Público-alvo',
            ),
        ),
        migrations.CreateModel(
            name='SharedDocumentReadStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('read_at', models.DateTimeField(blank=True, null=True, verbose_name='Lido em')),
                ('document', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='read_statuses',
                    to='documents.shareddocument',
                    verbose_name='Documento',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='shared_document_reads',
                    to='core.user',
                    verbose_name='Usuário',
                )),
            ],
            options={
                'verbose_name': 'Leitura de documento',
                'verbose_name_plural': 'Leituras de documentos',
                'unique_together': {('document', 'user')},
            },
        ),
    ]
