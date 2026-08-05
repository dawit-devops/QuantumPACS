from pydantic import BaseModel, Field, model_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    password2: str | None = None

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password2 is not None and self.password != self.password2:
            raise ValueError('Passwords do not match')
        return self
