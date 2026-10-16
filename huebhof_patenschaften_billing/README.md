# huebhof_patenschaften_billing

Verrechnung der Patenschaften aus [`huebhof_patenschaften`](../huebhof_patenschaften/README.md) über `juntagrico_billing`. Ohne diese App funktionieren die Patenschaften auch, werden aber nicht verrechnet.

## Installation

`settings.py`:

```python
INSTALLED_APPS = [
    ...
    'juntagrico_billing',
    'huebhof_patenschaften_billing',   # vor huebhof_patenschaften
    'huebhof_patenschaften',
    'juntagrico',
    ...
]
```

`urls.py` (vor `juntagrico_billing.urls`):

```python
re_path(r'^', include('huebhof_patenschaften_billing.urls')),
```

Danach `python -m manage migrate`.

Beide Reihenfolgen sind wichtig: Die App erweitert Templates und Admin von `huebhof_patenschaften` und ersetzt drei Views von `juntagrico_billing` (siehe unten).

## Verrechnung

Patenschaften erscheinen als eigene Rechnungspositionen (Custom Bill-Item Types) auf den QR-Rechnungen, im Buchungsexport und im Bexio-Export. Die Verrechnung läuft im normalen Ablauf unter **Rechnungen und Buchhaltung**:

1. Optional pro Patenschaftstyp einen **Rechnungspositionstyp** mit Buchungskonto zuweisen: Custom Bill-Item Types im Django-Admin anlegen, dann unter Patenschaften → Patenschaftstypen beim Typ auswählen. Ohne Zuweisung wird der Typ "Patenschaft" verwendet; er wird beim ersten Verrechnen ohne Buchungskonto angelegt, das Konto im Django-Admin nachtragen (oder den Typ "Patenschaft" vorher selbst mit Konto anlegen).
2. **Anstehende Rechnungen** zeigt neben den Ernteanteilen auch die unverrechneten Patenschaften, auch von Mitgliedern ohne Ernteanteil.
3. **Alle erstellen** erstellt die Ernteanteil-Rechnungen und fügt die Patenschaften daran an. Jedes Mitglied erhält eine Rechnung; Mitglieder ohne Ernteanteil eine Rechnung nur mit Patenschaften. Hat ein Mitglied im Jahr bereits eine unveröffentlichte Rechnung, kommen die Patenschaften dorthin.
4. **Rechnung neu berechnen** (Django-Admin bei der Rechnung) berechnet auch die Patenschaften neu (z.B. nach einem Austritt) und ergänzt fehlende Patenschaften des Mitglieds.

Verrechnet werden alle aktivierten Patenschaften mit einem Beitrag über 0, die im Geschäftsjahr laufen. Wie bei den Ernteanteilen wird nur die Zeit im Geschäftsjahr verrechnet: Beginnt oder endet eine Patenschaft während des Jahres, wird der Jahresbeitrag tageweise anteilig berechnet und auf 5 Rappen gerundet (gleiche Berechnung wie `scale_subscriptionpart_price` von juntagrico_billing). Auf der Rechnung steht dann der Zeitraum, z.B. "Patenschaft Huhn (16.10.2026–31.12.2026)". Jede Patenschaft wird pro Geschäftsjahr nur einmal verrechnet; wird die Rechnung gelöscht, ist sie wieder verrechenbar. Veröffentlichte Rechnungen werden nur beim expliziten Neu berechnen ergänzt.

Beim Bestellen sehen Mitglieder neben dem Jahresbeitrag auch den anteiligen Betrag für das laufende Geschäftsjahr ("Für 2026 anteilig ab heute: ca. 7.60 CHF"): auf den Karten im Mitgliederbereich und im Anmeldeprozess, in der Zusammenfassung und in der Bestätigungsmail. "Ca.", weil ab der Aktivierung verrechnet wird, die Admins unter "Pendente Änderungen" vornehmen.

Die Rechnungen einer Patenschaft stehen auf ihrer Bearbeiten-Seite und im Django-Admin.

## Berechtigungen

| Berechtigung | Erlaubt |
|---|---|
| `juntagrico.is_book_keeper` | Patenschaften erscheinen in "Anstehende Rechnungen" usw. (Recht von juntagrico_billing). |
| `huebhof_patenschaften.change_sponsorshiptype` | Rechnungspositionstyp beim Patenschaftstyp wählen (wie die übrigen Felder des Typs). |

## Eingriffe in juntagrico_billing

| Datei | Was | Voraussetzung |
|---|---|---|
| `views.py`, `urls.py` | Eigene Views unter den Pfaden von juntagrico_billing (`jb/pending_bills`, `jb/bills_generate`, `jb/bill_recalc/<id>`). Sie rufen die Funktionen von juntagrico_billing auf und ergänzen die Patenschaften. Bei Updates prüfen, ob sich die Original-Views geändert haben. Sauberer wären Hooks in juntagrico_billing, die es noch nicht gibt. | `huebhof_patenschaften_billing.urls` steht in `urls.py` vor `juntagrico_billing.urls` (ein Test prüft das). |
| `migrations/0001_initial.py` | Übernimmt die Daten der Billing-Felder, die bis Migration 0003 in `huebhof_patenschaften` waren, und läuft vor deren Entfernung (`run_before`). | – |

## Tests

```
python -m manage test huebhof_patenschaften_billing
```
