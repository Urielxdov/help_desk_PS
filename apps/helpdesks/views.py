"""
Vistas del módulo de Help Desk.

Contiene tres ViewSets con responsabilidades separadas:
- HelpDeskViewSet: ciclo de vida completo del ticket (crear, listar, cambiar
  estado, asignar, resolver).
- HDAttachmentViewSet: gestión de archivos y URLs adjuntos a un ticket.
- HDCommentViewSet: comentarios públicos e internos de un ticket.

La visibilidad de los tickets en el listado es una regla de seguridad:
cada rol solo accede a los tickets que le corresponden (ver get_queryset).
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.permissions import IsAreaAdmin
from .models import VALID_TRANSITIONS, HDAttachment, HDComment, HelpDesk
from .permissions import IsTechnicianOrAdmin
from .serializers import (
    HDAttachmentSerializer,
    HDCommentSerializer,
    HelpDeskAssignSerializer,
    HelpDeskCreateSerializer,
    HelpDeskSerializer,
)
from .storage import get_storage

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


class HelpDeskViewSet(viewsets.GenericViewSet):
    serializer_class = HelpDeskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['estado', 'prioridad', 'service', 'responsable_id']

    def get_queryset(self):
        # La visibilidad es una restricción de seguridad, no solo de UX.
        # Garantiza que un 'user' no pueda ver tickets de otros usuarios
        # aunque conozca el ID directamente. Un 'technician' solo accede
        # a los que le fueron asignados. Los roles admin ven todo para
        # gestión, auditoría y soporte de nivel superior.
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
        # solicitante_id se extrae del token, no del body, para evitar que
        # un usuario pueda abrir tickets en nombre de otro.
        serializer = HelpDeskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hd = serializer.save(solicitante_id=getattr(request.user, 'user_id', None))
        return Response(HelpDeskSerializer(hd).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='status',
            permission_classes=[IsTechnicianOrAdmin])
    def change_status(self, request, pk=None):
        """
        Cambia el estado de un ticket validando que la transición sea permitida.

        Las transiciones válidas están definidas en VALID_TRANSITIONS (models.py).
        Este endpoint cubre cambios de estado genéricos (ej. abierto → en_progreso).
        Para resolver un ticket usa /resolve/, que exige descripcion_solucion.

        Parámetros (body): estado — nuevo estado deseado.
        Lanza ValidationError si la transición no está permitida.
        """
        hd = get_object_or_404(self.get_queryset(), pk=pk)
        new_status = request.data.get('estado')

        if new_status not in VALID_TRANSITIONS.get(hd.estado, []):
            raise ValidationError(
                {'estado': f'Transición no permitida: {hd.estado} → {new_status}. '
                           f'Opciones válidas: {VALID_TRANSITIONS[hd.estado]}'}
            )

        if getattr(request.user, 'role', None) == 'technician' and new_status in ('resuelto', 'cerrado'):
            raise PermissionDenied('Los técnicos no pueden marcar como resuelto o cerrado desde este endpoint.')

        hd.estado = new_status
        hd.save(update_fields=['estado', 'updated_at'])
        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='assign',
            permission_classes=[IsAreaAdmin])
    def assign(self, request, pk=None):
        """
        Asigna un técnico a un ticket y registra la fecha de asignación.

        fecha_asignacion se establece automáticamente al momento de la llamada
        para generar un registro de auditoría preciso — no es configurable por
        el cliente. fecha_compromiso es opcional: el área puede comprometerse
        a una fecha límite o dejarlo sin definir.

        Parámetros (body):
            responsable_id: ID del técnico en el sistema externo.
            fecha_compromiso (opcional): fecha límite de resolución (ISO 8601).
        """
        hd = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = HelpDeskAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        hd.responsable_id = serializer.validated_data['responsable_id']
        hd.fecha_asignacion = timezone.now()
        if serializer.validated_data.get('fecha_compromiso'):
            hd.fecha_compromiso = serializer.validated_data['fecha_compromiso']
        hd.save(update_fields=['responsable_id', 'fecha_asignacion', 'fecha_compromiso', 'updated_at'])
        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='resolve',
            permission_classes=[IsTechnicianOrAdmin])
    def resolve(self, request, pk=None):
        """
        Marca el ticket como resuelto y registra la solución aplicada.

        descripcion_solucion es nullable en el modelo para preservar registros
        históricos sin solución documentada, pero al resolver vía este endpoint
        se exige para garantizar trazabilidad operativa — los tickets resueltos
        deben dejar constancia de qué se hizo.

        fecha_efectividad se registra automáticamente al resolver para calcular
        tiempos reales de atención en reportes y SLAs.

        Parámetros (body):
            descripcion_solucion: descripción de la acción tomada (obligatorio).
        Lanza ValidationError si el ticket no está en_progreso o en_espera,
        o si descripcion_solucion está vacía.
        """
        hd = get_object_or_404(self.get_queryset(), pk=pk)

        if hd.estado not in ('en_progreso', 'en_espera', 'resuelto'):
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

    @action(detail=True, methods=['patch'], url_path='close',
            permission_classes=[IsAuthenticated])
    def close(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)

        role = getattr(request.user, 'role', None)
        is_solicitante = hd.solicitante_id == request.user.user_id

        if role == 'technician':
            raise PermissionDenied('Los técnicos no pueden cerrar tickets.')

        if role == 'user':
            if not is_solicitante:
                raise PermissionDenied('Solo el solicitante del ticket puede cerrarlo.')
            if not hd.service.client_close:
                raise PermissionDenied('Este tipo de servicio no permite que el solicitante cierre el ticket.')

        if hd.estado != 'resuelto':
            raise ValidationError({'estado': f'Solo se puede cerrar un ticket resuelto. Estado actual: {hd.estado}'})

        hd.estado = 'cerrado'
        hd.save(update_fields=['estado', 'updated_at'])
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
            if file.size > MAX_UPLOAD_SIZE:
                raise ValidationError({'archivo': f'El archivo supera el tamaño máximo de {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.'})
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
        # Solo los adjuntos tipo 'archivo' tienen un archivo físico que limpiar.
        # Las URLs son referencias externas — borrar el registro no requiere
        # ninguna operación sobre storage.
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
    pagination_class = None

    def get_queryset(self):
        # Los comentarios internos son notas del equipo de TI.
        # El rol 'user' no debe verlos — se filtran aquí para que el listado
        # y la serialización sean transparentes al tipo de comentario.
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
