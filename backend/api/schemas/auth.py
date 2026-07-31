from pydantic import BaseModel, Field, model_validator


class LoginRequest(BaseModel):
    username: str = Field(description="User login identifier")
    password: str = Field(description="User password in plain text")


class ChangePasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128, description="New password (8–128 characters)")
    password2: str | None = Field(None, description="Confirmation — must match password")

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password2 is not None and self.password != self.password2:
            raise ValueError('Passwords do not match')
        return self
