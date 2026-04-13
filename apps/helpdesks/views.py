from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import VALID_TRANSITIONS, HDAttachment, HDComment, HelpDesk
from .permissions import IsAreaAdmin, IsOwnerOrAdmin, IsTechnicianOrAdmin
from .serializers import (
    HDAttachmentSerializer,
    HDCommentSerializer,
    HelpDeskCreateSerializer,
    HelpDeskSerializer,
)
from .storage import get_storage


class HelpDeskViewSet(viewsets.GenericViewSet):
    serializer_class = HelpDeskSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['estado', 'prioridad', 'service', 'responsable_id']

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', None)
        qs = HelpDesk.objects.select_related('service__category__department').prefetch_related('attachments')

        if role == 'user':
            return qs.filter(solicitante_id=user.user_id)
        if role == 'technician':
            return qs.filter(responsable_id=user.user_id)
        return qs  # area_admin, super_admin ven todos

    def list(self, request):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(HelpDeskSerializer(page, many=True).data)
        return Response(HelpDeskSerializer(qs, many=True).data)

    def create(self, request):
        serializer = HelpDeskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hd = serializer.save(solicitante_id=getattr(request.user, 'user_id', None))
        return Response(HelpDeskSerializer(hd).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(request, hd)
        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='status',
            permission_classes=[IsTechnicianOrAdmin])
    def change_status(self, request, pk=None):
        hd = get_object_or_404(HelpDesk, pk=pk)
        new_status = request.data.get('estado')

        if new_status not in VALID_TRANSITIONS.get(hd.estado, []):
            raise ValidationError(
                {'estado': f'Transición no permitida: {hd.estado} → {new_status}. '
                           f'Opciones válidas: {VALID_TRANSITIONS[hd.estado]}'}
            )

        hd.estado = new_status
        hd.save(update_fields=['estado', 'updated_at'])
        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='assign',
            permission_classes=[IsAreaAdmin])
    def assign(self, request, pk=None):
        hd = get_object_or_404(HelpDesk, pk=pk)
        responsable_id = request.data.get('responsable_id')
        fecha_compromiso = request.data.get('fecha_compromiso')

        hd.responsable_id = responsable_id
        hd.fecha_asignacion = timezone.now()
        if fecha_compromiso:
            hd.fecha_compromiso = fecha_compromiso
        hd.save(update_fields=['responsable_id', 'fecha_asignacion', 'fecha_compromiso', 'updated_at'])
        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='resolve',
            permission_classes=[IsTechnicianOrAdmin])
    def resolve(self, request, pk=None):
        hd = get_object_or_404(HelpDesk, pk=pk)

        if hd.estado not in ('en_progreso', 'en_espera'):
            raise ValidationError(
                {'estado': f'Solo se puede resolver desde en_progreso o en_espera. Estado actual: {hd.estado}'}
            )

        descripcion_solucion = request.data.get('descripcion_solucion', '').strip()
        if not descripcion_solucion:
            raise ValidationError({'descripcion_solucion': 'Este campo es obligatorio para resolver un HD.'})

        hd.estado = 'resuelto'
        hd.descripcion_solucion = descripcion_solucion
        hd.fecha_efectividad = timezone.now()
        hd.save(update_fields=['estado', 'descripcion_solucion', 'fecha_efectividad', 'updated_at'])
        return Response(HelpDeskSerializer(hd).data)


class HDAttachmentViewSet(
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = HDAttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HDAttachment.objects.filter(help_desk_id=self.kwargs['helpdesk_pk'])

    def create(self, request, helpdesk_pk=None):
        hd = get_object_or_404(HelpDesk, pk=helpdesk_pk)
        tipo = request.data.get('tipo')
        nombre = request.data.get('nombre', '')

        if tipo == 'archivo':
            file = request.FILES.get('archivo')
            if not file:
                raise ValidationError({'archivo': 'Se requiere un archivo cuando tipo=archivo.'})
            storage = get_storage()
            valor = storage.save(file, file.name)
        elif tipo == 'url':
            valor = request.data.get('valor', '').strip()
            if not valor:
                raise ValidationError({'valor': 'Se requiere una URL cuando tipo=url.'})
        else:
            raise ValidationError({'tipo': 'Debe ser "archivo" o "url".'})

        attachment = HDAttachment.objects.create(
            help_desk=hd, tipo=tipo, nombre=nombre, valor=valor
        )
        return Response(HDAttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, helpdesk_pk=None, pk=None):
        attachment = get_object_or_404(self.get_queryset(), pk=pk)
        if attachment.tipo == 'archivo':
            get_storage().delete(attachment.valor)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HDCommentViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = HDCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = HDComment.objects.filter(help_desk_id=self.kwargs['helpdesk_pk'])
        if getattr(self.request.user, 'role', None) == 'user':
            qs = qs.filter(es_interno=False)
        return qs

    def perform_create(self, serializer):
        hd = get_object_or_404(HelpDesk, pk=self.kwargs['helpdesk_pk'])
        serializer.save(
            help_desk=hd,
            autor_id=getattr(self.request.user, 'user_id', None),
        )
