import datetime

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Layout, Submit
from django import forms
from django.core.validators import MaxValueValidator
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from juntagrico.entity.member import Member
from juntagrico.forms import JuntagricoDateWidget as _JuntagricoDateWidget

from . import extensions
from .config import SponsorshipConfig
from .models import Sponsorship, SponsorshipType


class SponsorshipSelectionForm(forms.Form):
    """One number field per orderable type. All 0 = continue without sponsorship."""

    def __init__(self, *args, selection=None, **kwargs):
        super().__init__(*args, **kwargs)
        selection = {str(k): v for k, v in (selection or {}).items()}
        self.types = list(SponsorshipType.objects.visible())
        for sponsorship_type in self.types:
            # available is also used in the template ("noch 3 verfügbar", "ausgebucht")
            sponsorship_type.available = sponsorship_type.available_count()
            max_value = SponsorshipConfig.max_quantity()
            if sponsorship_type.available is not None:
                max_value = min(max_value, sponsorship_type.available)
            field = forms.IntegerField(
                label=sponsorship_type.name, min_value=0, max_value=max_value,
                required=False, initial=selection.get(str(sponsorship_type.id), 0),
                widget=forms.NumberInput(attrs={'class': 'form-control sponsorship-quantity'}),
                error_messages={'max_value': _('Höchstens %(limit_value)s möglich.')},
            )
            if sponsorship_type.available == 0:
                field.disabled = True
                field.initial = 0
            self.fields[self.field_name(sponsorship_type)] = field

    @staticmethod
    def field_name(sponsorship_type):
        return f'type_{sponsorship_type.id}'

    def rows(self):
        """For the template: [(type, boundfield)]."""
        return [(t, self[self.field_name(t)]) for t in self.types]

    def selection(self):
        """{'type_id': quantity} with quantity > 0 only, JSON serializable for the session."""
        return {str(t.id): self.cleaned_data.get(self.field_name(t)) or 0
                for t in self.types if self.cleaned_data.get(self.field_name(t))}


class SponsorshipOrderForm(SponsorshipSelectionForm):
    """Ordering in the member area: at least one sponsorship required."""

    def clean(self):
        cleaned = super().clean()
        if not any(cleaned.get(self.field_name(t)) for t in self.types):
            raise forms.ValidationError(_('Bitte wähle mindestens eine Patenschaft aus.'))
        return cleaned


# ---------------------------------------------------------------- Management

class JuntagricoDateWidget(_JuntagricoDateWidget):
    """Browser date picker like in juntagrico, but also for empty fields."""

    def format_value(self, value):
        return None if value in (None, '') else super().format_value(value)


def _button(name, label, css_class, **kwargs):
    """Submit button with exactly the given style (crispy forms always adds btn-primary otherwise)."""
    button = Submit(name, label, **kwargs)
    button.field_classes = f'btn {css_class}'
    return button


def _helper(*fields, submit=_('Speichern'), extra=None, cancel_url=None):
    helper = FormHelper()
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-md-3'
    helper.field_class = 'col-md-9'
    buttons = [_button('submit', submit, 'btn-success')]
    if extra:
        buttons.append(extra)
    buttons.append(HTML('<a href="%s" class="btn btn-outline-secondary">%s</a>'
                        % (reverse(cancel_url or 'sponsorships-manage'), _('Abbrechen'))))
    helper.layout = Layout(*fields, FormActions(*buttons))
    return helper


class MemberChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, member):
        return f'{member.last_name} {member.first_name} ({member.email})'


class SponsorshipTypeForm(forms.ModelForm):
    class Meta:
        model = SponsorshipType
        fields = ['name', 'description', 'annual_fee', 'visible', 'max_count', 'sort_order']
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, cancel_url=None, **kwargs):
        super().__init__(*args, **kwargs)
        for extension in extensions.type_form_extensions():
            extension.contribute(self)
        self.helper = _helper(*self.fields, cancel_url=cancel_url)

    def save(self, commit=True):
        sponsorship_type = super().save(commit)
        for extension in extensions.type_form_extensions():
            extension.save(self, sponsorship_type)
        return sponsorship_type


class SponsorshipCreateForm(forms.Form):
    """Admins create sponsorships for a member (e.g. ordered by phone)."""
    member = MemberChoiceField(queryset=Member.objects.none(), label=_('Pat:in'))
    type = forms.ModelChoiceField(queryset=SponsorshipType.objects.all(), label=_('Typ'))
    quantity = forms.IntegerField(label=_('Anzahl'), min_value=1, initial=1)
    custom_annual_fee = forms.DecimalField(
        label=_('Abweichender Jahresbeitrag'), required=False, min_value=0, max_digits=8, decimal_places=2,
        help_text=_('Pro Patenschaft. Leer: Jahresbeitrag des Typs, auch bei späteren Preisänderungen. '
                    'Nur für Ausnahmen ausfüllen, z.B. einen Sonderpreis.'))
    order_date = forms.DateField(label=_('Bestellt am'), initial=datetime.date.today, widget=JuntagricoDateWidget)
    activation_date = forms.DateField(
        label=_('Aktiviert am'), required=False, initial=datetime.date.today, widget=JuntagricoDateWidget,
        help_text=_('Leer: Patenschaft bleibt "bestellt", bis sie aktiviert wird.'))
    notes = forms.CharField(label=_('Notizen'), required=False, widget=forms.Textarea(attrs={'rows': 3}))
    send_confirmation = forms.BooleanField(label=_('Bestätigung per E-Mail an die Pat:in senden'), required=False)

    def __init__(self, *args, cancel_url=None, **kwargs):
        super().__init__(*args, **kwargs)
        today = datetime.date.today()
        self.fields['member'].queryset = Member.objects.filter(
            Q(deactivation_date__isnull=True) | Q(deactivation_date__gt=today)).order_by('last_name', 'first_name')
        self.fields['quantity'].max_value = SponsorshipConfig.max_quantity()
        self.fields['quantity'].validators.append(MaxValueValidator(SponsorshipConfig.max_quantity()))
        self.helper = _helper(*self.fields, submit=_('Erfassen'), cancel_url=cancel_url,
                              extra=_button('another', _('Erfassen und weitere erfassen'), 'btn-outline-success'))


class SponsorshipEditForm(forms.ModelForm):
    class Meta:
        model = Sponsorship
        fields = ['type', 'custom_annual_fee', 'order_date', 'activation_date', 'cancellation_date', 'end_date', 'notes']
        widgets = {f: JuntagricoDateWidget for f in ['order_date', 'activation_date', 'cancellation_date', 'end_date']}
        widgets['notes'] = forms.Textarea(attrs={'rows': 3})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['custom_annual_fee'].widget.attrs['placeholder'] = f'{self.instance.type.annual_fee:.2f}'
        extra = None
        if self.instance.can_be_canceled:
            extra = _button('cancel', _('Kündigen'), 'btn-danger',
                            onclick="return confirm('%s')" % _('Patenschaft kündigen?'))
        self.helper = _helper(*self.Meta.fields, extra=extra)
