import datetime
import re
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from juntagrico.entity.depot import Depot
from juntagrico.entity.subtypes import SubscriptionType
from juntagrico.tests import JuntagricoTestCase

from .models import Sponsorship, SponsorshipType

SIGNUP_MANAGER = 'huebhof_patenschaften.signup.SponsorshipSignupManager'


@override_settings(SIGNUP_MANAGER=SIGNUP_MANAGER, ENABLE_SHARES=False,
                   BUSINESS_YEAR_START={'day': 1, 'month': 1}, BUSINESS_YEAR_CANCELATION_MONTH=9)
class SponsorshipTestCase(JuntagricoTestCase):
    with_extra_subs = False

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tree = SponsorshipType.objects.create(name='Baumpatenschaft', annual_fee=Decimal('120'), sort_order=1)
        cls.bee = SponsorshipType.objects.create(name='Bienenpatenschaft', annual_fee=Decimal('50'), sort_order=2)
        cls.hidden = SponsorshipType.objects.create(name='Alt', annual_fee=Decimal('10'), visible=False)


class NextEndDateTests(SponsorshipTestCase):
    def test_before_cancellation_deadline_end_of_year(self):
        self.assertEqual(Sponsorship.next_end_date(datetime.date(2026, 9, 30)), datetime.date(2026, 12, 31))

    def test_after_cancellation_deadline_end_of_next_year(self):
        self.assertEqual(Sponsorship.next_end_date(datetime.date(2026, 10, 1)), datetime.date(2027, 12, 31))


class LifecycleTests(SponsorshipTestCase):
    def test_status_and_cancellation(self):
        s = Sponsorship.objects.create(member=self.member, type=self.tree, activation_date=datetime.date.today())
        self.assertEqual(s.annual_fee, Decimal('120'))
        self.assertEqual(s.status, 'active')
        s.cancel()
        self.assertEqual(s.status, 'canceled')
        self.assertEqual(s.end_date, Sponsorship.next_end_date())
        self.assertIn(s, Sponsorship.objects.canceled())
        self.assertFalse(s.can_be_canceled)

    def test_ordered_is_withdrawn(self):
        s = Sponsorship.objects.create(member=self.member, type=self.tree)
        self.assertEqual(s.status, 'ordered')
        self.assertIn(s, Sponsorship.objects.ordered())
        s.cancel()
        self.assertEqual(s.status, 'withdrawn')
        self.assertNotIn(s, Sponsorship.objects.open())

    def test_price_change_is_not_retroactive(self):
        s = Sponsorship.objects.create(member=self.member, type=self.tree)
        self.tree.annual_fee = Decimal('200')
        self.tree.save()
        s.refresh_from_db()
        self.assertEqual(s.annual_fee, Decimal('120'))

    def test_member_deactivation_ends_sponsorships(self):
        s = Sponsorship.objects.create(member=self.member5, type=self.tree, activation_date=datetime.date(2020, 1, 1))
        ordered = Sponsorship.objects.create(member=self.member5, type=self.bee)
        today = datetime.date.today()
        self.member5.deactivation_date = today
        self.member5.save()
        s.refresh_from_db()
        ordered.refresh_from_db()
        self.assertEqual(s.end_date, today)
        self.assertEqual(ordered.status, 'withdrawn')


class SignupTests(SponsorshipTestCase):
    @staticmethod
    def subscription_selection():
        ids = SubscriptionType.objects.values_list('id', flat=True)
        return {f'amount[{type_id}]': 1 if i == 0 else 0 for i, type_id in enumerate(ids)}

    def _until_sponsorships(self):
        """Member without subscription (member4) orders a subscription."""
        self.client.force_login(self.member4.user)
        response = self.client.post(reverse('cs-subscription'), self.subscription_selection())
        self.assertRedirects(response, reverse('cs-sponsorships'), fetch_redirect_response=False)
        response = self.client.get(reverse('cs-sponsorships'))
        self.assertContains(response, 'Baumpatenschaft')
        self.assertNotContains(response, '>Alt<')

    def _rest_until_summary(self):
        response = self.client.post(reverse('cs-depot'), {'depot': Depot.objects.values_list('id', flat=True)[0]})
        self.assertRedirects(response, reverse('cs-start'), fetch_redirect_response=False)
        response = self.client.post(reverse('cs-start'), {'start_date': '01.01.2030'})
        self.assertRedirects(response, reverse('cs-co-members'), fetch_redirect_response=False)
        response = self.client.get(reverse('cs-co-members'), {'next': '1'})
        self.assertRedirects(response, reverse('cs-summary'), fetch_redirect_response=False)

    def test_with_sponsorships(self):
        self._until_sponsorships()
        response = self.client.post(reverse('cs-sponsorships'),
                                    {f'type_{self.tree.id}': 2, f'type_{self.bee.id}': 1})
        self.assertRedirects(response, reverse('cs-depot'), fetch_redirect_response=False)
        self._rest_until_summary()
        response = self.client.get(reverse('cs-summary'))
        self.assertContains(response, '2 &times; Baumpatenschaft')
        self.assertContains(response, '240 CHF')
        mail.outbox.clear()
        response = self.client.post(reverse('cs-summary'), {'comment': ''})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Sponsorship.objects.filter(member=self.member4, type=self.tree).count(), 2)
        # like subscriptions: ordered, activated by admins
        self.assertEqual(Sponsorship.objects.filter(member=self.member4).ordered().count(), 3)
        self.assertFalse(Sponsorship.objects.filter(member=self.member4).active().exists())
        self.assertTrue(any('Baumpatenschaft' in m.body for m in mail.outbox))

    def test_without_sponsorship(self):
        self._until_sponsorships()
        response = self.client.post(reverse('cs-sponsorships'), {})
        self.assertRedirects(response, reverse('cs-depot'), fetch_redirect_response=False)
        self._rest_until_summary()
        response = self.client.get(reverse('cs-summary'))
        self.assertContains(response, 'Keine Patenschaft')
        self.client.post(reverse('cs-summary'), {'comment': ''})
        self.assertFalse(Sponsorship.objects.filter(member=self.member4).exists())

    def test_edit_from_summary(self):
        self._until_sponsorships()
        self.client.post(reverse('cs-sponsorships'), {f'type_{self.tree.id}': 1})
        self._rest_until_summary()
        # like in juntagrico: after "?mod" you get back to the summary via an intermediate step
        response = self.client.post(reverse('cs-sponsorships') + '?mod', {f'type_{self.bee.id}': 3}, follow=True)
        self.assertEqual(response.redirect_chain[-1][0], reverse('cs-summary'))
        self.assertContains(response, '3 &times; Bienenpatenschaft')
        self.assertNotContains(response, 'Baumpatenschaft')

    @override_settings(SIGNUP_MANAGER='juntagrico.util.sessions.SignupManager')
    def test_no_step_without_signup_manager(self):
        self.client.force_login(self.member4.user)
        response = self.client.post(reverse('cs-subscription'), self.subscription_selection())
        self.assertRedirects(response, reverse('cs-depot'), fetch_redirect_response=False)


class MemberAreaTests(SponsorshipTestCase):
    @override_settings(SPONSORSHIPS_AUTO_ACTIVATE=True)
    def test_list_order_cancel(self):
        self.client.force_login(self.member.user)
        response = self.client.get(reverse('sponsorships-mine'))
        self.assertContains(response, 'keine Patenschaft')
        self.assertContains(response, 'href="%s"' % reverse('sponsorships-mine'))  # menu entry

        # empty order is rejected
        response = self.client.post(reverse('sponsorships-mine'), {})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Sponsorship.objects.filter(member=self.member).exists())

        response = self.client.post(reverse('sponsorships-mine'), {f'type_{self.bee.id}': 2})
        self.assertRedirects(response, reverse('sponsorships-mine'))
        self.assertEqual(Sponsorship.objects.filter(member=self.member).active().count(), 2)
        response = self.client.get(reverse('sponsorships-mine'))
        self.assertContains(response, '100 CHF')

        s = Sponsorship.objects.filter(member=self.member).first()
        response = self.client.post(reverse('sponsorships-cancel', args=[s.id]))
        self.assertRedirects(response, reverse('sponsorships-mine'))
        s.refresh_from_db()
        self.assertEqual(s.status, 'canceled')

    def test_cannot_cancel_others_sponsorship(self):
        s = Sponsorship.objects.create(member=self.member2, type=self.tree, activation_date=datetime.date.today())
        self.client.force_login(self.member.user)
        response = self.client.post(reverse('sponsorships-cancel', args=[s.id]))
        self.assertEqual(response.status_code, 404)

    def test_manual_activation_is_default(self):
        self.client.force_login(self.member.user)
        self.client.post(reverse('sponsorships-mine'), {f'type_{self.tree.id}': 2})
        s, withdrawn = Sponsorship.objects.filter(member=self.member)
        self.assertEqual(s.status, 'ordered')
        self.assertContains(self.client.get(reverse('sponsorships-mine')), 'Bestellt')
        # canceling a not yet activated order = withdrawing it
        self.client.post(reverse('sponsorships-cancel', args=[withdrawn.id]))
        withdrawn.refresh_from_db()
        self.assertEqual(withdrawn.status, 'withdrawn')
        # admin activates
        self.client.force_login(self.admin.user)
        response = self.client.post(reverse('sponsorships-pending-apply'), {'sponsorships[]': [s.id]})
        self.assertEqual(response.status_code, 302)
        s.refresh_from_db()
        self.assertEqual(s.status, 'active')

    def test_old_path_redirects(self):
        self.client.force_login(self.member.user)
        self.assertRedirects(self.client.get('/my/patenschaften/'), reverse('sponsorships-mine'), status_code=301)


class AdminTests(SponsorshipTestCase):
    def test_overview(self):
        Sponsorship.objects.create(member=self.member, type=self.tree, activation_date=datetime.date.today())
        Sponsorship.objects.create(member=self.member2, type=self.bee)
        self.client.force_login(self.admin.user)
        for status in ('active', 'canceled', 'all', 'unknown'):
            response = self.client.get(reverse('sponsorships-manage'), {'status': status})
            self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('sponsorships-manage'))
        self.assertContains(response, 'Baumpatenschaft')
        self.assertContains(response, 'Bienenpatenschaft')
        # dropdown in the admin menu, open on sponsorship pages
        self.assertContains(response, 'href="%s?status=active"' % reverse('sponsorships-manage'))
        self.assertContains(response, 'href="%s"' % reverse('sponsorships-types'))
        self.assertContains(response, 'href="%s"' % reverse('sponsorships-create'))
        self.assertContains(response, 'collapse show" id="sponsorshipsman"')
        self.assertContains(response, '<ul class="nav nav-tabs')

    def test_one_row_per_member(self):
        today = datetime.date.today()
        for _ in range(3):
            Sponsorship.objects.create(member=self.member, type=self.tree, activation_date=today)
        Sponsorship.objects.create(member=self.member, type=self.bee, activation_date=today)
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('sponsorships-manage'))
        members = response.context['members']
        self.assertEqual(len(members), 1)
        self.assertEqual([line['count'] for line in members[0]['lines']], [3, 1])
        self.assertEqual(members[0]['annual_total'], 3 * self.tree.annual_fee + self.bee.annual_fee)
        self.assertContains(response, 'Patenschaft 3 von 3')  # menu to choose which one to edit
        self.assertContains(response, 'Summe pro Jahr')

    def test_no_access_without_permission(self):
        self.client.force_login(self.member.user)
        response = self.client.get(reverse('sponsorships-manage'))
        self.assertNotEqual(response.status_code, 200)

    def test_django_admin(self):
        Sponsorship.objects.create(member=self.member, type=self.tree, activation_date=datetime.date.today())
        self.client.force_login(self.admin.user)
        for url in (reverse('admin:huebhof_patenschaften_sponsorship_changelist'),
                    reverse('admin:huebhof_patenschaften_sponsorshiptype_changelist'),
                    reverse('admin:juntagrico_member_change', args=[self.member.id])):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_admin_notification(self):
        perm = Permission.objects.get(codename='notified_on_sponsorship_creation')
        self.admin.user.user_permissions.add(perm)
        self.client.force_login(self.member.user)
        mail.outbox.clear()
        self.client.post(reverse('sponsorships-mine'), {f'type_{self.tree.id}': 1})
        self.assertEqual(len(mail.outbox), 2)  # confirmation + admin
        self.assertIn(self.admin.email, mail.outbox[1].bcc)
        self.assertIn(reverse('sponsorships-pending'), mail.outbox[1].body)


class ManagementTests(SponsorshipTestCase):
    def test_type_create_edit_delete(self):
        self.client.force_login(self.admin.user)
        self.assertContains(self.client.get(reverse('sponsorships-types')), 'Baumpatenschaft')
        self.assertEqual(self.client.get(reverse('sponsorships-type-new')).status_code, 200)
        response = self.client.post(reverse('sponsorships-type-new'), {
            'name': 'Hühnerpatenschaft', 'description': 'Gack', 'annual_fee': '80', 'visible': 'on',
            'sort_order': '3'})
        self.assertRedirects(response, reverse('sponsorships-types'))
        chicken = SponsorshipType.objects.get(name='Hühnerpatenschaft')
        self.assertEqual(chicken.annual_fee, Decimal('80'))
        response = self.client.post(reverse('sponsorships-type', args=[chicken.id]), {
            'name': 'Huhn', 'annual_fee': '90', 'sort_order': '3'})
        self.assertRedirects(response, reverse('sponsorships-types'))
        chicken.refresh_from_db()
        self.assertEqual((chicken.name, chicken.visible), ('Huhn', False))
        self.client.post(reverse('sponsorships-type', args=[chicken.id]), {'delete': ''})
        self.assertFalse(SponsorshipType.objects.filter(id=chicken.id).exists())

    def test_type_with_sponsorships_cannot_be_deleted(self):
        Sponsorship.objects.create(member=self.member, type=self.tree)
        self.client.force_login(self.admin.user)
        self.client.post(reverse('sponsorships-type', args=[self.tree.id]), {'delete': ''})
        self.assertTrue(SponsorshipType.objects.filter(id=self.tree.id).exists())

    def test_create(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('sponsorships-create'), {'member': self.member2.id})
        self.assertContains(response, f'<option value="{self.member2.id}" selected>')
        # buttons with exactly one style each (no btn-primary mixed in)
        self.assertContains(response, 'class="btn btn-outline-success"')
        self.assertNotContains(response, 'btn-primary')
        mail.outbox.clear()
        response = self.client.post(reverse('sponsorships-create'), {
            'member': self.member2.id, 'type': self.tree.id, 'quantity': 3, 'annual_fee': '',
            'order_date': '2026-02-01', 'activation_date': '2026-03-01', 'notes': 'Telefon',
            'send_confirmation': 'on'})
        self.assertRedirects(response, reverse('sponsorships-manage'))
        created = Sponsorship.objects.filter(member=self.member2)
        self.assertEqual(created.count(), 3)
        s = created.first()
        self.assertEqual((s.annual_fee, s.activation_date, s.notes),
                         (Decimal('120'), datetime.date(2026, 3, 1), 'Telefon'))
        self.assertEqual(len(mail.outbox), 1)
        # own fee, without activation, without mail, "create another"
        mail.outbox.clear()
        response = self.client.post(reverse('sponsorships-create'), {
            'member': self.member3.id, 'type': self.bee.id, 'quantity': 1, 'annual_fee': '75',
            'order_date': '2026-02-01', 'activation_date': '', 'another': ''})
        self.assertRedirects(response, reverse('sponsorships-create'))
        s = Sponsorship.objects.get(member=self.member3)
        self.assertEqual((s.annual_fee, s.status), (Decimal('75'), 'ordered'))
        self.assertEqual(len(mail.outbox), 0)

    def test_edit_and_cancel(self):
        s = Sponsorship.objects.create(member=self.member, type=self.tree, activation_date=datetime.date.today())
        self.client.force_login(self.admin.user)
        url = reverse('sponsorships-edit', args=[s.id])
        self.assertContains(self.client.get(url), 'Kündigen')
        response = self.client.post(url, {'type': self.tree.id, 'annual_fee': '100',
                                           'order_date': s.order_date.isoformat(),
                                           'activation_date': s.activation_date.isoformat(), 'notes': 'Rabatt'})
        self.assertRedirects(response, reverse('sponsorships-manage'))
        s.refresh_from_db()
        self.assertEqual((s.annual_fee, s.notes), (Decimal('100'), 'Rabatt'))
        self.client.post(url, {'cancel': ''})
        s.refresh_from_db()
        self.assertEqual(s.status, 'canceled')
        self.assertNotContains(self.client.get(url), 'name="cancel"')

    def test_overview_links_frontend(self):
        s = Sponsorship.objects.create(member=self.member, type=self.tree, activation_date=datetime.date.today())
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('sponsorships-manage'))
        for url in (reverse('sponsorships-create'), reverse('sponsorships-types'),
                    reverse('sponsorships-edit', args=[s.id]), reverse('sponsorships-type', args=[self.tree.id])):
            self.assertContains(response, f'href="{url}"')

    def test_no_access_without_permission(self):
        self.client.force_login(self.member.user)
        s = Sponsorship.objects.create(member=self.member, type=self.tree)
        for url in (reverse('sponsorships-types'), reverse('sponsorships-type-new'),
                    reverse('sponsorships-create'), reverse('sponsorships-edit', args=[s.id])):
            self.assertNotEqual(self.client.get(url).status_code, 200, url)


class PermissionTests(SponsorshipTestCase):
    """Partial permissions: menu, links and pages match the granted permissions."""

    def login_with(self, *codenames):
        user = self.member2.user
        user.user_permissions.set(Permission.objects.filter(
            content_type__app_label='huebhof_patenschaften', codename__in=codenames))
        self.client.force_login(user)

    def menu(self):
        return self.client.get(reverse('home')).content.decode()

    def assertAllowed(self, url, allowed=True):
        status = self.client.get(url).status_code
        if allowed:
            self.assertEqual(status, 200, url)
        else:
            self.assertIn(status, (302, 403), url)

    def setUp(self):
        self.s = Sponsorship.objects.create(member=self.member, type=self.tree, activation_date=datetime.date.today())

    def test_no_permissions_no_menu(self):
        self.login_with()
        self.assertNotIn('sponsorshipsman', self.menu())

    def test_view_only(self):
        self.login_with('view_sponsorship')
        menu = self.menu()
        self.assertIn(reverse('sponsorships-manage') + '?status=active', menu)
        self.assertNotIn(reverse('sponsorships-create'), menu)
        self.assertNotIn(reverse('sponsorships-types'), menu)
        response = self.client.get(reverse('sponsorships-manage'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('sponsorships-edit', args=[self.s.id]))
        self.assertNotContains(response, reverse('sponsorships-type', args=[self.tree.id]))
        self.assertAllowed(reverse('sponsorships-edit', args=[self.s.id]), False)
        self.assertAllowed(reverse('sponsorships-create'), False)
        self.assertAllowed(reverse('sponsorships-types'), False)

    def test_edit(self):
        self.login_with('view_sponsorship', 'change_sponsorship')
        self.assertContains(self.client.get(reverse('sponsorships-manage')),
                            reverse('sponsorships-edit', args=[self.s.id]))
        self.assertAllowed(reverse('sponsorships-edit', args=[self.s.id]))

    def test_create_only(self):
        self.login_with('add_sponsorship')
        menu = self.menu()
        self.assertIn(reverse('sponsorships-create'), menu)
        self.assertNotIn(reverse('sponsorships-manage') + '?status=active', menu)
        self.assertAllowed(reverse('sponsorships-manage'), False)
        response = self.client.post(reverse('sponsorships-create'), {
            'member': self.member3.id, 'type': self.tree.id, 'quantity': 1,
            'order_date': '2026-02-01', 'activation_date': '2026-02-01'})
        # back to the form, not to the overview, which is not allowed
        self.assertRedirects(response, reverse('sponsorships-create'))
        self.assertTrue(Sponsorship.objects.filter(member=self.member3).exists())

    def test_types_view_only(self):
        self.login_with('view_sponsorshiptype')
        self.assertIn(reverse('sponsorships-types'), self.menu())
        response = self.client.get(reverse('sponsorships-types'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('sponsorships-type', args=[self.tree.id]))
        self.assertNotContains(response, reverse('sponsorships-type-new'))
        self.assertAllowed(reverse('sponsorships-type', args=[self.tree.id]), False)
        self.assertAllowed(reverse('sponsorships-type-new'), False)

    def test_types_manage_without_delete(self):
        self.login_with('view_sponsorshiptype', 'add_sponsorshiptype', 'change_sponsorshiptype')
        response = self.client.get(reverse('sponsorships-types'))
        self.assertContains(response, reverse('sponsorships-type', args=[self.hidden.id]))
        self.assertContains(response, reverse('sponsorships-type-new'))
        self.assertNotContains(self.client.get(reverse('sponsorships-type', args=[self.hidden.id])), 'name="delete"')
        response = self.client.post(reverse('sponsorships-type', args=[self.hidden.id]), {'delete': ''})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(SponsorshipType.objects.filter(id=self.hidden.id).exists())

    def test_new_type_only_with_add(self):
        self.login_with('change_sponsorshiptype')
        self.assertEqual(self.client.get(reverse('sponsorships-type-new')).status_code, 403)
        self.assertAllowed(reverse('sponsorships-type', args=[self.tree.id]))


class PendingTests(SponsorshipTestCase):
    def setUp(self):
        self.a = Sponsorship.objects.create(member=self.member, type=self.tree, order_date=datetime.date(2026, 3, 1))
        self.b = Sponsorship.objects.create(member=self.member, type=self.bee, order_date=datetime.date(2026, 4, 1))
        self.active = Sponsorship.objects.create(member=self.member2, type=self.tree,
                                                 activation_date=datetime.date(2026, 1, 1))

    def test_list_and_menu(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('sponsorships-pending'))
        self.assertContains(response, f'value="{self.a.id}"')
        self.assertContains(response, f'value="{self.b.id}"')
        self.assertNotContains(response, f'value="{self.active.id}"')
        self.assertContains(response, 'Bestellt am 01.03.2026')
        self.assertContains(response, 'href="%s"' % reverse('sponsorships-pending'))  # menu entry

    def test_checkboxes_belong_to_form(self):
        """Regression: same number for member and sponsorship led to duplicate HTML ids,
        the checkboxes were then not submitted."""
        self.client.force_login(self.admin.user)
        html = self.client.get(reverse('sponsorships-pending')).content.decode()
        html = html[html.index('id="filter-table"'):]  # only the table, the menu appears twice
        ids = re.findall(r'\sid="([^"]+)"', html)
        self.assertEqual(len(ids), len(set(ids)), 'duplicate HTML ids')
        forms = set(re.findall(r'<form[^>]*\sid="([^"]+)"', html))
        checkboxes = re.findall(r'<input type="checkbox" form="([^"]+)"[^>]*name="sponsorships\[\]"', html)
        self.assertTrue(checkboxes)
        for form_id in checkboxes:
            self.assertIn(form_id, forms)

    def test_apply_selected(self):
        self.client.force_login(self.admin.user)
        url = reverse('sponsorships-pending')
        response = self.client.post(reverse('sponsorships-pending-apply'),
                                    {'sponsorships[]': [self.a.id]}, HTTP_REFERER=url)
        self.assertRedirects(response, url)
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual((self.a.status, self.a.activation_date), ('active', datetime.date.today()))
        self.assertEqual(self.b.status, 'ordered')

    def test_with_change_date(self):
        self.client.force_login(self.admin.user)
        session = self.client.session
        session['changedate'] = '2026-05-01'
        session.save()
        self.client.post(reverse('sponsorships-pending-apply'), {'sponsorships[]': [self.a.id, self.b.id]})
        self.a.refresh_from_db()
        self.assertEqual(self.a.activation_date, datetime.date(2026, 5, 1))
        self.assertFalse(Sponsorship.objects.ordered().exists())

    def test_change_permission_required(self):
        user = self.member2.user
        user.user_permissions.set(Permission.objects.filter(codename='view_sponsorship'))
        self.client.force_login(user)
        self.assertNotIn(reverse('sponsorships-pending'), self.client.get(reverse('home')).content.decode())
        self.assertNotEqual(self.client.get(reverse('sponsorships-pending')).status_code, 200)
        response = self.client.post(reverse('sponsorships-pending-apply'), {'sponsorships[]': [self.a.id]})
        self.assertEqual(response.status_code, 403)
        self.a.refresh_from_db()
        self.assertEqual(self.a.status, 'ordered')


class CheckAndActivationTests(SponsorshipTestCase):
    """Orders are checked by admins: activate (confirmation mail) or reject (mail with reason)."""

    def setUp(self):
        self.a = Sponsorship.objects.create(member=self.member, type=self.tree)
        self.b = Sponsorship.objects.create(member=self.member, type=self.bee)
        self.client.force_login(self.admin.user)

    def test_order_mail_says_it_is_checked(self):
        self.client.force_login(self.member2.user)
        mail.outbox.clear()
        self.client.post(reverse('sponsorships-mine'), {f'type_{self.tree.id}': 1})
        self.assertIn('Wir prüfen, ob die Patenschaft möglich ist', mail.outbox[0].body)

    def test_pending_shows_occupancy(self):
        Sponsorship.objects.create(member=self.member2, type=self.tree, activation_date=datetime.date(2025, 1, 1))
        self.tree.max_count = 10
        self.tree.save()
        response = self.client.get(reverse('sponsorships-pending'))
        self.assertContains(response, 'insgesamt: 1 von max. 10 Plätzen belegt, 1 Bestellung offen')
        self.assertContains(response, reverse('sponsorships-pending-reject'))
        # reject asks for the reason in a dialog, the form carries it as hidden field
        self.assertContains(response, 'id="reject-modal"')
        self.assertContains(response, f'data-form="pending-form-{self.member.id}"')
        self.assertContains(response, '<input type="hidden" name="reason" value="">')

    def test_activate_sends_confirmation(self):
        mail.outbox.clear()
        self.client.post(reverse('sponsorships-pending-apply'), {'sponsorships[]': [self.a.id, self.b.id]})
        self.a.refresh_from_db()
        self.assertEqual(self.a.status, 'active')
        self.assertEqual(len(mail.outbox), 1)  # one mail per member
        self.assertEqual(mail.outbox[0].to, [self.member.email])
        self.assertIn('bestätigt', mail.outbox[0].subject)
        self.assertIn('Baumpatenschaft', mail.outbox[0].body)
        self.assertIn('Bienenpatenschaft', mail.outbox[0].body)

    def test_reject_with_reason(self):
        mail.outbox.clear()
        self.client.post(reverse('sponsorships-pending-reject'),
                         {'sponsorships[]': [self.a.id], 'reason': 'Alle Bäume sind vergeben.'})
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual((self.a.status, self.b.status), ('withdrawn', 'ordered'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('nicht annehmen', mail.outbox[0].body)
        self.assertIn('Alle Bäume sind vergeben.', mail.outbox[0].body)
        self.assertNotIn('Bienenpatenschaft', mail.outbox[0].body)

    def test_reject_needs_change_permission(self):
        user = self.member2.user
        user.user_permissions.set(Permission.objects.filter(codename='view_sponsorship'))
        self.client.force_login(user)
        response = self.client.post(reverse('sponsorships-pending-reject'), {'sponsorships[]': [self.a.id]})
        self.assertEqual(response.status_code, 403)
        self.a.refresh_from_db()
        self.assertEqual(self.a.status, 'ordered')


class MaxCountTests(SponsorshipTestCase):
    """Optional maximum per type: running and ordered sponsorships count."""

    def setUp(self):
        self.tree.max_count = 2
        self.tree.save()
        Sponsorship.objects.create(member=self.member2, type=self.tree)
        self.client.force_login(self.member.user)

    def test_available_shown_and_enforced(self):
        self.assertEqual(self.tree.available_count(), 1)
        self.assertIsNone(self.bee.available_count())
        self.assertContains(self.client.get(reverse('sponsorships-mine')), 'Noch 1 verfügbar')
        response = self.client.post(reverse('sponsorships-mine'), {f'type_{self.tree.id}': 2})
        self.assertContains(response, 'Höchstens 1 möglich.')
        self.assertEqual(Sponsorship.objects.filter(member=self.member).count(), 0)
        self.client.post(reverse('sponsorships-mine'), {f'type_{self.tree.id}': 1})
        self.assertEqual(Sponsorship.objects.filter(member=self.member).count(), 1)

    def test_fully_booked(self):
        Sponsorship.objects.create(member=self.member3, type=self.tree)
        response = self.client.get(reverse('sponsorships-mine'))
        self.assertContains(response, 'Zurzeit ausgebucht')
        self.assertContains(response, f'name="type_{self.tree.id}"')
        self.assertRegex(response.content.decode(), rf'name="type_{self.tree.id}"[^>]*disabled')
        # a disabled field is ignored, other types can still be ordered
        self.client.post(reverse('sponsorships-mine'), {f'type_{self.tree.id}': 1, f'type_{self.bee.id}': 1})
        self.assertEqual(list(Sponsorship.objects.filter(member=self.member).values_list('type', flat=True)),
                         [self.bee.id])

    def test_withdrawn_and_ended_do_not_count(self):
        Sponsorship.objects.filter(member=self.member2).get().cancel()
        Sponsorship.objects.create(member=self.member3, type=self.tree, activation_date=datetime.date(2020, 1, 1),
                                   end_date=datetime.date(2021, 12, 31))
        self.assertEqual(self.tree.available_count(), 2)

    def test_types_list_and_form(self):
        self.client.force_login(self.admin.user)
        self.assertContains(self.client.get(reverse('sponsorships-types')), '1 / 2')
        self.assertContains(self.client.get(reverse('sponsorships-type', args=[self.tree.id])), 'name="max_count"')


class ExportTests(SponsorshipTestCase):
    def setUp(self):
        Sponsorship.objects.create(member=self.member, type=self.tree, activation_date=datetime.date.today(),
                                   notes='aktiv')
        Sponsorship.objects.create(member=self.member2, type=self.bee, notes='nur bestellt')

    def test_csv_with_status_filter(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('sponsorships-export'), {'status': 'active', 'format': 'csv'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('patenschaften_active_', response['Content-Disposition'])
        content = response.content.decode()
        self.assertIn('Vorname,Nachname,E-Mail,Typ,Jahresbeitrag,Bestellt am', content)  # readable headers
        self.assertIn('Baumpatenschaft', content)
        self.assertNotIn('nur bestellt', content)

    def test_excel(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('sponsorships-export'), {'status': 'all', 'format': 'xlsx'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'PK'))  # xlsx is a zip archive
        self.assertTrue(response['Content-Disposition'].endswith('.xlsx"'))

    def test_button_in_list(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('sponsorships-manage'), {'status': 'canceled'})
        self.assertContains(response, reverse('sponsorships-export') + '?status=canceled&format=xlsx')
        self.assertNotContains(response, reverse('admin:huebhof_patenschaften_sponsorship_export'))

    def test_view_permission_is_enough_without_staff(self):
        user = self.member2.user
        user.user_permissions.set(Permission.objects.filter(codename='view_sponsorship'))
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('sponsorships-export')).status_code, 200)

    def test_without_permission(self):
        self.client.force_login(self.member.user)
        self.assertNotEqual(self.client.get(reverse('sponsorships-export')).status_code, 200)


class NoTypesTests(SponsorshipTestCase):
    def setUp(self):
        SponsorshipType.objects.update(visible=False)

    def test_member_sees_notice(self):
        self.client.force_login(self.member.user)
        response = self.client.get(reverse('sponsorships-mine'))
        self.assertContains(response, 'Zurzeit werden keine Patenschaften angeboten')
        self.assertNotContains(response, 'Verbindlich bestellen')
        self.assertNotContains(response, reverse('sponsorships-types'))

    def test_admin_sees_link_to_types(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('sponsorships-mine'))
        self.assertContains(response, 'Hinweis für Admins')
        self.assertContains(response, reverse('sponsorships-types'))

    def test_with_type_order_form(self):
        self.tree.visible = True
        self.tree.save()
        self.client.force_login(self.member.user)
        response = self.client.get(reverse('sponsorships-mine'))
        self.assertContains(response, 'Verbindlich bestellen')
        self.assertNotContains(response, 'Zurzeit werden keine Patenschaften angeboten')
