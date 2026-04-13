from django.db import models


class Department(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'catalog_department'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ServiceCategory(models.Model):
    nombre = models.CharField(max_length=100)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='categories',
    )
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'catalog_servicecategory'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.department.nombre} / {self.nombre}'


class Service(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name='services',
    )
    tiempo_estimado_default = models.PositiveIntegerField(
        help_text='Tiempo estimado en horas',
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'catalog_service'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
