import datetime
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.core import mail
from django.test import override_settings
from django.urls import resolve, reverse

from juntagrico.entity.depot import Depot
from juntagrico.entity.subtypes import SubscriptionType
from juntagrico.tests import JuntagricoTestCase

from juntagrico_billing.models.bill import Bill, BillItem, BillItemType, BusinessYear
from juntagrico_billing.models.settings import Settings
from juntagrico_billing.util.billing import recalc_bill

from . import billing
from .models import Patenschaft, PatenschaftTyp

SIGNUP_MANAGER = 'huebhof_patenschaften.signup.PatenschaftSignupManager'


@override_settings(SIGNUP_MANAGER=SIGNUP_MANAGER, ENABLE_SHARES=False,
                   BUSINESS_YEAR_START={'day': 1, 'month': 1}, BUSINESS_YEAR_CANCELATION_MONTH=9)
class PatenschaftTestCase(JuntagricoTestCase):
    with_extra_subs = False

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.baum = PatenschaftTyp.objects.create(name='Baumpatenschaft', jahresbeitrag=Decimal('120'), sortierung=1)
        cls.biene = PatenschaftTyp.objects.create(name='Bienenpatenschaft', jahresbeitrag=Decimal('50'), sortierung=2)
        cls.versteckt = PatenschaftTyp.objects.create(name='Alt', jahresbeitrag=Decimal('10'), sichtbar=False)


class NaechstesEndeTests(PatenschaftTestCase):
    def test_vor_kuendigungsfrist_ende_jahr(self):
        self.assertEqual(Patenschaft.naechstes_ende(datetime.date(2026, 9, 30)), datetime.date(2026, 12, 31))

    def test_nach_kuendigungsfrist_ende_folgejahr(self):
        self.assertEqual(Patenschaft.naechstes_ende(datetime.date(2026, 10, 1)), datetime.date(2027, 12, 31))


class LebenszyklusTests(PatenschaftTestCase):
    def test_status_und_kuendigung(self):
        p = Patenschaft.objects.create(member=self.member, typ=self.baum, aktiviert_am=datetime.date.today())
        self.assertEqual(p.jahresbeitrag, Decimal('120'))
        self.assertEqual(p.status, 'aktiv')
        p.kuendigen()
        self.assertEqual(p.status, 'gekuendigt')
        self.assertEqual(p.ende, Patenschaft.naechstes_ende())
        self.assertIn(p, Patenschaft.objects.gekuendigt())
        self.assertFalse(p.kann_gekuendigt_werden)

    def test_bestellte_wird_storniert(self):
        p = Patenschaft.objects.create(member=self.member, typ=self.baum)
        self.assertEqual(p.status, 'bestellt')
        self.assertIn(p, Patenschaft.objects.bestellt())
        p.kuendigen()
        self.assertEqual(p.status, 'storniert')
        self.assertNotIn(p, Patenschaft.objects.offen())

    def test_preisaenderung_wirkt_nicht_rueckwirkend(self):
        p = Patenschaft.objects.create(member=self.member, typ=self.baum)
        self.baum.jahresbeitrag = Decimal('200')
        self.baum.save()
        p.refresh_from_db()
        self.assertEqual(p.jahresbeitrag, Decimal('120'))

    def test_austritt_beendet_patenschaften(self):
        p = Patenschaft.objects.create(member=self.member5, typ=self.baum, aktiviert_am=datetime.date(2020, 1, 1))
        offen = Patenschaft.objects.create(member=self.member5, typ=self.biene)
        heute = datetime.date.today()
        self.member5.deactivation_date = heute
        self.member5.save()
        p.refresh_from_db()
        offen.refresh_from_db()
        self.assertEqual(p.ende, heute)
        self.assertEqual(offen.status, 'storniert')


class SignupTests(PatenschaftTestCase):
    @staticmethod
    def sub_auswahl():
        ids = SubscriptionType.objects.values_list('id', flat=True)
        return {f'amount[{type_id}]': 1 if i == 0 else 0 for i, type_id in enumerate(ids)}

    def _bis_patenschaften(self):
        """Mitglied ohne Ernteanteil (member4) bestellt einen Ernteanteil."""
        self.client.force_login(self.member4.user)
        response = self.client.post(reverse('cs-subscription'), self.sub_auswahl())
        self.assertRedirects(response, reverse('cs-patenschaften'), fetch_redirect_response=False)
        response = self.client.get(reverse('cs-patenschaften'))
        self.assertContains(response, 'Baumpatenschaft')
        self.assertNotContains(response, '>Alt<')

    def _rest_bis_summary(self):
        response = self.client.post(reverse('cs-depot'), {'depot': Depot.objects.values_list('id', flat=True)[0]})
        self.assertRedirects(response, reverse('cs-start'), fetch_redirect_response=False)
        response = self.client.post(reverse('cs-start'), {'start_date': '01.01.2030'})
        self.assertRedirects(response, reverse('cs-co-members'), fetch_redirect_response=False)
        response = self.client.get(reverse('cs-co-members'), {'next': '1'})
        self.assertRedirects(response, reverse('cs-summary'), fetch_redirect_response=False)

    def test_mit_patenschaften(self):
        self._bis_patenschaften()
        response = self.client.post(reverse('cs-patenschaften'),
                                    {f'typ_{self.baum.id}': 2, f'typ_{self.biene.id}': 1})
        self.assertRedirects(response, reverse('cs-depot'), fetch_redirect_response=False)
        self._rest_bis_summary()
        response = self.client.get(reverse('cs-summary'))
        self.assertContains(response, '2 &times; Baumpatenschaft')
        self.assertContains(response, "240.00")
        mail.outbox.clear()
        response = self.client.post(reverse('cs-summary'), {'comment': ''})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Patenschaft.objects.filter(member=self.member4, typ=self.baum).count(), 2)
        # wie bei den Ernteanteilen: bestellt, Aktivierung durch Admins
        self.assertEqual(Patenschaft.objects.filter(member=self.member4).bestellt().count(), 3)
        self.assertFalse(Patenschaft.objects.filter(member=self.member4).aktiv().exists())
        self.assertTrue(any('Baumpatenschaft' in m.body for m in mail.outbox))

    def test_ohne_patenschaft(self):
        self._bis_patenschaften()
        response = self.client.post(reverse('cs-patenschaften'), {})
        self.assertRedirects(response, reverse('cs-depot'), fetch_redirect_response=False)
        self._rest_bis_summary()
        response = self.client.get(reverse('cs-summary'))
        self.assertContains(response, 'Keine Patenschaft')
        self.client.post(reverse('cs-summary'), {'comment': ''})
        self.assertFalse(Patenschaft.objects.filter(member=self.member4).exists())

    def test_bearbeiten_aus_summary(self):
        self._bis_patenschaften()
        self.client.post(reverse('cs-patenschaften'), {f'typ_{self.baum.id}': 1})
        self._rest_bis_summary()
        # wie in juntagrico: nach "?mod" landet man über einen Zwischenschritt wieder in der Zusammenfassung
        response = self.client.post(reverse('cs-patenschaften') + '?mod', {f'typ_{self.biene.id}': 3}, follow=True)
        self.assertEqual(response.redirect_chain[-1][0], reverse('cs-summary'))
        self.assertContains(response, '3 &times; Bienenpatenschaft')
        self.assertNotContains(response, 'Baumpatenschaft')

    @override_settings(PATENSCHAFTEN_IM_SIGNUP=False)
    def test_schritt_abschaltbar(self):
        self.client.force_login(self.member4.user)
        response = self.client.post(reverse('cs-subscription'), self.sub_auswahl())
        self.assertRedirects(response, reverse('cs-depot'), fetch_redirect_response=False)


class MitgliederbereichTests(PatenschaftTestCase):
    @override_settings(PATENSCHAFTEN_AUTO_AKTIVIEREN=True)
    def test_liste_bestellen_kuendigen(self):
        self.client.force_login(self.member.user)
        response = self.client.get(reverse('patenschaften-mine'))
        self.assertContains(response, 'keine Patenschaft')
        self.assertContains(response, 'href="%s"' % reverse('patenschaften-mine'))  # Menüpunkt

        # leere Bestellung wird abgelehnt
        response = self.client.post(reverse('patenschaften-mine'), {})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Patenschaft.objects.filter(member=self.member).exists())

        response = self.client.post(reverse('patenschaften-mine'), {f'typ_{self.biene.id}': 2})
        self.assertRedirects(response, reverse('patenschaften-mine'))
        self.assertEqual(Patenschaft.objects.filter(member=self.member).aktiv().count(), 2)
        response = self.client.get(reverse('patenschaften-mine'))
        self.assertContains(response, '100.00')

        p = Patenschaft.objects.filter(member=self.member).first()
        response = self.client.post(reverse('patenschaften-kuendigen', args=[p.id]))
        self.assertRedirects(response, reverse('patenschaften-mine'))
        p.refresh_from_db()
        self.assertEqual(p.status, 'gekuendigt')

    def test_fremde_patenschaft_nicht_kuendbar(self):
        p = Patenschaft.objects.create(member=self.member2, typ=self.baum, aktiviert_am=datetime.date.today())
        self.client.force_login(self.member.user)
        response = self.client.post(reverse('patenschaften-kuendigen', args=[p.id]))
        self.assertEqual(response.status_code, 404)

    def test_manuelle_aktivierung_ist_standard(self):
        self.client.force_login(self.member.user)
        self.client.post(reverse('patenschaften-mine'), {f'typ_{self.baum.id}': 2})
        p, storniert = Patenschaft.objects.filter(member=self.member)
        self.assertEqual(p.status, 'bestellt')
        self.assertContains(self.client.get(reverse('patenschaften-mine')), 'Bestellt')
        # noch nicht aktivierte Bestellung kündigen = stornieren
        self.client.post(reverse('patenschaften-kuendigen', args=[storniert.id]))
        storniert.refresh_from_db()
        self.assertEqual(storniert.status, 'storniert')
        # Admin aktiviert
        self.client.force_login(self.admin.user)
        response = self.client.post(reverse('patenschaften-pendent-anwenden'), {'patenschaften[]': [p.id]})
        self.assertEqual(response.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.status, 'aktiv')


class AdminTests(PatenschaftTestCase):
    def test_uebersicht(self):
        Patenschaft.objects.create(member=self.member, typ=self.baum, aktiviert_am=datetime.date.today())
        Patenschaft.objects.create(member=self.member2, typ=self.biene)
        self.client.force_login(self.admin.user)
        for status in ('aktiv', 'gekuendigt', 'alle', 'unbekannt'):
            response = self.client.get(reverse('patenschaften-manage'), {'status': status})
            self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('patenschaften-manage'))
        self.assertContains(response, 'Baumpatenschaft')
        self.assertContains(response, 'Bienenpatenschaft')
        # Aufklappmenü im Admin-Menü, auf Patenschaften-Seiten offen
        self.assertContains(response, 'href="%s?status=aktiv"' % reverse('patenschaften-manage'))
        self.assertContains(response, 'href="%s"' % reverse('patenschaften-typen'))
        self.assertContains(response, 'href="%s"' % reverse('patenschaften-erfassen'))
        self.assertContains(response, 'collapse show" id="patenschaftenman"')

    def test_kein_zugriff_ohne_recht(self):
        self.client.force_login(self.member.user)
        response = self.client.get(reverse('patenschaften-manage'))
        self.assertNotEqual(response.status_code, 200)

    def test_django_admin(self):
        Patenschaft.objects.create(member=self.member, typ=self.baum, aktiviert_am=datetime.date.today())
        self.client.force_login(self.admin.user)
        for url in (reverse('admin:huebhof_patenschaften_patenschaft_changelist'),
                    reverse('admin:huebhof_patenschaften_patenschafttyp_changelist'),
                    reverse('admin:juntagrico_member_change', args=[self.member.id])):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_admin_benachrichtigung(self):
        perm = Permission.objects.get(codename='notified_on_patenschaft_bestellung')
        self.admin.user.user_permissions.add(perm)
        self.client.force_login(self.member.user)
        mail.outbox.clear()
        self.client.post(reverse('patenschaften-mine'), {f'typ_{self.baum.id}': 1})
        self.assertEqual(len(mail.outbox), 2)  # Bestätigung + Admin
        self.assertIn(self.admin.email, mail.outbox[1].bcc)


class VerrechnungTests(PatenschaftTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Settings.objects.create(debtor_account='1100')
        cls.jahr = BusinessYear.objects.create(
            start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 12, 31), name='2026')
        cls.konto_baum = BillItemType.objects.create(name='Baumpatenschaft', booking_account='3400')
        cls.baum.rechnungsposition = cls.konto_baum
        cls.baum.save()
        aktiv = datetime.date(2025, 3, 1)
        # member4 hat keinen Ernteanteil, member hat einen
        cls.p_baum = Patenschaft.objects.create(member=cls.member4, typ=cls.baum, aktiviert_am=aktiv)
        cls.p_biene = Patenschaft.objects.create(member=cls.member4, typ=cls.biene, aktiviert_am=aktiv)
        # nicht verrechenbar: storniert, vor dem Jahr beendet, erst nach dem Jahr aktiv, Beitrag 0
        storniert = Patenschaft.objects.create(member=cls.member2, typ=cls.baum)
        storniert.kuendigen()
        Patenschaft.objects.create(member=cls.member3, typ=cls.baum, aktiviert_am=aktiv, ende=datetime.date(2025, 12, 31))
        Patenschaft.objects.create(member=cls.member3, typ=cls.biene, aktiviert_am=datetime.date(2027, 1, 1))
        Patenschaft.objects.create(member=cls.member3, typ=cls.biene, aktiviert_am=aktiv, jahresbeitrag=Decimal('0'))

    def test_verrechenbar(self):
        self.assertEqual(set(billing.verrechenbar(self.jahr)), {self.p_baum, self.p_biene})

    def test_neue_rechnung(self):
        neu, ergaenzt = billing.verrechnen(self.jahr, billing.verrechenbar(self.jahr))
        self.assertEqual((len(neu), len(ergaenzt)), (1, 0))
        bill = neu[0]
        self.assertEqual(bill.member, self.member4)
        self.assertEqual(bill.amount, 170.0)
        self.assertFalse(bill.published)
        # eigener Positionstyp mit Buchungskonto, sonst Standard "Patenschaft"
        item_baum = self.p_baum.rechnungspositionen.get()
        self.assertEqual(item_baum.custom_item_type, self.konto_baum)
        self.assertEqual(str(item_baum), 'Baumpatenschaft')
        self.assertEqual(str(self.p_biene.rechnungspositionen.get()), 'Patenschaft Bienenpatenschaft')
        # kein zweites Mal im selben Jahr, im Folgejahr wieder
        self.assertFalse(billing.verrechenbar(self.jahr).exists())
        folgejahr = BusinessYear.objects.create(
            start_date=datetime.date(2027, 1, 1), end_date=datetime.date(2027, 12, 31), name='2027')
        # die beiden verrechneten und die ab 2027 aktive
        self.assertEqual(billing.verrechenbar(folgejahr).count(), 3)

    def test_an_unveroeffentlichte_rechnung_anfuegen(self):
        bestehend = Bill.objects.create(business_year=self.jahr, member=self.member4, amount=500.0,
                                        bill_date=datetime.date(2026, 1, 1), booking_date=datetime.date(2026, 1, 1))
        BillItem.objects.create(bill=bestehend, description='Ernteanteil', amount=500.0)
        neu, ergaenzt = billing.verrechnen(self.jahr, billing.verrechenbar(self.jahr))
        self.assertEqual((neu, ergaenzt), ([], [bestehend]))
        bestehend.refresh_from_db()
        self.assertEqual(bestehend.amount, 670.0)
        # Neuberechnung durch juntagrico_billing lässt die Patenschaften stehen
        recalc_bill(bestehend)
        bestehend.refresh_from_db()
        self.assertEqual(bestehend.items.filter(patenschaften__isnull=False).count(), 2)

    def test_veroeffentlichte_rechnung_bleibt_unveraendert(self):
        Bill.objects.create(business_year=self.jahr, member=self.member4, amount=500.0, published=True,
                            bill_date=datetime.date(2026, 1, 1), booking_date=datetime.date(2026, 1, 1))
        neu, ergaenzt = billing.verrechnen(self.jahr, billing.verrechenbar(self.jahr))
        self.assertEqual((len(neu), len(ergaenzt)), (1, 0))

    def test_jb_urls_zeigen_auf_addon(self):
        from . import views_billing
        self.assertEqual(resolve(reverse('jb:pending-bills-list')).func, views_billing.pending_bills)
        self.assertEqual(resolve(reverse('jb:bills-generate')).func, views_billing.bills_generate)
        self.assertEqual(resolve(reverse('jb:bill-recalc', args=[1])).func, views_billing.bill_recalc)

    def test_anstehende_rechnungen(self):
        self.client.force_login(self.admin.user)
        self.client.post(reverse('jb:bills-setyear'), {'year': '2026'})
        response = self.client.get(reverse('jb:pending-bills-list'))
        self.assertContains(response, '1 &times; Baumpatenschaft')
        self.assertContains(response, '1 &times; Bienenpatenschaft')
        self.assertContains(response, 'data-order="170.00"')  # Betrag ohne Ernteanteil
        self.assertNotContains(response, 'Patenschaften verrechnen')  # kein separater Menüpunkt mehr

    def test_alle_erstellen_eine_rechnung_pro_mitglied(self):
        mit_ernteanteil = Patenschaft.objects.create(member=self.member, typ=self.baum,
                                                     aktiviert_am=datetime.date(2025, 3, 1))
        self.client.force_login(self.admin.user)
        self.client.post(reverse('jb:bills-setyear'), {'year': '2026'})
        response = self.client.post(reverse('jb:bills-generate'))
        self.assertRedirects(response, reverse('jb:unpublished-bills-list'))
        # Mitglied mit Ernteanteil: eine Rechnung mit Ernteanteil und Patenschaft
        bill = self.member.bills.get(business_year=self.jahr)
        self.assertTrue(bill.items.filter(subscription_part__isnull=False).exists())
        self.assertEqual(list(bill.items.filter(patenschaften__isnull=False)), list(mit_ernteanteil.rechnungspositionen.all()))
        self.assertAlmostEqual(bill.amount, sum(i.amount for i in bill.items.all()))
        # Mitglied ohne Ernteanteil: eigene Rechnung nur mit Patenschaften
        bill4 = self.member4.bills.get(business_year=self.jahr)
        self.assertEqual(bill4.amount, 170.0)
        self.assertFalse(billing.verrechenbar(self.jahr).exists())
        url = reverse('admin:huebhof_patenschaften_patenschaft_change', args=[self.p_baum.id])
        self.assertContains(self.client.get(url), reverse('admin:juntagrico_billing_bill_change', args=[bill4.id]))

    def test_neu_berechnen_fuegt_patenschaften_an(self):
        bill = Bill.objects.create(business_year=self.jahr, member=self.member4, amount=0.0,
                                   bill_date=datetime.date(2026, 1, 1), booking_date=datetime.date(2026, 1, 1))
        self.client.force_login(self.admin.user)
        next_url = reverse('admin:juntagrico_billing_bill_change', args=[bill.id])
        response = self.client.get(reverse('jb:bill-recalc', args=[bill.id]) + '?next=' + next_url)
        self.assertRedirects(response, next_url)
        bill.refresh_from_db()
        self.assertEqual(bill.amount, 170.0)
        # zweites Mal ändert nichts
        self.client.get(reverse('jb:bill-recalc', args=[bill.id]))
        bill.refresh_from_db()
        self.assertEqual(bill.items.count(), 2)

    def test_nur_buchhaltung(self):
        self.client.force_login(self.member.user)
        self.assertNotEqual(self.client.get(reverse('jb:pending-bills-list')).status_code, 200)
        self.client.post(reverse('jb:bills-generate'))
        self.assertFalse(Bill.objects.exists())


class VerwaltungTests(PatenschaftTestCase):
    def test_typ_erstellen_bearbeiten_loeschen(self):
        self.client.force_login(self.admin.user)
        self.assertContains(self.client.get(reverse('patenschaften-typen')), 'Baumpatenschaft')
        self.assertEqual(self.client.get(reverse('patenschaften-typ-neu')).status_code, 200)
        response = self.client.post(reverse('patenschaften-typ-neu'), {
            'name': 'Hühnerpatenschaft', 'beschreibung': 'Gack', 'jahresbeitrag': '80', 'sichtbar': 'on',
            'sortierung': '3', 'rechnungsposition': ''})
        self.assertRedirects(response, reverse('patenschaften-typen'))
        huhn = PatenschaftTyp.objects.get(name='Hühnerpatenschaft')
        self.assertEqual(huhn.jahresbeitrag, Decimal('80'))
        response = self.client.post(reverse('patenschaften-typ', args=[huhn.id]), {
            'name': 'Huhn', 'jahresbeitrag': '90', 'sortierung': '3'})
        self.assertRedirects(response, reverse('patenschaften-typen'))
        huhn.refresh_from_db()
        self.assertEqual((huhn.name, huhn.sichtbar), ('Huhn', False))
        self.client.post(reverse('patenschaften-typ', args=[huhn.id]), {'loeschen': ''})
        self.assertFalse(PatenschaftTyp.objects.filter(id=huhn.id).exists())

    def test_typ_mit_patenschaften_nicht_loeschbar(self):
        Patenschaft.objects.create(member=self.member, typ=self.baum)
        self.client.force_login(self.admin.user)
        self.client.post(reverse('patenschaften-typ', args=[self.baum.id]), {'loeschen': ''})
        self.assertTrue(PatenschaftTyp.objects.filter(id=self.baum.id).exists())

    def test_erfassen(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('patenschaften-erfassen'), {'member': self.member2.id})
        self.assertContains(response, f'<option value="{self.member2.id}" selected>')
        mail.outbox.clear()
        response = self.client.post(reverse('patenschaften-erfassen'), {
            'member': self.member2.id, 'typ': self.baum.id, 'anzahl': 3, 'jahresbeitrag': '',
            'bestellt_am': '2026-02-01', 'aktiviert_am': '2026-03-01', 'notizen': 'Telefon', 'bestaetigung': 'on'})
        self.assertRedirects(response, reverse('patenschaften-manage'))
        neue = Patenschaft.objects.filter(member=self.member2)
        self.assertEqual(neue.count(), 3)
        p = neue.first()
        self.assertEqual((p.jahresbeitrag, p.aktiviert_am, p.notizen),
                         (Decimal('120'), datetime.date(2026, 3, 1), 'Telefon'))
        self.assertEqual(len(mail.outbox), 1)
        # eigener Beitrag, ohne Aktivierung, ohne Mail, "weitere erfassen"
        mail.outbox.clear()
        response = self.client.post(reverse('patenschaften-erfassen'), {
            'member': self.member3.id, 'typ': self.biene.id, 'anzahl': 1, 'jahresbeitrag': '75',
            'bestellt_am': '2026-02-01', 'aktiviert_am': '', 'weitere': ''})
        self.assertRedirects(response, reverse('patenschaften-erfassen'))
        p = Patenschaft.objects.get(member=self.member3)
        self.assertEqual((p.jahresbeitrag, p.status), (Decimal('75'), 'bestellt'))
        self.assertEqual(len(mail.outbox), 0)

    def test_bearbeiten_und_kuendigen(self):
        p = Patenschaft.objects.create(member=self.member, typ=self.baum, aktiviert_am=datetime.date.today())
        self.client.force_login(self.admin.user)
        url = reverse('patenschaften-bearbeiten', args=[p.id])
        self.assertContains(self.client.get(url), 'Kündigen')
        response = self.client.post(url, {'typ': self.baum.id, 'jahresbeitrag': '100',
                                           'bestellt_am': p.bestellt_am.isoformat(),
                                           'aktiviert_am': p.aktiviert_am.isoformat(), 'notizen': 'Rabatt'})
        self.assertRedirects(response, reverse('patenschaften-manage'))
        p.refresh_from_db()
        self.assertEqual((p.jahresbeitrag, p.notizen), (Decimal('100'), 'Rabatt'))
        self.client.post(url, {'kuendigen': ''})
        p.refresh_from_db()
        self.assertEqual(p.status, 'gekuendigt')
        self.assertNotContains(self.client.get(url), 'name="kuendigen"')

    def test_uebersicht_verlinkt_frontend(self):
        p = Patenschaft.objects.create(member=self.member, typ=self.baum, aktiviert_am=datetime.date.today())
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('patenschaften-manage'))
        for url in (reverse('patenschaften-erfassen'), reverse('patenschaften-typen'),
                    reverse('patenschaften-bearbeiten', args=[p.id]), reverse('patenschaften-typ', args=[self.baum.id])):
            self.assertContains(response, f'href="{url}"')

    def test_kein_zugriff_ohne_recht(self):
        self.client.force_login(self.member.user)
        p = Patenschaft.objects.create(member=self.member, typ=self.baum)
        for url in (reverse('patenschaften-typen'), reverse('patenschaften-typ-neu'),
                    reverse('patenschaften-erfassen'), reverse('patenschaften-bearbeiten', args=[p.id])):
            self.assertNotEqual(self.client.get(url).status_code, 200, url)


class BerechtigungTests(PatenschaftTestCase):
    """Teilrechte: Menü, Links und Seiten passen zu den vergebenen Berechtigungen."""

    def login_mit(self, *codenames):
        user = self.member2.user
        user.user_permissions.set(Permission.objects.filter(
            content_type__app_label='huebhof_patenschaften', codename__in=codenames))
        self.client.force_login(user)

    def menu(self):
        return self.client.get(reverse('home')).content.decode()

    def assertErlaubt(self, url, erlaubt=True):
        status = self.client.get(url).status_code
        if erlaubt:
            self.assertEqual(status, 200, url)
        else:
            self.assertIn(status, (302, 403), url)

    def setUp(self):
        self.p = Patenschaft.objects.create(member=self.member, typ=self.baum, aktiviert_am=datetime.date.today())

    def test_ohne_rechte_kein_menu(self):
        self.login_mit()
        self.assertNotIn('patenschaftenman', self.menu())

    def test_nur_ansehen(self):
        self.login_mit('view_patenschaft')
        menu = self.menu()
        self.assertIn(reverse('patenschaften-manage') + '?status=aktiv', menu)
        self.assertNotIn(reverse('patenschaften-erfassen'), menu)
        self.assertNotIn(reverse('patenschaften-typen'), menu)
        response = self.client.get(reverse('patenschaften-manage'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('patenschaften-bearbeiten', args=[self.p.id]))
        self.assertNotContains(response, reverse('patenschaften-typ', args=[self.baum.id]))
        self.assertErlaubt(reverse('patenschaften-bearbeiten', args=[self.p.id]), False)
        self.assertErlaubt(reverse('patenschaften-erfassen'), False)
        self.assertErlaubt(reverse('patenschaften-typen'), False)

    def test_bearbeiten(self):
        self.login_mit('view_patenschaft', 'change_patenschaft')
        self.assertContains(self.client.get(reverse('patenschaften-manage')),
                            reverse('patenschaften-bearbeiten', args=[self.p.id]))
        self.assertErlaubt(reverse('patenschaften-bearbeiten', args=[self.p.id]))

    def test_nur_erfassen(self):
        self.login_mit('add_patenschaft')
        menu = self.menu()
        self.assertIn(reverse('patenschaften-erfassen'), menu)
        self.assertNotIn(reverse('patenschaften-manage') + '?status=aktiv', menu)
        self.assertErlaubt(reverse('patenschaften-manage'), False)
        response = self.client.post(reverse('patenschaften-erfassen'), {
            'member': self.member3.id, 'typ': self.baum.id, 'anzahl': 1,
            'bestellt_am': '2026-02-01', 'aktiviert_am': '2026-02-01'})
        # zurück zum Formular, nicht zur Übersicht, die nicht erlaubt ist
        self.assertRedirects(response, reverse('patenschaften-erfassen'))
        self.assertTrue(Patenschaft.objects.filter(member=self.member3).exists())

    def test_typen_nur_ansehen(self):
        self.login_mit('view_patenschafttyp')
        self.assertIn(reverse('patenschaften-typen'), self.menu())
        response = self.client.get(reverse('patenschaften-typen'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('patenschaften-typ', args=[self.baum.id]))
        self.assertNotContains(response, reverse('patenschaften-typ-neu'))
        self.assertErlaubt(reverse('patenschaften-typ', args=[self.baum.id]), False)
        self.assertErlaubt(reverse('patenschaften-typ-neu'), False)

    def test_typen_verwalten_ohne_loeschen(self):
        self.login_mit('view_patenschafttyp', 'add_patenschafttyp', 'change_patenschafttyp')
        response = self.client.get(reverse('patenschaften-typen'))
        self.assertContains(response, reverse('patenschaften-typ', args=[self.versteckt.id]))
        self.assertContains(response, reverse('patenschaften-typ-neu'))
        self.assertNotContains(self.client.get(reverse('patenschaften-typ', args=[self.versteckt.id])), 'loeschen')
        response = self.client.post(reverse('patenschaften-typ', args=[self.versteckt.id]), {'loeschen': ''})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(PatenschaftTyp.objects.filter(id=self.versteckt.id).exists())

    def test_neuer_typ_nur_mit_add(self):
        self.login_mit('change_patenschafttyp')
        self.assertEqual(self.client.get(reverse('patenschaften-typ-neu')).status_code, 403)
        self.assertErlaubt(reverse('patenschaften-typ', args=[self.baum.id]))


class PendentTests(PatenschaftTestCase):
    def setUp(self):
        self.a = Patenschaft.objects.create(member=self.member, typ=self.baum, bestellt_am=datetime.date(2026, 3, 1))
        self.b = Patenschaft.objects.create(member=self.member, typ=self.biene, bestellt_am=datetime.date(2026, 4, 1))
        self.aktiv = Patenschaft.objects.create(member=self.member2, typ=self.baum, aktiviert_am=datetime.date(2026, 1, 1))

    def test_liste_und_menu(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('patenschaften-pendent'))
        self.assertContains(response, f'value="{self.a.id}"')
        self.assertContains(response, f'value="{self.b.id}"')
        self.assertNotContains(response, f'value="{self.aktiv.id}"')
        self.assertContains(response, '2026-03-01')
        self.assertContains(response, 'href="%s"' % reverse('patenschaften-pendent'))  # Menüpunkt

    def test_ausgewaehlte_anwenden(self):
        self.client.force_login(self.admin.user)
        url = reverse('patenschaften-pendent')
        response = self.client.post(reverse('patenschaften-pendent-anwenden'),
                                    {'patenschaften[]': [self.a.id]}, HTTP_REFERER=url)
        self.assertRedirects(response, url)
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual((self.a.status, self.a.aktiviert_am), ('aktiv', datetime.date.today()))
        self.assertEqual(self.b.status, 'bestellt')

    def test_mit_aenderungsdatum(self):
        self.client.force_login(self.admin.user)
        session = self.client.session
        session['changedate'] = '2026-05-01'
        session.save()
        self.client.post(reverse('patenschaften-pendent-anwenden'), {'patenschaften[]': [self.a.id, self.b.id]})
        self.a.refresh_from_db()
        self.assertEqual(self.a.aktiviert_am, datetime.date(2026, 5, 1))
        self.assertFalse(Patenschaft.objects.bestellt().exists())

    def test_nur_mit_change_recht(self):
        user = self.member2.user
        user.user_permissions.set(Permission.objects.filter(codename='view_patenschaft'))
        self.client.force_login(user)
        self.assertNotIn(reverse('patenschaften-pendent'), self.client.get(reverse('home')).content.decode())
        self.assertNotEqual(self.client.get(reverse('patenschaften-pendent')).status_code, 200)
        response = self.client.post(reverse('patenschaften-pendent-anwenden'), {'patenschaften[]': [self.a.id]})
        self.assertEqual(response.status_code, 403)
        self.a.refresh_from_db()
        self.assertEqual(self.a.status, 'bestellt')


class ExportTests(PatenschaftTestCase):
    def setUp(self):
        Patenschaft.objects.create(member=self.member, typ=self.baum, aktiviert_am=datetime.date.today(), notizen='aktiv')
        Patenschaft.objects.create(member=self.member2, typ=self.biene, notizen='nur bestellt')

    def test_csv_mit_statusfilter(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('patenschaften-export'), {'status': 'aktiv', 'format': 'csv'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('patenschaften_aktiv_', response['Content-Disposition'])
        inhalt = response.content.decode()
        self.assertIn('Baumpatenschaft', inhalt)
        self.assertNotIn('nur bestellt', inhalt)

    def test_excel(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('patenschaften-export'), {'status': 'alle', 'format': 'xlsx'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'PK'))  # xlsx ist ein Zip-Archiv
        self.assertTrue(response['Content-Disposition'].endswith('.xlsx"'))

    def test_knopf_in_liste(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('patenschaften-manage'), {'status': 'gekuendigt'})
        self.assertContains(response, reverse('patenschaften-export') + '?status=gekuendigt&format=xlsx')
        self.assertNotContains(response, reverse('admin:huebhof_patenschaften_patenschaft_export'))

    def test_ansehen_reicht_ohne_staff(self):
        user = self.member2.user
        user.user_permissions.set(Permission.objects.filter(codename='view_patenschaft'))
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('patenschaften-export')).status_code, 200)

    def test_ohne_recht(self):
        self.client.force_login(self.member.user)
        self.assertNotEqual(self.client.get(reverse('patenschaften-export')).status_code, 200)


class OhneTypenTests(PatenschaftTestCase):
    def setUp(self):
        PatenschaftTyp.objects.update(sichtbar=False)

    def test_mitglied_sieht_hinweis(self):
        self.client.force_login(self.member.user)
        response = self.client.get(reverse('patenschaften-mine'))
        self.assertContains(response, 'Zurzeit werden keine Patenschaften angeboten')
        self.assertNotContains(response, 'Verbindlich bestellen')
        self.assertNotContains(response, reverse('patenschaften-typen'))

    def test_admin_sieht_link_zu_typen(self):
        self.client.force_login(self.admin.user)
        response = self.client.get(reverse('patenschaften-mine'))
        self.assertContains(response, 'Hinweis für Admins')
        self.assertContains(response, reverse('patenschaften-typen'))

    def test_mit_typ_bestellformular(self):
        self.baum.sichtbar = True
        self.baum.save()
        self.client.force_login(self.member.user)
        response = self.client.get(reverse('patenschaften-mine'))
        self.assertContains(response, 'Verbindlich bestellen')
        self.assertNotContains(response, 'Zurzeit werden keine Patenschaften angeboten')
