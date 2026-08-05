from pydantic import BaseModel, Field, field_validator


class SaveReadingPresetRequest(BaseModel):
    preset_type: str = Field(..., description="window_level | layout")
    modality: str = Field(..., description="DICOM modality (CT, MR, etc.)")
    name: str = Field(..., min_length=1, max_length=80, description="Preset name")
    config: dict = Field(default_factory=dict, description="Preset payload")
    is_default: bool = Field(False, description="Auto-apply when opening this modality")

    @field_validator('preset_type')
    @classmethod
    def _valid_type(cls, v):
        if v not in ('window_level', 'layout'):
            raise ValueError('preset_type must be window_level or layout')
        return v


class UpdateReadingPresetRequest(BaseModel):
    name: str | None = Field(None, max_length=80, description="New name")
    config: dict | None = Field(None, description="New payload")
    is_default: bool | None = Field(None, description="Set as default for modality")
    modality: str | None = Field(None, description="New modality")
