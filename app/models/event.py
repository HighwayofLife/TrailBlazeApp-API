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
    date_start = Column(DateTime, nullable=False, index=True)  # Changed from start_date to match schema
    date_end = Column(DateTime, nullable=False)               # Changed from end_date to match schema
    location_name = Column(String(255), nullable=False)
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100), default="USA")
    latitude = Column(Float)
    longitude = Column(Float)
    organization = Column(String(100))  # AERC, PNER, EDRA, etc.
    
    # Event details
    distances = Column(ARRAY(String), nullable=True)  # Array of available distances e.g. [25, 50, 100]
    requirements = Column(JSON)  # Any special requirements/rules
    flyer_url = Column(String(512), nullable=True)  # URL to the ride flyer PDF or image
    website_url = Column(String(512), nullable=True)  # Event or ride manager's website
    contact_name = Column(String(255))
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    
    # Core structured fields to add (universal across event types)
    ride_manager = Column(String, nullable=True)
    manager_contact = Column(String, nullable=True)  # General contact info
    event_type = Column(String, nullable=True)  # AERC, EDRA, CTR, etc.
    
    # Semi-structured flexible data (varies by event type)
    event_details = Column(JSONB, nullable=True)  # Store type-specific structured data
    
    # General notes field (completely unstructured)
    notes = Column(Text, nullable=True)  # For any additional information
    
    # External reference
    external_id = Column(String, nullable=True)  # For the "tag" from source system
    
    # Timestamps and metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    is_canceled = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    source = Column(String(255))  # Where this info was scraped from
    
    # Relationships
    announcements = relationship("Announcement", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Event {self.id}: {self.name}>"

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
