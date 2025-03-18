"""
Core schema definitions for TrailBlazeApp API.

This module contains the central schema definitions for the entire application.
All data structures should be defined here to ensure consistency across the codebase.
"""

# Import and expose main schemas
from .event import (
    # Core event schemas
    EventBase, EventCreate, EventUpdate, EventResponse, EventDetail, EventListResponse,
    # Component schemas
    EventDistance, ControlJudge, LocationDetails, Coordinates, ContactInfo,
    # Source-specific schemas
    AERCEvent, SERAEvent, UMECRAEvent,
    # Enums
    EventSourceEnum, EventTypeEnum, RegionEnum,
    # Utility functions
    validate_event, SOURCE_SCHEMAS,
    # Announcements
    AnnouncementBase, AnnouncementCreate, Announcement
)
from .scraper import ScraperResponse, ScraperRun
from .ai import QuestionRequest, AnswerResponse

# Indicate which schemas are publicly available
__all__ = [
    # Event schemas
    'EventBase', 'EventCreate', 'EventUpdate', 'EventResponse', 'EventDetail', 'EventListResponse',
    # Component schemas
    'EventDistance', 'ControlJudge', 'LocationDetails', 'Coordinates', 'ContactInfo',
    # Source-specific schemas
    'AERCEvent', 'SERAEvent', 'UMECRAEvent',
    # Enums
    'EventSourceEnum', 'EventTypeEnum', 'RegionEnum',
    # Utility functions
    'validate_event', 'SOURCE_SCHEMAS',
    
    # Announcement schemas
    'AnnouncementBase', 'AnnouncementCreate', 'Announcement',
    
    # Scraper schemas
    'ScraperResponse', 'ScraperRun',
    
    # AI schemas
    'QuestionRequest', 'AnswerResponse'
]
