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
4. **Rechnung neu berechnen** (Django-Admin bei der Rechnung) berechnet auch die Patenschaften neu (z.B. nach einer Preisänderung) und ergänzt fehlende Patenschaften des Mitglieds. Die Sammelaktion "Rechnungen neu berechnen" in der Rechnungsliste berechnet die Patenschaften nicht mit; Rechnungen mit Patenschaften einzeln neu berechnen.

Verrechnet werden alle aktivierten Patenschaften mit einem Beitrag über 0, die im Geschäftsjahr laufen. Massgebend ist der Preis des Typs beim Erstellen oder Neu berechnen der Rechnung, ausser die Patenschaft hat einen abweichenden Jahresbeitrag (wie bei den Ernteanteilen). Anders als bei den Ernteanteilen wird immer der volle Jahresbeitrag verrechnet, auch wenn eine Patenschaft während des Jahres beginnt oder endet (keine anteilige Berechnung): Eine Patenschaft unterstützt die Tierhaltung für ein ganzes Jahr, und die Kosten (Klauenpflege, Tierarzt, Futter) fallen pro Jahr an. Soll eine Patenschaft erst im neuen Jahr beginnen, beim Aktivieren den 01.01. als Datum setzen. Jede Patenschaft wird pro Geschäftsjahr nur einmal verrechnet; wird die Rechnung gelöscht, ist sie wieder verrechenbar. Veröffentlichte Rechnungen werden nur beim expliziten Neu berechnen ergänzt.

Die Rechnungen einer Patenschaft stehen auf ihrer Bearbeiten-Seite und im Django-Admin.

## Berechtigungen

| Berechtigung | Erlaubt |
|---|---|
| `juntagrico.is_book_keeper` | Patenschaften erscheinen in "Anstehende Rechnungen" usw. (Recht von juntagrico_billing). |
| `huebhof_patenschaften.change_sponsorshiptype` | Rechnungspositionstyp beim Patenschaftstyp wählen (wie die übrigen Felder des Typs). |

## Eingriffe in juntagrico_billing

| Datei | Was | Voraussetzung |
|---|---|---|
| `views.py`, `urls.py` | Eigene Views unter den Pfaden von juntagrico_billing (`jb/pending_bills`, `jb/bills_generate`, `jb/bill_recalc/<id>`). Sie rufen die Funktionen von juntagrico_billing auf und ergänzen die Patenschaften. Bei Updates prüfen, ob sich die Original-Views geändert haben. Sauberer wären Hooks in juntagrico_billing, die es noch nicht gibt ([juntagrico-billing#88](https://github.com/juntagrico/juntagrico-billing/issues/88)). | `huebhof_patenschaften_billing.urls` steht in `urls.py` vor `juntagrico_billing.urls` (ein Test prüft das). |
| `migrations/0001_squashed_0001_initial.py` | Ersetzt die frühere 0001 (`replaces`) ohne die Datenübernahme aus den Billing-Feldern von `huebhof_patenschaften`, die es in deren zusammengefasster Migration nicht mehr gibt. | – |

## Tests

```
python -m manage test huebhof_patenschaften_billing
```
