from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.catalog.permissions import IsAreaAdmin, IsSuperAdmin
from .models import SLAConfig, ServiceQueue, TechnicianProfile
from .serializers import SLAConfigSerializer, ServiceQueueSerializer, TechnicianProfileSerializer


class TechnicianProfileViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TechnicianProfileSerializer
    permission_classes = [IsAreaAdmin]
    queryset = TechnicianProfile.objects.select_related('department').all()


class SLAConfigViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SLAConfigSerializer
    permission_classes = [IsAreaAdmin]
    queryset = SLAConfig.objects.select_related('department').all()


class ServiceQueueViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ServiceQueueSerializer
    permission_classes = [IsAreaAdmin]
    queryset = (
        ServiceQueue.objects
        .select_related('help_desk__service__category__department')
        .order_by('-urgency_score', 'queued_at')
    )
