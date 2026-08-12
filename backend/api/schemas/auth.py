from pydantic import BaseModel, Field, model_validator


class LoginRequest(BaseModel):
    # Bounded (R2-M6): unbounded fields let a client send multi-KB
    # credentials through bcrypt work and the audit path on every attempt.
    username: str = Field(min_length=1, max_length=128, description="User login identifier")
    password: str = Field(min_length=1, max_length=256, description="User password in plain text")
    # M-1: the tenant the credentials belong to. Required to authenticate users
    # whose rows live in a tenant-specific database (DB-per-tenant model). The
    # frontend sends the slug the user selected on the login screen; it may also
    # arrive as the X-Tenant-ID header. Omitted for platform/main-DB users.
    tenant: str | None = Field(None, description="Tenant slug the user belongs to")


class ChangePasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128, description="New password (8–128 characters)")
    password2: str | None = Field(None, description="Confirmation — must match password")

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password2 is not None and self.password != self.password2:
            raise ValueError('Passwords do not match')
        return self
