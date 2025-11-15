from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages_sent = relationship('Message', back_populates='sender', foreign_keys='Message.sender_id')
    messages_received = relationship('Message', back_populates='recipient', foreign_keys='Message.recipient_id')

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey('users.id'))
    recipient_id = Column(Integer, ForeignKey('users.id'))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    sender = relationship('User', back_populates='messages_sent', foreign_keys=[sender_id])
    recipient = relationship('User', back_populates='messages_received', foreign_keys=[recipient_id])