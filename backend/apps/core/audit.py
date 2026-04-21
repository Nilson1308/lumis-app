from apps.core.models import AccessAuditLog


def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def register_access_audit(request, action, resource_type, resource_id=None, student_id=None, details=None):
    """
    Registra auditoria de acesso sensível sem quebrar o fluxo principal.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return

    payload = details or {}

    try:
        AccessAuditLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else '',
            student_id=student_id,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details=payload,
        )
    except Exception:
        # Auditoria nunca deve interromper o endpoint funcional.
        return
