import asyncio
import aiohttp
import ssl
import json
import time
import hashlib
import re
from typing import Dict, List, Optional, Any, Set, Tuple
from urllib.parse import quote
from bs4 import BeautifulSoup
import logging
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class AuthorSearchEngine:
    """
    Academic author search engine that aggregates data from multiple sources.
    """
    
    def __init__(self):
        self.session = None
        self.cache = {}
        self.rate_limits = {
            'semantic_scholar': {'calls': 0, 'reset_time': time.time()},
            'openalex': {'calls': 0, 'reset_time': time.time()},
            'crossref': {'calls': 0, 'reset_time': time.time()},
            'arxiv': {'calls': 0, 'reset_time': time.time()},
            'pubmed': {'calls': 0, 'reset_time': time.time()}
        }
        
    async def __aenter__(self):
        # Create SSL context that handles certificate issues
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Configure timeout settings
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        # Create connector with SSL context
        connector = aiohttp.TCPConnector(
            ssl=ssl_context,
            limit=100,
            limit_per_host=10,
            enable_cleanup_closed=True
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        return hashlib.md5(str(args).encode()).hexdigest()

    async def _rate_limit_check(self, api_name: str, max_calls: int = 100, window: int = 3600):
        """Check and enforce rate limits."""
        now = time.time()
        if now - self.rate_limits[api_name]['reset_time'] > window:
            self.rate_limits[api_name] = {'calls': 0, 'reset_time': now}
        
        if self.rate_limits[api_name]['calls'] >= max_calls:
            sleep_time = window - (now - self.rate_limits[api_name]['reset_time'])
            if sleep_time > 0:
                await asyncio.sleep(min(sleep_time, 60))  # Cap at 1 minute
        
        self.rate_limits[api_name]['calls'] += 1

    async def _make_request(self, url: str, headers: Dict = None) -> Optional[Dict]:
        """Make HTTP request with error handling."""
        if not self.session:
            # Create session with SSL context if not exists
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                ssl=ssl_context,
                limit=100,
                limit_per_host=10,
                enable_cleanup_closed=True
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
            
        try:
            async with self.session.get(url, headers=headers or {}) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Request failed: {url} - Status: {response.status}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout error for {url}")
            return None
        except aiohttp.ClientSSLError as e:
            logger.error(f"SSL error for {url}: {str(e)}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Client error for {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {str(e)}")
            return None

    async def _search_semantic_scholar(self, name: str, surname: str) -> List[Dict]:
        """Search Semantic Scholar API."""
        await self._rate_limit_check('semantic_scholar', 100)
        
        query = f"{name} {surname}"
        url = f"https://api.semanticscholar.org/graph/v1/author/search?query={quote(query)}&fields=authorId,name,affiliations,papers,papers.title,papers.authors,papers.venue,papers.year"
        
        data = await self._make_request(url)
        if data and 'data' in data:
            return data['data']
        return []

    async def _search_openalex(self, name: str, surname: str, institution: Optional[str] = None) -> List[Dict]:
        """Search OpenAlex API."""
        await self._rate_limit_check('openalex', 100)
        
        query = f"{name} {surname}"
        if institution:
            query += f" {institution}"
            
        url = f"https://api.openalex.org/authors?search={quote(query)}&per-page=10"
        
        data = await self._make_request(url)
        if data and 'results' in data:
            return data['results']
        return []

    async def _search_crossref(self, name: str, surname: str) -> List[Dict]:
        """Search Crossref API."""
        await self._rate_limit_check('crossref', 100)
        
        query = f"{name} {surname}"
        url = f"https://api.crossref.org/works?query.author={quote(query)}&rows=50"
        
        data = await self._make_request(url)
        if data and 'message' in data and 'items' in data['message']:
            return data['message']['items']
        return []

    async def _search_arxiv(self, name: str, surname: str) -> List[Dict]:
        """Search arXiv API."""
        await self._rate_limit_check('arxiv', 30)
        
        query = f"au:\"{name} {surname}\""
        url = f"http://export.arxiv.org/api/query?search_query={quote(query)}&start=0&max_results=50"
        
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    # Parse XML content (simplified)
                    return [{'source': 'arxiv', 'content': content}]
        except Exception as e:
            logger.error(f"ArXiv search error: {str(e)}")
        
        return []

    def _normalize_author_name(self, name: str) -> str:
        """Normalize author names for comparison."""
        return ' '.join(name.lower().split())

    def _extract_coauthors_from_semantic_scholar(self, author_data: Dict) -> List[Dict]:
        """Extract co-authors from Semantic Scholar data."""
        coauthors = {}
        
        if 'papers' in author_data:
            for paper in author_data['papers']:
                if 'authors' in paper:
                    for author in paper['authors']:
                        if author.get('name'):
                            name = self._normalize_author_name(author['name'])
                            if name not in coauthors:
                                coauthors[name] = {
                                    'name': author['name'],
                                    'id': author.get('authorId'),
                                    'collaborations': 0,
                                    'source': 'semantic_scholar'
                                }
                            coauthors[name]['collaborations'] += 1
        
        return list(coauthors.values())

    def _extract_coauthors_from_openalex(self, author_data: Dict) -> List[Dict]:
        """Extract co-authors from OpenAlex data."""
        coauthors = {}
        
        # This would require additional API calls to get works
        # For now, return basic structure
        return []

    def _merge_author_data(self, data_sources: List[Tuple[str, List[Dict]]]) -> Dict:
        """Merge author data from multiple sources."""
        merged = {
            'names': set(),
            'institutions': set(),
            'papers': [],
            'coauthors': {},
            'keywords': Counter()
        }
        
        for source, data_list in data_sources:
            for item in data_list:
                if source == 'semantic_scholar':
                    if 'name' in item:
                        merged['names'].add(item['name'])
                    if 'affiliations' in item:
                        for aff in item['affiliations']:
                            merged['institutions'].add(aff.get('name', ''))
                    
                    coauthors = self._extract_coauthors_from_semantic_scholar(item)
                    for coauthor in coauthors:
                        name = coauthor['name']
                        if name not in merged['coauthors']:
                            merged['coauthors'][name] = coauthor
                        else:
                            merged['coauthors'][name]['collaborations'] += coauthor['collaborations']
        
        return merged

    async def get_coauthors(self, name: str, surname: str, institution: Optional[str] = None, field: Optional[str] = None) -> List[Dict]:
        """Get co-authors for a given author."""
        cache_key = self._get_cache_key('coauthors', name, surname, institution, field)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Search multiple sources in parallel
        tasks = [
            ('semantic_scholar', self._search_semantic_scholar(name, surname)),
            ('openalex', self._search_openalex(name, surname, institution)),
            ('crossref', self._search_crossref(name, surname)),
        ]
        
        results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
        data_sources = []
        
        for i, result in enumerate(results):
            if not isinstance(result, Exception) and result:
                data_sources.append((tasks[i][0], result))

        # Merge data from all sources
        merged_data = self._merge_author_data(data_sources)
        
        # Convert to final format
        coauthors = []
        for name, data in merged_data['coauthors'].items():
            coauthors.append({
                'name': data['name'],
                'collaborations': data['collaborations'],
                'source': data['source']
            })
        
        # Sort by collaboration count
        coauthors.sort(key=lambda x: x['collaborations'], reverse=True)
        
        self.cache[cache_key] = coauthors
        return coauthors

    async def get_author_keywords(self, name: str, surname: str, institution: Optional[str] = None) -> List[Dict]:
        """Get research keywords for a given author."""
        cache_key = self._get_cache_key('keywords', name, surname, institution)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Search semantic scholar for papers
        semantic_data = await self._search_semantic_scholar(name, surname)
        keywords = Counter()
        
        for author in semantic_data:
            if 'papers' in author:
                for paper in author['papers']:
                    title = paper.get('title', '')
                    venue = paper.get('venue', '')
                    
                    # Extract keywords from title and venue (simplified)
                    words = title.lower().split() + venue.lower().split()
                    # Filter out common words and short words
                    filtered_words = [w for w in words if len(w) > 3 and w not in ['the', 'and', 'for', 'with', 'from', 'that', 'this']]
                    keywords.update(filtered_words)

        # Convert to final format
        keyword_list = [
            {'keyword': word, 'frequency': count}
            for word, count in keywords.most_common(20)
        ]
        
        self.cache[cache_key] = keyword_list
        return keyword_list

    async def get_author_keywords_from_scholar(self, name: str, surname: str, institution: Optional[str] = None) -> List[str]:
        """Get research keywords for a given author from Google Scholar only."""
        cache_key = self._get_cache_key('scholar_keywords', name, surname, institution)
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # Step 1: Search for author and find their profile URL
            profile_url = await self._search_author_profile(name, surname, institution)
            
            # Small delay to be respectful
            await asyncio.sleep(2)
            
            # Step 2: Extract keywords from profile
            keywords = await self._extract_keywords_from_profile(profile_url)
            
            self.cache[cache_key] = keywords
            return keywords
            
        except Exception as e:
            logger.error(f"Error getting keywords from Google Scholar: {str(e)}")
            # Return fallback keywords based on other sources
            try:
                # Try to get keywords from other APIs as fallback
                fallback_keywords = await self.get_author_keywords(name, surname, institution)
                if fallback_keywords and isinstance(fallback_keywords, list):
                    extracted_keywords = [item.get('keyword', '') for item in fallback_keywords if isinstance(item, dict) and 'keyword' in item]
                    return extracted_keywords[:10]  # Limit to first 10
            except:
                pass
            return []

    async def _search_author_profile(self, name: str, surname: str, institution: str = None):
        """Step 1: Search for author and find their profile URL"""
        if not self.session:
            # Create session with SSL context if not exists
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                ssl=ssl_context,
                limit=100,
                limit_per_host=10,
                enable_cleanup_closed=True
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
            
        search_query = f"{name} {surname}"
        if institution:
            search_query += f" {institution}"
        
        search_url = f"https://scholar.google.com/scholar?q={quote(search_query)}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        try:
            async with self.session.get(search_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Search failed with status {response.status}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for citation profile links
                citation_links = soup.find_all('a', href=lambda x: x and 'citations?user=' in x)
                
                if not citation_links:
                    raise Exception("No author profile found in search results")
                
                # Get the first profile URL
                profile_href = citation_links[0].get('href')
                if profile_href.startswith('/'):
                    profile_url = 'https://scholar.google.com' + profile_href
                else:
                    profile_url = profile_href
                
                return profile_url
                
        except asyncio.TimeoutError:
            raise Exception("Google Scholar search timed out")
        except aiohttp.ClientSSLError as e:
            raise Exception(f"SSL connection error to Google Scholar: {str(e)}")
        except aiohttp.ClientError as e:
            raise Exception(f"Network error connecting to Google Scholar: {str(e)}")
        except Exception as e:
            if "profile found" in str(e) or "failed with status" in str(e):
                raise e
            else:
                raise Exception(f"Unexpected error searching Google Scholar: {str(e)}")

    async def _extract_keywords_from_profile(self, profile_url: str):
        """Step 2: Extract keywords from author's profile page"""
        if not self.session:
            # Create session with SSL context if not exists
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                ssl=ssl_context,
                limit=100,
                limit_per_host=10,
                enable_cleanup_closed=True
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        try:
            async with self.session.get(profile_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Profile page failed with status {response.status}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for interests/keywords section
                interests_div = soup.find('div', {'id': 'gsc_prf_int'})
                
                if not interests_div:
                    # Try alternative selectors
                    interests_div = soup.find('div', class_='gsc_prf_il')
                
                if not interests_div:
                    return []
                
                # Extract keyword links
                keyword_links = interests_div.find_all('a', class_='gsc_prf_inta')
                keywords = [link.get_text().strip() for link in keyword_links if link.get_text().strip()]
                
                return keywords
                
        except asyncio.TimeoutError:
            raise Exception("Google Scholar profile page timed out")
        except aiohttp.ClientSSLError as e:
            raise Exception(f"SSL connection error to Google Scholar profile: {str(e)}")
        except aiohttp.ClientError as e:
            raise Exception(f"Network error connecting to Google Scholar profile: {str(e)}")
        except Exception as e:
            if "failed with status" in str(e):
                raise e
            else:
                raise Exception(f"Unexpected error extracting keywords from profile: {str(e)}")

    async def _scrape_google_scholar(self, name: str, surname: str, institution: Optional[str] = None) -> List[Dict]:
        """Deprecated - use get_author_keywords_from_scholar instead"""
        keywords = await self.get_author_keywords_from_scholar(name, surname, institution)
        return [{'keyword': kw, 'source': 'google_scholar', 'frequency': 1} for kw in keywords]

    async def _scrape_scholar_profile(self, profile_url: str, headers: Dict) -> List[Dict]:
        """Deprecated - use _extract_keywords_from_profile instead"""
        keywords = await self._extract_keywords_from_profile(profile_url)
        return [{'keyword': kw, 'source': 'google_scholar', 'frequency': 1} for kw in keywords]
