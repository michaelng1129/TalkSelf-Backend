import pydantic

class UserBase(pydantic.BaseModel):
    email: str
    
class UserCreate(UserBase):
    password: str

    class Config:
        from_attributes = True


class User(UserBase):
    id: int

    class Config:
        from_attributes = True

class UserInfoBase(pydantic.BaseModel):
    user_id: int
    name: str
    avatar_url: str

class UserInfoCreate(UserInfoBase):
    pass

class UserInfo(UserInfoBase):
    id: int

    class Config:
        from_attributes = True
