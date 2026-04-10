from typing import Optional
from domains.users.dtos import UserDTO
from domains.users.repository import IUserRepository


class MockUserRepository(IUserRepository):
    def __init__(self, users: list[UserDTO] = None):
        self._users: dict[str, UserDTO] = {u.id: u for u in (users or [])}
        self._next_id = 1

    def get_by_id(self, user_id: str) -> Optional[UserDTO]:
        u = self._users.get(user_id)
        return u if (u and u.is_active) else None

    def get_by_email(self, email: str) -> Optional[UserDTO]:
        return next(
            (u for u in self._users.values() if u.email == email and u.is_active),
            None,
        )

    def list_active(self) -> list[UserDTO]:
        return [u for u in self._users.values() if u.is_active]

    def list_by_role(self, role: str) -> list[UserDTO]:
        return [u for u in self._users.values() if u.role == role and u.is_active]

    def create(self, email: str, full_name: str, role: str, password: str) -> UserDTO:
        uid = str(self._next_id)
        self._next_id += 1
        user = UserDTO(id=uid, email=email, full_name=full_name, role=role)
        self._users[uid] = user
        return user

    def update(self, user_id: str, **fields) -> Optional[UserDTO]:
        u = self._users.get(user_id)
        if not u:
            return None
        updated = UserDTO(
            id=u.id,
            email=fields.get('email', u.email),
            full_name=fields.get('full_name', u.full_name),
            role=fields.get('role', u.role),
            is_active=u.is_active,
        )
        self._users[user_id] = updated
        return updated

    def soft_delete(self, user_id: str) -> None:
        u = self._users.get(user_id)
        if u:
            self._users[user_id] = UserDTO(
                id=u.id, email=u.email, full_name=u.full_name,
                role=u.role, is_active=False,
            )
