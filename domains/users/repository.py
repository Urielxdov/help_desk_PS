from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from .dtos import UserDTO
from .mappers import UserMapper


class IUserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[UserDTO]: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[UserDTO]: ...

    @abstractmethod
    def list_active(self) -> list[UserDTO]: ...

    @abstractmethod
    def list_by_role(self, role: str) -> list[UserDTO]: ...

    @abstractmethod
    def create(self, email: str, full_name: str, role: str, password: str) -> UserDTO: ...

    @abstractmethod
    def update(self, user_id: str, **fields) -> UserDTO: ...

    @abstractmethod
    def soft_delete(self, user_id: str) -> None: ...


class DjangoUserRepository(IUserRepository):
    def get_by_id(self, user_id: str) -> Optional[UserDTO]:
        from .models import User
        try:
            return UserMapper.to_dto(User.objects.get(id=user_id, is_active=True))
        except User.DoesNotExist:
            return None

    def get_by_email(self, email: str) -> Optional[UserDTO]:
        from .models import User
        try:
            return UserMapper.to_dto(User.objects.get(email=email, is_active=True))
        except User.DoesNotExist:
            return None

    def list_active(self) -> list[UserDTO]:
        from .models import User
        return [UserMapper.to_dto(u) for u in User.objects.filter(is_active=True)]

    def list_by_role(self, role: str) -> list[UserDTO]:
        from .models import User
        return [UserMapper.to_dto(u) for u in User.objects.filter(role=role, is_active=True)]

    def create(self, email: str, full_name: str, role: str, password: str) -> UserDTO:
        from .models import User
        user = User.objects.create_user(
            email=email, full_name=full_name, role=role, password=password
        )
        return UserMapper.to_dto(user)

    def update(self, user_id: str, **fields) -> UserDTO:
        from .models import User
        User.objects.filter(id=user_id).update(**fields)
        return self.get_by_id(user_id)

    def soft_delete(self, user_id: str) -> None:
        from .models import User
        try:
            User.objects.get(id=user_id).soft_delete()
        except User.DoesNotExist:
            pass
