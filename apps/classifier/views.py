from django.conf import settings
from django.db.models import F
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.permissions import IsAreaAdmin
from .models import ClassificationFeedback, ServiceKeyword, UserFeedbackProfile
from .serializers import (
    ClassificationFeedbackSerializer,
    ClassifySerializer,
    ServiceKeywordSerializer,
    UserFeedbackProfileSerializer,
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
    user_id = getattr(request.user, 'user_id', None)
    user_role = getattr(request.user, 'role', None)

    profile = None
    if user_id is not None:
        profile = UserFeedbackProfile.objects.filter(user_id=user_id).first()
        if profile and profile.flagged:
            return Response(
                {'detail': 'Tu cuenta no puede enviar feedback en este momento.'},
                status=status.HTTP_403_FORBIDDEN,
            )

    # Rate limit: max N feedbacks por usuario por día calendario
    is_limited = False
    if user_id is not None:
        limit = getattr(settings, 'CLASSIFIER_DAILY_FEEDBACK_LIMIT', 20)
        today_count = ClassificationFeedback.objects.filter(
            user_id=user_id,
            created_at__date=timezone.localdate(),
        ).count()
        is_limited = today_count >= limit

    serializer = ClassificationFeedbackSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(user_id=user_id, user_role=user_role, rate_limited=is_limited)

    # Actualizar contadores del perfil (get_or_create + F() para evitar race conditions)
    if user_id is not None:
        if profile is None:
            profile, _ = UserFeedbackProfile.objects.get_or_create(user_id=user_id)
        UserFeedbackProfile.objects.filter(user_id=user_id).update(
            feedback_count=F('feedback_count') + 1,
            rate_limited_count=F('rate_limited_count') + (1 if is_limited else 0),
        )

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
    pending = ClassificationFeedback.objects.filter(trained=False, rate_limited=False).count()
    rate_limited_total = ClassificationFeedback.objects.filter(rate_limited=True).count()
    flagged_users = UserFeedbackProfile.objects.filter(flagged=True).count()
    return Response({
        'total_feedback': total,
        'accepted': accepted,
        'rejected': total - accepted,
        'acceptance_rate': round(accepted / total * 100, 1) if total else 0,
        'pending_training': pending,
        'rate_limited': rate_limited_total,
        'flagged_users': flagged_users,
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


class UserFeedbackProfileViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Gestión de perfiles de confianza de usuarios. Solo area_admin y super_admin.

    GET  /classify/user-feedback-profiles/       — lista todos los perfiles
    GET  /classify/user-feedback-profiles/{id}/  — detalle de un perfil
    PATCH /classify/user-feedback-profiles/{id}/ — ajustar trust_score o flagged
    """
    serializer_class = UserFeedbackProfileSerializer
    permission_classes = [IsAreaAdmin]
    queryset = UserFeedbackProfile.objects.all()
    http_method_names = ['get', 'patch', 'head', 'options']
