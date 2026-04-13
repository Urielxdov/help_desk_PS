"""
Interfaz de almacenamiento de archivos adjuntos.

Para migrar a S3, Azure Blob, etc.:
  1. Crear una nueva clase que herede de FileStorage.
  2. Cambiar get_storage() para retornarla.
  3. Sin cambios en el resto del código.
"""
from abc import ABC, abstractmethod

from django.core.files.storage import default_storage


class FileStorage(ABC):
    @abstractmethod
    def save(self, file, filename: str) -> str:
        """Guarda el archivo y retorna la ruta almacenada."""

    @abstractmethod
    def url(self, path: str) -> str:
        """Retorna la URL pública del archivo."""

    @abstractmethod
    def delete(self, path: str) -> None:
        """Elimina el archivo."""


class LocalFileStorage(FileStorage):
    def save(self, file, filename: str) -> str:
        path = default_storage.save(f'attachments/{filename}', file)
        return path

    def url(self, path: str) -> str:
        return default_storage.url(path)

    def delete(self, path: str) -> None:
        if default_storage.exists(path):
            default_storage.delete(path)


def get_storage() -> FileStorage:
    """Punto de entrada único para obtener la implementación de storage activa."""
    return LocalFileStorage()
