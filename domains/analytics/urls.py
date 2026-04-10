from django.urls import path
from .api.views import SnapshotListView, SnapshotExportView

urlpatterns = [
    path('snapshots', SnapshotListView.as_view(), name='analytics-snapshots'),
    path('export', SnapshotExportView.as_view(), name='analytics-export'),
]
