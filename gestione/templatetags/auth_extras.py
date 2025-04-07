# gestione/templatetags/auth_extras.py
from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Verifica se un utente appartiene a un gruppo specifico.
    Uso: {{ user|has_group:"NomeGruppo" }}
    """
    # Se l'utente non è autenticato, non può avere gruppi
    if not user.is_authenticated:
        return False
    try:
        # Cerca il gruppo per nome
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        # Se il gruppo non esiste nel DB, l'utente non può appartenerci
        return False
    # Restituisce True se il gruppo trovato è tra i gruppi dell'utente, False altrimenti
    return group in user.groups.all()