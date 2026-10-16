from django import template

from ..services import resolve_selection

register = template.Library()


@register.simple_tag
def sponsorship_selection(selection):
    """{'type_id': quantity} -> [{'type', 'quantity', 'total'}] for the summary."""
    return [{'type': t, 'quantity': quantity, 'total': t.annual_fee * quantity}
            for t, quantity in resolve_selection(selection)]


@register.filter
def chf(value):
    """1234.5 -> 1'234.50"""
    try:
        return f"{float(value):,.2f}".replace(',', "'")
    except (TypeError, ValueError):
        return value
