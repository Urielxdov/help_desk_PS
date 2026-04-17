from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('api/', include('apps.catalog.urls')),
    path('api/', include('apps.helpdesks.urls')),
    path('api/', include('apps.sla.urls')),
    path('api/auth/', include('authentication_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
