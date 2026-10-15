from django.urls import path

from . import views

urlpatterns = [
    # Bestellprozess (url-Name muss mit dem SignupManager übereinstimmen)
    path('subscription/create/patenschaften/', views.SelectPatenschaftenView.as_view(), name='cs-patenschaften'),
    # Mitgliederbereich
    path('my/patenschaften/', views.meine_patenschaften, name='patenschaften-mine'),
    path('my/patenschaften/<int:patenschaft_id>/kuendigen/', views.patenschaft_kuendigen,
         name='patenschaften-kuendigen'),
    # Administration
    path('manage/patenschaften/', views.PatenschaftenManageView.as_view(), name='patenschaften-manage'),
    path('manage/patenschaften/aktivieren/', views.patenschaften_aktivieren, name='patenschaften-aktivieren'),
]
