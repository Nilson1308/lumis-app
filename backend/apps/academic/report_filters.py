"""Filtros padronizados para relatórios PDF (período letivo + intervalo de datas)."""

from datetime import datetime, timedelta

from django.http import HttpResponse

from .models import AcademicPeriod, ClassRoom

MAX_REPORT_RANGE_DAYS = 366


def _parse_date(value, field_name):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValueError(f"Formato inválido em '{field_name}'. Use YYYY-MM-DD.")


def resolve_classroom_report_window(request, *, require_period=True):
    """
    Resolve turma, período letivo e janela efetiva de datas (interseção).

    Retorna (payload, None) ou (None, HttpResponse de erro).
  payload: dict com classroom, period, date_start, date_end, range_label.
    """
    classroom_id = request.GET.get('classroom')
    period_id = request.GET.get('period')
    start_raw = (request.GET.get('start_date') or '').strip()
    end_raw = (request.GET.get('end_date') or '').strip()

    if not classroom_id:
        return None, HttpResponse('Parâmetro classroom é obrigatório.', status=400)
    if require_period and not period_id:
        return None, HttpResponse('Parâmetro period é obrigatório.', status=400)

    if bool(start_raw) ^ bool(end_raw):
        return None, HttpResponse(
            'Informe start_date e end_date juntos, ou deixe ambos vazios.',
            status=400,
        )

    try:
        classroom = ClassRoom.objects.get(pk=classroom_id)
    except ClassRoom.DoesNotExist:
        return None, HttpResponse('Turma não encontrada.', status=404)

    period = None
    if period_id:
        try:
            period = AcademicPeriod.objects.get(pk=period_id)
        except AcademicPeriod.DoesNotExist:
            return None, HttpResponse('Período letivo não encontrado.', status=404)

    period_start = period.start_date if period else None
    period_end = period.end_date if period else None

    if start_raw and end_raw:
        try:
            requested_start = _parse_date(start_raw, 'start_date')
            requested_end = _parse_date(end_raw, 'end_date')
        except ValueError as exc:
            return None, HttpResponse(str(exc), status=400)

        if requested_end < requested_start:
            return None, HttpResponse(
                'end_date deve ser maior ou igual a start_date.',
                status=400,
            )

        span_days = (requested_end - requested_start).days + 1
        if span_days > MAX_REPORT_RANGE_DAYS:
            return None, HttpResponse(
                f'O intervalo máximo permitido é de {MAX_REPORT_RANGE_DAYS} dias.',
                status=400,
            )

        date_start, date_end = requested_start, requested_end
    elif period:
        date_start, date_end = period_start, period_end
    else:
        return None, HttpResponse(
            'Informe period ou um intervalo start_date/end_date.',
            status=400,
        )

    if period_start and period_end:
        date_start = max(date_start, period_start)
        date_end = min(date_end, period_end)

    if date_end < date_start:
        return None, HttpResponse(
            'Nenhum dado no intervalo: as datas selecionadas não coincidem com o período letivo.',
            status=400,
        )

    range_label = (
        f'{date_start.strftime("%d/%m/%Y")} a {date_end.strftime("%d/%m/%Y")}'
    )

    return {
        'classroom': classroom,
        'period': period,
        'date_start': date_start,
        'date_end': date_end,
        'range_label': range_label,
    }, None


def resolve_student_card_date_window(request, period):
    """Intervalo opcional para boletim (intersecta com o período letivo quando informado)."""
    start_raw = (request.GET.get('start_date') or '').strip()
    end_raw = (request.GET.get('end_date') or '').strip()

    if not start_raw and not end_raw:
        if period:
            return period.start_date, period.end_date, None
        return None, None, None

    if bool(start_raw) ^ bool(end_raw):
        return None, None, HttpResponse(
            'Informe start_date e end_date juntos, ou deixe ambos vazios.',
            status=400,
        )

    try:
        date_start = _parse_date(start_raw, 'start_date')
        date_end = _parse_date(end_raw, 'end_date')
    except ValueError as exc:
        return None, None, HttpResponse(str(exc), status=400)

    if date_end < date_start:
        return None, None, HttpResponse(
            'end_date deve ser maior ou igual a start_date.',
            status=400,
        )

    span_days = (date_end - date_start).days + 1
    if span_days > MAX_REPORT_RANGE_DAYS:
        return None, None, HttpResponse(
            f'O intervalo máximo permitido é de {MAX_REPORT_RANGE_DAYS} dias.',
            status=400,
        )

    if period:
        date_start = max(date_start, period.start_date)
        date_end = min(date_end, period.end_date)
        if date_end < date_start:
            return None, None, HttpResponse(
                'Nenhum dado no intervalo: as datas não coincidem com o período letivo.',
                status=400,
            )

    return date_start, date_end, None
