"""
Modelos del dominio de Help Desk.

Un HelpDesk representa un ticket de soporte iniciado por un usuario del sistema
externo. Atraviesa un ciclo de vida controlado (ver VALID_TRANSITIONS) y puede
llevar adjuntos y comentarios asociados.

Dependencias internas: apps.catalog (Service)
"""
from django.db import models
from apps.catalog.models import Service

ORIGEN_CHOICES = [
    ('error', 'Error'),
    ('solicitud', 'Solicitud'),
    ('consulta', 'Consulta'),
    ('mantenimiento', 'Mantenimiento'),
]

PRIORIDAD_CHOICES = [
    ('baja', 'Baja'),
    ('media', 'Media'),
    ('alta', 'Alta'),
    ('critica', 'Crítica'),
]

ESTADO_CHOICES = [
    ('abierto', 'Abierto'),
    ('en_progreso', 'En progreso'),
    ('en_espera', 'En espera'),
    ('resuelto', 'Resuelto'),
    ('cerrado', 'Cerrado'),
]

# Máquina de estados del ciclo de vida de un ticket.
# El flujo normal es: abierto → en_progreso → resuelto → cerrado.
# en_espera permite pausar un ticket (ej. esperando respuesta del usuario)
# y retomarlo sin perder el historial de progreso.
# cerrado es estado terminal — un ticket cerrado no puede reabrirse.
# Las transiciones se validan en la vista (no en el modelo) para mantener
# la lógica de negocio centralizada y testeable en un solo lugar.
VALID_TRANSITIONS = {
    'abierto':     ['en_progreso'],
    'en_progreso': ['en_espera', 'resuelto'],
    'en_espera':   ['en_progreso', 'resuelto'],
    'resuelto':    ['cerrado'],
    'cerrado':     [],
}

TIPO_ADJUNTO_CHOICES = [
    ('archivo', 'Archivo'),
    ('url', 'URL'),
]


class HelpDesk(models.Model):
    """
    Ticket de soporte técnico. Entidad central del sistema.

    El folio (ej. HD-000001) es el identificador visible para el usuario final.
    Se usa en correos, reportes y seguimiento operativo por teléfono, por eso
    es incremental y legible — no un UUID. Ver método save().

    solicitante_id y responsable_id son IDs del sistema externo de usuarios.
    No hay FK a una tabla local porque la gestión de identidad es
    responsabilidad del sistema externo; este servicio solo almacena la
    referencia numérica.

    tiempo_estimado se hereda de service.tiempo_estimado_default al crear
    el ticket si el solicitante no especifica uno. Ver HelpDeskCreateSerializer.
    """
    folio = models.CharField(max_length=20, unique=True, blank=True)
    solicitante_id = models.IntegerField(null=True, blank=True, db_index=True)
    responsable_id = models.IntegerField(null=True, blank=True, db_index=True)
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='helpdesks')
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES)
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='abierto', db_index=True)
    descripcion_problema = models.TextField()
    descripcion_solucion = models.TextField(null=True, blank=True)
    fecha_asignacion = models.DateTimeField(null=True, blank=True)
    fecha_compromiso = models.DateTimeField(null=True, blank=True)
    fecha_efectividad = models.DateTimeField(null=True, blank=True)
    tiempo_estimado = models.PositiveIntegerField(help_text='Horas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'helpdesks_helpdesk'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # El folio depende del PK, que solo existe después del primer INSERT.
        # Por eso se requieren dos escrituras: la primera genera el PK,
        # la segunda persiste el folio derivado de ese PK.
        # update_fields=['folio'] evita una actualización innecesaria de
        # todos los campos en ese segundo guardado.
        super().save(*args, **kwargs)
        if not self.folio:
            self.folio = f'HD-{self.pk:06d}'
            super().save(update_fields=['folio'])

    def __str__(self):
        return self.folio


class HDAttachment(models.Model):
    """
    Adjunto asociado a un ticket. Soporta dos modos de almacenamiento:
    - tipo='archivo': el archivo se persiste físicamente vía FileStorage;
      valor almacena la ruta interna retornada por storage.save().
    - tipo='url': referencia a un recurso externo; valor almacena la URL.

    El almacenamiento físico está desacoplado del modelo en storage.py,
    lo que permite migrar de almacenamiento local a S3 o Azure sin
    modificar este modelo ni las vistas.
    """
    help_desk = models.ForeignKey(HelpDesk, on_delete=models.CASCADE, related_name='attachments')
    tipo = models.CharField(max_length=10, choices=TIPO_ADJUNTO_CHOICES)
    nombre = models.CharField(max_length=200)
    valor = models.TextField(help_text='Ruta del archivo o URL')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'helpdesks_hdattachment'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.help_desk.folio} — {self.nombre}'


class HDComment(models.Model):
    """
    Comentario en un ticket. Puede ser público o interno al equipo de TI.

    Los comentarios con es_interno=True son notas internas del equipo técnico
    que no deben mostrarse a quien tiene el rol 'user'. El filtrado se aplica
    en HDCommentViewSet.get_queryset() (capa de vista), no aquí, para que el
    modelo no asuma el contexto de autenticación.

    autor_id es el ID del sistema externo; puede ser None si el comentario
    fue creado por un proceso automatizado o por un usuario anónimo.
    """
    help_desk = models.ForeignKey(HelpDesk, on_delete=models.CASCADE, related_name='comments')
    autor_id = models.IntegerField(null=True, blank=True)
    contenido = models.TextField()
    es_interno = models.BooleanField(default=False, help_text='Solo visible para TI')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'helpdesks_hdcomment'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.help_desk.folio} — comentario {self.pk}'
