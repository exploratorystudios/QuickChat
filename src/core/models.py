from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    model_name = Column(String(100), nullable=True)
    is_pinned = Column(Boolean, default=False)
    
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Chat(id={self.id}, title='{self.title}')>"

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=False)
    role = Column(String(50), nullable=False) # user, assistant, system
    content = Column(Text, nullable=False)
    thinking = Column(Text, nullable=True, default=None) # Thinking content from model
    content_type = Column(String(50), default='text') # text, code, etc.
    images = Column(Text, nullable=True, default=None) # JSON array of image metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', length={len(self.content)})>"
