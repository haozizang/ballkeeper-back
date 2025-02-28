from typing import Optional
from sqlmodel import SQLModel, Field, create_engine, Session
from datetime import datetime
from envs import DATABASE_URL

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
    __tablename__ = "user_league"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    league_id: int = Field(foreign_key="leagues.id")
    role: str = Field(default="creator")  # 可以是 "creator", "admin", "member" 等

# 数据库配置 - 使用 SQLite
global_engine = create_engine(DATABASE_URL)

# 创建数据库表
SQLModel.metadata.create_all(global_engine)

# 依赖项
def get_session():
    with Session(global_engine) as session:
        yield session
