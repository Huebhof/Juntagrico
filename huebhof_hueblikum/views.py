import hmac

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse

from juntagrico.entity.member import Member


def _authorized(request):
    expected = settings.HUEBLIKUM_SYNC_TOKEN
    if not expected:
        return False
    given = request.headers.get('Authorization', '')
    return hmac.compare_digest(given, f'Bearer {expected}')


def members(request):
    """Aktive Ernteanteil-Bezueger (= Vereinsmitglieder) fuer die hueblikum-App.

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
            'addr_street': member.addr_street,
            'addr_zipcode': member.addr_zipcode,
            'addr_location': member.addr_location,
        }
        for member in Member.objects.has_active_subscription()
    ]
    return JsonResponse({'members': data})
