from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.urls import reverse

from juntagrico.tests import JuntagricoTestCase

WEAK = 'kurz123'
STRONG = 'ein-wirklich-langes-Passwort-2026'


class PasswordValidationTests(JuntagricoTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.plain = cls.create_member('plain@email.org')
        cls.grouped = cls.create_member('grouped@email.org')
        cls.grouped.user.groups.add(Group.objects.create(name='impersonators'))
        cls.staff = cls.create_member('staff@email.org')
        cls.staff.user.is_staff = True
        cls.staff.user.save()

    def assertRejected(self, password, user):
        with self.assertRaises(ValidationError):
            validate_password(password, user)

    def test_plain_member_is_not_checked(self):
        validate_password(WEAK, self.plain.user)

    def test_new_unsaved_user_is_not_checked(self):
        validate_password(WEAK, User(username='neu'))

    def test_privileged_accounts_are_checked(self):
        for user in (self.staff.user, self.grouped.user, self.depot_coordinator.user):
            with self.subTest(user=user.username):
                self.assertRejected(WEAK, user)
                validate_password(STRONG, user)

    def _login(self, member, password):
        member.user.set_password(password)
        member.user.save()
        type(member).objects.filter(pk=member.pk).update(confirmed=True)
        return self.client.post(reverse('login'), {'username': member.email, 'password': password})

    def test_login_plain_member_with_weak_password(self):
        response = self._login(self.plain, WEAK)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.client.session.get('must_change_password'))

    def test_login_coordinator_with_weak_password_requires_change(self):
        response = self._login(self.depot_coordinator, WEAK)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get('must_change_password'))
        self.assertRedirects(self.client.get(reverse('home')), reverse('password'), fetch_redirect_response=False)
