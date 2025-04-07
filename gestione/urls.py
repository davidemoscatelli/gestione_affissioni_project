# gestione/urls.py
from django.urls import path, re_path
from . import views

app_name = 'gestione' # Namespace per le URL di questa app

urlpatterns = [
    path('', views.HomePageView.as_view(), name='home'),
    path('spazi/', views.SpazioListView.as_view(), name='spazio_list'),
    path('spazi/nuovo/', views.SpazioCreateView.as_view(), name='spazio_create'),
    path('spazi/<int:pk>/calendario/', views.spazio_calendario_view, name='spazio_calendario'),
     re_path(
        r'^spazi/(?P<pk>\d+)/calendario/(?:(?P<year>\d{4})/(?P<month>\d{1,2})/)?$',
        views.spazio_calendario_view,
        name='spazio_calendario'
    ),

    path('spazi/<int:spazio_pk>/blocca/', views.blocco_slot_generico_view, name='blocca_slot_generico'),
    path('installatore/tasks/', views.task_list_installatore_view, name='installatore_task_list'),
    path('installatore/task/<int:task_pk>/', views.task_detail_installatore_view, name='installatore_task_detail'),
    path('pannello/tasks/', views.admin_task_overview_view, name='admin_task_overview'),
]