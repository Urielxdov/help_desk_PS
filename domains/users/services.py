from shared.exceptions import NotFoundError, ConflictError, ForbiddenError
from .dtos import UserDTO
from .repository import IUserRepository, DjangoUserRepository


class UserService:
    def __init__(self, repo: IUserRepository = None):
        self._repo = repo or DjangoUserRepository()

    def create_user(self, email: str, full_name: str, role: str, password: str) -> UserDTO:
        if self._repo.get_by_email(email):
            raise ConflictError(f"Ya existe un usuario con el email '{email}'")
        return self._repo.create(email=email, full_name=full_name, role=role, password=password)

    def get_user(self, user_id: str) -> UserDTO:
        user = self._repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"Usuario '{user_id}' no encontrado")
        return user

    def list_users(self) -> list[UserDTO]:
        return self._repo.list_active()

    def update_user(self, user_id: str, **fields) -> UserDTO:
        self.get_user(user_id)  # valida que exista
        return self._repo.update(user_id, **fields)

    def delete_user(self, user_id: str, requesting_role: str) -> None:
        if requesting_role != 'admin':
            raise ForbiddenError('Solo un admin puede eliminar usuarios')
        self.get_user(user_id)  # valida que exista
        self._repo.soft_delete(user_id)

    def list_agents(self) -> list[UserDTO]:
        return self._repo.list_by_role('agent')
