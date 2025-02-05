from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    firstname = Column(String, nullable=True)
    lastname = Column(String, nullable=True)
    password = Column(String, nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String, nullable=True)
    verification_code_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    access_tokens = relationship("AccessToken", back_populates="user")
    # Add this line to define the relationship with Role
    role = relationship("Role", back_populates="users")

    def __repr__(self):
        return f"<User {self.email}>"
    
class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))

    users = relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role {self.name}>"

class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(255), unique=True, nullable=False, index=True)
    client_secret = Column(String(255), nullable=False)
    redirect_uri = Column(Text, nullable=False)
    grant_types = Column(String(255), nullable=False)
    scope = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    access_tokens = relationship("AccessToken", back_populates="client")

    def __repr__(self):
        return f"<Client {self.client_id}>"

class AccessToken(Base):
    __tablename__ = "access_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(Text, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for client credentials flow
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    scopes = Column(Text)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="access_tokens")
    client = relationship("Client", back_populates="access_tokens")
    refresh_token = relationship("RefreshToken", back_populates="access_token", uselist=False)

    def __repr__(self):
        return f"<AccessToken {self.id}>"

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(Text, unique=True, nullable=False, index=True)
    access_token_id = Column(Integer, ForeignKey("access_tokens.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    access_token = relationship("AccessToken", back_populates="refresh_token")

    def __repr__(self):
        return f"<RefreshToken {self.id}>"

class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), unique=True, nullable=False, index=True)
    credit_balance = Column(Integer, default=3)

    def __repr__(self):
        return f"<GuestIpCredit {self.ip_address}>"