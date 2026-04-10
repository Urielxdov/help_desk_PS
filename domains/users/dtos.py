from dataclasses import dataclass
from typing import Optional


@dataclass
class DepartmentDTO:
    id: str
    name: str
    keywords: str = ""
    sla_hours: int = 24
    is_active: bool = True


@dataclass
class UserDTO:
    id: str
    email: str
    full_name: str
    role: str                           # admin | hd_manager | agent | end_user
    is_active: bool = True
    department_id: Optional[str] = None
    position: Optional[str] = None
