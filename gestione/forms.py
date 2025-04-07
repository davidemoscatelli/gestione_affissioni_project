# gestione/forms.py
from django import forms
from .models import Affissione, Cliente, SpazioPubblicitario, FotoInstallazione
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class AffissioneBlockForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.order_by('ragione_sociale', 'nome_cognome'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    data_inizio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    data_fine = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    note = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = Affissione
        fields = ['cliente', 'data_inizio', 'data_fine', 'note']

    def __init__(self, *args, **kwargs):
        self.spazio = kwargs.pop('spazio', None)
        if not self.spazio:
             raise ValueError("È necessario fornire uno Spazio Pubblicitario al form.")
        super().__init__(*args, **kwargs)

    def clean_data_fine(self):
        data_inizio = self.cleaned_data.get('data_inizio')
        data_fine = self.cleaned_data.get('data_fine')
        if data_inizio and data_fine and data_fine < data_inizio:
            raise ValidationError(_('La data di fine non può essere precedente alla data di inizio.'))
        return data_fine

    def clean(self):
        cleaned_data = super().clean()
        data_inizio = cleaned_data.get('data_inizio')
        data_fine = cleaned_data.get('data_fine')

        if data_inizio and data_fine and self.spazio:
            affissioni_confermate_sovrapposte = Affissione.objects.filter(
                spazio=self.spazio,
                stato='Confermato',
                data_inizio__lte=data_fine,
                data_fine__gte=data_inizio
            )
            if self.instance and self.instance.pk:
                 affissioni_confermate_sovrapposte = affissioni_confermate_sovrapposte.exclude(pk=self.instance.pk)

            if affissioni_confermate_sovrapposte.exists():
                raise ValidationError(
                    _('Impossibile bloccare questo periodo: esiste già un\'affissione confermata per lo spazio "%(spazio)s" che si sovrappone.') %
                    {'spazio': self.spazio}
                )
        return cleaned_data
    

class FotoInstallazioneForm(forms.ModelForm):
    """
    Form per permettere all'installatore di caricare una foto
    associata a un TaskInstallazione.
    """
    # Sovrascriviamo i campi per aggiungere widget e classi CSS se necessario
    foto = forms.ImageField(
        # ClearableFileInput è il widget di default, permette di cancellare
        # il file selezionato prima dell'invio.
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        label=_("Seleziona Foto"),
        help_text=_("Carica la foto come prova dell'avvenuta installazione."),
        required=True # Una foto è obbligatoria per l'upload
    )
    descrizione = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False, # La descrizione è opzionale
        label=_("Descrizione (Opzionale)"),
        help_text=_("Breve descrizione della foto (es. 'Lato sinistro', 'Dettaglio').")
    )

    class Meta:
        model = FotoInstallazione
        # Includiamo solo i campi che l'utente deve compilare nel form
        # I campi 'task' e 'caricata_da' verranno impostati nella view
        fields = ['foto', 'descrizione']

class SpazioPubblicitarioForm(forms.ModelForm):
    class Meta:
        model = SpazioPubblicitario
        # Includi tutti i campi che l'admin deve poter inserire/modificare
        # Escludiamo i campi auto-generati come data_creazione/modifica
        fields = [
            'identificativo', 'descrizione', 'posizione_indirizzo',
            'posizione_lat', 'posizione_lon', 'dimensioni',
            'tipologia', 'note', 'attivo'
        ]
        widgets = {
            # Applica classi Bootstrap per coerenza
            'identificativo': forms.TextInput(attrs={'class': 'form-control'}),
            'descrizione': forms.TextInput(attrs={'class': 'form-control'}),
            'posizione_indirizzo': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'posizione_lat': forms.NumberInput(attrs={'step': '0.000001', 'class': 'form-control'}),
            'posizione_lon': forms.NumberInput(attrs={'step': '0.000001', 'class': 'form-control'}),
            'dimensioni': forms.TextInput(attrs={'class': 'form-control'}),
            'tipologia': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'attivo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'identificativo': _("Es. BS-001, MI-P05. Deve essere unico."),
            'posizione_lat': _("Formato decimale, es. 45.123456"),
            'posizione_lon': _("Formato decimale, es. 9.123456"),
            'attivo': _("Spunta se lo spazio è disponibile per affissioni."),
        }
