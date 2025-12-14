"""
Genius Lyrics Web Scraper - Extracts lyrics with annotation IDs from HTML
"""

import logging
import re
import httpx
from bs4 import BeautifulSoup
from src.core.config import SCRAPING_TIMEOUT, SCRAPING_HEADERS

logger = logging.getLogger(__name__)


class LyricsScraper:
    """Scrapes lyrics from Genius HTML pages."""
    
    @staticmethod
    def build_song_url(song_name: str, artist_name: str) -> str:
        """Build Genius URL from song and artist names."""
        def clean(text: str) -> str:
            # Remove special characters
            text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
            # Convert to lowercase and replace spaces with hyphens
            text = text.strip().lower()
            text = re.sub(r'\s+', '-', text)
            # Capitalize first letter of each word
            parts = text.split('-')
            return '-'.join(word.capitalize() for word in parts if word)
        
        artist = clean(artist_name)
        song = clean(song_name)
        return f"https://genius.com/{artist}-{song}-lyrics"
    
    @staticmethod
    async def fetch_html(url: str) -> str:
        """Fetch HTML from URL."""
        async with httpx.AsyncClient(timeout=SCRAPING_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(url, headers=SCRAPING_HEADERS)
            response.raise_for_status()
            return response.text
    
    @staticmethod
    def parse_lyrics_with_ids(html: str) -> str:
        """Extract lyrics with annotation IDs from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for elem in soup.find_all(['button', 'div'], class_=re.compile(r'Translation|Dropdown|Contributor')):
            elem.decompose()
        
        # Find lyrics containers
        containers = soup.find_all('div', {'data-lyrics-container': 'true'})
        
        if not containers:
            logger.exception("No lyrics containers found in page")
            raise Exception("No lyrics found on page")
        
        lines = []
        
        for container in containers:
            for element in container.children:
                # Use NavigableString and Tag for type checking
                from bs4 import NavigableString, Tag
                if isinstance(element, NavigableString):
                    text = element.strip()
                    if text and text not in ['\n', ' ']:
                        lines.append(text)
                elif isinstance(element, Tag):
                    if element.name == 'br':
                        lines.append("")
                    elif element.name == 'a':
                        href = element.get('href', '')
                        text = element.get_text()
                        match = re.search(r'/(\d+)', href)
                        if match:
                            ann_id = match.group(1)
                            lines.append(f"{text} [ID: {ann_id}]")
                        else:
                            lines.append(text)
                    else:
                        text = element.get_text().strip()
                        if text:
                            lines.append(text)

        return '\n'.join(lines)
    
    @staticmethod
    def extract_title(html: str) -> str:
        """Extract song title from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        title_elem = soup.find('h1')
        if title_elem:
            return title_elem.get_text(strip=True)
        return "Unknown Song"
    
    @classmethod
    async def get_lyrics_with_ids(cls, song_name: str, artist_name: str) -> str:
        """
        Get lyrics with annotation IDs inline.
        
        Returns:
            Plain text lyrics with [ID: xxx] markers
        """
        try:
            url = cls.build_song_url(song_name, artist_name)
            html = await cls.fetch_html(url)
            title = cls.extract_title(html)
            lyrics = cls.parse_lyrics_with_ids(html)
            
            return f"{title}\n{'=' * 60}\n\n{lyrics}"
        except httpx.HTTPStatusError as e:
            url = cls.build_song_url(song_name, artist_name)
            if e.response.status_code == 403:
                logger.error(f"Access forbidden when accessing URL: {url} - Genius may be blocking requests")
                raise PermissionError(f"Access forbidden when accessing URL: {url} - Genius may be blocking requests")
            elif e.response.status_code == 404:
                logger.error(f"Song not found at URL: {url}")
                raise FileNotFoundError(f"Song not found at URL: {url}")
            elif e.response.status_code == 429:
                logger.error(f"Rate limited when accessing URL: {url}")
                raise ConnectionError(f"Rate limited when accessing URL: {url}")
            else:
                logger.error(f"HTTP error {e.response.status_code} when accessing URL: {url}")
                raise RuntimeError(f"HTTP error {e.response.status_code} when accessing URL: {url}")

        except httpx.TimeoutException:
            logger.error(f"Request timed out after {SCRAPING_TIMEOUT}s")
            raise TimeoutError(f"Request timed out after {SCRAPING_TIMEOUT}s")

        except httpx.ConnectError:
            logger.error("Failed to connect to Genius - check internet connection")
            raise ConnectionError("Failed to connect to Genius - check internet connection")

        except Exception as e:
            if "No lyrics found" in str(e):
                logger.error(f"No lyrics found for '{artist_name} - {song_name}'")
                raise ValueError(f"No lyrics found for '{artist_name} - {song_name}'")

            logger.error(f"Scraping failed: {str(e)}")
            raise RuntimeError(f"Scraping failed: {str(e)}")
