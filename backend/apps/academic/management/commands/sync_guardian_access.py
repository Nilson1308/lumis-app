import csv
import re
import unicodedata
from pathlib import Path

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academic.models import Guardian
from apps.core.models import User


def normalize_username_seed(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = normalized.encode("ascii", "ignore").decode("utf-8")
    slug = re.sub(r"[^a-zA-Z0-9\s]", "", ascii_only).strip().lower()
    parts = slug.split()
    if not parts:
        return "responsavel"
    if len(parts) == 1:
        return parts[0][:24]
    return f"{parts[0][:12]}.{parts[-1][:12]}"


def build_unique_username(base: str) -> str:
    candidate = base
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base[:20]}{suffix}"
        suffix += 1
    return candidate


class Command(BaseCommand):
    help = (
        "Sincroniza acesso dos responsáveis: cria grupo, cria/vincula usuário, "
        "reseta senha e gera CSV de credenciais."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--group-name",
            type=str,
            default="Reponsaveis",
            help="Nome do grupo a ser criado/usado. Padrão: Reponsaveis",
        )
        parser.add_argument(
            "--password",
            type=str,
            default="123@senha",
            help="Senha padrão para todos os usuários do grupo. Padrão: 123@senha",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="guardian_access.csv",
            help="Caminho do CSV de saída (relativo à raiz do projeto ou absoluto).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        group_name = options["group_name"].strip()
        default_password = options["password"]
        output_path = Path(options["output"]).expanduser()
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        group, created = Group.objects.get_or_create(name=group_name)
        self.stdout.write(
            self.style.SUCCESS(
                f"Grupo '{group_name}' {'criado' if created else 'localizado'} com sucesso."
            )
        )

        guardians = Guardian.objects.select_related("user").order_by("name")
        created_users = 0
        linked_users = 0
        updated_passwords = 0
        rows = []

        for guardian in guardians:
            user = guardian.user

            if not user:
                seed = normalize_username_seed(guardian.name)
                username = build_unique_username(seed)
                email = (guardian.email or "").strip() or f"{username}@responsaveis.local"
                user = User.objects.create(
                    username=username,
                    first_name=guardian.name.split(" ")[0][:150],
                    email=email,
                    must_change_password=True,
                )
                created_users += 1

            user.groups.add(group)
            user.set_password(default_password)
            user.must_change_password = True
            user.save()
            updated_passwords += 1

            if guardian.user_id != user.id:
                guardian.user = user
                guardian.save(update_fields=["user"])
                linked_users += 1

            rows.append(
                {
                    "guardian_id": guardian.id,
                    "guardian_name": guardian.name,
                    "guardian_cpf": guardian.cpf or "",
                    "guardian_email": guardian.email or "",
                    "guardian_phone": guardian.phone or "",
                    "user_id": user.id,
                    "username": user.username,
                    "login_email": user.email or "",
                    "password": default_password,
                    "group": group_name,
                }
            )

        # Garante a atualização de senha para todos os usuários do grupo,
        # inclusive os que não tenham Guardian vinculado.
        group_users = User.objects.filter(groups=group).distinct()
        for user in group_users:
            user.set_password(default_password)
            user.must_change_password = True
            user.save(update_fields=["password", "must_change_password"])

        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=[
                    "guardian_id",
                    "guardian_name",
                    "guardian_cpf",
                    "guardian_email",
                    "guardian_phone",
                    "user_id",
                    "username",
                    "login_email",
                    "password",
                    "group",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS("Sincronização concluída com sucesso."))
        self.stdout.write(
            f"Responsáveis processados: {guardians.count()} | "
            f"Usuários criados: {created_users} | "
            f"Vínculos atualizados: {linked_users} | "
            f"Senhas atualizadas: {updated_passwords}"
        )
        self.stdout.write(self.style.SUCCESS(f"CSV gerado em: {output_path}"))
