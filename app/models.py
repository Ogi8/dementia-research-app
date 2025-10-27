"""Data models for the application."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ResearchArticle(BaseModel):
    """Research article model."""
    
    id: str
    title: str
    summary: str
    publication_date: datetime
    authors: List[str] = []
    url: Optional[str] = None
    source: str = "PubMed"


class Treatment(BaseModel):
    """Treatment information model."""
    
    id: str
    name: str
    description: str
    status: str  # "approved", "clinical_trial", "research"
    approval_date: Optional[datetime] = None
    url: Optional[str] = None
    source: str = "Clinical Trial"


class SummarizeRequest(BaseModel):
    """Request model for text summarization."""
    
    text: str = Field(..., min_length=50, max_length=10000)
    max_length: int = Field(default=150, ge=50, le=500)


class SummarizeResponse(BaseModel):
    """Response model for text summarization."""
    
    original_text: str
    summary: str


class TranslateRequest(BaseModel):
    """Request model for translation."""
    
    text: str = Field(..., min_length=1, max_length=10000)
    target_language: str = Field(..., pattern="^(EN|DE|FR|ES|IT|HR)$")


class TranslateResponse(BaseModel):
    """Response model for translation."""
    
    original_text: str
    translated_text: str
    source_language: str
    target_language: str


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    timestamp: datetime
