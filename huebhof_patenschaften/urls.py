from django.urls import path
from django.views.generic import RedirectView

from . import views, views_billing

urlpatterns = [
    # Order process (url name must match the SignupManager)
    path('subscription/create/sponsorships/', views.SelectSponsorshipsView.as_view(), name='cs-sponsorships'),
    # Member area
    path('my/sponsorships/', views.my_sponsorships, name='sponsorships-mine'),
    path('my/sponsorships/<int:sponsorship_id>/cancel/', views.cancel_sponsorship, name='sponsorships-cancel'),
    path('my/patenschaften/', RedirectView.as_view(pattern_name='sponsorships-mine', permanent=True)),  # old path
    # Management
    path('manage/sponsorships/', views.SponsorshipsManageView.as_view(), name='sponsorships-manage'),
    path('manage/sponsorships/export/', views.export, name='sponsorships-export'),
    path('manage/sponsorships/pending/', views.pending, name='sponsorships-pending'),
    path('manage/sponsorships/pending/apply/', views.pending_apply, name='sponsorships-pending-apply'),
    path('manage/sponsorships/create/', views.create, name='sponsorships-create'),
    path('manage/sponsorships/<int:sponsorship_id>/', views.edit, name='sponsorships-edit'),
    path('manage/sponsorships/types/', views.types, name='sponsorships-types'),
    path('manage/sponsorships/types/new/', views.edit_type, name='sponsorships-type-new'),
    path('manage/sponsorships/types/<int:type_id>/', views.edit_type, name='sponsorships-type'),
    # juntagrico_billing: same paths as there, so that sponsorships are part of the billing workflow
    # (see views_billing.py; works because these URLs are included before juntagrico_billing.urls).
    # Same names as there, so that the page gets the same body id.
    path('jb/pending_bills', views_billing.pending_bills, name='pending-bills-list'),
    path('jb/bills_generate', views_billing.bills_generate, name='bills-generate'),
    path('jb/bill_recalc/<int:bill_id>', views_billing.bill_recalc, name='bill-recalc'),
]
