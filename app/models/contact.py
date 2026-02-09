from typing import Literal

from pydantic import BaseModel


class Contact(BaseModel):
    id: str
    name: str
    email: str = ""
    type: Literal["customer", "vendor", "both"] = "customer"
