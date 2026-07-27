from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, Enum
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import enum
import config

engine = create_engine(config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class ResetStatus(str, enum.Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    REJECTED = "REJECTED"

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    marital_status = Column(String, nullable=False)
    country = Column(String, nullable=False)
    hobbies = Column(Text, nullable=False)
    image_path = Column(String, nullable=False)  # Local file path or Telegram File ID

    users = relationship("User", back_populates="selected_profile")

class User(Base):
    __tablename__ = "users"

    telegram_id = Column(Integer, primary_key=True)  # Telegram User ID
    username = Column(String, nullable=True)
    selected_profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    reset_status = Column(String, default=ResetStatus.NONE.value)

    selected_profile = relationship("Profile", back_populates="users")

def init_db():
    Base.metadata.create_all(bind=engine)
