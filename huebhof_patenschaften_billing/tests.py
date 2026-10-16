import datetime
from decimal import Decimal

from django.urls import resolve, reverse

from juntagrico_billing.models.bill import Bill, BillItem, BillItemType, BusinessYear
from juntagrico_billing.models.settings import Settings
from juntagrico_billing.util.billing import recalc_bill

from huebhof_patenschaften.models import Sponsorship
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
        Sponsorship.objects.create(member=cls.member3, type=cls.bee, activation_date=activation, annual_fee=Decimal('0'))

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
