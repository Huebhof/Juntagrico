import hmac

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse

from juntagrico.entity.member import Member
from juntagrico.entity.subs import Subscription


def _authorized(request):
    expected = settings.HUEBLIKUM_SYNC_TOKEN
    if not expected:
        return False
    given = request.headers.get('Authorization', '')
    return hmac.compare_digest(given, f'Bearer {expected}')


def members(request):
    """Haupt-Ernteanteil-BezieherInnen (= Vereinsmitglieder) fuer die hueblikum-App.

    Nur die primary_member von aktiven Subscriptions, nicht alle Mit-BezieherInnen
    eines Ernteanteils - nur Haupt-BezieherInnen sind automatisch Vereinsmitglieder.

    Keine Adresse: fuer die Buchhaltung (QR-Rechnungsversand) nicht zwingend
    noetig - die Swiss-QR-Bill-Norm erlaubt eine Rechnung auch ganz ohne
    Debitor-Adresse. Aus Datenschutzsicht (Datenminimierung) wird sie deshalb
    hier gar nicht erst exportiert.

    Nur GET, geschuetzt durch ein statisches Bearer-Token (HUEBLIKUM_SYNC_TOKEN).
    """
    if not _authorized(request):
        return HttpResponseForbidden()

    data = [
        {
            'juntagrico_id': member.id,
            'first_name': member.first_name,
            'last_name': member.last_name,
            'email': member.email,
        }
        for member in Member.objects.filter(subscription_primary__in=Subscription.objects.active()).distinct()
    ]
    return JsonResponse({'members': data})
