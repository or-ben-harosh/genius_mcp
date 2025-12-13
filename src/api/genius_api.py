"""
Enhanced Genius API Client - Annotations and search
"""

import json
import logging
import httpx
from ..utils.utils import APIError
from ..core.config import GENIUS_BASE_URL, SCRAPING_TIMEOUT

logger = logging.getLogger(__name__)

class GeniusAPI:
    """Enhanced Genius API client for annotation lookups and search."""
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Genius-MCP-Server/1.0"
        }
    
    async def get_annotation_explanation(self, annotation_id: str) -> str:
        """
        Get annotation explanation by ID.
        
        Args:
            annotation_id: The annotation ID (e.g., "2310153")
        
        Returns:
            JSON with annotation details
        """
        try:
            async with httpx.AsyncClient(timeout=SCRAPING_TIMEOUT) as client:
                response = await client.get(
                    f"{GENIUS_BASE_URL}/referents/{annotation_id}",
                    headers=self.headers,
                    params={"text_format": "plain"}
                )
                
                if response.status_code == 404:
                    raise APIError(f"Annotation ID {annotation_id} not found")
                
                if response.status_code == 429:
                    raise APIError("Rate limit exceeded. Please try again later")
                
                if response.status_code != 200:
                    raise APIError(f"API error: status {response.status_code}")
                
                data = response.json()
                referent = data.get("response", {}).get("referent", {})
                
                if not referent:
                    raise APIError("No data returned from API")
                
                lyric = referent.get("fragment", "")
                annotations = referent.get("annotations", [])
                
                if not annotations:
                    explanation = "No explanation available"
                else:
                    explanation = annotations[0].get("body", {}).get("plain", "No explanation available")
                
                result = {
                    "annotation_id": annotation_id,
                    "lyric": lyric,
                    "explanation": explanation,
                    "success": True,
                    "url": f"https://genius.com/annotations/{annotation_id}"
                }
                
                return json.dumps(result, indent=2, ensure_ascii=False)
                
        except httpx.HTTPError as e:
            raise APIError(f"Network error: {str(e)}")
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Failed to get annotation: {str(e)}")
    
    async def search_songs(self, query: str, limit: int = 5) -> str:
        """
        Search for songs on Genius.
        
        Args:
            query: Search query
            limit: Number of results (1-20)
        
        Returns:
            JSON with search results
        """
        try:
            async with httpx.AsyncClient(timeout=SCRAPING_TIMEOUT) as client:
                response = await client.get(
                    f"{GENIUS_BASE_URL}/search",
                    headers=self.headers,
                    params={
                        "q": query,
                        "per_page": limit
                    }
                )
                
                if response.status_code == 429:
                    raise APIError("Rate limit exceeded. Please try again later")
                
                if response.status_code != 200:
                    raise APIError(f"Search failed: status {response.status_code}")
                
                data = response.json()
                hits = data.get("response", {}).get("hits", [])
                
                results = []
                for hit in hits:
                    song = hit.get("result", {})
                    results.append({
                        "id": song.get("id"),
                        "title": song.get("title", ""),
                        "artist": song.get("primary_artist", {}).get("name", ""),
                        "url": song.get("url", ""),
                        "lyrics_state": song.get("lyrics_state", ""),
                        "has_lyrics": song.get("lyrics_state") == "complete"
                    })
                
                return json.dumps({
                    "query": query,
                    "results_count": len(results),
                    "results": results,
                    "success": True
                }, indent=2, ensure_ascii=False)
                
        except httpx.HTTPError as e:
            raise APIError(f"Network error: {str(e)}")
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Search failed: {str(e)}")