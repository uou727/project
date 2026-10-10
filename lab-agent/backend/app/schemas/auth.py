from pydantic import BaseModel


class loginResponse(BaseModel):
    username: str
    password: str
