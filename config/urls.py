from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


# wrappers com import lazy para evitar problemas de carregamento no startup do django
def schema_view(request, *args, **kwargs):
    from drf_spectacular.views import SpectacularAPIView
    return SpectacularAPIView.as_view()(request, *args, **kwargs)


def swagger_view(request, *args, **kwargs):
    from drf_spectacular.views import SpectacularSwaggerView
    return SpectacularSwaggerView.as_view(url_name='schema')(request, *args, **kwargs)


def redoc_view(request, *args, **kwargs):
    from drf_spectacular.views import SpectacularRedocView
    return SpectacularRedocView.as_view(url_name='schema')(request, *args, **kwargs)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')), 
    path('api/schema/', schema_view, name='schema'),
    path('swagger/', swagger_view, name='schema-swagger-ui'),
    path('redoc/', redoc_view, name='schema-redoc'),
]

# serve arquivos de mídia localmente apenas em modo debug
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
