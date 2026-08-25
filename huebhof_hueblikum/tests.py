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

    def test_valid_token_returns_active_members(self):
        member = make_member('active@example.com')
        with mock.patch(
            'huebhof_hueblikum.views.Member.objects.has_active_subscription',
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
        self.assertEqual(entry['addr_location'], 'Zürich')

    def test_inactive_members_excluded(self):
        make_member('inactive@example.com')
        with mock.patch(
            'huebhof_hueblikum.views.Member.objects.has_active_subscription',
            return_value=Member.objects.none(),
        ):
            response = self.client.get(
                '/api/hueblikum/members/', HTTP_AUTHORIZATION='Bearer test-token'
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['members'], [])
