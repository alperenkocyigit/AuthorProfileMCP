[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/alperenkocyigit-authorprofilemcp-badge.png)](https://mseep.ai/app/alperenkocyigit-authorprofilemcp)

# Academic Author Network MCP Server

A Model Context Protocol (MCP) server for analyzing academic author networks and research collaborations.

## Features

- **get_coauthors**: Find all co-authors for a given researcher
- **get_author_keywords**: Extract research keywords from Google Scholar profile

## Installation

1. Clone or download this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Server

```bash
python server.py
```

### Example Tool Calls

#### Finding Co-authors
```python
result = await get_coauthors(
    name="Yann", 
    surname="LeCun",
    institution="NYU"  # Optional
)
```

#### Getting Research Keywords from Google Scholar
```python
keywords = await get_author_keywords(
    name="Yann",
    surname="LeCun"
)
```

## Data Sources

The server uses:

- **Semantic Scholar API**: Primary source for author and publication data
- **OpenAlex API**: Open academic knowledge graph  
- **Crossref API**: DOI resolution and metadata
- **Google Scholar**: Web scraping for research interests and keywords

## Features

- **Rate Limiting**: Respects API rate limits and includes delays for web scraping
- **Caching**: Reduces redundant API calls and scraping requests
- **Error Handling**: Graceful handling of API failures and scraping issues
- **Data Merging**: Combines data from multiple sources for co-authors
- **Async Operations**: Parallel API requests for better performance

## Configuration

The server includes built-in rate limiting and error handling. No additional configuration is required for basic usage.

## Limitations

- Free tier API limits apply
- Google Scholar scraping includes respectful delays
- Results quality depends on author name uniqueness
- Web scraping may occasionally fail due to anti-bot measures

## Contributing

Contributions are welcome! Please ensure all API integrations respect rate limits and terms of service.
