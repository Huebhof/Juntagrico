from django.urls import path

from . import views, views_billing

urlpatterns = [
    # Bestellprozess (url-Name muss mit dem SignupManager übereinstimmen)
    path('subscription/create/patenschaften/', views.SelectPatenschaftenView.as_view(), name='cs-patenschaften'),
    # Mitgliederbereich
    path('my/patenschaften/', views.meine_patenschaften, name='patenschaften-mine'),
    path('my/patenschaften/<int:patenschaft_id>/kuendigen/', views.patenschaft_kuendigen,
         name='patenschaften-kuendigen'),
    # Administration
    path('manage/patenschaften/', views.PatenschaftenManageView.as_view(), name='patenschaften-manage'),
    path('manage/patenschaften/export/', views.export, name='patenschaften-export'),
    path('manage/patenschaften/pendent/', views.pendent, name='patenschaften-pendent'),
    path('manage/patenschaften/pendent/anwenden/', views.pendent_anwenden, name='patenschaften-pendent-anwenden'),
    path('manage/patenschaften/erfassen/', views.erfassen, name='patenschaften-erfassen'),
    path('manage/patenschaften/<int:patenschaft_id>/', views.bearbeiten, name='patenschaften-bearbeiten'),
    path('manage/patenschaften/typen/', views.typen, name='patenschaften-typen'),
    path('manage/patenschaften/typen/neu/', views.typ_bearbeiten, name='patenschaften-typ-neu'),
    path('manage/patenschaften/typen/<int:typ_id>/', views.typ_bearbeiten, name='patenschaften-typ'),
    # juntagrico_billing: gleiche Pfade wie dort, damit Patenschaften im Rechnungsablauf mitlaufen
    # (siehe views_billing.py; funktioniert, weil diese URLs vor juntagrico_billing.urls eingebunden sind).
    # Gleiche Namen wie dort, damit die Seite dieselbe body-id erhält.
    path('jb/pending_bills', views_billing.pending_bills, name='pending-bills-list'),
    path('jb/bills_generate', views_billing.bills_generate, name='bills-generate'),
    path('jb/bill_recalc/<int:bill_id>', views_billing.bill_recalc, name='bill-recalc'),
]
