from django import template

from .. import years
from ..services import chosen_year, resolve_selection

register = template.Library()


@register.simple_tag
def sponsorship_selection(selection, chosen_years=None):
    """{'type_id': quantity} -> [{'type', 'quantity', 'total', 'year'}] for the summary."""
    orderable = years.orderable()
    return [{'type': t, 'quantity': quantity, 'total': t.annual_fee * quantity,
             'year': years.label(chosen_year(t, chosen_years, orderable))}
            for t, quantity in resolve_selection(selection)]
