# huebhof_patenschaften

Juntagrico-Addon (ab Juntagrico 2.0) für Patenschaften der Solawi Huebhof. Setzt `juntagrico_billing` voraus.

## Funktionen

* **Patenschaftstypen** mit Name, Beschreibung, Jahresbeitrag und optional eigenem Buchungskonto. Nur "bestellbare" Typen werden Mitgliedern angeboten.
* **Bestellprozess**: Nach der Auswahl der Ernteanteile (und Zusatz-Abos) folgt der Schritt "Patenschaft übernehmen". Alle Felder auf 0 = ohne Patenschaft weiter. Die Zusammenfassung zeigt die Auswahl mit Bearbeiten-Link.
* **Kumulierbar**: Pro übernommener Patenschaft ein eigener Datensatz (3 × Baum = 3 Einträge), jede einzeln kündbar.
* **Unabhängig vom Ernteanteil**: Patenschaften hängen am Mitglied, nicht am Abo.
* **Mitgliederbereich** "Patenschaften" (im Menü direkt nach dem Ernteanteil): eigene Patenschaften mit Jahrestotal, weitere bestellen, kündigen.
* **Kündigung** per Ende Geschäftsjahr, gleiche Regel wie bei den Ernteanteilen: bis Ende `BUSINESS_YEAR_CANCELATION_MONTH` aufs Ende des laufenden Jahres, danach aufs Ende des Folgejahres. Noch nicht aktivierte Bestellungen werden sofort storniert.
* **Verwaltung im Frontend** (Admin-Menü → Patenschaften, siehe unten): Übersicht, Typen verwalten, Patenschaften erfassen, bearbeiten und kündigen. Der Django-Admin wird dafür nicht gebraucht.
* **Verrechnung** im normalen Rechnungsablauf von `juntagrico_billing` (siehe unten).
* **Austritt**: Wird ein Mitglied deaktiviert, enden seine Patenschaften am selben Tag.
* **E-Mails**: Bestätigung an die Pat:in bei Bestellung und Kündigung. Admins mit den Rechten "Wird bei neuer / gekündigter Patenschaft per E-Mail informiert" erhalten eine Benachrichtigung.

## Bedienung

Im Admin-Menü gibt es nach den Ernteanteilen das Aufklappmenü **Patenschaften** (offen auf allen Seiten unter `/manage/patenschaften/`):

| Menüpunkt | Inhalt |
|---|---|
| **Aktive** | Kennzahlen pro Typ (bestellt, aktiv, gekündigt, Summe Jahresbeiträge) und Liste der Patenschaften. Filter: alle offenen, bestellt, aktiv, gekündigt, alle inkl. beendete. E-Mail an die ausgewählten Pat:innen, Sammelaktivierung, Export (Excel/CSV). Klick auf den Typ öffnet die einzelne Patenschaft. |
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

SIGNUP_MANAGER = 'huebhof_patenschaften.signup.PatenschaftSignupManager'
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
| `PATENSCHAFTEN_AUTO_AKTIVIEREN` | `True` | `False`: Bestellungen von Mitgliedern bleiben "bestellt", bis ein Admin sie aktiviert (z.B. nach Zahlungseingang). Gilt nicht für "Patenschaft erfassen", dort wird das Aktivierungsdatum direkt angegeben. |
| `PATENSCHAFTEN_IM_SIGNUP` | `True` | Schritt im Bestellprozess anzeigen. |
| `PATENSCHAFTEN_MAX_ANZAHL` | `20` | Maximale Anzahl pro Typ und Bestellung. |
| `PATENSCHAFTEN_INFO_URL` | `''` | Link "Mehr erfahren" zu einem Infodokument. |

## Berechtigungen

* `huebhof_patenschaften.view_patenschaft` / `change_patenschaft`: Menü und Übersicht sehen; mit `change` zusätzlich aktivieren, bearbeiten und kündigen.
* `add_patenschaft`: Patenschaften erfassen.
* `change_patenschafttyp` / `add_patenschafttyp` / `delete_patenschafttyp`: Patenschaftstypen verwalten.
* `notified_on_patenschaft_bestellung`, `notified_on_patenschaft_kuendigung`: E-Mail-Benachrichtigungen.
* `juntagrico.is_book_keeper`: Verrechnung (wie bei `juntagrico_billing`).

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

Neue Migrationen nur mit `python -m manage makemigrations huebhof_patenschaften` erzeugen. Ohne App-Namen legt Django auch Migrationen in den installierten Paketen (juntagrico, juntagrico_billing) an, die später zu Konflikten führen.

## Tests

```
python -m manage test huebhof_patenschaften
```

## Noch offen

* Unterjährige Bestellungen werden mit dem vollen Jahresbeitrag verrechnet (kein pro rata).
* Mitgliederauswahl bei "Patenschaft erfassen" ist eine einfache Auswahlliste (keine Suche).
