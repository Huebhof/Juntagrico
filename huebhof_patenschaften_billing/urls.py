from django.urls import path

from . import views

urlpatterns = [
    # Same paths as juntagrico_billing, so that sponsorships are part of the billing workflow
    # (see views.py; works because these URLs are included before juntagrico_billing.urls).
    # Same names as there, so that the page gets the same body id.
    path('jb/pending_bills', views.pending_bills, name='pending-bills-list'),
    path('jb/bills_generate', views.bills_generate, name='bills-generate'),
    path('jb/bill_recalc/<int:bill_id>', views.bill_recalc, name='bill-recalc'),
]
