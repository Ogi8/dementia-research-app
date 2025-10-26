"""Main FastAPI application."""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from datetime import datetime
from typing import List
import os

from app.config import get_settings
from app.models import (
    ResearchArticle,
    Treatment,
    TranslateRequest,
    TranslateResponse,
    HealthResponse
)
from app.services.research import get_latest_research, get_latest_treatments
from app.services.translator import translate_text
from app.services.cache import get_cached, set_cached

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API for dementia research and treatment information with summarization and translation capabilities"
)

# Mount static files - languages directory needs to be accessible
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_path):
    # Mount languages directory for multilingual pages
    languages_path = os.path.join(static_path, "languages")
    if os.path.exists(languages_path):
        app.mount("/languages", StaticFiles(directory=languages_path, html=True), name="languages")
    
    # Mount general static files
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Redirect to English version of the multilingual site."""
    multilang_path = os.path.join(os.path.dirname(__file__), "..", "static", "index_multilang.html")
    if os.path.exists(multilang_path):
        return FileResponse(multilang_path)
    
    # Fallback to original dynamic page
    html_path = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return HTMLResponse(content="<h1>Welcome to Dementia Research Information</h1>")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.now()
    )


@app.get("/api/news", response_model=List[ResearchArticle])
async def get_news():
    """
    Get latest research news articles.
    Results are cached for improved performance.
    """
    cache_key = "news_articles"
    cached_data = get_cached(cache_key)
    
    if cached_data:
        return cached_data
    
    articles = await get_latest_research()
    set_cached(cache_key, articles)
    
    return articles


@app.get("/api/treatments", response_model=List[Treatment])
async def get_treatments():
    """
    Get latest treatment information.
    Results are cached for improved performance.
    """
    cache_key = "treatments"
    cached_data = get_cached(cache_key)
    
    if cached_data:
        return cached_data
    
    treatments = await get_latest_treatments()
    set_cached(cache_key, treatments)
    
    return treatments


@app.post("/api/translate", response_model=TranslateResponse)
async def translate(request: TranslateRequest):
    """
    Translate text using Google Translate (free).
    
    Args:
        request: Text and target language for translation
        
    Returns:
        Original text, translated text, and language information
    """
    # Check cache first
    cache_key = f"translation_{hash(request.text)}_{request.target_language}"
    cached_translation = get_cached(cache_key)
    
    if cached_translation:
        return cached_translation
    
    # Translate text
    result = await translate_text(request.text, request.target_language.lower())
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to translate text")
    
    translated_text, source_lang = result
    
    response = TranslateResponse(
        original_text=request.text,
        translated_text=translated_text,
        source_language=source_lang,
        target_language=request.target_language.lower()
    )
    
    # Cache the result
    set_cached(cache_key, response)
    
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
