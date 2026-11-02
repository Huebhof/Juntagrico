import datetime

from django import template

from ..services import resolve_selection

register = template.Library()


@register.simple_tag
def sponsorship_selection(selection):
    """{'type_id': quantity} -> [{'type', 'quantity', 'total'}] for the summary."""
    return [{'type': t, 'quantity': quantity, 'total': t.annual_fee * quantity}
            for t, quantity in resolve_selection(selection)]


@register.simple_tag
def sponsorship_start_date(subscriptions, raw):
    """Desired start chosen on the sponsorship page, None with a subscription (its start date applies)."""
    if any((subscriptions or {}).values()) or not raw:
        return None
    return datetime.date.fromisoformat(raw)
