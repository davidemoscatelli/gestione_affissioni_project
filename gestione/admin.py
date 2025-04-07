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
    @admin.action(description=_('Conferma le affissioni selezionate (da Bloccato a Confermato)'))
    def conferma_selezionati(self, request, queryset):
        bloccate = queryset.filter(stato='Bloccato')
        updated_count = bloccate.update(stato='Confermato')
        self.message_user(
            request,
            _('%(count)d affissioni sono state confermate con successo.') % {'count': updated_count},
            messages.SUCCESS
        )
        not_updated_count = queryset.exclude(stato='Bloccato').count()
        if not_updated_count > 0:
             self.message_user(
                request,
                _('%(count)d affissioni selezionate non erano nello stato "Bloccato" e non sono state modificate.') % {'count': not_updated_count},
                messages.WARNING
            )

    # --- Azione 2: Crea Task Installazione ---
    @admin.action(description=_('Crea Task di Installazione per le affissioni selezionate (se Confermate)'))
    def crea_task_installazione(self, request, queryset):
        confermate_senza_task = queryset.filter(
            stato='Confermato',
            task_installazione__isnull=True
        )
        tasks_creati_count = 0
        affissioni_gia_task_count = queryset.filter(
            stato='Confermato',
            task_installazione__isnull=False
        ).count()
        affissioni_non_confermate_count = queryset.exclude(stato='Confermato').count()

        for affissione in confermate_senza_task:
            TaskInstallazione.objects.create(
                affissione=affissione,
                stato_task='DA_ASSEGNARE'
            )
            tasks_creati_count += 1

        if tasks_creati_count > 0:
            self.message_user(request, _('%(count)d Task di Installazione creati con successo.') % {'count': tasks_creati_count}, messages.SUCCESS)
        if affissioni_gia_task_count > 0:
             self.message_user(request, _('%(count)d affissioni selezionate avevano già un task e sono state ignorate.') % {'count': affissioni_gia_task_count}, messages.WARNING)
        if affissioni_non_confermate_count > 0:
             self.message_user(request, _('%(count)d affissioni selezionate non erano "Confermate" e sono state ignorate.') % {'count': affissioni_non_confermate_count}, messages.WARNING)
        if tasks_creati_count == 0 and affissioni_gia_task_count == 0 and affissioni_non_confermate_count == 0:
             self.message_user(request, _('Nessuna affissione valida selezionata per creare nuovi task.'), messages.INFO)

    # --- Registra ENTRAMBE le azioni ---
    actions = ['conferma_selezionati', 'crea_task_installazione']


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