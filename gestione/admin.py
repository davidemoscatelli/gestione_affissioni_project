# gestione/admin.py
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
# Importa tutti i modelli necessari
from .models import Cliente, SpazioPubblicitario, Affissione, TaskInstallazione

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    # (Codice ClienteAdmin - INVARIATO)
    list_display = ('get_identificativo_cliente', 'telefono', 'email', 'data_creazione')
    search_fields = ('nome_cognome', 'ragione_sociale', 'email', 'telefono')
    list_filter = ('data_creazione',)
    ordering = ('ragione_sociale', 'nome_cognome')
    fieldsets = (
        (None, {
            'fields': (('nome_cognome', 'ragione_sociale'), ('telefono', 'email'), 'indirizzo')
        }),
        ('Informazioni Aggiuntive', {
            'fields': ('note',),
            'classes': ('collapse',)
        }),
        ('Date', {
            'fields': ('data_creazione', 'data_modifica'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('data_creazione', 'data_modifica')

    def get_identificativo_cliente(self, obj):
        return obj.ragione_sociale or obj.nome_cognome
    get_identificativo_cliente.short_description = 'Cliente'

@admin.register(SpazioPubblicitario)
class SpazioPubblicitarioAdmin(admin.ModelAdmin):
    # (Codice SpazioPubblicitarioAdmin - INVARIATO)
    list_display = ('identificativo', 'posizione_indirizzo', 'tipologia', 'dimensioni', 'attivo')
    search_fields = ('identificativo', 'posizione_indirizzo', 'descrizione')
    list_filter = ('tipologia', 'attivo')
    ordering = ('identificativo',)
    fieldsets = (
         (None, {
            'fields': ('identificativo', 'descrizione', 'tipologia', 'dimensioni', 'attivo')
        }),
        ('Posizione', {
            'fields': ('posizione_indirizzo', ('posizione_lat', 'posizione_lon')),
        }),
         ('Note', {
            'fields': ('note',),
             'classes': ('collapse',)
        }),
        ('Date', {
            'fields': ('data_creazione', 'data_modifica'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('data_creazione', 'data_modifica')


@admin.register(Affissione) # Registra Affissione UNA SOLA VOLTA
class AffissioneAdmin(admin.ModelAdmin): # Definisci la classe UNA SOLA VOLTA
    # --- Configurazioni della lista e del form ---
    list_display = ('spazio', 'cliente', 'data_inizio', 'data_fine', 'stato', 'durata_giorni', 'utente_creazione')
    list_filter = ('stato', 'spazio', 'cliente', 'data_inizio', 'data_fine')
    search_fields = (
        'spazio__identificativo',
        'spazio__posizione_indirizzo',
        'cliente__ragione_sociale',
        'cliente__nome_cognome',
        'note',
        'utente_creazione__username'
    )
    date_hierarchy = 'data_inizio'
    ordering = ('-data_inizio', 'spazio')
    raw_id_fields = ['spazio', 'cliente', 'utente_creazione']
    readonly_fields = ('data_creazione', 'data_modifica')
    list_select_related = ('spazio', 'cliente', 'utente_creazione')

    fieldsets = (
        (None, {
            'fields': (('spazio', 'cliente'), ('data_inizio', 'data_fine'), 'stato', 'utente_creazione')
        }),
        ('Dettagli', {
            'fields': ('note',),
            'classes': ('collapse',)
        }),
         ('Date Sistema', {
            'fields': ('data_creazione', 'data_modifica'),
            'classes': ('collapse',)
        }),
    )

    # --- Azione 1: Conferma Selezionati ---
    @admin.action(description=_('Conferma Affissioni e Crea Task (da Bloccato a Confermato)')) # Descrizione aggiornata
    def conferma_selezionati(self, request, queryset):
        # Filtra solo quelle che sono effettivamente bloccate
        # Manteniamo il queryset originale bloccate per iterare dopo l'update
        bloccate = queryset.filter(stato='Bloccato')
        bloccate_ids = list(bloccate.values_list('id', flat=True)) # Memorizza gli ID

        if not bloccate_ids:
             self.message_user(request, _('Nessuna affissione selezionata era nello stato "Bloccato".'), messages.WARNING)
             return # Esce se non c'è nulla da confermare

        # Esegui l'update di stato
        updated_count = Affissione.objects.filter(id__in=bloccate_ids).update(stato='Confermato')

        # Messaggio per la conferma dello stato
        if updated_count > 0:
            self.message_user(
                request,
                _('%(count)d affissioni sono state confermate con successo.') % {'count': updated_count},
                messages.SUCCESS
            )

        # --- NUOVA LOGICA: Crea i Task per le affissioni appena confermate ---
        tasks_creati_count = 0
        affissioni_confermate = Affissione.objects.filter(id__in=bloccate_ids) # Recupera gli oggetti aggiornati

        for affissione in affissioni_confermate:
            # Usa get_or_create per evitare errori se il task esistesse già per qualche motivo
            # e per creare solo se non esiste. Imposta i default solo alla creazione.
            task, created = TaskInstallazione.objects.get_or_create(
                affissione=affissione,
                defaults={
                    'stato_task': 'DA_ASSEGNARE',
                    # data_prevista_installazione viene impostata automaticamente dal save() del modello TaskInstallazione
                }
            )
            if created:
                tasks_creati_count += 1
        # --- FINE NUOVA LOGICA ---

        # Messaggio per la creazione dei task
        if tasks_creati_count > 0:
             self.message_user(
                request,
                _('%(count)d nuovi Task di Installazione sono stati creati.') % {'count': tasks_creati_count},
                messages.INFO # Usiamo INFO per distinguerlo dal messaggio di conferma stato
            )

        # Messaggio (invariato) se alcune selezionate non erano 'Bloccato'
        not_processed_count = queryset.exclude(id__in=bloccate_ids).count()
        if not_processed_count > 0:
             self.message_user(
                request,
                _('%(count)d affissioni selezionate non erano nello stato "Bloccato" e sono state ignorate.') % {'count': not_processed_count},
                messages.WARNING
            )

    # --- Registra SOLO l'azione di conferma (che ora crea anche i task) ---
    actions = ['conferma_selezionati'] # Rimuovi 'crea_task_installazione' da qui



@admin.register(TaskInstallazione)
class TaskInstallazioneAdmin(admin.ModelAdmin):
    # (Codice TaskInstallazioneAdmin - INVARIATO e CORRETTO)
    list_display = ('id', 'affissione', 'data_prevista_installazione', 'stato_task', 'installatore_assegnato')
    list_filter = ('stato_task', 'data_prevista_installazione', 'installatore_assegnato')
    search_fields = (
        'id',
        'affissione__spazio__identificativo',
        'affissione__cliente__ragione_sociale',
        'affissione__cliente__nome_cognome',
        'installatore_assegnato__username',
        'note_admin'
    )
    list_select_related = ('affissione__spazio', 'affissione__cliente', 'installatore_assegnato')
    raw_id_fields = ('affissione', 'installatore_assegnato')
    date_hierarchy = 'data_prevista_installazione'
    ordering = ('-data_prevista_installazione',)

    fieldsets = (
        (None, {'fields': ('affissione', 'stato_task', 'installatore_assegnato')}),
        ('Dettagli', {'fields': ('data_prevista_installazione', 'note_admin')}),
        ('Sistema', {'fields': ('data_creazione', 'data_modifica'), 'classes': ('collapse',)}),
    )
    readonly_fields = ('data_creazione', 'data_modifica')
    list_editable = ('stato_task', 'installatore_assegnato')