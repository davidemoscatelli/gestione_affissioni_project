# gestione/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _ # Per traduzioni future
from django.core.exceptions import ValidationError 
from django.utils import timezone 
from django.conf import settings
import os

class Cliente(models.Model):
    """
    Modello per rappresentare un cliente [RF01].
    """
    nome_cognome = models.CharField(_("Nome/Cognome"), max_length=150, blank=True, null=True, help_text=_("Per persone fisiche"))
    ragione_sociale = models.CharField(_("Ragione Sociale"), max_length=200, blank=True, null=True, help_text=_("Per aziende"))
    telefono = models.CharField(_("Telefono"), max_length=30, blank=True, null=True)
    email = models.EmailField(_("Email"), max_length=254, blank=True, null=True)
    indirizzo = models.TextField(_("Indirizzo"), blank=True, null=True)
    note = models.TextField(_("Altre Informazioni Rilevanti"), blank=True, null=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Cliente")
        verbose_name_plural = _("Clienti")
        ordering = ['ragione_sociale', 'nome_cognome'] # Ordina per ragione sociale o nome

    def __str__(self):
        # Restituisce la ragione sociale se esiste, altrimenti nome/cognome
        return self.ragione_sociale or self.nome_cognome or f"Cliente ID: {self.pk}"

    def clean(self):
        # Assicura che almeno uno tra nome_cognome e ragione_sociale sia compilato
        if not self.nome_cognome and not self.ragione_sociale:
            from django.core.exceptions import ValidationError
            raise ValidationError(_('È necessario specificare almeno il Nome/Cognome o la Ragione Sociale.'))

class SpazioPubblicitario(models.Model):
    """
    Modello per rappresentare uno spazio pubblicitario [RF05].
    """
    TIPOLOGIA_CHOICES = [
        ('cartellone', _('Cartellone Stradale')),
        ('pensilina', _('Pensilina Autobus')),
        ('transenna', _('Transenna Parapedonale')),
        ('altro', _('Altro')),
    ]

    identificativo = models.CharField(_("Identificativo Univoco"), max_length=50, unique=True, help_text=_("Es. BS-001, MI-P05"))
    descrizione = models.CharField(_("Descrizione Breve"), max_length=200, blank=True, null=True)
    posizione_indirizzo = models.TextField(_("Posizione (Indirizzo)"), help_text=_("Indirizzo completo dello spazio"))
    posizione_lat = models.DecimalField(_("Latitudine"), max_digits=9, decimal_places=6, blank=True, null=True, help_text=_("Coordinate geografiche (opzionale)"))
    posizione_lon = models.DecimalField(_("Longitudine"), max_digits=9, decimal_places=6, blank=True, null=True, help_text=_("Coordinate geografiche (opzionale)"))
    dimensioni = models.CharField(_("Dimensioni"), max_length=50, blank=True, null=True, help_text=_("Es. 6x3m, 100x140cm"))
    tipologia = models.CharField(_("Tipologia"), max_length=50, choices=TIPOLOGIA_CHOICES, default='cartellone')
    note = models.TextField(_("Altre Caratteristiche Rilevanti"), blank=True, null=True)
    attivo = models.BooleanField(_("Attivo"), default=True, help_text=_("Indica se lo spazio è attualmente utilizzabile"))
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Spazio Pubblicitario")
        verbose_name_plural = _("Spazi Pubblicitari")
        ordering = ['identificativo']

    def __str__(self):
        return f"{self.identificativo} ({self.get_tipologia_display()})"
    

class Affissione(models.Model):
    """
    Modello per rappresentare una prenotazione/affissione di uno spazio [RF10].
    Collega uno SpazioPubblicitario a un Cliente per un periodo definito.
    """
    STATO_CHOICES = [
        ('Bloccato', _('Bloccato (Venditore)')), # [RF15] Slot bloccato in attesa di conferma
        ('Confermato', _('Confermato')),         # Affissione confermata, pronta per pianificazione installazione
        # Aggiungeremo altri stati in seguito (es. 'Installazione Pianificata', 'Installato', 'Scaduto')
    ]

    spazio = models.ForeignKey(
        SpazioPubblicitario,
        on_delete=models.PROTECT, # Impedisce cancellazione Spazio se ha affissioni collegate
        verbose_name=_("Spazio Pubblicitario"),
        related_name="affissioni" # Permette di accedere alle affissioni da un oggetto Spazio (spazio.affissioni.all())
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT, # Impedisce cancellazione Cliente se ha affissioni collegate
        verbose_name=_("Cliente"),
        related_name="affissioni" # Permette di accedere alle affissioni da un oggetto Cliente (cliente.affissioni.all())
    )
    data_inizio = models.DateField(_("Data Inizio Affissione"), default=timezone.now)
    data_fine = models.DateField(_("Data Fine Affissione"))
    stato = models.CharField(
        _("Stato Affissione"),
        max_length=30,
        choices=STATO_CHOICES,
        default='Confermato' # Default per creazioni da Admin, il 'Bloccato' sarà usato dai venditori
    )
    note = models.TextField(_("Note Interne"), blank=True, null=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Affissione/Prenotazione")
        verbose_name_plural = _("Affissioni/Prenotazioni")
        ordering = ['data_inizio', 'spazio']
        # Aggiungiamo un vincolo per evitare sovrapposizioni sullo stesso spazio?
        # unique_together = [['spazio', 'data_inizio']] # Troppo restrittivo, non gestisce la durata.
        # La validazione delle sovrapposizioni è più complessa, la gestiremo a livello di form/view.

    def __str__(self):
        return f"{self.spazio} | {self.cliente} ({self.data_inizio} - {self.data_fine})"

    def clean(self):
        # Validazione base: Data fine non può essere precedente alla data inizio [Logica intrinseca RF10]
        if self.data_fine and self.data_inizio and self.data_fine < self.data_inizio:
            raise ValidationError(_('La data di fine non può essere precedente alla data di inizio.'))

        # Validazione Sovrapposizioni (Semplificata - controllo base all'interno del clean del modello)
        # ATTENZIONE: Una validazione completa delle sovrapposizioni è complessa e spesso
        # è meglio gestirla nei Form o nelle View dove si ha più contesto.
        # Questa è una base di partenza.
        # Escludiamo l'oggetto corrente dalla verifica se è già salvato (in fase di modifica)
        qs = Affissione.objects.filter(
            spazio=self.spazio,
            data_fine__gte=self.data_inizio, # Finisce dopo (o lo stesso giorno) che la nuova inizia
            data_inizio__lte=self.data_fine  # Inizia prima (o lo stesso giorno) che la nuova finisce
        )
        if self.pk: # Se l'oggetto esiste già (modifica), escludilo dalla query
            qs = qs.exclude(pk=self.pk)

        # Consideriamo solo le affissioni confermate per le sovrapposizioni rigide
        # Potremmo voler permettere sovrapposizioni con stati 'Bloccato' (da decidere)
        if qs.filter(stato='Confermato').exists():
             raise ValidationError(
                 _('Esiste già un\'affissione confermata per lo spazio "%(spazio)s" che si sovrappone con le date selezionate (%(inizio)s - %(fine)s).') %
                 {'spazio': self.spazio, 'inizio': self.data_inizio, 'fine': self.data_fine}
             )

    @property
    def durata_giorni(self):
        if self.data_inizio and self.data_fine:
            return (self.data_fine - self.data_inizio).days + 1 # +1 per includere entrambi i giorni
        return 0   

class Affissione(models.Model):
    # ... (campi esistenti: spazio, cliente, data_inizio, data_fine, stato, note) ...
    STATO_CHOICES = [
        ('Bloccato', _('Bloccato (Venditore)')),
        ('Confermato', _('Confermato')),
        # Aggiungeremo altri stati...
    ]

    spazio = models.ForeignKey(
        SpazioPubblicitario,
        on_delete=models.PROTECT,
        verbose_name=_("Spazio Pubblicitario"),
        related_name="affissioni"
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        verbose_name=_("Cliente"),
        related_name="affissioni"
    )
    data_inizio = models.DateField(_("Data Inizio Affissione"), default=timezone.now)
    data_fine = models.DateField(_("Data Fine Affissione"))
    stato = models.CharField(
        _("Stato Affissione"),
        max_length=30,
        choices=STATO_CHOICES,
        default='Confermato'
    )
    note = models.TextField(_("Note Interne"), blank=True, null=True)

    # NUOVO CAMPO: Utente che ha creato/bloccato l'affissione
    utente_creazione = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Se l'utente viene cancellato, non cancellare l'affissione
        null=True,                 # Permetti che sia nullo (es. per vecchi record o creazioni da admin non tracciate)
        blank=True,                # Permetti che sia vuoto nei form
        verbose_name=_("Utente Creazione/Blocco"),
        related_name="affissioni_create" # Nome relazione inversa
    )

    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    # ... (Meta, __str__, clean, durata_giorni) ...
    class Meta:
        verbose_name = _("Affissione/Prenotazione")
        verbose_name_plural = _("Affissioni/Prenotazioni")
        ordering = ['data_inizio', 'spazio']

    def __str__(self):
         # ... (invariato) ...
         return f"{self.spazio} | {self.cliente} ({self.data_inizio} - {self.data_fine})"

    def clean(self):
         # ... (validazione date e sovrapposizioni - invariata per ora) ...
         super().clean() # Chiama il clean del genitore se necessario

    @property
    def durata_giorni(self):
         # ... (invariato) ...
         if self.data_inizio and self.data_fine:
             return (self.data_fine - self.data_inizio).days + 1
         return 0
class TaskInstallazione(models.Model):
    """
    Rappresenta un compito specifico di installazione/rimozione
    legato a un'Affissione confermata. [RF17]
    """
    STATO_TASK_CHOICES = [
        ('DA_ASSEGNARE', _('Da Assegnare')),
        ('ASSEGNATO', _('Assegnato')),
        # ('IN_CORSO', _('In Corso')), # Stato opzionale
        ('COMPLETATO', _('Completato')),
        ('PROBLEMA', _('Problema Segnalato')),
    ]

    # Usiamo OneToOneField perché (normalmente) c'è un solo task di installazione per affissione
    affissione = models.OneToOneField(
        Affissione,
        on_delete=models.CASCADE, # Se l'affissione viene cancellata, cancella anche il task
        verbose_name=_("Affissione Correlata"),
        related_name="task_installazione" # Nome per accesso inverso da Affissione
    )
    installatore_assegnato = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Se l'installatore viene cancellato, il task rimane (ma non assegnato)
        null=True,
        blank=True,
        verbose_name=_("Installatore Assegnato"),
        limit_choices_to={'groups__name': 'Installatori'}, # Limita la scelta agli utenti del gruppo 'Installatori'
        related_name="task_assegnati" # Nome per accesso inverso da User
    )
    stato_task = models.CharField(
        _("Stato Task"),
        max_length=20,
        choices=STATO_TASK_CHOICES,
        default='DA_ASSEGNARE'
    )
    data_prevista_installazione = models.DateField(
        _("Data Prevista Installazione"),
        help_text=_("Normalmente coincide con la data inizio dell'affissione")
    )
    # Potremmo aggiungere data_completamento, data_assegnazione etc. in futuro
    note_admin = models.TextField(
        _("Note per l'Installatore (da Admin)"),
        blank=True,
        null=True
    )
    # Aggiungeremo campi per le note e foto dell'installatore dopo
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Task Installazione")
        verbose_name_plural = _("Task Installazione")
        ordering = ['data_prevista_installazione', 'stato_task']

    def __str__(self):
        installatore = f" -> {self.installatore_assegnato}" if self.installatore_assegnato else " (Non Ass.)"
        return f"Task {self.pk}: {self.affissione.spazio} ({self.get_stato_task_display()}){installatore}"

    def save(self, *args, **kwargs):
        # Imposta automaticamente la data prevista se non fornita
        if not self.data_prevista_installazione and self.affissione:
            self.data_prevista_installazione = self.affissione.data_inizio
        super().save(*args, **kwargs) # Chiama il metodo save originale

class FotoInstallazione(models.Model):
    """
    Rappresenta una foto caricata come prova per un TaskInstallazione. [RF23]
    """
    task = models.ForeignKey(
        TaskInstallazione,
        on_delete=models.CASCADE, # Se il task viene cancellato, cancella le sue foto
        related_name='foto',      # Nome per accedere alle foto da un task (task.foto.all())
        verbose_name=_("Task Associato")
    )
    # Campo Immagine - richiede Pillow installato
    # upload_to specifica la sotto-cartella dentro MEDIA_ROOT dove salvare le foto
    # %Y/%m/%d creano cartelle per anno/mese/giorno automaticamente
    foto = models.ImageField(
        _("File Foto"),
        upload_to='installazioni/%Y/%m/%d/'
    )
    caricata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Mantieni la foto se l'utente viene cancellato
        null=True,
        verbose_name=_("Caricata Da")
    )
    data_caricamento = models.DateTimeField(
        _("Data Caricamento"),
        auto_now_add=True
    )
    descrizione = models.CharField(
        _("Descrizione (Opzionale)"),
        max_length=200,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _("Foto Installazione")
        verbose_name_plural = _("Foto Installazioni")
        ordering = ['-data_caricamento'] # Mostra le più recenti prima

    def __str__(self):
        # Restituisce il nome del file
        return f"Foto per Task {self.task.id} ({os.path.basename(self.foto.name)})"