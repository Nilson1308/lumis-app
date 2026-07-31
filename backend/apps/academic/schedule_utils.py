"""Utilitários de dia da semana alinhados ao frontend (FullCalendar / Date.getDay)."""

from datetime import date


def schedule_day_of_week(value: date) -> int:
    """
    Retorna 0=domingo … 6=sábado, mesmo padrão de ClassSchedule e Date.getDay().
    """
    return value.isoweekday() % 7
