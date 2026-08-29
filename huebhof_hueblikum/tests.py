from unittest import mock

from django.test import TestCase, override_settings

from juntagrico.entity.member import Member


def make_member(email, **kwargs):
    data = {
        'first_name': 'first_name',
        'last_name': 'last_name',
        'email': email,
        'addr_street': 'Street 1',
        'addr_zipcode': '8000',
        'addr_location': 'Zürich',
        'phone': '0791234567',
    }
    data.update(kwargs)
    return Member.objects.create(**data)


@override_settings(HUEBLIKUM_SYNC_TOKEN='test-token')
class MembersEndpointTest(TestCase):
    def test_missing_authorization_header_denied(self):
        response = self.client.get('/api/hueblikum/members/')
        self.assertEqual(response.status_code, 403)

    def test_wrong_token_denied(self):
        response = self.client.get(
            '/api/hueblikum/members/', HTTP_AUTHORIZATION='Bearer wrong-token'
        )
        self.assertEqual(response.status_code, 403)

    def test_empty_token_setting_never_authorizes(self):
        # An unset/empty HUEBLIKUM_SYNC_TOKEN must not make an empty
        # Authorization header (or "Bearer ") pass.
        with override_settings(HUEBLIKUM_SYNC_TOKEN=''):
            response = self.client.get(
                '/api/hueblikum/members/', HTTP_AUTHORIZATION='Bearer '
            )
        self.assertEqual(response.status_code, 403)

    def test_valid_token_returns_primary_members(self):
        member = make_member('active@example.com')
        with mock.patch(
            'huebhof_hueblikum.views.Member.objects.filter',
            return_value=Member.objects.filter(pk=member.pk),
        ):
            response = self.client.get(
                '/api/hueblikum/members/', HTTP_AUTHORIZATION='Bearer test-token'
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['members']), 1)
        entry = data['members'][0]
        self.assertEqual(entry['juntagrico_id'], member.id)
        self.assertEqual(entry['email'], 'active@example.com')
        self.assertEqual(entry['first_name'], 'first_name')
        # Adresse wird bewusst nicht exportiert (Datenminimierung, siehe views.py).
        self.assertNotIn('addr_location', entry)

    def test_co_members_without_own_subscription_excluded(self):
        # Mit-BezieherInnen desselben Ernteanteils, die nicht selbst
        # primary_member sind, duerfen hier nicht auftauchen - nur die
        # Haupt-BezieherIn ist automatisch Vereinsmitglied.
        make_member('co-member@example.com')
        with mock.patch(
            'huebhof_hueblikum.views.Member.objects.filter',
            return_value=Member.objects.none(),
        ):
            response = self.client.get(
                '/api/hueblikum/members/', HTTP_AUTHORIZATION='Bearer test-token'
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['members'], [])
