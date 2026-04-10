from dataclasses import dataclass
from typing import Optional


@dataclass
class UserDTO:
    id: str
    email: str
    full_name: str
    role: str           # admin | hd_manager | agent
    is_active: bool = True
