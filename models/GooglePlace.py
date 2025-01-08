from pydantic import BaseModel
from pydantic.fields import Field


class GooglePlace(BaseModel):
    name: str
    id: str
    types: list[str] = Field(default_factory=list)
    formattedAddress: str
    rating: float | None = None
    displayName: dict[str, str]
    primaryType: str | None = None
