from rest_framework import mixins, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.permissions import IsAreaAdmin
from .models import ClassificationFeedback, ServiceKeyword
from .serializers import (
    ClassificationFeedbackSerializer,
    ClassifySerializer,
    ServiceKeywordSerializer,
)
from .services import classify
from .tasks import train_classifier


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def classify_view(request):
    serializer = ClassifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    suggestions = classify(serializer.validated_data['text'])
    return Response({'suggestions': suggestions})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def feedback_view(request):
    serializer = ClassificationFeedbackSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAreaAdmin])
def train_view(request):
    train_classifier.delay()
    return Response({'detail': 'Entrenamiento encolado.'})


@api_view(['GET'])
@permission_classes([IsAreaAdmin])
def stats_view(request):
    total = ClassificationFeedback.objects.count()
    accepted = ClassificationFeedback.objects.filter(accepted=True).count()
    pending = ClassificationFeedback.objects.filter(trained=False).count()
    return Response({
        'total_feedback': total,
        'accepted': accepted,
        'rejected': total - accepted,
        'acceptance_rate': round(accepted / total * 100, 1) if total else 0,
        'pending_training': pending,
    })


class ServiceKeywordViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ServiceKeywordSerializer
    permission_classes = [IsAreaAdmin]
    queryset = ServiceKeyword.objects.select_related('service').all()
