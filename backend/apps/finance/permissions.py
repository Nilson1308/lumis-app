from rest_framework.permissions import BasePermission


class IsFinanceUser(BasePermission):
    """Acesso ao módulo financeiro: staff, superuser ou grupos administrativos."""

    ADMIN_GROUPS = [
        'Coordenadores', 'Coordenação', 'Coordenacao',
        'Direção', 'Direcao', 'Diretoria', 'Secretaria',
    ]

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        return user.groups.filter(name__in=self.ADMIN_GROUPS).exists()
