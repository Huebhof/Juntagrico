"""Erweiterte Views von juntagrico_billing, damit Patenschaften im normalen Rechnungsablauf mitlaufen.

Die URLs in urls.py sind identisch mit denen von juntagrico_billing ('jb/...'). Weil huebhof_patenschaften.urls
in huebhof/urls.py vor juntagrico_billing.urls eingebunden ist, werden diese Views verwendet; Links und
reverse('jb:...') bleiben unverändert. Die eigentliche Arbeit machen weiterhin die Funktionen von juntagrico_billing.
"""
from datetime import date

from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from juntagrico_billing import views as jb_views
from juntagrico_billing.models.bill import Bill, BusinessYear
from juntagrico_billing.util.billing import create_bills_for_items, get_billable_subscription_parts, \
    group_billables_by_member, recalc_bill

from . import billing, services


@permission_required('juntagrico.is_book_keeper')
def pending_bills(request):
    """Anstehende Rechnungen: Ernteanteile (wie juntagrico_billing) plus unverrechnete Patenschaften."""
    business_years, selected_year = jb_views.get_years_and_selected(request)
    pending = []
    if selected_year:
        parts_per_member = group_billables_by_member(get_billable_subscription_parts(selected_year))
        paten_per_member = billing.nach_member(billing.verrechenbar(selected_year))
        members = list(parts_per_member) + [m for m in paten_per_member if m not in parts_per_member]
        for member in members:
            parts = parts_per_member.get(member, [])
            patenschaften = paten_per_member.get(member, [])
            pending.append({
                'member': member,
                'subscription': jb_views.get_subscription(parts),
                'short_parts': jb_views.get_short_parts(parts),
                'patenschaften': services.gruppieren(patenschaften),
                'price': jb_views.get_price(parts, selected_year) + sum(p.jahresbeitrag for p in patenschaften),
                'existing_bills': jb_views.get_existing_bills(member, selected_year),
            })

    return render(request, 'huebhof_patenschaften/pending_bills.html', {
        'business_years': business_years,
        'selected_year': selected_year,
        'pending_bills': pending,
    })


@permission_required('juntagrico.is_book_keeper')
@require_POST
@transaction.atomic
def bills_generate(request):
    """Erst die Ernteanteil-Rechnungen (juntagrico_billing), dann die Patenschaften daran anfügen,
    so dass jedes Mitglied eine Rechnung erhält."""
    year = BusinessYear.objects.by_name(request.session['bills_businessyear'])
    create_bills_for_items(get_billable_subscription_parts(year), year, date.today())
    billing.verrechnen(year, billing.verrechenbar(year))
    return redirect(reverse('jb:unpublished-bills-list'))


@permission_required('juntagrico.is_book_keeper')
@transaction.atomic
def bill_recalc(request, bill_id):
    """Neuberechnung wie juntagrico_billing, zusätzlich werden fehlende Patenschaften angefügt."""
    bill = get_object_or_404(Bill, pk=bill_id)
    recalc_bill(bill)
    billing.anfuegen(bill, billing.verrechenbar(bill.business_year).filter(member=bill.member))

    next_url = request.GET.get('next')
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = reverse('admin:juntagrico_billing_bill_change', args=[bill.id])
    return redirect(next_url)
