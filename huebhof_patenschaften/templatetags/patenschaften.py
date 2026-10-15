from django import template

from ..services import auswahl_aufloesen

register = template.Library()


@register.simple_tag
def patenschaften_auswahl(auswahl):
    """{'typ_id': anzahl} -> [{'typ', 'anzahl', 'summe'}] für die Zusammenfassung."""
    return [{'typ': typ, 'anzahl': anzahl, 'summe': typ.jahresbeitrag * anzahl}
            for typ, anzahl in auswahl_aufloesen(auswahl)]


@register.filter
def chf(value):
    """1234.5 -> 1'234.50"""
    try:
        return f"{float(value):,.2f}".replace(',', "'")
    except (TypeError, ValueError):
        return value
