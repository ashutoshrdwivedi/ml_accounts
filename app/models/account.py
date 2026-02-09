from typing import Literal

from pydantic import BaseModel


class Account(BaseModel):
    id: str
    name: str
    type: Literal["asset", "liability", "equity", "income", "expense"]
    code: str = ""
    parent_id: str | None = None
    is_active: bool = True
