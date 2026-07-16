from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db import Base, get_id_column


class AiProviderConfig(Base):
    __tablename__ = "ai_provider_config"

    id = get_id_column()
    provider_name = Column(String(50), nullable=False)
    api_base_url = Column(String(255), nullable=False)
    api_key = Column(String(255), nullable=False)
    model_name = Column(String(100), nullable=False)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)
    system_prompt = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AiChatSession(Base):
    __tablename__ = "ai_chat_session"

    id = get_id_column()
    title = Column(String(100), default="新对话")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    messages = relationship("AiChatMessage", back_populates="session", cascade="all, delete-orphan")


class AiChatMessage(Base):
    __tablename__ = "ai_chat_message"

    id = get_id_column()
    session_id = Column(Integer, ForeignKey("ai_chat_session.id", ondelete="CASCADE"))
    role = Column(String(20), nullable=False)  # user, assistant, tool
    content = Column(Text, nullable=False)
    tool_calls = Column(Text, nullable=True)   # JSON string
    created_at = Column(DateTime, default=datetime.now)

    session = relationship("AiChatSession", back_populates="messages")
