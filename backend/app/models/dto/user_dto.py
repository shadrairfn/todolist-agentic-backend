from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    
class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
