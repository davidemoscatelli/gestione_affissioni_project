
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings # Importa settings
from django.conf.urls.static import static # Importa static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('gestione.urls', namespace='gestione')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('gestione.urls', namespace='gestione')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)