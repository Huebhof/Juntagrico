import datetime
from decimal import Decimal

from django.core import mail
from django.template.defaultfilters import floatformat
from django.urls import resolve, reverse

from juntagrico_billing.models.bill import Bill, BillItem, BillItemType, BusinessYear
from juntagrico_billing.models.settings import Settings
from juntagrico_billing.util.billing import recalc_bill

from huebhof_patenschaften.models import Sponsorship, SponsorshipType
from huebhof_patenschaften import tests as core_tests
from huebhof_patenschaften.tests import SponsorshipTestCase

from . import billing, views
from .models import SponsorshipTypeBilling


class BillingTests(SponsorshipTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Settings.objects.create(debtor_account='1100')
        cls.year = BusinessYear.objects.create(
            start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 12, 31), name='2026')
        cls.tree_item_type = BillItemType.objects.create(name='Baumpatenschaft', booking_account='3400')
        SponsorshipTypeBilling.objects.create(type=cls.tree, bill_item_type=cls.tree_item_type)
        activation = datetime.date(2025, 3, 1)
        # member4 has no subscription, member has one
        cls.s_tree = Sponsorship.objects.create(member=cls.member4, type=cls.tree, activation_date=activation)
        cls.s_bee = Sponsorship.objects.create(member=cls.member4, type=cls.bee, activation_date=activation)
        # not billable: withdrawn, ended before the year, activated after the year, fee 0
        withdrawn = Sponsorship.objects.create(member=cls.member2, type=cls.tree)
        withdrawn.cancel()
        Sponsorship.objects.create(member=cls.member3, type=cls.tree, activation_date=activation,
                                   end_date=datetime.date(2025, 12, 31))
        Sponsorship.objects.create(member=cls.member3, type=cls.bee, activation_date=datetime.date(2027, 1, 1))
        Sponsorship.objects.create(member=cls.member3, type=cls.bee, activation_date=activation,
                                   custom_annual_fee=Decimal('0'))

    @staticmethod
    def items_of(sponsorship):
        return BillItem.objects.filter(sponsorship_link__sponsorship=sponsorship)

    def test_billable(self):
        self.assertEqual(set(billing.billable(self.year)), {self.s_tree, self.s_bee})

    def test_new_bill(self):
        created, extended = billing.create_bills(self.year, billing.billable(self.year))
        self.assertEqual((len(created), len(extended)), (1, 0))
        bill = created[0]
        self.assertEqual(bill.member, self.member4)
        self.assertEqual(bill.amount, 170.0)
        self.assertFalse(bill.published)
        # own item type with booking account, otherwise default "Patenschaft"
        item_tree = self.items_of(self.s_tree).get()
        self.assertEqual(item_tree.custom_item_type, self.tree_item_type)
        self.assertEqual(str(item_tree), 'Baumpatenschaft')
        self.assertEqual(str(self.items_of(self.s_bee).get()), 'Patenschaft Bienenpatenschaft')
        # not a second time in the same year, again in the following year
        self.assertFalse(billing.billable(self.year).exists())
        next_year = BusinessYear.objects.create(
            start_date=datetime.date(2027, 1, 1), end_date=datetime.date(2027, 12, 31), name='2027')
        # the two billed ones and the one active from 2027
        self.assertEqual(billing.billable(next_year).count(), 3)

    def test_current_type_price_and_custom_fee(self):
        self.tree.annual_fee = Decimal('150')
        self.tree.save()
        self.s_bee.custom_annual_fee = Decimal('30')
        self.s_bee.save()
        bill = billing.create_bills(self.year, billing.billable(self.year))[0][0]
        self.assertEqual(bill.amount, 180.0)

    def test_add_to_unpublished_bill(self):
        existing = Bill.objects.create(business_year=self.year, member=self.member4, amount=500.0,
                                       bill_date=datetime.date(2026, 1, 1), booking_date=datetime.date(2026, 1, 1))
        BillItem.objects.create(bill=existing, description='Ernteanteil', amount=500.0)
        created, extended = billing.create_bills(self.year, billing.billable(self.year))
        self.assertEqual((created, extended), ([], [existing]))
        existing.refresh_from_db()
        self.assertEqual(existing.amount, 670.0)
        # recalculation by juntagrico_billing keeps the sponsorships
        recalc_bill(existing)
        existing.refresh_from_db()
        self.assertEqual(existing.items.filter(sponsorship_link__isnull=False).count(), 2)

    def test_published_bill_stays_unchanged(self):
        Bill.objects.create(business_year=self.year, member=self.member4, amount=500.0, published=True,
                            bill_date=datetime.date(2026, 1, 1), booking_date=datetime.date(2026, 1, 1))
        created, extended = billing.create_bills(self.year, billing.billable(self.year))
        self.assertEqual((len(created), len(extended)), (1, 0))

    def test_jb_urls_point_to_addon(self):
        self.assertEqual(resolve(reverse('jb:pending-bills-list')).func, views.pending_bills)
        self.assertEqual(resolve(reverse('jb:bills-generate')).func, views.bills_generate)
        self.assertEqual(resolve(reverse('jb:bill-recalc', args=[1])).func, views.bill_recalc)

    def test_pending_bills(self):
        self.client.force_login(self.admin.user)
        self.client.post(reverse('jb:bills-setyear'), {'year': '2026'})
        response = self.client.get(reverse('jb:pending-bills-list'))
        self.assertContains(response, '1 &times; Baumpatenschaft')
        self.assertContains(response, '1 &times; Bienenpatenschaft')
        self.assertContains(response, 'data-order="170.00"')  # amount without subscription
        self.assertNotContains(response, 'Patenschaften verrechnen')  # no separate menu entry anymore

    def test_generate_all_one_bill_per_member(self):
        with_subscription = Sponsorship.objects.create(member=self.member, type=self.tree,
                                                       activation_date=datetime.date(2025, 3, 1))
        self.client.force_login(self.admin.user)
        self.client.post(reverse('jb:bills-setyear'), {'year': '2026'})
        response = self.client.post(reverse('jb:bills-generate'))
        self.assertRedirects(response, reverse('jb:unpublished-bills-list'))
        # member with subscription: one bill with subscription and sponsorship
        bill = self.member.bills.get(business_year=self.year)
        self.assertTrue(bill.items.filter(subscription_part__isnull=False).exists())
        self.assertEqual(list(bill.items.filter(sponsorship_link__isnull=False)), list(self.items_of(with_subscription)))
        self.assertAlmostEqual(bill.amount, sum(i.amount for i in bill.items.all()))
        # member without subscription: own bill with sponsorships only
        bill4 = self.member4.bills.get(business_year=self.year)
        self.assertEqual(bill4.amount, 170.0)
        self.assertFalse(billing.billable(self.year).exists())
        # bills are shown in the Django admin and on the edit page of the sponsorship
        bill_url = reverse('admin:juntagrico_billing_bill_change', args=[bill4.id])
        self.assertContains(self.client.get(
            reverse('admin:huebhof_patenschaften_sponsorship_change', args=[self.s_tree.id])), bill_url)
        self.assertContains(self.client.get(reverse('sponsorships-edit', args=[self.s_tree.id])), bill_url)

    def test_recalc_adds_sponsorships(self):
        bill = Bill.objects.create(business_year=self.year, member=self.member4, amount=0.0,
                                   bill_date=datetime.date(2026, 1, 1), booking_date=datetime.date(2026, 1, 1))
        self.client.force_login(self.admin.user)
        next_url = reverse('admin:juntagrico_billing_bill_change', args=[bill.id])
        response = self.client.get(reverse('jb:bill-recalc', args=[bill.id]) + '?next=' + next_url)
        self.assertRedirects(response, next_url)
        bill.refresh_from_db()
        self.assertEqual(bill.amount, 170.0)
        # a second time changes nothing
        self.client.get(reverse('jb:bill-recalc', args=[bill.id]))
        bill.refresh_from_db()
        self.assertEqual(bill.items.count(), 2)

    def test_book_keepers_only(self):
        self.client.force_login(self.member.user)
        self.assertNotEqual(self.client.get(reverse('jb:pending-bills-list')).status_code, 200)
        self.client.post(reverse('jb:bills-generate'))
        self.assertFalse(Bill.objects.exists())


class ProRataTests(SponsorshipTestCase):
    """Like subscriptions: only the days within the business year are billed."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.year = BusinessYear.objects.create(
            start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 12, 31), name='2026')
        cls.chicken = SponsorshipType.objects.create(name='Huhn', annual_fee=Decimal('36'))

    def test_full_year(self):
        s = Sponsorship.objects.create(member=self.member4, type=self.chicken, activation_date=datetime.date(2025, 5, 1))
        self.assertEqual(billing.amount(s, self.year), Decimal('36'))

    def test_start_during_year(self):
        # 16.10.-31.12.: 77 of 365 days, 36 * 77 / 365 = 7.59 -> 7.60
        s = Sponsorship.objects.create(member=self.member4, type=self.chicken,
                                       activation_date=datetime.date(2026, 10, 16))
        self.assertEqual(billing.amount(s, self.year), Decimal('7.6'))
        bill = billing.create_bills(self.year, [s])[0][0]
        item = bill.items.get()
        self.assertEqual(item.amount, 7.6)
        self.assertEqual(bill.amount, 7.6)
        self.assertIn('(16.10.2026–31.12.2026)', str(item))
        # following year: full fee, no period on the bill
        next_year = BusinessYear.objects.create(
            start_date=datetime.date(2027, 1, 1), end_date=datetime.date(2027, 12, 31), name='2027')
        item = billing.create_bills(next_year, [s])[0][0].items.get()
        self.assertEqual(item.amount, 36.0)
        self.assertNotIn('(', str(item))

    def test_end_during_year(self):
        # 1.1.-30.6.: 181 of 365 days, 120 * 181 / 365 = 59.51 -> 59.50
        s = Sponsorship.objects.create(member=self.member4, type=self.tree, activation_date=datetime.date(2025, 1, 1),
                                       end_date=datetime.date(2026, 6, 30))
        self.assertEqual(billing.amount(s, self.year), Decimal('59.5'))

    def test_pending_bills_show_pro_rata_amount(self):
        Settings.objects.create(debtor_account='1100')
        Sponsorship.objects.create(member=self.member4, type=self.chicken, activation_date=datetime.date(2026, 10, 16))
        self.client.force_login(self.admin.user)
        self.client.post(reverse('jb:bills-setyear'), {'year': '2026'})
        self.assertContains(self.client.get(reverse('jb:pending-bills-list')), 'data-order="7.60"')

    def test_recalc_after_leaving(self):
        s = Sponsorship.objects.create(member=self.member4, type=self.tree, activation_date=datetime.date(2025, 1, 1))
        bill = billing.create_bills(self.year, [s])[0][0]
        self.assertEqual(bill.amount, 120.0)
        s.end_date = datetime.date(2026, 6, 30)
        s.save()
        self.client.force_login(self.admin.user)
        self.client.get(reverse('jb:bill-recalc', args=[bill.id]))
        bill.refresh_from_db()
        self.assertEqual(bill.items.count(), 1)
        self.assertEqual(bill.amount, 59.5)
        self.assertIn('(01.01.2026–30.06.2026)', str(bill.items.get()))


class BilledOverviewTests(SponsorshipTestCase):
    """The overview of the management page shows what was billed in the current business year."""

    def test_billed_per_type(self):
        year = BusinessYear.objects.create(
            start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 12, 31), name='2026')
        s = Sponsorship.objects.create(member=self.member4, type=self.tree, activation_date=datetime.date(2025, 1, 1))
        billing.create_bills(year, [s])
        billed = billing.billed_per_type(datetime.date(2026, 6, 1))
        self.assertEqual((billed['year'], billed['per_type'], billed['total']),
                         ('2026', {self.tree.id: Decimal('120')}, Decimal('120')))
        self.assertIsNone(billing.billed_per_type(datetime.date(2030, 6, 1)))

    def test_column_in_overview(self):
        today = datetime.date.today()
        year = BusinessYear.objects.create(start_date=today.replace(month=1, day=1),
                                           end_date=today.replace(month=12, day=31), name='Laufend')
        s = Sponsorship.objects.create(member=self.member4, type=self.tree,
                                       activation_date=today.replace(year=today.year - 1))
        billing.create_bills(year, [s])
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('sponsorships-manage'))
        self.assertContains(response, 'Verrechnet Laufend')
        self.assertContains(response, '<th class="text-right">120 CHF</th>', html=False)


class FirstYearShareTests(SponsorshipTestCase):
    """Pro rata amount shown when ordering (card, signup summary, confirmation mail)."""

    def test_calculation(self):
        share = billing.first_year_share(Decimal('36'), datetime.date(2026, 10, 16))
        self.assertEqual(share['amount'], Decimal('7.60'))
        self.assertEqual((share['start'], share['end'], share['year']),
                         (datetime.date(2026, 10, 16), datetime.date(2026, 12, 31), '2026'))
        self.assertEqual(billing.first_year_share(Decimal('36'), datetime.date(2026, 10, 16), 2)['amount'],
                         Decimal('15.20'))
        # first day of the business year: full annual fee, nothing to show
        self.assertIsNone(billing.first_year_share(Decimal('36'), datetime.date(2026, 1, 1)))

    def expected(self, annual_fee, quantity=1):
        share = billing.first_year_share(annual_fee, quantity=quantity)
        return share and floatformat(share['amount'], '-2u')  # same format as the price filter

    def test_card_in_member_area(self):
        self.client.force_login(self.member.user)
        response = self.client.get(reverse('sponsorships-mine'))
        expected = self.expected(self.tree.annual_fee)
        if expected:
            self.assertContains(response, 'sponsorship-first-year')
            self.assertContains(response, f'ca. {expected} CHF')
        else:
            self.assertNotContains(response, 'sponsorship-first-year')

    subscription_selection = staticmethod(core_tests.SignupTests.subscription_selection)

    def test_signup_summary(self):
        # walk through the order process with the steps of the core tests
        core_tests.SignupTests._until_sponsorships(self)
        self.client.post(reverse('cs-sponsorships'), {f'type_{self.tree.id}': 2})
        core_tests.SignupTests._rest_until_summary(self)
        response = self.client.get(reverse('cs-summary'))
        self.assertContains(response, '2 &times; Baumpatenschaft: 240 CHF')
        expected = self.expected(self.tree.annual_fee, 2)
        if expected:
            self.assertContains(response, f'anteilig ab heute: ca. {expected} CHF')

    def test_confirmation_mail(self):
        self.client.force_login(self.member.user)
        mail.outbox.clear()
        self.client.post(reverse('sponsorships-mine'), {f'type_{self.tree.id}': 2})
        body = mail.outbox[0].body
        self.assertIn('Baumpatenschaft: 120 CHF pro Jahr', body)
        expected = self.expected(self.tree.annual_fee, 2)
        if expected:
            self.assertIn(f'(anteilig): ca. {expected} CHF', body)
        else:
            self.assertNotIn('anteilig', body)


class PendingAndActivationTests(SponsorshipTestCase):
    """Pro rata amount on the check page (from the change date) and in the confirmation mail."""

    def setUp(self):
        self.chicken = SponsorshipType.objects.create(name='Huhn', annual_fee=Decimal('36'))
        self.s = Sponsorship.objects.create(member=self.member, type=self.chicken)
        self.client.force_login(self.admin.user)
        session = self.client.session
        session['changedate'] = '2026-10-16'
        session.save()

    def test_pending_shows_amount_from_change_date(self):
        self.assertContains(self.client.get(reverse('sponsorships-pending')), '2026: 7.60 CHF ab 16.10.')

    def test_confirmation_mail_with_amount(self):
        mail.outbox.clear()
        self.client.post(reverse('sponsorships-pending-apply'), {'sponsorships[]': [self.s.id]})
        body = mail.outbox[0].body
        self.assertIn('gültig ab 16.10.2026', body)
        self.assertIn('für 2026 anteilig: 7.60 CHF (16.10.–31.12.2026)', body)


class TypeSettingsTests(SponsorshipTestCase):
    """The bill item type is set on the management pages of huebhof_patenschaften (form extension)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.item_type = BillItemType.objects.create(name='Bienen', booking_account='3410')

    def test_set_and_clear_in_frontend(self):
        self.client.force_login(self.admin.user)
        url = reverse('sponsorships-type', args=[self.bee.id])
        self.assertContains(self.client.get(url), 'name="bill_item_type"')
        data = {'name': self.bee.name, 'annual_fee': '50', 'visible': 'on', 'sort_order': '2'}
        response = self.client.post(url, dict(data, bill_item_type=self.item_type.id))
        self.assertRedirects(response, reverse('sponsorships-types'))
        self.assertEqual(SponsorshipTypeBilling.objects.get(type=self.bee).bill_item_type, self.item_type)
        # shown in the list of types and preselected in the form
        self.assertContains(self.client.get(reverse('sponsorships-types')), '<td>Bienen</td>')
        self.assertContains(self.client.get(url), f'<option value="{self.item_type.id}" selected>')
        # cleared
        self.client.post(url, dict(data, bill_item_type=''))
        self.assertIsNone(SponsorshipTypeBilling.objects.get(type=self.bee).bill_item_type)

    def test_new_type_with_bill_item_type(self):
        self.client.force_login(self.admin.user)
        self.client.post(reverse('sponsorships-type-new'), {
            'name': 'Hühnerpatenschaft', 'annual_fee': '80', 'sort_order': '3', 'bill_item_type': self.item_type.id})
        self.assertEqual(SponsorshipTypeBilling.objects.get(type__name='Hühnerpatenschaft').bill_item_type,
                         self.item_type)

    def test_django_admin_inline(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('admin:huebhof_patenschaften_sponsorshiptype_change', args=[self.bee.id]))
        self.assertContains(response, 'billing-0-bill_item_type')
