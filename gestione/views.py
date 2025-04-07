# gestione/views.py

# 1. Import Standard Library
import calendar
from datetime import date, timedelta

# 2. Import Third-Party Libraries (Django)
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
# Importazioni Mixin corrette:
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger # Era in un'altra view, meglio qui
from django.db.models import Count # Era in un'altra view, meglio qui
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy # reverse_lazy aggiunto qui
from django.utils import timezone
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView
from django.db.models import Count # <-- Aggiungi/Verifica questo import
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger # <-- Aggiungi/Verifica questo import

# 3. Import Local Application (le tue app)
from .models import (
    Cliente, SpazioPubblicitario, Affissione, TaskInstallazione, FotoInstallazione
)
from .forms import (
    AffissioneBlockForm, FotoInstallazioneForm, SpazioPubblicitarioForm
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
class SpazioCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView): # Ora UserPassesTestMixin è importato
    model = SpazioPubblicitario
    form_class = SpazioPubblicitarioForm
    template_name = 'gestione/spaziopubblicitario_form.html'
    success_url = reverse_lazy('gestione:spazio_list') # Ora reverse_lazy è importato

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
    month_days = cal.monthdatescalendar(current_year, current_month)
    first_day_of_calendar = month_days[0][0]
    last_day_of_calendar = month_days[-1][-1]

    # Recupera le affissioni usando l'ordinamento predefinito del modello
    affissioni_nel_periodo = Affissione.objects.filter(
        spazio=spazio,
        data_inizio__lte=last_day_of_calendar,
        data_fine__gte=first_day_of_calendar
    ).select_related('cliente') # Mantenuto per ottimizzazione

    # Prepara i dati per il template del calendario
    calendar_data = {}
    for week in month_days:
        for day in week:
            calendar_data[day] = {'affissioni': [], 'is_confirmed': False}

    for affissione in affissioni_nel_periodo:
        current_day = max(affissione.data_inizio, first_day_of_calendar)
        end_day = min(affissione.data_fine, last_day_of_calendar)
        while current_day <= end_day:
             if current_day in calendar_data:
                 calendar_data[current_day]['affissioni'].append(affissione)
                 if affissione.stato == 'Confermato':
                     calendar_data[current_day]['is_confirmed'] = True
             current_day += timedelta(days=1)

    # Determina se l'utente è un venditore
    is_venditore = request.user.groups.filter(name='Venditori').exists()

    # Prepara contesto finale per il template
    context = {
        'spazio': spazio,
        'month_days': month_days,
        'current_date': date(current_year, current_month, 1),
        'current_month': current_month,
        'current_year': current_year,
        'calendar_data': calendar_data,
        'today': today,
        'prev_month_url': reverse('gestione:spazio_calendario', kwargs={'pk': pk, 'year': prev_month_year, 'month': prev_month_month}),
        'next_month_url': reverse('gestione:spazio_calendario', kwargs={'pk': pk, 'year': next_month_year, 'month': next_month_month}),
        'is_venditore': is_venditore,
    }
    return render(request, 'gestione/spazio_calendario.html', context)


@login_required
def blocco_affissione_view(request, spazio_pk, year, month, day):
    # Controlla se l'utente appartiene al gruppo 'Venditori'
    if not request.user.groups.filter(name='Venditori').exists():
         messages.error(request, "Non hai i permessi per bloccare uno slot.")
         return redirect(reverse('gestione:spazio_list'))

    # Recupera spazio e valida la data
    spazio = get_object_or_404(SpazioPubblicitario, pk=spazio_pk)
    try:
        start_date = date(year, month, day)
    except ValueError:
        messages.error(request, "Data non valida.")
        return redirect(reverse('gestione:spazio_calendario', kwargs={'pk': spazio.pk}))

    # Controlla se il giorno di inizio è già confermato
    if Affissione.objects.filter(spazio=spazio, stato='Confermato', data_inizio__lte=start_date, data_fine__gte=start_date).exists():
         messages.warning(request, f"Il giorno {start_date.strftime('%d/%m/%Y')} è già occupato da un'affissione confermata.")
         return redirect(reverse('gestione:spazio_calendario', kwargs={'pk': spazio.pk, 'year': year, 'month': month}))

    # Gestione richiesta POST (invio form) o GET (visualizzazione form)
    if request.method == 'POST':
        form = AffissioneBlockForm(request.POST, spazio=spazio)
        if form.is_valid():
            affissione = form.save(commit=False)
            affissione.spazio = spazio
            affissione.stato = 'Bloccato'
            affissione.utente_creazione = request.user
            affissione.save()
            messages.success(request, f"Slot dal {affissione.data_inizio.strftime('%d/%m/%Y')} al {affissione.data_fine.strftime('%d/%m/%Y')} bloccato con successo per {affissione.cliente}.")
            return redirect(reverse('gestione:spazio_calendario', kwargs={'pk': spazio.pk, 'year': year, 'month': month}))
        else:
             messages.error(request, "Errore nel form. Controlla i campi.")
             # Se invalido, ripresenta il form con gli errori (andrà al blocco GET sotto implicito)

    # Se GET o se il form POST era invalido
    form = AffissioneBlockForm(initial={'data_inizio': start_date}, spazio=spazio)

    context = {
        'form': form,
        'spazio': spazio,
        'start_date': start_date
    }
    return render(request, 'gestione/blocco_affissione_form.html', context)


@login_required
def task_list_installatore_view(request):
    # Verifica che l'utente appartenga al gruppo 'Installatori'
    if not request.user.groups.filter(name='Installatori').exists():
        messages.error(request, "Accesso riservato agli installatori.")
        return redirect(reverse('gestione:home'))

    # Filtra i task assegnati all'utente loggato
    tasks_assegnati = TaskInstallazione.objects.filter(
        installatore_assegnato=request.user,
        stato_task__in=['ASSEGNATO', 'PROBLEMA']
    ).select_related(
        'affissione__spazio',
        'affissione__cliente'
    ).order_by('data_prevista_installazione')

    context = {
        'tasks_list': tasks_assegnati,
    }
    return render(request, 'gestione/installatore_task_list.html', context)


@login_required
def task_detail_installatore_view(request, task_pk):
    # Recupera il task con dati correlati precaricati
    task = get_object_or_404(TaskInstallazione.objects.select_related(
        'affissione__spazio', 'affissione__cliente', 'installatore_assegnato'
    ), pk=task_pk)

    # Controllo Permessi
    is_assigned_installer = (request.user == task.installatore_assegnato)
    is_staff = request.user.is_staff
    if not (is_assigned_installer or is_staff):
        messages.error(request, "Non sei autorizzato a visualizzare o modificare questo task.")
        if request.user.groups.filter(name='Installatori').exists():
             return redirect(reverse('gestione:installatore_task_list'))
        else:
             return redirect(reverse('gestione:home'))

    upload_form = FotoInstallazioneForm() # Inizializza form upload

    if request.method == 'POST':
        # Gestione Upload Foto
        if 'upload_photo_submit' in request.POST:
            if not is_assigned_installer and not is_staff: # Check permesso specifico upload
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
                upload_form = form # Passa form con errori al template
                messages.error(request, "Errore nel caricamento della foto. Controlla i campi.")

        # Gestione Completamento Task
        elif 'complete_task_submit' in request.POST:
            if not is_assigned_installer and not is_staff: # Check permesso specifico completamento
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

    # Richiesta GET o POST upload fallito
    photos = task.foto.all()
    context = {
        'task': task,
        'photos': photos,
        'upload_form': upload_form,
        'can_complete': is_assigned_installer and task.stato_task != 'COMPLETATO',
        'can_upload': is_assigned_installer or is_staff
    }
    return render(request, 'gestione/installatore_task_detail.html', context)

# Nota: La vista admin_task_overview_view è stata rimossa perché avevi chiesto di implementare
# prima l'aggiunta spazi dall'interfaccia. Se la vuoi reinserire, assicurati di importare Count.
# from django.db.models import Count

@login_required
def admin_task_overview_view(request):
    # Controllo permessi: solo staff o membri del gruppo 'Amministratori'
    if not (request.user.is_staff or request.user.groups.filter(name='Amministratori').exists()):
        messages.error(request, "Accesso riservato agli amministratori.")
        return redirect(reverse('gestione:home'))

    # Recupera tutti i task, precaricando dati correlati e contando le foto associate
    task_list = TaskInstallazione.objects.select_related(
        'installatore_assegnato',
        'affissione__spazio',
        'affissione__cliente'
    ).annotate(
        num_foto=Count('foto') # Conta le foto per ogni task
    ).order_by('-data_prevista_installazione', 'stato_task') # Ordina

    # Implementa la paginazione
    paginator = Paginator(task_list, 25) # Mostra 25 task per pagina
    page_number = request.GET.get('page')
    try:
        tasks_page = paginator.page(page_number)
    except PageNotAnInteger:
        tasks_page = paginator.page(1) # Prima pagina se non è intero
    except EmptyPage:
        tasks_page = paginator.page(paginator.num_pages) # Ultima pagina se fuori range

    context = {
        'tasks_page': tasks_page, # Passa l'oggetto Page al template
    }
    return render(request, 'gestione/admin_task_overview.html', context)