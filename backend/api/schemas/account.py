from pydantic import BaseModel, Field, model_validator


class UpdateProfileRequest(BaseModel):
    email: str | None = Field(None, max_length=255, description="New email address for the profile")


class ChangePasswordRequestV2(BaseModel):
    current_password: str = Field(description="Current password for verification")
    new_password: str = Field(min_length=8, max_length=128, description="New password (8–128 characters)")
    new_password2: str | None = Field(None, description="Confirmation — must match new_password")

    @model_validator(mode='after')
    def passwords_match(self):
        if self.new_password2 is not None and self.new_password != self.new_password2:
            raise ValueError('Passwords do not match')
        return self
