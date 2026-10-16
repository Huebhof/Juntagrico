import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.generic import FormView, ListView

from juntagrico.util.auth import MultiplePermissionsRequiredMixin
from juntagrico.util import return_to_previous_location
from juntagrico.view_decorators import highlighted_menu, using_change_date
from juntagrico.views_subscription import SignupView

from . import mailer, services
from .admin import SponsorshipResource
from .config import SponsorshipConfig
from .forms import SponsorshipCreateForm, SponsorshipEditForm, SponsorshipOrderForm, SponsorshipSelectionForm, \
    SponsorshipTypeForm
from .models import Sponsorship, SponsorshipType


def any_permission_required(*perms):
    """Like permission_required, but one of the permissions is enough."""
    return user_passes_test(lambda u: any(u.has_perm(p) for p in perms))


# ---------------------------------------------------------------- Order process

class SelectSponsorshipsView(SignupView, FormView):
    """Step in the order process: select sponsorships (optional)."""
    template_name = 'huebhof_patenschaften/signup_select.html'
    form_class = SponsorshipSelectionForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['selection'] = self.signup_manager.get('sponsorships', {})
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(info_url=SponsorshipConfig.info_url(), **kwargs)

    def form_valid(self, form):
        # empty dict = deliberately continue without sponsorship
        self.signup_manager.set('sponsorships', form.selection())
        return redirect(self.signup_manager.get_next_page())


# ---------------------------------------------------------------- Member area

@login_required
@highlighted_menu('sponsorships')
def my_sponsorships(request):
    member = request.user.member
    if request.method == 'POST':
        form = SponsorshipOrderForm(request.POST)
        if form.is_valid():
            created = services.order(member, form.selection())
            mailer.confirm_order(member, created)
            mailer.notify_admins_ordered(member, created)
            messages.success(request, _('Vielen Dank! Deine Bestellung ist eingegangen.'))
            return redirect('sponsorships-mine')
    else:
        form = SponsorshipOrderForm()

    sponsorships = member.sponsorships.select_related('type').order_by('type__sort_order', 'type__name', 'order_date')
    current = [s for s in sponsorships if s.status in (Sponsorship.ORDERED, Sponsorship.ACTIVE, Sponsorship.CANCELED)]
    past = [s for s in sponsorships if s.status in (Sponsorship.ENDED, Sponsorship.WITHDRAWN)]
    return render(request, 'huebhof_patenschaften/mine.html', {
        'current': current,
        'past': past,
        'annual_total': sum(s.annual_fee for s in current if s.status != Sponsorship.CANCELED),
        'next_end_date': Sponsorship.next_end_date(),
        'form': form,
        'has_types': bool(form.types),
        'info_url': SponsorshipConfig.info_url(),
    })


@login_required
@require_POST
def cancel_sponsorship(request, sponsorship_id):
    sponsorship = get_object_or_404(Sponsorship, id=sponsorship_id, member=request.user.member)
    if sponsorship.can_be_canceled:
        was_ordered = sponsorship.status == Sponsorship.ORDERED
        sponsorship.cancel()
        mailer.confirm_cancellation(sponsorship.member, sponsorship)
        mailer.notify_admins_canceled(sponsorship.member, sponsorship)
        if was_ordered:
            messages.success(request, _('Die Bestellung wurde storniert.'))
        else:
            messages.success(request, _('Die Patenschaft ist gekündigt und läuft bis am {}.').format(
                sponsorship.end_date.strftime('%d.%m.%Y')))
    return redirect('sponsorships-mine')


# ---------------------------------------------------------------- Management

STATUS_FILTER = {
    # ordered, not yet active sponsorships: see "pending changes"
    'active': (_('Aktiv'), lambda qs: qs.active()),
    'canceled': (_('Gekündigt, laufen noch'), lambda qs: qs.canceled()),
    'all': (_('Alle inkl. beendete'), lambda qs: qs),
}


class SponsorshipsManageView(MultiplePermissionsRequiredMixin, ListView):
    permission_required = [['huebhof_patenschaften.view_sponsorship', 'huebhof_patenschaften.change_sponsorship']]
    template_name = 'huebhof_patenschaften/manage.html'

    def get_status(self):
        status = self.request.GET.get('status', 'active')
        return status if status in STATUS_FILTER else 'active'

    def get_queryset(self):
        qs = Sponsorship.objects.select_related('type', 'member')
        return STATUS_FILTER[self.get_status()][1](qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        running = Sponsorship.objects.running()
        context.update(
            status=self.get_status(),
            status_filter=[(k, v[0]) for k, v in STATUS_FILTER.items()],
            export_buttons=[('xlsx', _('Excel')), ('csv', _('CSV'))],
        )
        # Figures per type (deliberately in Python, small amounts of data)
        rows = []
        for sponsorship_type in SponsorshipType.objects.order_by('sort_order', 'name'):
            qs = Sponsorship.objects.filter(type=sponsorship_type)
            rows.append({
                'type': sponsorship_type,
                'ordered': qs.ordered().count(),
                'active': qs.active().count(),
                'canceled': qs.canceled().count(),
                'total': qs.running().total_annual_fee(),
            })
        context['overview'] = rows
        context['members'] = self.group_by_member(context['object_list'])
        context['totals'] = {
            'ordered': Sponsorship.objects.ordered().count(),
            'active': Sponsorship.objects.active().count(),
            'canceled': Sponsorship.objects.canceled().count(),
            'total': running.total_annual_fee(),
        }
        return context

    @staticmethod
    def group_by_member(sponsorships):
        """One entry per member, equal sponsorships (same type, fee, status and dates) in one line."""
        members = []
        for member, member_sponsorships in services.by_member(sponsorships).items():
            lines = {}
            for s in member_sponsorships:
                key = (s.type_id, s.annual_fee, s.status, s.order_date, s.activation_date, s.cancellation_date,
                       s.end_date)
                lines.setdefault(key, []).append(s)
            running = [s for s in member_sponsorships if s.status in (Sponsorship.ACTIVE, Sponsorship.CANCELED)]
            members.append({
                'member': member,
                'lines': [{'first': group[0], 'count': len(group), 'sponsorships': group} for group in lines.values()],
                'annual_total': sum(s.annual_fee for s in running),
                'notes': [s.notes for s in member_sponsorships if s.notes],
            })
        return members


EXPORT_FORMATS = {
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'csv': 'text/csv; charset=utf-8',
}


@any_permission_required('huebhof_patenschaften.view_sponsorship', 'huebhof_patenschaften.change_sponsorship')
def export(request):
    """Export of the list with the selected status filter as Excel or CSV (same columns as in the Django admin)."""
    status = request.GET.get('status')
    status = status if status in STATUS_FILTER else 'active'
    file_format = request.GET.get('format') if request.GET.get('format') in EXPORT_FORMATS else 'xlsx'
    qs = STATUS_FILTER[status][1](Sponsorship.objects.select_related('type', 'member'))
    data = SponsorshipResource().export(queryset=qs).export(file_format)
    if file_format == 'csv':
        data = '﻿' + data  # BOM, so that Excel reads umlauts correctly
    response = HttpResponse(data, content_type=EXPORT_FORMATS[file_format])
    response['Content-Disposition'] = f'attachment; filename="patenschaften_{status}_{datetime.date.today()}.{file_format}"'
    return response


# ---------------------------------------------------------------- Management: types and creating sponsorships

@any_permission_required('huebhof_patenschaften.view_sponsorshiptype', 'huebhof_patenschaften.change_sponsorshiptype',
                         'huebhof_patenschaften.add_sponsorshiptype')
def types(request):
    return render(request, 'huebhof_patenschaften/types.html', {
        'types': SponsorshipType.objects.annotate(
            open_count=Count('sponsorships', filter=Q(sponsorships__in=Sponsorship.objects.open()))
        ),
    })


@any_permission_required('huebhof_patenschaften.add_sponsorshiptype', 'huebhof_patenschaften.change_sponsorshiptype')
def edit_type(request, type_id=None):
    sponsorship_type = get_object_or_404(SponsorshipType, pk=type_id) if type_id else None
    if not request.user.has_perm('huebhof_patenschaften.change_sponsorshiptype' if sponsorship_type
                                 else 'huebhof_patenschaften.add_sponsorshiptype'):
        raise PermissionDenied
    if request.method == 'POST' and 'delete' in request.POST and sponsorship_type:
        if not request.user.has_perm('huebhof_patenschaften.delete_sponsorshiptype'):
            raise PermissionDenied
        if sponsorship_type.sponsorships.exists():
            messages.error(request, _('Typen mit Patenschaften können nicht gelöscht werden. '
                                      'Entferne stattdessen das Häkchen bei "Bestellbar".'))
            return redirect('sponsorships-type', type_id=sponsorship_type.id)
        sponsorship_type.delete()
        messages.success(request, _('Patenschaftstyp gelöscht.'))
        return redirect('sponsorships-types')
    form = SponsorshipTypeForm(request.POST or None, instance=sponsorship_type, cancel_url='sponsorships-types')
    if form.is_valid():
        form.save()
        messages.success(request, _('Patenschaftstyp gespeichert.'))
        return redirect('sponsorships-types')
    return render(request, 'huebhof_patenschaften/type_form.html', {'form': form, 'type': sponsorship_type})


def _can_view_overview(user):
    return user.has_perm('huebhof_patenschaften.view_sponsorship') or \
        user.has_perm('huebhof_patenschaften.change_sponsorship')


@permission_required('huebhof_patenschaften.add_sponsorship')
def create(request):
    initial = {}
    if request.GET.get('member', '').isdigit():
        initial['member'] = request.GET['member']
    form = SponsorshipCreateForm(request.POST or None, initial=initial,
                                 cancel_url=None if _can_view_overview(request.user) else 'home')
    if form.is_valid():
        d = form.cleaned_data
        created = services.create(d['member'], d['type'], d['quantity'], d['custom_annual_fee'],
                                  d['order_date'], d['activation_date'], d['notes'])
        if d['send_confirmation']:
            mailer.confirm_order(d['member'], created)
        messages.success(request, _('{} Patenschaft(en) für {} erfasst.').format(len(created), d['member']))
        if 'another' in request.POST or not _can_view_overview(request.user):
            return redirect('sponsorships-create')
        return redirect('sponsorships-manage')
    return render(request, 'huebhof_patenschaften/create.html', {
        'form': form,
        'annual_fees': {str(t.id): f'{t.annual_fee:.2f}' for t in SponsorshipType.objects.all()},
    })


@permission_required('huebhof_patenschaften.change_sponsorship')
def edit(request, sponsorship_id):
    sponsorship = get_object_or_404(Sponsorship.objects.select_related('member', 'type'), pk=sponsorship_id)
    if request.method == 'POST' and 'cancel' in request.POST:
        sponsorship.cancel()
        messages.success(request, _('Patenschaft gekündigt.'))
        return redirect('sponsorships-edit', sponsorship_id=sponsorship.id)
    form = SponsorshipEditForm(request.POST or None, instance=sponsorship)
    if form.is_valid():
        form.save()
        messages.success(request, _('Patenschaft gespeichert.'))
        return redirect('sponsorships-manage')
    return render(request, 'huebhof_patenschaften/edit.html', {'form': form, 'sponsorship': sponsorship})


# ---------------------------------------------------------------- Pending changes (like subscriptions)

@permission_required('huebhof_patenschaften.change_sponsorship')
@using_change_date
def pending(request, change_date):
    """Not yet activated orders to check, per member, grouped by order date."""
    sponsorships = list(Sponsorship.objects.ordered().select_related('member', 'type').order_by(
        'order_date', 'type__sort_order', 'type__name', 'id'))
    # occupancy of the types with a maximum, to check whether the sponsorships are still possible
    occupancy = {}
    for t in {s.type for s in sponsorships if s.type.max_count is not None}:
        occupancy[t] = {'type': t, 'running': t.sponsorships.running().count(),
                        'ordered': t.sponsorships.ordered().count(), 'max': t.max_count}
    pending = []
    for member, member_sponsorships in services.by_member(sponsorships).items():
        types = dict.fromkeys(s.type for s in member_sponsorships if s.type in occupancy)
        pending.append((member, member_sponsorships, [occupancy[t] for t in types]))
    return render(request, 'huebhof_patenschaften/pending.html', {
        'pending': pending,
        'change_date': change_date or datetime.date.today(),
    })


@require_POST
@permission_required('huebhof_patenschaften.change_sponsorship', raise_exception=True)
@using_change_date
def pending_apply(request, change_date):
    """Activates the selected sponsorships on the change date (default: today) and informs the members."""
    activated = services.activate(
        Sponsorship.objects.ordered().filter(id__in=request.POST.getlist('sponsorships[]')), change_date)
    messages.success(request, _('{} Patenschaft(en) aktiviert, Bestätigung per E-Mail versandt.').format(
        len(activated)))
    return return_to_previous_location(request)


@require_POST
@permission_required('huebhof_patenschaften.change_sponsorship', raise_exception=True)
def pending_reject(request):
    """Rejects the selected orders (e.g. no place left) and informs the members."""
    rejected = services.reject(
        Sponsorship.objects.ordered().filter(id__in=request.POST.getlist('sponsorships[]')),
        request.POST.get('reason', '').strip())
    messages.success(request, _('{} Bestellung(en) abgelehnt, Mitglied per E-Mail informiert.').format(
        len(rejected)))
    return return_to_previous_location(request)
