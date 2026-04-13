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
    """Usado solo en POST /helpdesks/. Hereda tiempo_estimado del servicio si no se indica."""

    class Meta:
        model = HelpDesk
        fields = [
            'service', 'origen', 'prioridad', 'descripcion_problema',
            'tiempo_estimado', 'fecha_compromiso',
        ]
        extra_kwargs = {'tiempo_estimado': {'required': False}}

    def validate(self, attrs):
        if 'tiempo_estimado' not in attrs:
            attrs['tiempo_estimado'] = attrs['service'].tiempo_estimado_default
        return attrs
