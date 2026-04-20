from django.db import models

from apps.catalog.models import Service


class ServiceKeyword(models.Model):
    """
    Palabra clave asociada a un servicio para clasificación automática.

    El clasificador busca estos keywords en la descripción del problema
    y suma sus pesos para determinar qué servicio sugerir.
    Mayor weight = señal más fuerte hacia ese servicio.

    Los keywords se almacenan en minúsculas para búsqueda case-insensitive.
    Pueden provenir de: carga manual, script TF-IDF sobre tickets históricos,
    o extracción automática de la descripción del servicio.
    """
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='keywords',
        help_text="Servicio al que apunta este keyword"
    )
    keyword = models.CharField(
        max_length=100,
        help_text="Palabra o frase clave en minúsculas"
    )
    weight = models.PositiveIntegerField(
        default=1,
        help_text="Peso de la señal. Mayor peso = más relevante para este servicio"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'classifier_servicekeyword'
        unique_together = [('service', 'keyword')]
        ordering = ['service', '-weight']

    def save(self, *args, **kwargs):
        self.keyword = self.keyword.lower().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'"{self.keyword}" → {self.service.name} (w={self.weight})'


class ClassificationFeedback(models.Model):
    """
    Registro de retroalimentación del usuario sobre la sugerencia del clasificador.

    Cuando el sistema sugiere un servicio y el usuario acepta o cambia,
    se guarda aquí. Con el tiempo, estos datos permiten ajustar pesos
    o entrenar un modelo más sofisticado.

    suggested_service puede ser null si el clasificador no encontró
    ninguna coincidencia con suficiente score.
    """
    problem_description = models.TextField(
        help_text="Texto original ingresado por el usuario"
    )
    suggested_service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggestions',
        help_text="Servicio que el sistema sugirió (null = sin sugerencia)"
    )
    chosen_service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='chosen_feedbacks',
        help_text="Servicio que el usuario eligió finalmente"
    )
    accepted = models.BooleanField(
        help_text="True si el usuario aceptó la sugerencia, False si la cambió"
    )
    trained = models.BooleanField(
        default=False,
        help_text="True si este feedback ya fue procesado por el ajuste de pesos"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'classifier_classificationfeedback'
        ordering = ['-created_at']

    def __str__(self):
        status = 'accepted' if self.accepted else 'rejected'
        return f'Feedback {status} → {self.chosen_service.name}'
