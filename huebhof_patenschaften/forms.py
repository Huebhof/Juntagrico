from django import forms
from django.utils.translation import gettext_lazy as _

from .config import PatenschaftConfig
from .models import PatenschaftTyp


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
