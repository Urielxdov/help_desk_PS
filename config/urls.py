from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('domains.users.urls')),
    path('api/v1/help-desk/', include('domains.help_desk.urls')),
    path('api/v1/analytics/', include('domains.analytics.urls')),
]
