import datetime
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from juntagrico.entity.depot import Depot
from juntagrico.entity.subtypes import SubscriptionType
from juntagrico.tests import JuntagricoTestCase

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
        self.assertEqual(Patenschaft.objects.filter(member=self.member4).aktiv().count(), 3)
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

    @override_settings(PATENSCHAFTEN_AUTO_AKTIVIEREN=False)
    def test_manuelle_aktivierung(self):
        self.client.force_login(self.member.user)
        self.client.post(reverse('patenschaften-mine'), {f'typ_{self.baum.id}': 1})
        p = Patenschaft.objects.get(member=self.member)
        self.assertEqual(p.status, 'bestellt')
        # Admin aktiviert
        self.client.force_login(self.admin.user)
        response = self.client.post(reverse('patenschaften-aktivieren'), {'ids': str(p.id)})
        self.assertEqual(response.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.status, 'aktiv')


class AdminTests(PatenschaftTestCase):
    def test_uebersicht(self):
        Patenschaft.objects.create(member=self.member, typ=self.baum, aktiviert_am=datetime.date.today())
        Patenschaft.objects.create(member=self.member2, typ=self.biene)
        self.client.force_login(self.admin.user)
        for status in ('offen', 'bestellt', 'aktiv', 'gekuendigt', 'alle'):
            response = self.client.get(reverse('patenschaften-manage'), {'status': status})
            self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('patenschaften-manage'))
        self.assertContains(response, 'Baumpatenschaft')
        self.assertContains(response, 'Bienenpatenschaft')
        # Menüpunkt im Admin-Menü
        self.assertContains(response, 'href="%s"' % reverse('patenschaften-manage'))

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
