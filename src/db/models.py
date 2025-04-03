from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime
from constants import SignupType
import sqlalchemy

class UserBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    username: str = Field(unique=True, index=True)
    avatar_path: Optional[str] = None
    gender: int = Field(default=0)
    mobile: str = Field(default="")
    team_id: Optional[int] = None
    create_time: datetime = Field(default_factory=datetime.utcnow)

class User(UserBase, table=True):
    __tablename__ = "users"
    password: str

# 添加用户-球队关联表模型
class UserTeam(SQLModel, table=True):
    __tablename__ = "user_teams"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    team_id: int = Field(foreign_key="teams.id")
    follow_time: datetime = Field(default_factory=datetime.utcnow)
    role: str = Field(default="member")  # 可以是 "creator", "admin", "member" 等

# 添加 Team 模型
class Team(SQLModel, table=True):
    __tablename__ = "teams"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    team_type: int
    is_public: bool = Field(default=True)
    mobile: str
    content: Optional[str] = None
    # creator_id: int = Field(foreign_key="users.id")
    creator_id: int = Field(index=True)
    logo_path: Optional[str] = None

    def __str__(self):
        return f"Team(id={self.id}, name='{self.name}')"

# 添加 League 模型
class League(SQLModel, table=True):
    __tablename__ = "leagues"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    league_type_ind: int
    mobile: str
    content: Optional[str] = None
    creator_id: int = Field(index=True)
    cover_path: Optional[str] = None

    def __str__(self):
        return f"League(id={self.id}, name='{self.name}')"

# 添加用户-联赛关联表模型
class UserLeague(SQLModel, table=True):
    __tablename__ = "user_leagues"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    league_id: int = Field(foreign_key="leagues.id")
    role: str = Field(default="creator")  # 可以是 "creator", "admin", "member" 等

class Activity(SQLModel, table=True):
    __tablename__ = "activities"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    type_id: int
    mobile: str
    address: Optional[str] = None
    content: Optional[str] = None
    creator_id: int = Field(index=True)
    team_id: Optional[int] = None
    max_attend: int = Field(default=0)
    cover_path: Optional[str] = None
    start_time: int = Field(default=0)

    def __str__(self):
        return f"Activity(id={self.id}, name='{self.name}')"

class ActivityUser(SQLModel, table=True):
    __tablename__ = "activity_users"
    activity_id: int = Field(primary_key=True, foreign_key="activities.id")
    user_id: int = Field(primary_key=True, foreign_key="users.id")
    signup_type: int = Field(default=SignupType.Unknown)
    create_time: int = Field(default=0)

    # 添加联合唯一约束
    __table_args__ = (
        sqlalchemy.UniqueConstraint("activity_id", "user_id", name="uix_activity_user"),
    )