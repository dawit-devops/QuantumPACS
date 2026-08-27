"""Pydantic v2 schemas for study bookmarks / collections (R-08)."""

from pydantic import BaseModel, Field


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field('', max_length=1000)


class CreateBookmarkRequest(BaseModel):
    study_uid: str = Field(..., min_length=1, max_length=256)
    study_desc: str = Field('', max_length=512)
    collection_id: str = Field('', max_length=64)
    notes: str = Field('', max_length=1000)