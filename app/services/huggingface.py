"""Hugging Face API integration for text summarization."""
import httpx
from app.config import get_settings
from typing import Optional

settings = get_settings()


async def summarize_text(text: str, max_length: int = 150) -> Optional[str]:
    """
    Summarize text using Hugging Face API.
    
    Args:
        text: Text to summarize
        max_length: Maximum length of summary
        
    Returns:
        Summarized text or None if error occurs
    """
    if not settings.hf_api_token:
        # Return truncated text if no API token
        return text[:max_length] + "..." if len(text) > max_length else text
    
    api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    headers = {"Authorization": f"Bearer {settings.hf_api_token}"}
    
    payload = {
        "inputs": text,
        "parameters": {
            "max_length": max_length,
            "min_length": 30,
            "do_sample": False
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("summary_text", text[:max_length])
            
            return text[:max_length]
    except Exception as e:
        print(f"Error summarizing text: {e}")
        return text[:max_length] + "..."
