from shared.exceptions import NotFoundError, ConflictError, ForbiddenError
from .dtos import UserDTO, DepartmentDTO
from .repository import (
    IUserRepository, DjangoUserRepository,
    IDepartmentRepository, DjangoDepartmentRepository,
)


class DepartmentService:
    def __init__(self, repo: IDepartmentRepository = None):
        self._repo = repo or DjangoDepartmentRepository()

    def create_department(self, name: str, keywords: str = "", sla_hours: int = 24) -> DepartmentDTO:
        return self._repo.create(name=name, keywords=keywords, sla_hours=sla_hours)

    def get_department(self, dept_id: str) -> DepartmentDTO:
        dept = self._repo.get_by_id(dept_id)
        if not dept:
            raise NotFoundError(f"Departamento '{dept_id}' no encontrado")
        return dept

    def list_departments(self) -> list[DepartmentDTO]:
        return self._repo.list_active()

    def list_agents(self, dept_id: str, user_repo: IUserRepository = None) -> list[UserDTO]:
        dept = self.get_department(dept_id)
        repo = user_repo or DjangoUserRepository()
        return repo.list_by_department(dept.id)


class UserService:
    def __init__(self, repo: IUserRepository = None):
        self._repo = repo or DjangoUserRepository()

    def create_user(self, email: str, full_name: str, role: str, department_id: str = None, password: str = None) -> UserDTO:
        existing = self._repo.get_by_email(email)
        if existing:
            raise ConflictError(f"Ya existe un usuario con el email '{email}'")
        return self._repo.create(
            email=email,
            full_name=full_name,
            role=role,
            department_id=department_id,
            password=password,
        )

    def get_user(self, user_id: str) -> UserDTO:
        user = self._repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"Usuario '{user_id}' no encontrado")
        return user

    def delete_user(self, user_id: str, requesting_role: str) -> None:
        if requesting_role != "admin":
            raise ForbiddenError("Solo un admin puede eliminar usuarios")
        self._repo.soft_delete(user_id)
