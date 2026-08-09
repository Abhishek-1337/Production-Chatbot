from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: str | None = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    is_active: bool

    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str


class RegisterResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str
