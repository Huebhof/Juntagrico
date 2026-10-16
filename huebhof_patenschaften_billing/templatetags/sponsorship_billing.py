from django import template

from .. import billing

register = template.Library()


@register.simple_tag
def first_year_share(annual_fee, quantity=1, date=None):
    """Pro rata amount until the end of the business year, see billing.first_year_share."""
    return billing.first_year_share(annual_fee, date, quantity)


@register.simple_tag
def first_year_total(sponsorships):
    """Sum of the pro rata amounts of new sponsorships (from their activation or order date)."""
    shares = [billing.first_year_share(s.annual_fee, s.activation_date or s.order_date) for s in sponsorships]
    shares = [share for share in shares if share]
    if not shares:
        return None
    return dict(shares[0], amount=sum(share['amount'] for share in shares))


@register.simple_tag
def billed_per_type():
    """Billed amounts of the current business year per sponsorship type, see billing.billed_per_type."""
    return billing.billed_per_type()


@register.filter
def get_item(mapping, key):
    return mapping.get(key, 0)
