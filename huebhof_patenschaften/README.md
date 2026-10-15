# huebhof_patenschaften

Juntagrico-Addon (ab Juntagrico 2.0) für Patenschaften der Solawi Huebhof.

## Funktionen

* **Patenschaftstypen** mit Name, Beschreibung und Jahresbeitrag (Django-Admin → Patenschaften → Patenschaftstypen). Nur "bestellbare" Typen werden angeboten.
* **Bestellprozess**: Nach der Auswahl der Ernteanteile (und Zusatz-Abos) folgt der Schritt "Patenschaft übernehmen". Alle Felder auf 0 = ohne Patenschaft weiter. Die Zusammenfassung zeigt die Auswahl mit Bearbeiten-Link.
* **Kumulierbar**: Pro übernommener Patenschaft ein eigener Datensatz (3 × Baum = 3 Einträge), jede einzeln kündbar.
* **Unabhängig vom Ernteanteil**: Patenschaften hängen am Mitglied, nicht am Abo.
* **Mitgliederbereich** "Patenschaften": Liste der eigenen Patenschaften mit Jahrestotal, weitere bestellen, kündigen.
* **Kündigung** per Ende Geschäftsjahr, gleiche Regel wie bei den Ernteanteilen: bis Ende `BUSINESS_YEAR_CANCELATION_MONTH` aufs Ende des laufenden Jahres, danach aufs Ende des Folgejahres. Noch nicht aktivierte Bestellungen werden sofort storniert.
* **Administration** "Patenschaften" im Admin-Menü: Kennzahlen pro Typ (bestellt, aktiv, gekündigt, Summe Jahresbeiträge), Liste mit Filtern, E-Mail an Pat:innen, Sammelaktivierung. Export (Excel/CSV) im Django-Admin.
* Patenschaften erscheinen im Django-Admin direkt beim Mitglied (Inline).
* **Austritt**: Wird ein Mitglied deaktiviert, enden seine Patenschaften am selben Tag.
* **E-Mails**: Bestätigung an die Pat:in bei Bestellung und Kündigung. Admins mit den Rechten "Wird bei neuer / gekündigter Patenschaft per E-Mail informiert" erhalten eine Benachrichtigung.

## Installation

`settings.py`:

```python
INSTALLED_APPS = [
    ...
    'huebhof_patenschaften',   # vor juntagrico_billing und juntagrico
    'juntagrico_billing',
    'juntagrico',
    ...
]

SIGNUP_MANAGER = 'huebhof_patenschaften.signup.PatenschaftSignupManager'
```

`urls.py` (vor `juntagrico.urls`):

```python
re_path(r'^', include('huebhof_patenschaften.urls')),
```

Danach `python -m manage migrate`.

## Einstellungen (optional)

| Setting | Standard | Bedeutung |
|---|---|---|
| `PATENSCHAFTEN_AUTO_AKTIVIEREN` | `True` | `False`: Bestellungen bleiben "bestellt", bis ein Admin sie aktiviert (z.B. nach Zahlungseingang). |
| `PATENSCHAFTEN_IM_SIGNUP` | `True` | Schritt im Bestellprozess anzeigen. |
| `PATENSCHAFTEN_MAX_ANZAHL` | `20` | Maximale Anzahl pro Typ und Bestellung. |
| `PATENSCHAFTEN_INFO_URL` | `''` | Link "Mehr erfahren" zu einem Infodokument. |

## Berechtigungen

* `huebhof_patenschaften.view_patenschaft` / `change_patenschaft`: Admin-Übersicht sehen bzw. aktivieren.
* `notified_on_patenschaft_bestellung`, `notified_on_patenschaft_kuendigung`: E-Mail-Benachrichtigungen.

## Tests

```
python -m manage test huebhof_patenschaften
```

## Noch offen

* Verrechnung: Aktuell über den Export. Eine Anbindung an `juntagrico_billing` (QR-Rechnung) ist möglich, aber noch nicht gebaut.
* Unterjährige Bestellungen werden mit dem vollen Jahresbeitrag erfasst (kein pro rata).
