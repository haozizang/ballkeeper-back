from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

# 添加用户-球队关联表模型
class UserTeam(SQLModel, table=True):
    __tablename__ = "user_team"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    team_id: int = Field(foreign_key="teams.id")
    follow_time: datetime = Field(default_factory=datetime.utcnow)
    role: str = Field(default="member")  # 可以是 "creator", "admin", "member" 等

# 修改 User 模型，移除 team_id 字段
class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password: str
    avatar_path: Optional[str] = None

# 添加 Team 模型
class Team(SQLModel, table=True):
    __tablename__ = "teams"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(unique=True, index=True)
    category_id: int
    is_public: bool = Field(default=True)
    mobile: str
    name: str
    content: Optional[str] = None
    # creator_id: int = Field(foreign_key="users.id")
    creator_id: int = Field(index=True)
    logo_path: Optional[str] = None

    def __str__(self):
        return f"Team(id={self.id}, title='{self.title}')"
