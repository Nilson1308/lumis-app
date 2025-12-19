from rest_framework import permissions

class IsGuardianOwner(permissions.BasePermission):
    """ Permite que o usuário edite apenas o seu próprio perfil de Responsável """
    def has_object_permission(self, request, view, obj):
        # Leitura permitida (GET)
        if request.method in permissions.SAFE_METHODS:
            return True
        # Edição apenas se o Guardian estiver vinculado ao User logado
        return obj.user == request.user

class IsGuardianOfStudent(permissions.BasePermission):
    """ Permite edição apenas se o usuário for um dos responsáveis pelo aluno """
    def has_object_permission(self, request, view, student):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Verifica se o usuário logado é um responsável vinculado a este aluno
        if hasattr(request.user, 'guardian_profile'):
            return student.guardians.filter(id=request.user.guardian_profile.id).exists()
        return False