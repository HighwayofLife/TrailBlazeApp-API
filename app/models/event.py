from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, JSON, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from .base import Base
from sqlalchemy.dialects.postgresql import JSONB

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    location = Column(String(255), nullable=False)
    date_start = Column(DateTime, nullable=False, index=True)
    date_end = Column(DateTime, nullable=True)
    organizer = Column(String(255), nullable=True)
    website = Column(String(512), nullable=True)
    flyer_url = Column(String(512), nullable=True)
    region = Column(String(100), nullable=True, index=True)
    distances = Column(ARRAY(String), nullable=True)
    
    # Core structured fields
    ride_manager = Column(String, nullable=True)
    manager_contact = Column(String, nullable=True)
    event_type = Column(String, nullable=True)
    
    # Semi-structured flexible data
    event_details = Column(JSONB, nullable=True)
    
    # General notes field
    notes = Column(Text, nullable=True)
    
    # External reference
    external_id = Column(String, nullable=True)
    
    # Manager details
    manager_email = Column(String, nullable=True)
    manager_phone = Column(String, nullable=True)
    
    # Additional AERC fields
    judges = Column(ARRAY(String), nullable=True)
    directions = Column(Text, nullable=True)
    map_link = Column(String, nullable=True)
    
    # Timestamps and metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    is_canceled = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    source = Column(String(255))
    
    # Relationships
    announcements = relationship("Announcement", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Event {self.name}>"

class Announcement(Base):
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(255))  # Where this announcement was scraped from
    is_important = Column(Boolean, default=False)
    
    # Relationship
    event = relationship("Event", back_populates="announcements")
