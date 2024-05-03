import sqlalchemy as sql
import passlib.hash as hash
import database as database
from sqlalchemy.orm import relationship

class User(database.Base):
    __tablename__ = "users"
    id = sql.Column(sql.Integer, primary_key=True, index=True)
    email = sql.Column(sql.String, unique=True, index=True)
    password = sql.Column(sql.String)

    user_info = relationship("UserInfo", uselist=False, back_populates="user")

    def verify_password(self, password: str):
        #return hash.bcrypt.verify(password, self.hashed_password)
        return password == self.password
    
class UserInfo(database.Base):
    __tablename__ = "usersInfo"
    id = sql.Column(sql.Integer, primary_key=True, index=True)
    name = sql.Column(sql.String)
    avatar_url = sql.Column(sql.String)

    user_id = sql.Column(sql.Integer, sql.ForeignKey('users.id'))
    user = relationship("User", back_populates="user_info")
