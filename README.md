# Academic Author Network MCP Server
[![smithery badge](https://smithery.ai/badge/@alperenkocyigit/authorprofilemcp)](https://smithery.ai/server/@alperenkocyigit/authorprofilemcp)

A Model Context Protocol (MCP) server for analyzing academic author networks and research collaborations.

## Features

- **get_coauthors**: Find all co-authors for a given researcher
- **get_author_keywords**: Extract research keywords and areas from publications  
- **get_second_degree_network**: Discover second-degree connections (co-authors of co-authors)

## Installation

### Installing via Smithery

To install authorprofilemcp for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@alperenkocyigit/authorprofilemcp):

```bash
npx -y @smithery/cli install @alperenkocyigit/authorprofilemcp --client claude
```

### Manual Installation
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

#### Getting Research Keywords
```python
keywords = await get_author_keywords(
    name="Yann",
    surname="LeCun"
)
```

#### Analyzing Second-Degree Network
```python
network = await get_second_degree_network(
    name="Yann",
    surname="LeCun",
    max_connections=50  # Optional, default 50
)
```

## Data Sources

The server aggregates data from multiple academic APIs:

- **Semantic Scholar API**: Primary source for author and publication data
- **OpenAlex API**: Open academic knowledge graph
- **Crossref API**: DOI resolution and metadata
- **arXiv API**: Preprint server data
- **PubMed API**: Biomedical literature (future enhancement)

## Features

- **Rate Limiting**: Respects API rate limits
- **Caching**: Reduces redundant API calls
- **Error Handling**: Graceful handling of API failures
- **Data Merging**: Combines data from multiple sources
- **Async Operations**: Parallel API requests for better performance

## Configuration

The server includes built-in rate limiting and error handling. No additional configuration is required for basic usage.

## Limitations

- Free tier API limits apply
- Some APIs may require registration for higher rate limits
- Google Scholar scraping is not implemented due to anti-bot measures
- Results quality depends on author name uniqueness

## Contributing

Contributions are welcome! Please ensure all API integrations respect rate limits and terms of service.
