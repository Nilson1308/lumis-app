from django.db.models import Q

from apps.academic.models import ClassRoom, Enrollment, Guardian, TeacherAssignment
from apps.core.models import Notification, User

GUARDIAN_GROUPS = ['Responsáveis', 'Responsaveis', 'Pais']

POWER_GROUPS = [
    'Coordenadores', 'Coordenação', 'Coordenacao',
    'Direção', 'Direcao', 'Diretoria', 'Secretaria',
]


def is_power_user(user):
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=POWER_GROUPS).exists()


def is_teacher(user):
    return user.groups.filter(name='Professores').exists()


def is_guardian(user):
    return (
        user.groups.filter(name__in=GUARDIAN_GROUPS).exists()
        or Guardian.objects.filter(user=user).exists()
    )


def notification_link_for_user(user):
    if is_guardian(user):
        return '/portal/documentos'
    if is_teacher(user):
        return '/teacher/documentos'
    return '/documentos/biblioteca'


def get_eligible_users(document):
    audience = document.target_audience

    if audience == 'ALL':
        return User.objects.filter(
            Q(groups__name='Professores') |
            Q(groups__name__in=GUARDIAN_GROUPS) |
            Q(guardian_profile__isnull=False)
        ).distinct()

    if audience == 'TEACHERS':
        return User.objects.filter(groups__name='Professores').distinct()

    if audience == 'GUARDIANS':
        return User.objects.filter(
            Q(groups__name__in=GUARDIAN_GROUPS) | Q(guardian_profile__isnull=False)
        ).distinct()

    if audience == 'CLASSROOM' and document.classroom_id:
        teacher_ids = TeacherAssignment.objects.filter(
            classroom_id=document.classroom_id
        ).values_list('teacher_id', flat=True)
        guardian_user_ids = Guardian.objects.filter(
            students__enrollment__classroom_id=document.classroom_id,
            user__isnull=False,
        ).values_list('user_id', flat=True)
        return User.objects.filter(
            Q(id__in=teacher_ids) | Q(id__in=guardian_user_ids)
        ).distinct()

    if audience == 'SEGMENT' and document.segment_id:
        classroom_ids = ClassRoom.objects.filter(
            segment_id=document.segment_id
        ).values_list('id', flat=True)
        teacher_ids = TeacherAssignment.objects.filter(
            classroom_id__in=classroom_ids
        ).values_list('teacher_id', flat=True)
        guardian_user_ids = Guardian.objects.filter(
            students__enrollment__classroom_id__in=classroom_ids,
            user__isnull=False,
        ).values_list('user_id', flat=True)
        return User.objects.filter(
            Q(id__in=teacher_ids) | Q(id__in=guardian_user_ids)
        ).distinct()

    return User.objects.none()


def document_matches_user_scope(document, user, classroom_ids=None, segment_ids=None):
    """Verifica se o documento está no escopo de leitura do usuário."""
    audience = document.target_audience
    if audience == 'ALL':
        return True
    if audience == 'TEACHERS':
        return is_teacher(user)
    if audience == 'GUARDIANS':
        return is_guardian(user)
    if audience == 'CLASSROOM':
        if not classroom_ids:
            return False
        return document.classroom_id in classroom_ids
    if audience == 'SEGMENT':
        if not segment_ids:
            return False
        return document.segment_id in segment_ids
    return False


def get_user_classroom_ids(user):
    if is_teacher(user):
        return set(
            TeacherAssignment.objects.filter(teacher=user).values_list('classroom_id', flat=True)
        )
    if is_guardian(user):
        guardian = Guardian.objects.filter(user=user).first()
        if not guardian:
            return set()
        return set(
            Enrollment.objects.filter(student__guardians=guardian).values_list('classroom_id', flat=True)
        )
    return set()


def get_user_segment_ids(classroom_ids):
    if not classroom_ids:
        return set()
    return set(
        ClassRoom.objects.filter(id__in=classroom_ids).values_list('segment_id', flat=True)
    )


def publish_document(document, publisher):
    """
    Cria registros de leitura e notifica destinatários elegíveis.
    Retorna quantidade de notificações novas criadas.
    """
    from .models import SharedDocumentReadStatus

    if not document.is_active:
        return 0

    recipients = get_eligible_users(document).exclude(pk=publisher.pk)
    read_rows = [
        SharedDocumentReadStatus(document=document, user=user)
        for user in recipients
    ]
    SharedDocumentReadStatus.objects.bulk_create(read_rows, ignore_conflicts=True)

    notifications_created = 0
    message = (document.description or 'Um novo documento foi publicado pela escola.').strip()[:500]
    for user in recipients:
        link = f'{notification_link_for_user(user)}?doc={document.id}'
        _, created = Notification.objects.get_or_create(
            recipient=user,
            link=link,
            defaults={
                'title': f'Novo documento: {document.title}',
                'message': message,
                'read': False,
            },
        )
        if created:
            notifications_created += 1
    return notifications_created
