# huebhof_patenschaften

Juntagrico-Addon (ab Juntagrico 2.0) für Patenschaften der Solawi Huebhof. Die Verrechnung über `juntagrico_billing` ist in der separaten App [`huebhof_patenschaften_billing`](../huebhof_patenschaften_billing/README.md).

Der Code (Klassen, Felder, Funktionen, Kommentare) ist englisch wie in juntagrico; die Texte für die Benutzer:innen sind wie im juntagrico-Core deutsch und können über `locale` übersetzt werden.

## Funktionen

* **Patenschaftstypen** mit Name, Beschreibung und Jahresbeitrag (mit `huebhof_patenschaften_billing` optional eigenes Buchungskonto). Nur "bestellbare" Typen werden Mitgliedern angeboten. Optional eine maximale Anzahl pro Typ: laufende und bestellte Patenschaften zählen, ist sie erreicht, ist der Typ "zurzeit ausgebucht"; vorher sehen Mitglieder "noch N verfügbar".
* **Jahresbeitrag** wie bei den Abotypen in juntagrico: Es gilt der aktuelle Preis des Typs, eine Preisänderung wirkt auch auf bestehende Patenschaften. Für Ausnahmen lässt sich pro Patenschaft ein abweichender Jahresbeitrag (Sonderpreis) eintragen, der fix bleibt. Siehe [Preisänderung und Sonderpreise](#preisänderung-und-sonderpreise).
* **Bestellprozess**: Nach der Auswahl der Ernteanteile (und Zusatz-Abos) folgt der Schritt "Patenschaft übernehmen". Alle Felder auf 0 = ohne Patenschaft weiter. Die Zusammenfassung zeigt die Auswahl mit Bearbeiten-Link.
* **Kumulierbar**: Pro übernommener Patenschaft ein eigener Datensatz (3 × Baum = 3 Einträge), jede einzeln kündbar.
* **Unabhängig vom Ernteanteil**: Patenschaften hängen am Mitglied, nicht am Abo.
* **Mitgliederbereich** "Patenschaften" (im Menü direkt nach dem Ernteanteil): eigene Patenschaften mit Jahrestotal, weitere bestellen, kündigen.
* **Prüfung und Aktivierung** wie bei den Ernteanteilen manuell durch Admins: Bestellungen sind zuerst "bestellt" und werden unter Patenschaften → Pendente Änderungen geprüft und aktiviert oder abgelehnt. Erst aktivierte Patenschaften werden verrechnet.
* **Kündigung** per Ende Geschäftsjahr, gleiche Regel wie bei den Ernteanteilen: bis Ende `BUSINESS_YEAR_CANCELATION_MONTH` aufs Ende des laufenden Jahres, danach aufs Ende des Folgejahres. Noch nicht aktivierte Bestellungen werden sofort storniert.
* **Verwaltung im Frontend** (Admin-Menü → Patenschaften, siehe unten): Übersicht, Typen verwalten, Patenschaften erfassen, bearbeiten und kündigen. Der Django-Admin wird dafür nicht gebraucht.
* **Verrechnung** im normalen Rechnungsablauf von `juntagrico_billing`, mit der App `huebhof_patenschaften_billing`.
* **Austritt**: Wird ein Mitglied deaktiviert, enden seine Patenschaften am selben Tag.
* **E-Mails**: an die Pat:in bei Bestellung ("wir prüfen"), Aktivierung ("bestätigt"), Ablehnung (mit optionaler Begründung) und Kündigung. Admins mit den Rechten "Wird bei neuer / gekündigter Patenschaft per E-Mail informiert" erhalten eine Benachrichtigung.

## Bedienung

Im Admin-Menü gibt es nach den Ernteanteilen das Aufklappmenü **Patenschaften** (offen auf allen Seiten unter `/manage/sponsorships/`):

| Menüpunkt | Inhalt |
|---|---|
| **Aktive** | Kennzahlen pro Typ: bestellt, aktiv, gekündigt und "Summe pro Jahr" (Jahresbeiträge der laufenden Patenschaften; mit `huebhof_patenschaften_billing` zusätzlich "Verrechnet <Jahr>": Rechnungspositionen im laufenden Geschäftsjahr). Darunter die Liste mit einer Zeile pro Mitglied; gleiche Patenschaften stehen zusammen ("3 × Hochstammbaum à 50 CHF · seit 15.10.2026"), der Stift öffnet die einzelne Patenschaft. Filter: aktiv (Standard), gekündigt (laufen noch), alle inkl. beendete, mit Sonderpreis (nicht beendete mit abweichendem Jahresbeitrag, mit Anzahl im Reiter). Sonderpreise sind in der Liste markiert ("Sonderpreis, Typ: 120 CHF"). Bestellte, noch nicht aktive Patenschaften stehen unter "Pendente Änderungen". Werkzeugleiste: E-Mail an die ausgewählten Pat:innen, E-Mails kopieren, Knöpfe "Excel" und "CSV" (Export mit dem gewählten Statusfilter, eine Zeile pro Patenschaft; Suche und Spaltenfilter werden nicht berücksichtigt). |
| **Pendente Änderungen** | Prüfung der Bestellungen: pro Mitglied die bestellten, noch nicht aktivierten Patenschaften (nach Bestelldatum gruppiert), je mit Jahresbeitrag. Bei Typen mit Maximum steht die Gesamtbelegung darunter ("Mutterkuh insgesamt: 1 von max. 2 Plätzen belegt, 1 Bestellung offen", rot bei Überbuchung). "Aktivieren per <Datum>" aktiviert die ausgewählten auf das Änderungsdatum (Standard heute, einstellbar wie bei den Ernteanteilen) und schickt dem Mitglied eine Bestätigung. "Ablehnen" storniert die Bestellung und informiert das Mitglied, optional mit Begründung. Kündigungen erscheinen hier nicht. |
| **Patenschaftstypen** | Typen anlegen und bearbeiten (Name, Beschreibung, Jahresbeitrag, Bestellbar, maximale Anzahl, Sortierung; mit `huebhof_patenschaften_billing` zusätzlich Rechnungspositionstyp). Löschen nur ohne Patenschaften, sonst "Bestellbar" ausschalten. |
| **Patenschaft erfassen** | Für Bestellungen, die nicht über den Mitgliederbereich kommen: Mitglied (Suche nach Name oder E-Mail wie beim E-Mail-Versand), Typ, Anzahl, abweichender Jahresbeitrag (leer = Preis des Typs), Bestell- und Aktivierungsdatum (leer = bleibt "bestellt"), Notizen, optional Bestätigungsmail. "Erfassen und weitere erfassen" für mehrere nacheinander. |

### Preisänderung und Sonderpreise

Ablauf bei einer Preiserhöhung aufs nächste Geschäftsjahr:

1. Mitteilung an die Pat:innen bis 31.8. (wie beim Ernteanteil).
2. Rechnungen fürs laufende Jahr erstellen. Verrechnet wird der Preis, der beim Erstellen oder Neu berechnen der Rechnung am Typ steht. Eine frühere Preisänderung würde also schon fürs laufende Jahr gelten, ebenso ein späteres Neu berechnen einer Rechnung des laufenden Jahres.
3. Unter "Aktive" den Reiter "Mit Sonderpreis" prüfen: Ausnahme noch gültig, Betrag anpassen oder Feld leeren.
4. Erst dann unter "Patenschaftstypen" den Preis ändern.

Den Grund für einen Sonderpreis in die Notizen der Patenschaft schreiben, damit er auch später nachvollziehbar ist.

Die einzelne Patenschaft zeigt den Status (mit `huebhof_patenschaften_billing` auch die Rechnungen); abweichender Jahresbeitrag, Daten und Notizen lassen sich ändern, "Kündigen" wendet die Kündigungsregel an.

Wie alle Listen in juntagrico wird die Seite "Aktive" in der breiten Ansicht angezeigt; die Formularseiten sind normal breit.

Beträge und Zahlen (Anzahl, maximale Anzahl, Sortierung) sind in den Verwaltungsformularen Textfelder ohne Pfeile, damit das Mausrad beim Scrollen den Wert nicht versehentlich ändert. Beträge lassen sich mit Punkt oder Komma eingeben ("75.50" oder "75,50"); auf dem Handy erscheint die Zahlentastatur.

Im Django-Admin erscheinen die Patenschaften zusätzlich direkt beim Mitglied (Inline).

## Installation

`settings.py`:

```python
INSTALLED_APPS = [
    ...
    'juntagrico_billing',
    'huebhof_patenschaften_billing',   # optional, vor huebhof_patenschaften
    'huebhof_patenschaften',   # nach juntagrico_billing, vor juntagrico
    'juntagrico',
    ...
]

SIGNUP_MANAGER = 'huebhof_patenschaften.signup.SponsorshipSignupManager'
```

`SIGNUP_MANAGER` fügt den Schritt "Patenschaft übernehmen" in den Bestellprozess ein. Ohne diese Einstellung werden Patenschaften nur im Mitgliederbereich angeboten.

`urls.py` (vor `juntagrico.urls` und `juntagrico_billing.urls`):

```python
re_path(r'^', include('huebhof_patenschaften.urls')),
re_path(r'^', include('huebhof_patenschaften_billing.urls')),  # optional
```

Danach `python -m manage migrate`.

Beide Reihenfolgen sind wichtig, siehe [Eingriffe in juntagrico und juntagrico_billing](#eingriffe-in-juntagrico-und-juntagrico_billing).

## Einstellungen (optional)

| Setting | Standard | Bedeutung |
|---|---|---|
| `SPONSORSHIPS_AUTO_ACTIVATE` | `False` | Wie bei den Ernteanteilen bleiben Bestellungen von Mitgliedern "bestellt", bis ein Admin sie aktiviert. `True`: ab Bestellung aktiv. Gilt nicht für "Patenschaft erfassen", dort wird das Aktivierungsdatum direkt angegeben. |
| `SPONSORSHIPS_MAX_QUANTITY` | `20` | Maximale Anzahl pro Typ und Bestellung. |
| `SPONSORSHIPS_INFO_URL` | `''` | Link "Mehr erfahren" zu einem Infodokument. Ab juntagrico 2.1 durch `DOCUMENTS` ersetzen. |

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
| `huebhof_patenschaften.change_sponsorshiptype` | Patenschaftstypen bearbeiten (Preis, Bestellbar, Buchungskonto ...). Ein neuer Preis gilt für alle Patenschaften des Typs ohne Sonderpreis. |
| `huebhof_patenschaften.delete_sponsorshiptype` | Patenschaftstypen löschen, nur solange sie keine Patenschaften haben. |
| `huebhof_patenschaften.notified_on_sponsorship_creation` | E-Mail bei jeder neuen Patenschaft. Muss auch Superusern explizit gegeben werden. |
| `huebhof_patenschaften.notified_on_sponsorship_cancellation` | E-Mail bei jeder Kündigung. Muss auch Superusern explizit gegeben werden. |

Das Menü "Patenschaften" erscheint, sobald jemand eines der Rechte zum Ansehen, Erfassen oder Verwalten hat; es zeigt nur die erlaubten Unterpunkte. Links in den Listen (z.B. auf eine einzelne Patenschaft) erscheinen nur, wenn die Zielseite erlaubt ist.

Der **Export** in der Liste braucht nur `view_sponsorship`. Das Inline beim Mitglied läuft über den Django-Admin und braucht deshalb zusätzlich den **Status "Mitarbeiter" (Staff)**.

### Vorschlag für Gruppen

| Gruppe | Berechtigungen |
|---|---|
| Patenschaften ansehen | `view_sponsorship`, `view_sponsorshiptype` |
| Patenschaften betreuen | wie "ansehen", plus `add_sponsorship`, `change_sponsorship`, `notified_on_sponsorship_creation`, `notified_on_sponsorship_cancellation` |
| Patenschaften verwalten | wie "betreuen", plus `add_sponsorshiptype`, `change_sponsorshiptype`, `delete_sponsorshiptype` |

Für die Verrechnung siehe `huebhof_patenschaften_billing`. Wie in der juntagrico-Dokumentation empfohlen: jede Rolle mit einem Test-Benutzer durchklicken.

## Erweiterungen

Andere Apps können das Addon erweitern, ohne es zu ändern (so macht es `huebhof_patenschaften_billing`):

* `extensions.register_type_form_extension()`: zusätzliche Felder im Formular der Patenschaftstypen
* Template-Blöcke (Liste in `extensions.py`), z.B. `type_columns` in `types.html`, `status_extra` in `edit.html`, `type_price_extra` in der Auswahl, `sponsorship_row_extra` in der Zusammenfassung und `sponsorship_line_extra` / `total_extra` in der Bestätigungsmail: die erweiternde App überschreibt das Template mit `{% extends %}` auf sich selbst und steht dafür in `INSTALLED_APPS` vor `huebhof_patenschaften`
* `juntagrico.util.addons.config.register_model_inline()` für `Sponsorship` und `SponsorshipType`: die Admins basieren auf `BaseAdmin`

## Eingriffe in juntagrico und juntagrico_billing

Bei Updates von juntagrico oder juntagrico_billing diese Stellen prüfen:

| Datei | Was | Voraussetzung |
|---|---|---|
| `templates/juntagrico/menu/user.html` | **Kopie** des Benutzermenüs von juntagrico 2.0 mit "Patenschaften" nach dem Ernteanteil (juntagrico bietet dort keinen Block). Bei Updates mit dem Original abgleichen. | `huebhof_patenschaften` steht in `INSTALLED_APPS` nach `juntagrico_billing`, damit dessen Menüpunkt "Rechnungen" darauf aufbaut. |
| `templates/juntagrico/menu/admin.html` | Erweitert den Block `subscriptions` des Admin-Menüs um das Aufklappmenü. Keine Kopie. | – |
| `migrations/0001_squashed_0005_max_count.py` | Fasst die früheren Migrationen 0001–0005 zusammen (`replaces`), ohne Abhängigkeit auf `juntagrico_billing`. Die alten Dateien sind entfernt: Eine bestehende Datenbank muss vor dem Update bereits auf 0005 sein (Stand `master` b6442ed), sonst zuerst diesen Stand deployen. | – |

Neue Migrationen nur mit `python -m manage makemigrations huebhof_patenschaften` erzeugen. Ohne App-Namen legt Django auch Migrationen in den installierten Paketen (juntagrico, juntagrico_billing) an, die später zu Konflikten führen.

## Tests

```
python -m manage test huebhof_patenschaften huebhof_patenschaften_billing
```

Lokal muss `JUNTAGRICO_SECRET_KEY` gesetzt sein (beliebiger Wert), sonst schlagen die Tests mit Sessions fehl.

## Noch offen

* Link zur Vereinbarung zur Patenschaft als `SPONSORSHIPS_INFO_URL` eintragen, sobald die Vereinbarung fertig ist.

### Beim Update auf juntagrico 2.1

* `templates/juntagrico/menu/user.html`: Kopie des Benutzermenüs durch die neuen Template-Blöcke ersetzen ([juntagrico#948](https://github.com/juntagrico/juntagrico/pull/948)).
* `SPONSORSHIPS_INFO_URL` durch das Setting `DOCUMENTS` ersetzen.
