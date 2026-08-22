import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Date, DateTime, Text, ForeignKey, Numeric, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(String(50), default="starter")
    settings = Column(JSONB, default=dict)
    branding = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    users = relationship("User", back_populates="tenant")
    profiles = relationship("Profile", back_populates="tenant")

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id = Column(String(255), unique=True, nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    hashed_password = Column(String(255), nullable=True)
    role = Column(String(50), default="user")
    avatar_url = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    tenant = relationship("Tenant", back_populates="users")
    evaluations = relationship("Evaluation", back_populates="evaluator")

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    code = Column(String(50), unique=True)
    full_name = Column(String(255), nullable=False)
    artistic_name = Column(String(255))
    birth_date = Column(Date)
    gender = Column(String(50))
    height_cm = Column(Integer)
    weight_kg = Column(Numeric(5, 2))
    eye_color = Column(String(50))
    hair_color = Column(String(50))
    skin_tone = Column(String(50))
    body_type = Column(String(50))
    shoe_size = Column(String(20))
    dress_size = Column(String(20))
    pants_size = Column(String(20))
    shirt_size = Column(String(20))
    languages = Column(ARRAY(String))
    skills = Column(ARRAY(String))
    experience_years = Column(Integer)
    bio = Column(Text)
    instagram = Column(String(100))
    portfolio_url = Column(Text)
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    tenant = relationship("Tenant", back_populates="profiles")
    photoshoots = relationship("Photoshoot", back_populates="profile")
    analyses = relationship("Analysis", back_populates="profile")
    reports = relationship("Report", back_populates="profile")

class Photoshoot(Base):
    __tablename__ = "photoshoots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    photographer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    title = Column(String(255))
    type = Column(String(50))
    date = Column(Date)
    location = Column(String(255))
    notes = Column(Text)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    profile = relationship("Profile", back_populates="photoshoots")
    photos = relationship("Photo", back_populates="photoshoot")
    analyses = relationship("Analysis", back_populates="photoshoot")
    reports = relationship("Report", back_populates="photoshoot")

class Photo(Base):
    __tablename__ = "photos"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    photoshoot_id = Column(UUID(as_uuid=True), ForeignKey("photoshoots.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    url = Column(Text, nullable=False)
    thumbnail_url = Column(Text)
    angle = Column(String(50))
    format = Column(String(20))
    file_size_bytes = Column(Integer)
    dimensions = Column(String(50))
    color_space = Column(String(50))
    _metadata = Column(JSONB, default=dict)
    analysis_status = Column(String(50), default="pending")
