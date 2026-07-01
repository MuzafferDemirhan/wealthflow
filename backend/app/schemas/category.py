import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    icon: Optional[str] = None
    is_system: bool
    parent_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
