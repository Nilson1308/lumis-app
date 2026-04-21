from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.academic.calendar_xlsx_import import (
    IMPORT_MARKER,
    import_calendar_events,
    iter_parsed_events,
)
from apps.academic.models import SchoolEvent

User = get_user_model()


class Command(BaseCommand):
    help = (
        'Importa eventos do calendário escolar a partir do ficheiro Excel no layout '
        'Lumis 2026 (abas com blocos B/K/T/AC/AL/AU nas linhas 14–21 e 31–37).'
    )

    def add_arguments(self, parser):
        default_path = Path(settings.BASE_DIR).parent / 'calendario 2026.xlsx'
        parser.add_argument(
            '--file',
            type=str,
            default=str(default_path),
            help='Caminho para o .xlsx (por omissão: <raiz do repo>/calendario 2026.xlsx).',
        )
        parser.add_argument(
            '--year',
            type=int,
            default=2026,
            help='Ano letivo das datas interpretadas.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas mostra os eventos interpretados; não grava na base.',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Não cria registo se já existir SchoolEvent com o mesmo título e data de início.',
        )
        parser.add_argument(
            '--replace-imported',
            action='store_true',
            help=f'Antes de importar, apaga eventos cuja descrição contém "{IMPORT_MARKER}" (reimportação).',
        )
        parser.add_argument(
            '--user',
            type=str,
            default='',
            help='Username do utilizador a gravar em created_by (opcional).',
        )
        parser.add_argument(
            '--count-only',
            action='store_true',
            help='Mostra só quantos eventos o ficheiro gera (sem dry-run linha a linha).',
        )

    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.is_file():
            raise CommandError(f'Ficheiro não encontrado: {path}')

        if options['replace_imported'] and not options['dry_run']:
            deleted, _ = SchoolEvent.objects.filter(description__contains=IMPORT_MARKER).delete()
            self.stdout.write(self.style.WARNING(f'Removidos {deleted} evento(s) de importação anterior.'))

        created_by = None
        if options['user']:
            created_by = User.objects.filter(username=options['user']).first()
            if not created_by:
                raise CommandError(f'Utilizador não encontrado: {options["user"]}')

        if options['count_only']:
            n = sum(1 for _ in iter_parsed_events(path, year=options['year']))
            self.stdout.write(self.style.SUCCESS(f'Eventos interpretados: {n}'))
            return

        stats = import_calendar_events(
            path,
            year=options['year'],
            dry_run=options['dry_run'],
            skip_existing=options['skip_existing'],
            created_by=created_by,
            stdout=self.stdout,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Concluído: interpretados={stats["parsed"]}, '
                f'criados={stats["created"]}, '
                f'ignorados_duplicado={stats["skipped_duplicate"]}'
                + (f', linhas_dry_run={stats["dry_run_lines"]}' if options['dry_run'] else '')
            )
        )
        if not options['dry_run'] and stats['created']:
            self.stdout.write(
                'Dica: para reimportar sem duplicar, use --replace-imported ou --skip-existing.'
            )
