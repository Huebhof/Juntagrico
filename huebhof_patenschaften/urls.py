from django.urls import path
from django.views.generic import RedirectView

from . import views

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
]
