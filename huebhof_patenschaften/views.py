from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.generic import FormView, ListView

from juntagrico.util.auth import MultiplePermissionsRequiredMixin
from juntagrico.util import return_to_previous_location
from juntagrico.view_decorators import highlighted_menu, using_change_date
from juntagrico.views_subscription import SignupView

from . import mailer, services
from .config import PatenschaftConfig
from .forms import PatenschaftAuswahlForm, PatenschaftBearbeitenForm, PatenschaftBestellenForm, \
    PatenschaftErfassenForm, PatenschaftTypForm
from .models import Patenschaft, PatenschaftTyp


# ---------------------------------------------------------------- Bestellprozess

class SelectPatenschaftenView(SignupView, FormView):
    """Schritt im Bestellprozess: Patenschaften wählen (optional)."""
    template_name = 'huebhof_patenschaften/signup_select.html'
    form_class = PatenschaftAuswahlForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['auswahl'] = self.signup_manager.get('patenschaften', {})
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(info_url=PatenschaftConfig.info_url(), **kwargs)

    def form_valid(self, form):
        # leeres Dict = bewusst ohne Patenschaft weiter
        self.signup_manager.set('patenschaften', form.auswahl())
        return redirect(self.signup_manager.get_next_page())


# ---------------------------------------------------------------- Mitgliederbereich

@login_required
@highlighted_menu('patenschaften')
def meine_patenschaften(request):
    member = request.user.member
    if request.method == 'POST':
        form = PatenschaftBestellenForm(request.POST)
        if form.is_valid():
            neue = services.bestellen(member, form.auswahl())
            mailer.bestaetigung_an_pate(member, neue)
            mailer.admin_bestellt(member, neue)
            messages.success(request, _('Vielen Dank! Deine Bestellung ist eingegangen.'))
            return redirect('patenschaften-mine')
    else:
        form = PatenschaftBestellenForm()

    alle = member.patenschaften.select_related('typ').order_by('typ__sortierung', 'typ__name', 'bestellt_am')
    laufend = [p for p in alle if p.status in ('bestellt', 'aktiv', 'gekuendigt')]
    vergangen = [p for p in alle if p.status in ('beendet', 'storniert')]
    return render(request, 'huebhof_patenschaften/meine.html', {
        'laufend': laufend,
        'vergangen': vergangen,
        'jahressumme': sum(p.jahresbeitrag for p in laufend if p.status != 'gekuendigt'),
        'naechstes_ende': Patenschaft.naechstes_ende(),
        'form': form,
        'hat_typen': bool(form.typen),
        'info_url': PatenschaftConfig.info_url(),
    })


@login_required
@require_POST
def patenschaft_kuendigen(request, patenschaft_id):
    patenschaft = get_object_or_404(Patenschaft, id=patenschaft_id, member=request.user.member)
    if patenschaft.kann_gekuendigt_werden:
        war_bestellt = patenschaft.status == 'bestellt'
        patenschaft.kuendigen()
        mailer.kuendigung_an_pate(patenschaft.member, patenschaft)
        mailer.admin_gekuendigt(patenschaft.member, patenschaft)
        if war_bestellt:
            messages.success(request, _('Die Bestellung wurde storniert.'))
        else:
            messages.success(request, _('Die Patenschaft ist gekündigt und läuft bis am {}.').format(
                patenschaft.ende.strftime('%d.%m.%Y')))
    return redirect('patenschaften-mine')


# ---------------------------------------------------------------- Administration

STATUS_FILTER = {
    'offen': (_('Alle laufenden und bestellten'), lambda qs: qs.offen()),
    'bestellt': (_('Bestellt, noch nicht aktiv'), lambda qs: qs.bestellt()),
    'aktiv': (_('Aktiv'), lambda qs: qs.aktiv()),
    'gekuendigt': (_('Gekündigt, laufen noch'), lambda qs: qs.gekuendigt()),
    'alle': (_('Alle inkl. beendete'), lambda qs: qs),
}


class PatenschaftenManageView(MultiplePermissionsRequiredMixin, ListView):
    permission_required = [['huebhof_patenschaften.view_patenschaft', 'huebhof_patenschaften.change_patenschaft']]
    template_name = 'huebhof_patenschaften/manage.html'

    def get_status(self):
        status = self.request.GET.get('status', 'offen')
        return status if status in STATUS_FILTER else 'offen'

    def get_queryset(self):
        qs = Patenschaft.objects.select_related('typ', 'member')
        return STATUS_FILTER[self.get_status()][1](qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        laufend = Patenschaft.objects.laufend()
        context.update(
            status=self.get_status(),
            status_filter=[(k, v[0]) for k, v in STATUS_FILTER.items()],
        )
        # Kennzahlen pro Typ (bewusst in Python, kleine Datenmengen)
        zeilen = []
        for typ in PatenschaftTyp.objects.order_by('sortierung', 'name'):
            qs = Patenschaft.objects.filter(typ=typ)
            zeilen.append({
                'typ': typ,
                'bestellt': qs.bestellt().count(),
                'aktiv': qs.aktiv().count(),
                'gekuendigt': qs.gekuendigt().count(),
                'summe': qs.laufend().aggregate(s=Sum('jahresbeitrag'))['s'] or 0,
            })
        context['uebersicht'] = zeilen
        context['total'] = {
            'bestellt': Patenschaft.objects.bestellt().count(),
            'aktiv': Patenschaft.objects.aktiv().count(),
            'gekuendigt': Patenschaft.objects.gekuendigt().count(),
            'summe': laufend.aggregate(s=Sum('jahresbeitrag'))['s'] or 0,
        }
        return context


@require_POST
@permission_required('huebhof_patenschaften.change_patenschaft', raise_exception=True)
def patenschaften_aktivieren(request):
    ids = [i for i in request.POST.get('ids', '').replace('_', ',').split(',') if i.strip().isdigit()]
    anzahl = 0
    for p in Patenschaft.objects.bestellt().filter(id__in=ids):
        p.aktivieren()
        anzahl += 1
    messages.success(request, _('{} Patenschaft(en) aktiviert.').format(anzahl))
    return redirect(request.META.get('HTTP_REFERER') or 'patenschaften-manage')


# ---------------------------------------------------------------- Verwaltung: Typen und Patenschaften erfassen

def any_permission_required(*perms):
    """Wie permission_required, aber eine der Berechtigungen genügt."""
    return user_passes_test(lambda u: any(u.has_perm(p) for p in perms))


@any_permission_required('huebhof_patenschaften.view_patenschafttyp', 'huebhof_patenschaften.change_patenschafttyp',
                         'huebhof_patenschaften.add_patenschafttyp')
def typen(request):
    return render(request, 'huebhof_patenschaften/typen.html', {
        'typen': PatenschaftTyp.objects.annotate(
            anzahl=Count('patenschaften', filter=Q(patenschaften__in=Patenschaft.objects.offen()))
        ).select_related('rechnungsposition'),
    })


@any_permission_required('huebhof_patenschaften.add_patenschafttyp', 'huebhof_patenschaften.change_patenschafttyp')
def typ_bearbeiten(request, typ_id=None):
    typ = get_object_or_404(PatenschaftTyp, pk=typ_id) if typ_id else None
    if not request.user.has_perm('huebhof_patenschaften.change_patenschafttyp' if typ
                                 else 'huebhof_patenschaften.add_patenschafttyp'):
        raise PermissionDenied
    if request.method == 'POST' and 'loeschen' in request.POST and typ:
        if not request.user.has_perm('huebhof_patenschaften.delete_patenschafttyp'):
            raise PermissionDenied
        if typ.patenschaften.exists():
            messages.error(request, _('Typen mit Patenschaften können nicht gelöscht werden. '
                                      'Entferne stattdessen das Häkchen bei "Bestellbar".'))
            return redirect('patenschaften-typ', typ_id=typ.id)
        typ.delete()
        messages.success(request, _('Patenschaftstyp gelöscht.'))
        return redirect('patenschaften-typen')
    form = PatenschaftTypForm(request.POST or None, instance=typ, abbrechen='patenschaften-typen')
    if form.is_valid():
        form.save()
        messages.success(request, _('Patenschaftstyp gespeichert.'))
        return redirect('patenschaften-typen')
    return render(request, 'huebhof_patenschaften/typ_form.html', {'form': form, 'typ': typ})


def _darf_uebersicht(user):
    return user.has_perm('huebhof_patenschaften.view_patenschaft') or         user.has_perm('huebhof_patenschaften.change_patenschaft')


@permission_required('huebhof_patenschaften.add_patenschaft')
def erfassen(request):
    initial = {}
    if request.GET.get('member', '').isdigit():
        initial['member'] = request.GET['member']
    form = PatenschaftErfassenForm(request.POST or None, initial=initial,
                                   abbrechen=None if _darf_uebersicht(request.user) else 'home')
    if form.is_valid():
        d = form.cleaned_data
        neue = services.erfassen(d['member'], d['typ'], d['anzahl'], d['jahresbeitrag'],
                                 d['bestellt_am'], d['aktiviert_am'], d['notizen'])
        if d['bestaetigung']:
            mailer.bestaetigung_an_pate(d['member'], neue)
        messages.success(request, _('{} Patenschaft(en) für {} erfasst.').format(len(neue), d['member']))
        if 'weitere' in request.POST or not _darf_uebersicht(request.user):
            return redirect('patenschaften-erfassen')
        return redirect('patenschaften-manage')
    return render(request, 'huebhof_patenschaften/erfassen.html', {
        'form': form,
        'beitraege': {str(t.id): f'{t.jahresbeitrag:.2f}' for t in PatenschaftTyp.objects.all()},
    })


@permission_required('huebhof_patenschaften.change_patenschaft')
def bearbeiten(request, patenschaft_id):
    patenschaft = get_object_or_404(Patenschaft.objects.select_related('member', 'typ'), pk=patenschaft_id)
    if request.method == 'POST' and 'kuendigen' in request.POST:
        patenschaft.kuendigen()
        messages.success(request, _('Patenschaft gekündigt.'))
        return redirect('patenschaften-bearbeiten', patenschaft_id=patenschaft.id)
    form = PatenschaftBearbeitenForm(request.POST or None, instance=patenschaft)
    if form.is_valid():
        form.save()
        messages.success(request, _('Patenschaft gespeichert.'))
        return redirect('patenschaften-manage')
    return render(request, 'huebhof_patenschaften/bearbeiten.html', {
        'form': form, 'patenschaft': patenschaft,
        'rechnungen': patenschaft.rechnungspositionen.select_related('bill__business_year'),
    })


# ---------------------------------------------------------------- Pendente Änderungen (wie bei den Ernteanteilen)

@permission_required('huebhof_patenschaften.change_patenschaft')
def pendent(request):
    """Noch nicht aktivierte Bestellungen, pro Mitglied, nach Bestelldatum gruppiert."""
    pro_member = {}
    for p in Patenschaft.objects.bestellt().select_related('member', 'typ').order_by('bestellt_am', 'typ__sortierung', 'id'):
        pro_member.setdefault(p.member, []).append(p)
    return render(request, 'huebhof_patenschaften/pendent.html', {'pendent': list(pro_member.items())})


@require_POST
@permission_required('huebhof_patenschaften.change_patenschaft', raise_exception=True)
@using_change_date
def pendent_anwenden(request, change_date):
    """Aktiviert die ausgewählten Patenschaften auf das Änderungsdatum (Standard: heute)."""
    ids = request.POST.getlist('patenschaften[]')
    anzahl = 0
    with transaction.atomic():
        for p in Patenschaft.objects.bestellt().filter(id__in=ids):
            p.aktivieren(change_date)
            anzahl += 1
    messages.success(request, _('{} Patenschaft(en) aktiviert.').format(anzahl))
    return return_to_previous_location(request)
