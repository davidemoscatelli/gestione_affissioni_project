# gestione/views.py

# 1. Import Standard Library
import calendar
from datetime import date, timedelta

# 2. Import Third-Party Libraries (Django)
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin # Import Corretto
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger # Importato una sola volta
from django.db.models import Count # Importato una sola volta
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy # Import Corretto
from django.utils import timezone
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView

# 3. Import Local Application (le tue app)
from .models import (
    Cliente, SpazioPubblicitario, Affissione, TaskInstallazione, FotoInstallazione
)
from .forms import (
    AffissioneBlockForm, FotoInstallazioneForm, SpazioPubblicitarioForm, AssignInstallerForm
)


# --- Class-Based Views ---

class HomePageView(LoginRequiredMixin, TemplateView):
    template_name = 'gestione/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['num_clienti'] = Cliente.objects.count()
        context['num_spazi'] = SpazioPubblicitario.objects.filter(attivo=True).count()
        return context

class SpazioListView(LoginRequiredMixin, ListView):
    model = SpazioPubblicitario
    template_name = 'gestione/spazio_list.html'
    context_object_name = 'spazi'
    paginate_by = 15

    def get_queryset(self):
        return SpazioPubblicitario.objects.filter(attivo=True).order_by('identificativo')

# Vista per CREARE Spazi (solo Admin/Staff)
class SpazioCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = SpazioPubblicitario
    form_class = SpazioPubblicitarioForm
    template_name = 'gestione/spaziopubblicitario_form.html'
    success_url = reverse_lazy('gestione:spazio_list')

    # Test permessi
    def test_func(self):
        return self.request.user.is_staff or \
               self.request.user.groups.filter(name='Amministratori').exists()

    # Contesto extra
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titolo_pagina'] = "Aggiungi Nuovo Spazio Pubblicitario"
        return context

    # Messaggio successo
    def form_valid(self, form):
        messages.success(self.request, f"Spazio '{form.instance.identificativo}' creato con successo.")
        return super().form_valid(form)

# --- Function-Based Views ---

@login_required
def spazio_calendario_view(request, pk, year=None, month=None):
    # Recupera lo spazio e gestisce le date (anno/mese)
    spazio = get_object_or_404(SpazioPubblicitario, pk=pk)
    today = timezone.now().date()

    if year is None or month is None:
        current_year = today.year
        current_month = today.month
    else:
        try:
            current_year = int(year)
            current_month = int(month)
            if not (1 <= current_month <= 12):
                raise ValueError("Mese non valido")
            date(current_year, current_month, 1) # Validazione data
        except (ValueError, TypeError):
            return redirect(reverse('gestione:spazio_calendario', kwargs={'pk': pk}))

    # Calcola date per navigazione mese precedente/successivo
    first_day_current_month_dt = date(current_year, current_month, 1)
    prev_month_dt = first_day_current_month_dt - timedelta(days=1)
    prev_month_year = prev_month_dt.year
    prev_month_month = prev_month_dt.month

    _, last_day_num = calendar.monthrange(current_year, current_month)
    last_day_current_month_dt = date(current_year, current_month, last_day_num)
    next_month_dt = last_day_current_month_dt + timedelta(days=1)
    next_month_year = next_month_dt.year
    next_month_month = next_month_dt.month

    # Logica per recuperare e processare le affissioni
    cal = calendar.Calendar(firstweekday=0)
    month_days_raw = cal.monthdatescalendar(current_year, current_month) # Rinominato per chiarezza
    first_day_of_calendar = month_days_raw[0][0]
    last_day_of_calendar = month_days_raw[-1][-1]

    affissioni_nel_periodo = Affissione.objects.filter(
        spazio=spazio,
        data_inizio__lte=last_day_of_calendar,
        data_fine__gte=first_day_of_calendar
    ).select_related('cliente')

    # Prepara i dati per il template del calendario
    calendar_data = {}
    for week in month_days_raw:
        for day in week:
            # --- MODIFICA QUI ---
            # Inizializza con entrambi i flag
            calendar_data[day] = {'affissioni': [], 'is_confirmed': False, 'is_blocked': False}

    for affissione in affissioni_nel_periodo:
        current_day = max(affissione.data_inizio, first_day_of_calendar)
        end_day = min(affissione.data_fine, last_day_of_calendar)
        while current_day <= end_day:
             if current_day in calendar_data:
                 calendar_data[current_day]['affissioni'].append(affissione)
                 if affissione.stato == 'Confermato':
                     calendar_data[current_day]['is_confirmed'] = True
                 # --- MODIFICA QUI ---
                 # Imposta anche il flag per lo stato bloccato
                 if affissione.stato == 'Bloccato':
                       calendar_data[current_day]['is_blocked'] = True
             current_day += timedelta(days=1)

    # --- NUOVA LOGICA: Pre-processa i dati per il template ---
    processed_month_days = []
    for week in month_days_raw:
        processed_week = []
        for day_date in week:
            day_info_dict = calendar_data.get(day_date, {'affissioni': [], 'is_confirmed': False, 'is_blocked': False})
            processed_week.append({
                'date': day_date,
                'data': day_info_dict
            })
        processed_month_days.append(processed_week)
    # --- FINE NUOVA LOGICA ---

    # --- MODIFICA QUI ---
    # Determina se l'utente può usare il blocco generico (Venditore o Admin/Staff)
    can_block_generico = request.user.groups.filter(name='Venditori').exists() or \
                         request.user.is_staff or \
                         request.user.groups.filter(name='Amministratori').exists()
    # --- FINE MODIFICA ---

    # Prepara contesto finale per il template
    context = {
        'spazio': spazio,
        'processed_month_days': processed_month_days, # Passa la nuova struttura dati
        'current_date': date(current_year, current_month, 1),
        'today': today,
        'prev_month_url': reverse('gestione:spazio_calendario', kwargs={'pk': pk, 'year': prev_month_year, 'month': prev_month_month}),
        'next_month_url': reverse('gestione:spazio_calendario', kwargs={'pk': pk, 'year': next_month_year, 'month': next_month_month}),
        'can_block_generico': can_block_generico, # Passa il nuovo flag per il pulsante
    }
    return render(request, 'gestione/spazio_calendario.html', context)

# --- NUOVA VISTA PER BLOCCO SLOT GENERICO (Sostituisce la vecchia blocco_affissione_view) ---
@login_required
def blocco_slot_generico_view(request, spazio_pk):
    # Controllo permessi: Solo Venditori o Admin/Staff
    can_block = request.user.groups.filter(name='Venditori').exists() or \
                request.user.is_staff or \
                request.user.groups.filter(name='Amministratori').exists()
    if not can_block:
        messages.error(request, "Non hai i permessi per bloccare uno slot.")
        if request.user.groups.filter(name='Installatori').exists():
            return redirect(reverse('gestione:installatore_task_list'))
        return redirect(reverse('gestione:home'))

    spazio = get_object_or_404(SpazioPubblicitario, pk=spazio_pk)

    if request.method == 'POST':
        form = AffissioneBlockForm(request.POST, spazio=spazio)
        if form.is_valid():
            affissione = form.save(commit=False)
            affissione.spazio = spazio
            affissione.stato = 'Bloccato'
            affissione.utente_creazione = request.user
            affissione.save()
            messages.success(request, f"Slot dal {affissione.data_inizio.strftime('%d/%m/%Y')} al {affissione.data_fine.strftime('%d/%m/%Y')} bloccato con successo per {affissione.cliente}.")
            # Reindirizza al calendario del mese/anno di inizio del blocco
            return redirect(reverse('gestione:spazio_calendario', kwargs={
                'pk': spazio.pk,
                'year': affissione.data_inizio.year,
                'month': affissione.data_inizio.month
            }))
        else:
             messages.error(request, "Errore nel form. Controlla i campi.")
    else: # GET Request
        form = AffissioneBlockForm(spazio=spazio) # Form vuoto

    context = {
        'form': form,
        'spazio': spazio,
        'titolo_pagina': f"Blocca Slot per Spazio {spazio.identificativo}"
    }
    # Usa il template dedicato per il form di blocco
    return render(request, 'gestione/blocco_slot_form.html', context)


@login_required
def task_list_installatore_view(request):
    # (Codice task_list_installatore_view - INVARIATO)
    if not request.user.groups.filter(name='Installatori').exists():
        messages.error(request, "Accesso riservato agli installatori.")
        return redirect(reverse('gestione:home'))
    tasks_assegnati = TaskInstallazione.objects.filter(
        installatore_assegnato=request.user,
        stato_task__in=['ASSEGNATO', 'PROBLEMA']
    ).select_related(
        'affissione__spazio', 'affissione__cliente'
    ).order_by('data_prevista_installazione')
    context = {
        'tasks_list': tasks_assegnati,
    }
    return render(request, 'gestione/installatore_task_list.html', context)


@login_required
def task_detail_installatore_view(request, task_pk):
    # (Codice task_detail_installatore_view - INVARIATO)
    task = get_object_or_404(TaskInstallazione.objects.select_related(
        'affissione__spazio', 'affissione__cliente', 'installatore_assegnato'
    ), pk=task_pk)
    is_assigned_installer = (request.user == task.installatore_assegnato)
    is_staff = request.user.is_staff
    if not (is_assigned_installer or is_staff):
        messages.error(request, "Non sei autorizzato a visualizzare o modificare questo task.")
        if request.user.groups.filter(name='Installatori').exists():
             return redirect(reverse('gestione:installatore_task_list'))
        else:
             return redirect(reverse('gestione:home'))
    upload_form = FotoInstallazioneForm()
    if request.method == 'POST':
        if 'upload_photo_submit' in request.POST:
            if not is_assigned_installer and not is_staff:
                 messages.error(request, "Solo l'installatore assegnato può caricare foto.")
                 return redirect(reverse('gestione:installatore_task_detail', kwargs={'task_pk': task.pk}))
            form = FotoInstallazioneForm(request.POST, request.FILES)
            if form.is_valid():
                foto_obj = form.save(commit=False)
                foto_obj.task = task
                foto_obj.caricata_da = request.user
                foto_obj.save()
                messages.success(request, "Foto caricata con successo.")
                return redirect(reverse('gestione:installatore_task_detail', kwargs={'task_pk': task.pk}))
            else:
                upload_form = form
                messages.error(request, "Errore nel caricamento della foto. Controlla i campi.")
        elif 'complete_task_submit' in request.POST:
            if not is_assigned_installer and not is_staff:
                messages.error(request, "Solo l'installatore assegnato può completare il task.")
                return redirect(reverse('gestione:installatore_task_detail', kwargs={'task_pk': task.pk}))
            if task.stato_task != 'COMPLETATO':
                task.stato_task = 'COMPLETATO'
                task.save()
                messages.success(request, f"Task per {task.affissione.spazio} segnato come completato.")
                return redirect(reverse('gestione:installatore_task_list'))
            else:
                messages.info(request, "Questo task era già segnato come completato.")
                return redirect(reverse('gestione:installatore_task_detail', kwargs={'task_pk': task.pk}))
        else:
             return redirect(reverse('gestione:installatore_task_detail', kwargs={'task_pk': task.pk}))
    photos = task.foto.all()
    context = {
        'task': task,
        'photos': photos,
        'upload_form': upload_form,
        'can_complete': is_assigned_installer and task.stato_task != 'COMPLETATO',
        'can_upload': is_assigned_installer or is_staff
    }
    return render(request, 'gestione/installatore_task_detail.html', context)


@login_required
def admin_task_overview_view(request):
    # (Codice admin_task_overview_view - INVARIATO)
    if not (request.user.is_staff or request.user.groups.filter(name='Amministratori').exists()):
        messages.error(request, "Accesso riservato agli amministratori.")
        return redirect(reverse('gestione:home'))
    task_list = TaskInstallazione.objects.select_related(
        'installatore_assegnato',
        'affissione__spazio',
        'affissione__cliente'
    ).annotate(
        num_foto=Count('foto')
    ).order_by('-data_prevista_installazione', 'stato_task')
    paginator = Paginator(task_list, 25)
    page_number = request.GET.get('page')
    try:
        tasks_page = paginator.page(page_number)
    except PageNotAnInteger:
        tasks_page = paginator.page(1)
    except EmptyPage:
        tasks_page = paginator.page(paginator.num_pages)
    context = {
        'tasks_page': tasks_page,
    }
    return render(request, 'gestione/admin_task_overview.html', context)

@login_required
def assign_installer_view(request, task_pk):
    # Controllo permessi: solo staff o Amministratori possono assegnare
    if not (request.user.is_staff or request.user.groups.filter(name='Amministratori').exists()):
        messages.error(request, "Non hai i permessi per assegnare questo task.")
        return redirect(reverse('gestione:home')) # O admin_task_overview? Meglio home.

    task = get_object_or_404(TaskInstallazione, pk=task_pk)

    # Non permettere riassegnazione se già completato? (Opzionale)
    # if task.stato_task == 'COMPLETATO':
    #    messages.warning(request, "Questo task è già completato e non può essere riassegnato.")
    #    return redirect(reverse('gestione:admin_task_overview'))

    if request.method == 'POST':
        form = AssignInstallerForm(request.POST)
        if form.is_valid():
            selected_installer = form.cleaned_data['installatore']
            task.installatore_assegnato = selected_installer
            # Cambia stato a 'Assegnato' se era 'Da Assegnare'
            if task.stato_task == 'DA_ASSEGNARE':
                task.stato_task = 'ASSEGNATO'
            task.save()
            messages.success(
                request,
                f"Installatore '{selected_installer.username}' assegnato con successo al Task #{task.pk}."
            )
            return redirect(reverse('gestione:admin_task_overview')) # Torna alla lista task admin
        else:
            # Se form non valido, mostra di nuovo la pagina con errori
            messages.error(request, "Errore nel form. Seleziona un installatore valido.")
            # Ricadi nel rendering GET sotto
    else: # GET Request
         # Pre-popola il form se un installatore è già assegnato (per modifica)
        initial_data = {}
        if task.installatore_assegnato:
            initial_data['installatore'] = task.installatore_assegnato
        form = AssignInstallerForm(initial=initial_data)


    context = {
        'form': form,
        'task': task,
        'titolo_pagina': f"Assegna Installatore per Task #{task.pk}"
    }
    # Creeremo un template dedicato per questo form
    return render(request, 'gestione/assign_installer_form.html', context)
