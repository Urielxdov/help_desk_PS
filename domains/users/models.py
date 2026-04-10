from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models

from shared.models import SoftDeleteModel, TenantAwareModel


class Department(TenantAwareModel):
    name = models.CharField(max_length=200)
    keywords = models.TextField(
        blank=True,
        help_text="Palabras clave separadas por espacios. Usadas para clasificación automática.",
    )
    sla_hours = models.PositiveIntegerField(default=24)

    class Meta:
        db_table = "users_department"

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email, full_name, role="end_user", password=None, **extra):
        if not email:
            raise ValueError("El email es obligatorio")
        user = self.model(
            email=self.normalize_email(email),
            full_name=full_name,
            role=role,
            **extra,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password):
        return self.create_user(email, full_name, role="admin", password=password)


class User(AbstractBaseUser, SoftDeleteModel):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("hd_manager", "HD Manager"),
        ("agent", "Agent"),
        ("end_user", "End User"),
    ]

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="end_user")
    position = models.CharField(max_length=200, blank=True)
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        db_table = "users_user"

    def __str__(self):
        return f"{self.full_name} <{self.email}>"
