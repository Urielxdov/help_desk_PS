"""
Catálogo de servicios de soporte. Define la jerarquía:
    Department → ServiceCategory → Service

A Service is what the user selects when opening a HelpDesk ticket.
The estimated_hours field is inherited by the ticket at creation time
if the requester does not provide one explicitly.

FKs use PROTECT (not CASCADE) to avoid deleting departments or
categories that already have historical tickets linked through their services.
"""
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'catalog_department'
        ordering = ['name']

    def __str__(self):
        return self.name


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='categories',
    )
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'catalog_servicecategory'
        ordering = ['name']

    def __str__(self):
        return f'{self.department.name} / {self.name}'


class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name='services',
    )
    estimated_hours = models.PositiveIntegerField(
        help_text='Estimated time in hours',
    )
    active = models.BooleanField(default=True)
    client_close = models.BooleanField(default=True, help_text='Allow requester to close the ticket')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'catalog_service'
        ordering = ['name']

    def __str__(self):
        return self.name
