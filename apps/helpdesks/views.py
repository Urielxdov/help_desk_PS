"""
Vistas del módulo de Help Desk.

Three ViewSets with separate responsibilities:
- HelpDeskViewSet: full ticket lifecycle (create, list, change status, assign, resolve, close).
- HDAttachmentViewSet: file and URL attachments for a ticket.
- HDCommentViewSet: public and internal comments on a ticket.

Ticket visibility in the list is a security rule:
each role only accesses the tickets that belong to them (see get_queryset).
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
    filterset_fields = ['status', 'priority', 'service', 'assignee_id']

    def get_queryset(self):
        # Visibility is a security constraint, not just UX.
        # Ensures a 'user' cannot see other users' tickets even if they know the ID.
        # A 'technician' only accesses tickets assigned to them.
        # Admin roles see all for management, auditing and escalation.
        user = self.request.user
        role = getattr(user, 'role', None)
        qs = HelpDesk.objects.select_related('service__category__department').prefetch_related('attachments')

        if role == 'user':
            return qs.filter(requester_id=user.user_id)
        if role == 'technician':
            return qs.filter(assignee_id=user.user_id)
        return qs  # area_admin, super_admin see all

    def list(self, request):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(HelpDeskSerializer(page, many=True).data)
        return Response(HelpDeskSerializer(qs, many=True).data)

    def create(self, request):
        # requester_id is extracted from the token, not the body, to prevent
        # a user from opening tickets on behalf of another user.
        serializer = HelpDeskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hd = serializer.save(requester_id=getattr(request.user, 'user_id', None))
        return Response(HelpDeskSerializer(hd).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='status',
            permission_classes=[IsTechnicianOrAdmin])
    def change_status(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)
        new_status = request.data.get('status')

        if new_status not in VALID_TRANSITIONS.get(hd.status, []):
            raise ValidationError(
                {'status': f'Transition not allowed: {hd.status} → {new_status}. '
                           f'Valid options: {VALID_TRANSITIONS[hd.status]}'}
            )

        if getattr(request.user, 'role', None) == 'technician' and new_status in ('resolved', 'closed'):
            raise PermissionDenied('Technicians cannot mark tickets as resolved or closed from this endpoint.')

        hd.status = new_status
        hd.save(update_fields=['status', 'updated_at'])
        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='assign',
            permission_classes=[IsAreaAdmin])
    def assign(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = HelpDeskAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        hd.assignee_id = serializer.validated_data['assignee_id']
        hd.assigned_at = timezone.now()
        if serializer.validated_data.get('due_date'):
            hd.due_date = serializer.validated_data['due_date']
        if serializer.validated_data.get('impact'):
            hd.impact = serializer.validated_data['impact']
        hd.save(update_fields=['assignee_id', 'assigned_at', 'due_date', 'impact', 'updated_at'])
        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='resolve',
            permission_classes=[IsTechnicianOrAdmin])
    def resolve(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)

        if hd.status not in ('in_progress', 'on_hold', 'resolved'):
            raise ValidationError(
                {'status': f'Can only resolve from in_progress or on_hold. Current status: {hd.status}'}
            )

        solution_description = request.data.get('solution_description', '').strip()
        if not solution_description:
            raise ValidationError({'solution_description': 'This field is required to resolve a ticket.'})

        hd.status = 'resolved'
        hd.solution_description = solution_description
        hd.resolved_at = timezone.now()
        hd.save(update_fields=['status', 'solution_description', 'resolved_at', 'updated_at'])
        return Response(HelpDeskSerializer(hd).data)

    @action(detail=True, methods=['patch'], url_path='close',
            permission_classes=[IsAuthenticated])
    def close(self, request, pk=None):
        hd = get_object_or_404(self.get_queryset(), pk=pk)

        role = getattr(request.user, 'role', None)
        is_requester = hd.requester_id == request.user.user_id

        if role == 'technician':
            raise PermissionDenied('Technicians cannot close tickets.')

        if role == 'user':
            if not is_requester:
                raise PermissionDenied('Only the ticket requester can close it.')
            if not hd.service.client_close:
                raise PermissionDenied('This service type does not allow the requester to close the ticket.')

        if hd.status != 'resolved':
            raise ValidationError({'status': f'Can only close a resolved ticket. Current status: {hd.status}'})

        hd.status = 'closed'
        hd.save(update_fields=['status', 'updated_at'])
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
        type_ = request.data.get('type')
        name = request.data.get('name', '')

        if type_ == 'file':
            file = request.FILES.get('file')
            if not file:
                raise ValidationError({'file': 'A file is required when type=file.'})
            if file.size > MAX_UPLOAD_SIZE:
                raise ValidationError({'file': f'File exceeds the maximum size of {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.'})
            storage = get_storage()
            value = storage.save(file, file.name)
        elif type_ == 'url':
            value = request.data.get('value', '').strip()
            if not value:
                raise ValidationError({'value': 'A URL is required when type=url.'})
        else:
            raise ValidationError({'type': 'Must be "file" or "url".'})

        attachment = HDAttachment.objects.create(
            help_desk=hd, type=type_, name=name, value=value
        )
        return Response(HDAttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, helpdesk_pk=None, pk=None):
        # Only 'file' attachments have a physical file to clean up.
        # URLs are external references — deleting the record requires
        # no storage operation.
        attachment = get_object_or_404(self.get_queryset(), pk=pk)
        if attachment.type == 'file':
            get_storage().delete(attachment.value)
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
        # Internal comments are IT team notes.
        # The 'user' role must not see them — filtered here so the list
        # and serialization are transparent to comment type.
        qs = HDComment.objects.filter(help_desk_id=self.kwargs['helpdesk_pk'])
        if getattr(self.request.user, 'role', None) == 'user':
            qs = qs.filter(is_internal=False)
        return qs

    def perform_create(self, serializer):
        hd = get_object_or_404(HelpDesk, pk=self.kwargs['helpdesk_pk'])
        serializer.save(
            help_desk=hd,
            author_id=getattr(self.request.user, 'user_id', None),
        )
