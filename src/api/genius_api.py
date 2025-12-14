"""
Enhanced Genius API Client - Annotations and search
"""

import json
import logging
import httpx
from core.config import GENIUS_BASE_URL, SCRAPING_TIMEOUT, MAX_SEARCH_RESULTS

logger = logging.getLogger(__name__)

class GeniusAPI:
    """Genius API client for annotation lookups and search."""
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Genius-MCP-Server/1.0"
        }
    
    async def get_annotation_explanation(self, annotation_id: str) -> str:
        """
        Get annotation explanation by ID.
        
        Enhanced with better validation and error handling for batch processing.

        Args:
            annotation_id: The annotation ID as string (e.g., "2310153")

        Returns:
            JSON with annotation details including success flag
        """
        # Input validation
        if not annotation_id or not annotation_id.strip():
            logger.error("Annotation ID cannot be empty")
            raise ValueError("Annotation ID cannot be empty")

        annotation_id = annotation_id.strip()

        # Validate ID format (should be numeric)
        if not annotation_id.isdigit():
            logger.error(f"Invalid annotation ID format: {annotation_id}")
            raise ValueError(f"Annotation ID must be numeric, got: {annotation_id}")

        try:
            logger.debug(f"Fetching annotation {annotation_id} from Genius API")

            async with httpx.AsyncClient(timeout=SCRAPING_TIMEOUT) as client:
                response = await client.get(
                    f"{GENIUS_BASE_URL}/referents/{annotation_id}",
                    headers=self.headers,
                    params={"text_format": "plain"}
                )
                
                # Enhanced error handling with specific messages
                if response.status_code == 404:
                    logger.warning(f"Annotation ID {annotation_id} not found (404)")
                    raise ValueError(f"Annotation ID {annotation_id} not found")

                if response.status_code == 429:
                    logger.warning(f"Rate limit exceeded for annotation {annotation_id} (429)")
                    raise ConnectionError("Rate limit exceeded. Please try again later")

                if response.status_code == 403:
                    logger.warning(f"Access forbidden for annotation {annotation_id} (403)")
                    raise PermissionError("Access forbidden - API key may be invalid")

                if response.status_code != 200:
                    logger.error(f"API error for annotation {annotation_id}: status {response.status_code}")
                    raise RuntimeError(f"API error: HTTP {response.status_code}")

                # Parse response
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response for annotation {annotation_id}: {e}")
                    raise RuntimeError("Invalid response format from Genius API")

                referent = data.get("response", {}).get("referent", {})
                
                if not referent:
                    logger.warning(f"No referent data returned for annotation ID {annotation_id}")
                    raise RuntimeError("No annotation data found in API response")

                # Extract annotation details
                lyric = referent.get("fragment", "").strip()
                annotations = referent.get("annotations", [])
                
                if not annotations:
                    explanation = "No explanation available for this annotation"
                    logger.info(f"No explanation found for annotation {annotation_id}")
                else:
                    explanation = annotations[0].get("body", {}).get("plain", "No explanation available")
                    if not explanation or explanation.strip() == "":
                        explanation = "Explanation is empty"

                # Build result with enhanced metadata
                result = {
                    "annotation_id": annotation_id,
                    "lyric": lyric,
                    "explanation": explanation.strip() if explanation else "No explanation available",
                    "success": True,
                    "url": f"https://genius.com/annotations/{annotation_id}",
                    "has_explanation": bool(explanation and explanation.strip()),
                    "annotation_count": len(annotations)
                }
                
                logger.info(f"Successfully fetched annotation {annotation_id}")
                return json.dumps(result, indent=2, ensure_ascii=False)
                
        except httpx.TimeoutException:
            logger.error(f"Timeout while fetching annotation {annotation_id}")
            raise TimeoutError(f"Request timed out after {SCRAPING_TIMEOUT}s")

        except httpx.ConnectError as e:
            logger.error(f"Connection error for annotation {annotation_id}: {e}")
            raise ConnectionError("Failed to connect to Genius API - check internet connection")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error for annotation {annotation_id}: {e}")
            raise ConnectionError(f"Network error: {str(e)}")

        except (ValueError, PermissionError, TimeoutError, ConnectionError, RuntimeError):
            # Re-raise our custom exceptions as-is
            raise

        except Exception as e:
            logger.error(f"Unexpected error fetching annotation {annotation_id}: {e}", exc_info=True)
            raise RuntimeError(f"Unexpected error: {str(e)}")


    async def search_songs(self, query: str, limit: int = MAX_SEARCH_RESULTS) -> str:
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
                    logger.error(f"Rate limit exceeded for search query: {query}")
                    raise ConnectionError(f"Rate limit exceeded for search query: {query}")

                if response.status_code != 200:
                    logger.error(f"Search failed: status {response.status_code}")
                    raise RuntimeError(f"Search failed: status {response.status_code}")

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
            logger.error(f"Network error during search for query '{query}': {str(e)}")
            raise ConnectionError(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            raise RuntimeError(f"Search failed: {str(e)}")