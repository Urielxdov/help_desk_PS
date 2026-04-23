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
    user_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID del usuario que dio el feedback (del sistema externo)"
    )
    user_role = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Rol del usuario en el momento del feedback"
    )
    rate_limited = models.BooleanField(
        default=False,
        help_text="True si el feedback excedió el límite diario del usuario y no cuenta para entrenamiento"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'classifier_classificationfeedback'
        ordering = ['-created_at']

    def __str__(self):
        status = 'accepted' if self.accepted else 'rejected'
        return f'Feedback {status} → {self.chosen_service.name}'


class UserFeedbackProfile(models.Model):
    """
    Perfil de confianza de un usuario para el sistema de clasificación.

    Gestiona el impacto que tiene el feedback de un usuario sobre el entrenamiento
    del clasificador. Solo accesible por area_admin y super_admin.

    trust_score escala el delta de pesos en training: < 0.25 no mueve ningún peso,
    >= 0.8 aplica delta doble. Se recalcula automáticamente por consenso tras cada
    batch de entrenamiento.
    """
    user_id = models.IntegerField(unique=True)
    trust_score = models.FloatField(
        default=0.5,
        help_text="Confianza 0.0–1.0. < 0.25: sin efecto; >= 0.8: efecto doble"
    )
    flagged = models.BooleanField(
        default=False,
        help_text="Si True, el feedback de este usuario es ignorado completamente en entrenamiento"
    )
    feedback_count = models.PositiveIntegerField(
        default=0,
        help_text="Total de feedbacks enviados (incluye rate_limited)"
    )
    rate_limited_count = models.PositiveIntegerField(
        default=0,
        help_text="Cuántos feedbacks fueron bloqueados por límite diario"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'classifier_userfeedbackprofile'
        ordering = ['user_id']

    def __str__(self):
        status = 'flagged' if self.flagged else f'trust={self.trust_score}'
        return f'User {self.user_id} ({status})'
