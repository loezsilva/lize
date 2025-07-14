
from django import template
from datetime import timedelta, date

register = template.Library()

@register.filter
def remaining_days(base_date, days):
    """
    Filtro customizado para calcular quantos dias faltam até a expiração,
    baseada em uma data e um número de dias de validade.
    
    Uso: {{ some_date|dias_restantes:30 }}
    """
    if not base_date or not days:
        return ""

    try:
        days = int(days)
        data_validade = base_date.date() + timedelta(days=days)
        today = date.today()
        remaining_days = (data_validade - today).days
        return max(remaining_days, 0)
    except Exception:
        return ""
