from pydantic import BaseModel


class CreateModel(BaseModel):
    name: str


class RenameModel(BaseModel):
    old_name: str
    new_name: str


class DeleteModel(BaseModel):
    name: str


class LoginModel(BaseModel):
    username: str
    password: str


class RenameFileModel(BaseModel):
    folder: str
    old_name: str
    new_name: str


class DeleteFileModel(BaseModel):
    folder: str
    name: str
