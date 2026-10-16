# huebhof_patenschaften

Juntagrico-Addon (ab Juntagrico 2.0) für Patenschaften der Solawi Huebhof. Setzt `juntagrico_billing` voraus.

Der Code (Klassen, Felder, Funktionen, Kommentare) ist englisch wie in juntagrico; die Texte für die Benutzer:innen sind wie im juntagrico-Core deutsch und können über `locale` übersetzt werden.

## Funktionen

* **Patenschaftstypen** mit Name, Beschreibung, Jahresbeitrag und optional eigenem Buchungskonto. Nur "bestellbare" Typen werden Mitgliedern angeboten.
* **Bestellprozess**: Nach der Auswahl der Ernteanteile (und Zusatz-Abos) folgt der Schritt "Patenschaft übernehmen". Alle Felder auf 0 = ohne Patenschaft weiter. Die Zusammenfassung zeigt die Auswahl mit Bearbeiten-Link.
* **Kumulierbar**: Pro übernommener Patenschaft ein eigener Datensatz (3 × Baum = 3 Einträge), jede einzeln kündbar.
* **Unabhängig vom Ernteanteil**: Patenschaften hängen am Mitglied, nicht am Abo.
* **Mitgliederbereich** "Patenschaften" (im Menü direkt nach dem Ernteanteil): eigene Patenschaften mit Jahrestotal, weitere bestellen, kündigen.
* **Aktivierung** wie bei den Ernteanteilen manuell durch Admins: Bestellungen sind zuerst "bestellt" und werden unter Patenschaften → Pendente Änderungen aktiviert. Erst aktivierte Patenschaften werden verrechnet.
* **Kündigung** per Ende Geschäftsjahr, gleiche Regel wie bei den Ernteanteilen: bis Ende `BUSINESS_YEAR_CANCELATION_MONTH` aufs Ende des laufenden Jahres, danach aufs Ende des Folgejahres. Noch nicht aktivierte Bestellungen werden sofort storniert.
* **Verwaltung im Frontend** (Admin-Menü → Patenschaften, siehe unten): Übersicht, Typen verwalten, Patenschaften erfassen, bearbeiten und kündigen. Der Django-Admin wird dafür nicht gebraucht.
* **Verrechnung** im normalen Rechnungsablauf von `juntagrico_billing` (siehe unten).
* **Austritt**: Wird ein Mitglied deaktiviert, enden seine Patenschaften am selben Tag.
* **E-Mails**: Bestätigung an die Pat:in bei Bestellung und Kündigung. Admins mit den Rechten "Wird bei neuer / gekündigter Patenschaft per E-Mail informiert" erhalten eine Benachrichtigung.

## Bedienung

Im Admin-Menü gibt es nach den Ernteanteilen das Aufklappmenü **Patenschaften** (offen auf allen Seiten unter `/manage/sponsorships/`):

| Menüpunkt | Inhalt |
|---|---|
| **Aktive** | Kennzahlen pro Typ (bestellt, aktiv, gekündigt, Summe Jahresbeiträge) und Liste der Patenschaften. Filter: aktiv (Standard), gekündigt (laufen noch), alle inkl. beendete. Bestellte, noch nicht aktive Patenschaften stehen unter "Pendente Änderungen". Werkzeugleiste: E-Mail an die ausgewählten Pat:innen, E-Mails kopieren, Knöpfe "Excel" und "CSV" (Export mit dem gewählten Statusfilter; Suche und Spaltenfilter werden nicht berücksichtigt). Klick auf den Typ öffnet die einzelne Patenschaft. |
| **Pendente Änderungen** | Wie bei den Ernteanteilen: pro Mitglied die bestellten, noch nicht aktivierten Patenschaften (nach Bestelldatum gruppiert). Auswählen und "Ausgewählte anwenden" aktiviert sie auf das Änderungsdatum (Standard heute, einstellbar wie bei den Ernteanteilen). Kündigungen müssen nicht angewendet werden. |
| **Patenschaftstypen** | Typen anlegen und bearbeiten (Name, Beschreibung, Jahresbeitrag, Bestellbar, Sortierung, Rechnungspositionstyp). Löschen nur ohne Patenschaften, sonst "Bestellbar" ausschalten. |
| **Patenschaft erfassen** | Für Bestellungen, die nicht über den Mitgliederbereich kommen: Mitglied, Typ, Anzahl, Jahresbeitrag (leer = Preis des Typs), Bestell- und Aktivierungsdatum (leer = bleibt "bestellt"), Notizen, optional Bestätigungsmail. "Erfassen und weitere erfassen" für mehrere nacheinander. |

Die einzelne Patenschaft zeigt Status und Rechnungen; Beitrag, Daten und Notizen lassen sich ändern, "Kündigen" wendet die Kündigungsregel an.

Wie alle Listen in juntagrico wird die Seite "Aktive" in der breiten Ansicht angezeigt; die Formularseiten sind normal breit.

Im Django-Admin erscheinen die Patenschaften zusätzlich direkt beim Mitglied (Inline).

## Installation

`settings.py`:

```python
INSTALLED_APPS = [
    ...
    'juntagrico_billing',
    'huebhof_patenschaften',   # nach juntagrico_billing, vor juntagrico
    'juntagrico',
    ...
]

SIGNUP_MANAGER = 'huebhof_patenschaften.signup.SponsorshipSignupManager'
```

`urls.py` (vor `juntagrico.urls` und `juntagrico_billing.urls`):

```python
re_path(r'^', include('huebhof_patenschaften.urls')),
```

Danach `python -m manage migrate`.

Beide Reihenfolgen sind wichtig, siehe [Eingriffe in juntagrico und juntagrico_billing](#eingriffe-in-juntagrico-und-juntagrico_billing).

## Einstellungen (optional)

| Setting | Standard | Bedeutung |
|---|---|---|
| `SPONSORSHIPS_AUTO_ACTIVATE` | `False` | Wie bei den Ernteanteilen bleiben Bestellungen von Mitgliedern "bestellt", bis ein Admin sie aktiviert. `True`: ab Bestellung aktiv. Gilt nicht für "Patenschaft erfassen", dort wird das Aktivierungsdatum direkt angegeben. |
| `SPONSORSHIPS_IN_SIGNUP` | `True` | Schritt im Bestellprozess anzeigen. |
| `SPONSORSHIPS_MAX_QUANTITY` | `20` | Maximale Anzahl pro Typ und Bestellung. |
| `SPONSORSHIPS_INFO_URL` | `''` | Link "Mehr erfahren" zu einem Infodokument. |

## Berechtigungen

Wie in juntagrico werden die Rechte in der **Datenverwaltung** vergeben, am besten über **Gruppen** (Datenverwaltung → Gruppen → Gruppe anlegen, Berechtigungen hinzufügen, dann Benutzer:innen der Gruppe zuweisen). Einzelne Berechtigungen direkt am Benutzer gehen auch, sind aber schwerer zu übertragen. Superuser haben alle Rechte ausser den Benachrichtigungen.

| Berechtigung | Erlaubt |
|---|---|
| `huebhof_patenschaften.view_sponsorship` | Menü "Patenschaften → Aktive": Kennzahlen und Liste ansehen, exportieren, E-Mail an Pat:innen (zusätzlich `juntagrico.can_send_mails` nötig). |
| `huebhof_patenschaften.change_sponsorship` | Zusätzlich "Pendente Änderungen" (aktivieren), einzelne Patenschaften bearbeiten und kündigen. |
| `huebhof_patenschaften.add_sponsorship` | Menü "Patenschaft erfassen". Ohne `view_`/`change_sponsorship` bleibt man nach dem Erfassen im Formular. |
| `huebhof_patenschaften.delete_sponsorship` | Patenschaften im Django-Admin löschen (normalerweise kündigen statt löschen). |
| `huebhof_patenschaften.view_sponsorshiptype` | Menü "Patenschaftstypen": Liste ansehen. |
| `huebhof_patenschaften.add_sponsorshiptype` | Neue Patenschaftstypen anlegen. |
| `huebhof_patenschaften.change_sponsorshiptype` | Patenschaftstypen bearbeiten (Preis, Bestellbar, Buchungskonto ...). |
| `huebhof_patenschaften.delete_sponsorshiptype` | Patenschaftstypen löschen, nur solange sie keine Patenschaften haben. |
| `huebhof_patenschaften.notified_on_sponsorship_creation` | E-Mail bei jeder neuen Patenschaft. Muss auch Superusern explizit gegeben werden. |
| `huebhof_patenschaften.notified_on_sponsorship_cancellation` | E-Mail bei jeder Kündigung. Muss auch Superusern explizit gegeben werden. |
| `juntagrico.is_book_keeper` | Verrechnung: Patenschaften erscheinen in "Anstehende Rechnungen" usw. (Recht von juntagrico_billing). |

Das Menü "Patenschaften" erscheint, sobald jemand eines der Rechte zum Ansehen, Erfassen oder Verwalten hat; es zeigt nur die erlaubten Unterpunkte. Links in den Listen (z.B. auf eine einzelne Patenschaft) erscheinen nur, wenn die Zielseite erlaubt ist.

Der **Export** in der Liste braucht nur `view_sponsorship`. Das Inline beim Mitglied läuft über den Django-Admin und braucht deshalb zusätzlich den **Status "Mitarbeiter" (Staff)**.

### Vorschlag für Gruppen

| Gruppe | Berechtigungen |
|---|---|
| Patenschaften ansehen | `view_sponsorship`, `view_sponsorshiptype` |
| Patenschaften betreuen | wie "ansehen", plus `add_sponsorship`, `change_sponsorship`, `notified_on_sponsorship_creation`, `notified_on_sponsorship_cancellation` |
| Patenschaften verwalten | wie "betreuen", plus `add_sponsorshiptype`, `change_sponsorshiptype`, `delete_sponsorshiptype` |

Für die Verrechnung die Buchhaltung wie bisher mit `juntagrico.is_book_keeper` ausstatten. Wie in der juntagrico-Dokumentation empfohlen: jede Rolle mit einem Test-Benutzer durchklicken.

## Verrechnung (juntagrico_billing)

Patenschaften erscheinen als eigene Rechnungspositionen (Custom Bill-Item Types) auf den QR-Rechnungen, im Buchungsexport und im Bexio-Export. Die Verrechnung läuft im normalen Ablauf unter **Rechnungen und Buchhaltung**:

1. Optional pro Patenschaftstyp einen **Rechnungspositionstyp** mit Buchungskonto zuweisen (Custom Bill-Item Types im Django-Admin anlegen, dann beim Patenschaftstyp auswählen). Ohne Zuweisung wird der Typ "Patenschaft" verwendet; er wird beim ersten Verrechnen ohne Buchungskonto angelegt, das Konto im Django-Admin nachtragen.
2. **Anstehende Rechnungen** zeigt neben den Ernteanteilen auch die unverrechneten Patenschaften, auch von Mitgliedern ohne Ernteanteil.
3. **Alle erstellen** erstellt die Ernteanteil-Rechnungen und fügt die Patenschaften daran an. Jedes Mitglied erhält eine Rechnung; Mitglieder ohne Ernteanteil eine Rechnung nur mit Patenschaften. Hat ein Mitglied im Jahr bereits eine unveröffentlichte Rechnung, kommen die Patenschaften dorthin.
4. **Rechnung neu berechnen** (Django-Admin bei der Rechnung) ergänzt auch fehlende Patenschaften des Mitglieds.

Verrechnet werden alle aktivierten Patenschaften mit einem Beitrag über 0, die im Geschäftsjahr laufen, mit dem vollen Jahresbeitrag. Jede Patenschaft wird pro Geschäftsjahr nur einmal verrechnet; wird die Rechnung gelöscht, ist sie wieder verrechenbar. Veröffentlichte Rechnungen werden nur beim expliziten Neu berechnen ergänzt.

## Eingriffe in juntagrico und juntagrico_billing

Bei Updates von juntagrico oder juntagrico_billing diese Stellen prüfen:

| Datei | Was | Voraussetzung |
|---|---|---|
| `templates/juntagrico/menu/user.html` | **Kopie** des Benutzermenüs von juntagrico 2.0 mit "Patenschaften" nach dem Ernteanteil (juntagrico bietet dort keinen Block). Bei Updates mit dem Original abgleichen. | `huebhof_patenschaften` steht in `INSTALLED_APPS` nach `juntagrico_billing`, damit dessen Menüpunkt "Rechnungen" darauf aufbaut. |
| `templates/juntagrico/menu/admin.html` | Erweitert den Block `subscriptions` des Admin-Menüs um das Aufklappmenü. Keine Kopie. | – |
| `views_billing.py`, `urls.py` | Eigene Views unter den Pfaden von juntagrico_billing (`jb/pending_bills`, `jb/bills_generate`, `jb/bill_recalc/<id>`). Sie rufen die Funktionen von juntagrico_billing auf und ergänzen die Patenschaften. Bei Updates prüfen, ob sich die Original-Views geändert haben. | `huebhof_patenschaften.urls` steht in `urls.py` vor `juntagrico_billing.urls` (ein Test prüft das). |
| `migrations/0002_verrechnung.py` | Abhängigkeit auf `juntagrico_billing 0006_alter_payment_paid_date`. | – |
| `migrations/0003_english_names.py` | Benennt Modelle, Felder, ContentTypes und Berechtigungen von Deutsch auf Englisch um (Daten und Zuweisungen bleiben erhalten). Die `RenameModel` sind bewusst in `SeparateDatabaseAndState` verpackt: juntagrico hängt an jedes `RenameModel` eine Umbenennung der Berechtigungen an, die auf einer frischen Datenbank fehlschlägt. | – |

Neue Migrationen nur mit `python -m manage makemigrations huebhof_patenschaften` erzeugen. Ohne App-Namen legt Django auch Migrationen in den installierten Paketen (juntagrico, juntagrico_billing) an, die später zu Konflikten führen.

## Tests

```
python -m manage test huebhof_patenschaften
```

Lokal muss `JUNTAGRICO_SECRET_KEY` gesetzt sein (beliebiger Wert), sonst schlagen die Tests mit Sessions fehl.

## Noch offen

* Unterjährige Bestellungen werden mit dem vollen Jahresbeitrag verrechnet (kein pro rata).
* Mitgliederauswahl bei "Patenschaft erfassen" ist eine einfache Auswahlliste (keine Suche).
