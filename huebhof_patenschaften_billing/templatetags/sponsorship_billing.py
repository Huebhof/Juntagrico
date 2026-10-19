from django import template

from .. import billing

register = template.Library()


@register.simple_tag
def billed_per_type():
    """Billed amounts of the current business year per sponsorship type, see billing.billed_per_type."""
    return billing.billed_per_type()


@register.filter
def get_item(mapping, key):
    return mapping.get(key, 0)
