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

from .config import PatenschaftConfig
from .models import Patenschaft, PatenschaftTyp


class PatenschaftAuswahlForm(forms.Form):
    """Pro bestellbarem Typ ein Zahlenfeld. Alles 0 = ohne Patenschaft weiter."""

    def __init__(self, *args, auswahl=None, **kwargs):
        super().__init__(*args, **kwargs)
        auswahl = {str(k): v for k, v in (auswahl or {}).items()}
        self.typen = list(PatenschaftTyp.objects.sichtbar())
        for typ in self.typen:
            self.fields[self.feldname(typ)] = forms.IntegerField(
                label=typ.name, min_value=0, max_value=PatenschaftConfig.max_anzahl(),
                required=False, initial=auswahl.get(str(typ.id), 0),
                widget=forms.NumberInput(attrs={'class': 'form-control patenschaft-anzahl'}),
            )

    @staticmethod
    def feldname(typ):
        return f'typ_{typ.id}'

    def zeilen(self):
        """Für das Template: [(typ, boundfield)]."""
        return [(typ, self[self.feldname(typ)]) for typ in self.typen]

    def auswahl(self):
        """{'typ_id': anzahl} nur mit anzahl > 0, JSON-serialisierbar für die Session."""
        return {str(typ.id): self.cleaned_data.get(self.feldname(typ)) or 0
                for typ in self.typen if self.cleaned_data.get(self.feldname(typ))}


class PatenschaftBestellenForm(PatenschaftAuswahlForm):
    """Nachbestellen im Mitgliederbereich: mindestens eine Patenschaft nötig."""

    def clean(self):
        cleaned = super().clean()
        if not any(cleaned.get(self.feldname(t)) for t in self.typen):
            raise forms.ValidationError(_('Bitte wähle mindestens eine Patenschaft aus.'))
        return cleaned


# ---------------------------------------------------------------- Verwaltung

class JuntagricoDateWidget(_JuntagricoDateWidget):
    """Datumsauswahl des Browsers, wie in juntagrico, aber auch für leere Felder."""

    def format_value(self, value):
        return None if value in (None, '') else super().format_value(value)


def _helper(*felder, submit=_('Speichern'), extra=None, abbrechen=None):
    helper = FormHelper()
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-md-3'
    helper.field_class = 'col-md-9'
    buttons = [Submit('submit', submit, css_class='btn-success')]
    if extra:
        buttons.append(extra)
    buttons.append(HTML('<a href="%s" class="btn btn-outline-secondary">%s</a>'
                        % (reverse(abbrechen or 'patenschaften-manage'), _('Abbrechen'))))
    helper.layout = Layout(*felder, FormActions(*buttons))
    return helper


class MemberChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, member):
        return f'{member.last_name} {member.first_name} ({member.email})'


class PatenschaftTypForm(forms.ModelForm):
    class Meta:
        model = PatenschaftTyp
        fields = ['name', 'beschreibung', 'jahresbeitrag', 'sichtbar', 'sortierung', 'rechnungsposition']
        widgets = {'beschreibung': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, abbrechen=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = _helper(*self.Meta.fields, abbrechen=abbrechen)


class PatenschaftErfassenForm(forms.Form):
    """Admins erfassen Patenschaften für ein Mitglied (z.B. telefonische Bestellung)."""
    member = MemberChoiceField(queryset=Member.objects.none(), label=_('Pat:in'))
    typ = forms.ModelChoiceField(queryset=PatenschaftTyp.objects.all(), label=_('Typ'))
    anzahl = forms.IntegerField(label=_('Anzahl'), min_value=1, initial=1)
    jahresbeitrag = forms.DecimalField(
        label=_('Jahresbeitrag'), required=False, min_value=0, max_digits=8, decimal_places=2,
        help_text=_('Pro Patenschaft. Leer: Jahresbeitrag des Typs.'))
    bestellt_am = forms.DateField(label=_('Bestellt am'), initial=datetime.date.today, widget=JuntagricoDateWidget)
    aktiviert_am = forms.DateField(
        label=_('Aktiviert am'), required=False, initial=datetime.date.today, widget=JuntagricoDateWidget,
        help_text=_('Leer: Patenschaft bleibt "bestellt", bis sie aktiviert wird.'))
    notizen = forms.CharField(label=_('Notizen'), required=False, widget=forms.Textarea(attrs={'rows': 3}))
    bestaetigung = forms.BooleanField(label=_('Bestätigung per E-Mail an die Pat:in senden'), required=False)

    def __init__(self, *args, abbrechen=None, **kwargs):
        super().__init__(*args, **kwargs)
        today = datetime.date.today()
        self.fields['member'].queryset = Member.objects.filter(
            Q(deactivation_date__isnull=True) | Q(deactivation_date__gt=today)).order_by('last_name', 'first_name')
        self.fields['anzahl'].max_value = PatenschaftConfig.max_anzahl()
        self.fields['anzahl'].validators.append(MaxValueValidator(PatenschaftConfig.max_anzahl()))
        self.helper = _helper(*self.fields, submit=_('Erfassen'), abbrechen=abbrechen,
                              extra=Submit('weitere', _('Erfassen und weitere erfassen'), css_class='btn-outline-success'))


class PatenschaftBearbeitenForm(forms.ModelForm):
    class Meta:
        model = Patenschaft
        fields = ['typ', 'jahresbeitrag', 'bestellt_am', 'aktiviert_am', 'gekuendigt_am', 'ende', 'notizen']
        widgets = {f: JuntagricoDateWidget for f in ['bestellt_am', 'aktiviert_am', 'gekuendigt_am', 'ende']}
        widgets['notizen'] = forms.Textarea(attrs={'rows': 3})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        extra = None
        if self.instance.kann_gekuendigt_werden:
            extra = Submit('kuendigen', _('Kündigen'), css_class='btn-danger',
                           onclick="return confirm('%s')" % _('Patenschaft kündigen?'))
        self.helper = _helper(*self.Meta.fields, extra=extra)
