import datetime

from django.db import transaction

from .config import PatenschaftConfig
from .models import Patenschaft, PatenschaftTyp


def auswahl_aufloesen(auswahl):
    """{'typ_id': anzahl} (aus Session/Formular) -> [(PatenschaftTyp, anzahl)] mit anzahl > 0."""
    auswahl = {str(k): int(v or 0) for k, v in (auswahl or {}).items()}
    typen = PatenschaftTyp.objects.filter(id__in=[k for k, v in auswahl.items() if v > 0])
    return [(typ, auswahl[str(typ.id)]) for typ in typen]


@transaction.atomic
def bestellen(member, auswahl, date=None):
    """Legt pro bestellter Einheit eine Patenschaft an und gibt die neuen Objekte zurück."""
    date = date or datetime.date.today()
    aktiv_ab = date if PatenschaftConfig.auto_aktivieren() else None
    neue = []
    for typ, anzahl in auswahl_aufloesen(auswahl):
        for _ in range(anzahl):
            neue.append(Patenschaft.objects.create(
                member=member, typ=typ, jahresbeitrag=typ.jahresbeitrag,
                bestellt_am=date, aktiviert_am=aktiv_ab,
            ))
    return neue


@transaction.atomic
def erfassen(member, typ, anzahl, jahresbeitrag=None, bestellt_am=None, aktiviert_am=None, notizen=''):
    """Erfassung durch Admins: Daten werden explizit angegeben, PATENSCHAFTEN_AUTO_AKTIVIEREN gilt nicht."""
    return [Patenschaft.objects.create(
        member=member, typ=typ, jahresbeitrag=typ.jahresbeitrag if jahresbeitrag is None else jahresbeitrag,
        bestellt_am=bestellt_am or datetime.date.today(), aktiviert_am=aktiviert_am, notizen=notizen,
    ) for _ in range(anzahl)]


def gruppieren(patenschaften):
    """Gruppiert Patenschaften nach Typ und Status für die Anzeige ("3 × Baumpatenschaft")."""
    gruppen = {}
    for p in patenschaften:
        key = (p.typ_id, p.status, p.ende)
        if key not in gruppen:
            gruppen[key] = {'typ': p.typ, 'status': p.status, 'status_display': p.get_status_display(),
                            'ende': p.ende, 'objekte': [], 'summe': 0}
        gruppen[key]['objekte'].append(p)
        gruppen[key]['summe'] += p.jahresbeitrag
    for g in gruppen.values():
        g['anzahl'] = len(g['objekte'])
    return list(gruppen.values())
