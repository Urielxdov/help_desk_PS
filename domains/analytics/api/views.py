import csv
import json
from django.http import HttpResponse
from rest_framework.views import APIView

from shared.permissions import IsHDManager
from shared.responses import success_response
from shared.pagination import StandardPagination
from .serializers import SnapshotResponseSerializer


class SnapshotListView(APIView):
    permission_classes = [IsHDManager]

    def get(self, request):
        from domains.analytics.models import HelpDeskSnapshot

        qs = HelpDeskSnapshot.objects.all()

        # Filtros opcionales
        if event_type := request.query_params.get('event_type'):
            qs = qs.filter(event_type=event_type)
        if ticket_id := request.query_params.get('ticket_id'):
            qs = qs.filter(ticket_id=ticket_id)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)

        data = []
        for snap in (page if page is not None else qs):
            data.append({
                'id': str(snap.id),
                'ticket_id': str(snap.ticket_id),
                'event_type': snap.event_type,
                'status': snap.status,
                'priority': snap.priority,
                'category': snap.category,
                'assigned_to': str(snap.assigned_to) if snap.assigned_to else None,
                'was_escalated': snap.was_escalated,
                'suggested_category': snap.suggested_category,
                'suggested_priority': snap.suggested_priority,
                'accepted_category': snap.accepted_category,
                'accepted_priority': snap.accepted_priority,
                'suggestion_accepted': snap.suggestion_accepted,
                'classifier_confidence': snap.classifier_confidence,
                'snapshot_data': snap.snapshot_data,
                'created_at': snap.created_at,
            })

        if page is not None:
            return paginator.get_paginated_response(data)
        return success_response(data)


class SnapshotExportView(APIView):
    permission_classes = [IsHDManager]

    def get(self, request):
        from domains.analytics.models import HelpDeskSnapshot

        fmt = request.query_params.get('format', 'json')
        qs = HelpDeskSnapshot.objects.all().values(
            'ticket_id', 'event_type', 'status', 'priority', 'category',
            'was_escalated', 'suggested_category', 'suggested_priority',
            'accepted_category', 'accepted_priority', 'suggestion_accepted',
            'classifier_confidence', 'created_at',
        )

        if fmt == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="snapshots.csv"'
            fields = list(qs.first().keys()) if qs.exists() else []
            writer = csv.DictWriter(response, fieldnames=fields)
            writer.writeheader()
            for row in qs:
                writer.writerow({k: str(v) if v is not None else '' for k, v in row.items()})
            return response

        # JSON por defecto
        return success_response(list(qs))
