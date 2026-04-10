from django.urls import path
from .api.views import TenantListCreateView, TenantDetailView

urlpatterns = [
    path("", TenantListCreateView.as_view(), name="tenant-list-create"),
    path("<str:tenant_id>/", TenantDetailView.as_view(), name="tenant-detail"),
]
