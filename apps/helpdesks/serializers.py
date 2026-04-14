"""
Serializers del módulo de Help Desk.

Se usan dos serializers separados para HelpDesk:
- HelpDeskCreateSerializer: solo para escritura en POST /helpdesks/. Expone
  únicamente los campos que el solicitante puede proporcionar al crear.
- HelpDeskSerializer: para lectura y como respuesta en todos los endpoints.
  Estado, fechas de control y adjuntos son read-only porque solo se modifican
  a través de endpoints dedicados que aplican validaciones de negocio.
"""
from rest_framework import serializers
from .models import HelpDesk, HDAttachment, HDComment


class HDAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HDAttachment
        fields = ['id', 'tipo', 'nombre', 'valor', 'created_at']
        read_only_fields = ['id', 'created_at']


class HDCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HDComment
        fields = ['id', 'autor_id', 'contenido', 'es_interno', 'created_at']
        read_only_fields = ['id', 'autor_id', 'created_at']


class HelpDeskSerializer(serializers.ModelSerializer):
    attachments = HDAttachmentSerializer(many=True, read_only=True)
    service_nombre = serializers.CharField(source='service.nombre', read_only=True)

    class Meta:
        model = HelpDesk
        fields = [
            'id', 'folio', 'solicitante_id', 'responsable_id',
            'service', 'service_nombre', 'origen', 'prioridad', 'estado',
            'descripcion_problema', 'descripcion_solucion',
            'fecha_asignacion', 'fecha_compromiso', 'fecha_efectividad',
            'tiempo_estimado', 'attachments', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'folio', 'solicitante_id', 'responsable_id', 'estado',
            'fecha_asignacion', 'fecha_efectividad', 'service_nombre',
            'attachments', 'created_at', 'updated_at',
        ]


class HelpDeskCreateSerializer(serializers.ModelSerializer):
    """
    Serializer de escritura exclusivo para POST /helpdesks/.

    tiempo_estimado es opcional: si no se provee en el body, se hereda del campo
    tiempo_estimado_default del servicio seleccionado. Esta herencia permite que
    el área de TI configure tiempos estándar por servicio sin forzar al solicitante
    a conocerlos.

    fecha_compromiso no se expone aquí — es responsabilidad del area_admin
    al asignar el ticket vía el endpoint /assign/.
    """

    class Meta:
        model = HelpDesk
        fields = [
            'service', 'origen', 'prioridad', 'descripcion_problema',
            'tiempo_estimado',
        ]
        extra_kwargs = {'tiempo_estimado': {'required': False}}

    def validate(self, attrs):
        if 'tiempo_estimado' not in attrs:
            attrs['tiempo_estimado'] = attrs['service'].tiempo_estimado_default
        return attrs


class HelpDeskAssignSerializer(serializers.Serializer):
    """Valida los campos del endpoint /assign/."""
    responsable_id = serializers.IntegerField()
    fecha_compromiso = serializers.DateTimeField(required=False, allow_null=True)
