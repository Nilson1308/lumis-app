from rest_framework import permissions

class IsGuardianOwner(permissions.BasePermission):
    """ Permite que o usuário edite apenas o seu próprio perfil de Responsável """
    def has_object_permission(self, request, view, obj):
        # Leitura permitida (GET)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Admin, Staff OU membro do grupo Coordenação
        if request.user.is_staff or request.user.is_superuser:
            return True
        if request.user.groups.filter(name='Coordenacao').exists():
            return True

        # Edição apenas se o Guardian estiver vinculado ao User logado
        return obj.user == request.user

class IsGuardianOfStudent(permissions.BasePermission):
    """ Permite edição se for Admin/Coordenação OU se for um dos responsáveis pelo aluno """
    def has_object_permission(self, request, view, student):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 1. Admin, Staff (Equipe) ou Grupo Coordenação -> LIBERADO
        if request.user.is_staff or request.user.is_superuser:
            return True
        if request.user.groups.filter(name='Coordenacao').exists():
            return True

        # 2. Se for Pai/Mãe, verifica se é responsável DESTE aluno específico
        if hasattr(request.user, 'guardian_profile'):
            return student.guardians.filter(id=request.user.guardian_profile.id).exists()
            
        return False