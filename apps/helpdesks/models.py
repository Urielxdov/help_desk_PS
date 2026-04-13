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
    folio = models.CharField(max_length=20, unique=True, blank=True)
    solicitante_id = models.IntegerField(null=True, blank=True)
    responsable_id = models.IntegerField(null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='helpdesks')
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES)
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='abierto')
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
        super().save(*args, **kwargs)
        if not self.folio:
            self.folio = f'HD-{self.pk:06d}'
            super().save(update_fields=['folio'])

    def __str__(self):
        return self.folio


class HDAttachment(models.Model):
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
