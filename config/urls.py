from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Tratamento de erros customizados (Retornam JSON em vez de HTML nativo)
handler404 = 'core.views.custom_404'
handler500 = 'core.views.custom_500'
handler403 = 'core.views.custom_403'
handler400 = 'core.views.custom_400'

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Adicionamos o 'api/' para deixar claro que são rotas de dados (JSON)
    # Ex: http://localhost:8000/api/home/
    path('api/', include('core.urls')), 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)