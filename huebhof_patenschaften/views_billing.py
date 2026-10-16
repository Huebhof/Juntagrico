"""Extended views of juntagrico_billing, so that sponsorships are part of the regular billing workflow.

The URLs in urls.py are identical to those of juntagrico_billing ('jb/...'). Because huebhof_patenschaften.urls
is included before juntagrico_billing.urls in huebhof/urls.py, these views are used; links and
reverse('jb:...') stay unchanged. The actual work is still done by the functions of juntagrico_billing.
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
    """Pending bills: subscriptions (like juntagrico_billing) plus unbilled sponsorships."""
    business_years, selected_year = jb_views.get_years_and_selected(request)
    pending = []
    if selected_year:
        parts_per_member = group_billables_by_member(get_billable_subscription_parts(selected_year))
        sponsorships_per_member = billing.by_member(billing.billable(selected_year))
        members = list(parts_per_member) + [m for m in sponsorships_per_member if m not in parts_per_member]
        for member in members:
            parts = parts_per_member.get(member, [])
            sponsorships = sponsorships_per_member.get(member, [])
            pending.append({
                'member': member,
                'subscription': jb_views.get_subscription(parts),
                'short_parts': jb_views.get_short_parts(parts),
                'sponsorships': services.group(sponsorships),
                'price': jb_views.get_price(parts, selected_year) + sum(s.annual_fee for s in sponsorships),
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
    """First the subscription bills (juntagrico_billing), then add the sponsorships to them,
    so that every member gets one bill."""
    year = BusinessYear.objects.by_name(request.session['bills_businessyear'])
    create_bills_for_items(get_billable_subscription_parts(year), year, date.today())
    billing.create_bills(year, billing.billable(year))
    return redirect(reverse('jb:unpublished-bills-list'))


@permission_required('juntagrico.is_book_keeper')
@transaction.atomic
def bill_recalc(request, bill_id):
    """Recalculation like juntagrico_billing, additionally missing sponsorships are added."""
    bill = get_object_or_404(Bill, pk=bill_id)
    recalc_bill(bill)
    billing.add_to_bill(bill, billing.billable(bill.business_year).filter(member=bill.member))

    next_url = request.GET.get('next')
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = reverse('admin:juntagrico_billing_bill_change', args=[bill.id])
    return redirect(next_url)
