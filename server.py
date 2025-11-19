from typing import Any, List, Dict, Optional
import logging
import os
import uvicorn
from mcp.server.fastmcp import FastMCP
from search import AuthorSearchEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server for HTTP transport
# Port will be set from environment variable when running
mcp = FastMCP("authorProfile")

# Initialize search engine
search_engine = AuthorSearchEngine()

# Add health check endpoint for Smithery
# Note: Health check will be handled by FastMCP's built-in capabilities

@mcp.tool()
async def get_coauthors(
    name: str,
    surname: str,
    institution: Optional[str] = None,
    field: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get all co-authors for a given author.
    
    Args:
        name: Author's first name
        surname: Author's last name
        institution: Optional institution affiliation
        field: Optional research field
    
    Returns:
        Dictionary containing co-authors list with their information
    """
    try:
        logger.info(f"Searching co-authors for {name} {surname}")
        
        # Search for author and get co-authors
        coauthors = await search_engine.get_coauthors(
            name=name,
            surname=surname,
            institution=institution,
            field=field
        )
        
        return {
            "success": True,
            "author": f"{name} {surname}",
            "institution": institution,
            "total_coauthors": len(coauthors),
            "coauthors": coauthors
        }
        
    except Exception as e:
        logger.error(f"Error getting co-authors: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "coauthors": []
        }

@mcp.tool()
async def get_author_keywords(
    name: str,
    surname: str,
    institution: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get research keywords/areas for a given author from Google Scholar.
    
    Args:
        name: Author's first name
        surname: Author's last name
        institution: Optional institution affiliation
    
    Returns:
        Dictionary containing keywords extracted from Google Scholar
    """
    try:
        logger.info(f"Searching keywords for {name} {surname} on Google Scholar")
        
        keywords = await search_engine.get_author_keywords_from_scholar(
            name=name,
            surname=surname,
            institution=institution
        )
        
        return {
            "success": True,
            "author": f"{name} {surname}",
            "institution": institution,
            "source": "Google Scholar",
            "total_keywords": len(keywords),
            "keywords": keywords
        }
        
    except Exception as e:
        logger.error(f"Error getting keywords from Google Scholar: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "keywords": []
        }

if __name__ == "__main__":
    # Get transport mode from environment
    transport = os.getenv("TRANSPORT", "stdio")
    
    if transport == "http":
        # HTTP mode for Smithery deployment
        port = int(os.getenv("PORT", 8081))
        host = os.getenv("HOST", "0.0.0.0")
        
        logger.info(f"Starting HTTP server on {host}:{port}")
        # Access the FastAPI app instance from FastMCP
        app = mcp.streamable_http_app
        uvicorn.run(app, host=host, port=port)
    else:
        # STDIO mode for local development
        logger.info("Starting STDIO server")
        mcp.run()