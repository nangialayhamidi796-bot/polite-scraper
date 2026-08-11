from enum import Enum

from pydantic import BaseModel, Field


class BookCategory(str, Enum):
    FICTION = "fiction"
    NONFICTION = "nonfiction"
    CHILDREN = "children"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    FANTASY = "fantasy"
    OTHER = "other"


class EnrichRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    price: str = Field(min_length=1, max_length=50)
    availability: str = Field(min_length=1, max_length=100)
    rating: str = Field(min_length=1, max_length=20)


class EnrichResponse(BaseModel):
    category: BookCategory
    summary: str = Field(min_length=1, max_length=200)
    quality_flags: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    