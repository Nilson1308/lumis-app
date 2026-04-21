from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0020_lessonplan_attachment_link'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LessonPlanSubmissionBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.BooleanField(default=True, verbose_name='Ativo')),
                ('reason', models.TextField(blank=True, verbose_name='Motivo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('released_at', models.DateTimeField(blank=True, null=True)),
                ('blocked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lesson_plan_blocks_created', to=settings.AUTH_USER_MODEL, verbose_name='Bloqueado por')),
                ('released_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lesson_plan_blocks_released', to=settings.AUTH_USER_MODEL, verbose_name='Liberado por')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lesson_plan_blocks', to=settings.AUTH_USER_MODEL, verbose_name='Professor')),
            ],
            options={
                'verbose_name': 'Bloqueio de Envio de Planejamento',
                'verbose_name_plural': 'Bloqueios de Envio de Planejamento',
                'ordering': ['-created_at'],
            },
        ),
    ]
