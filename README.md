# Web Retrieval Pipeline

A Python project that performs web search, fetches page HTML, extracts readable text, and saves structured results to JSON.

## Overview

This project demonstrates a retrieval pipeline with object-oriented design. It uses a search engine implementation, web fetcher, content extractor, and JSON storage component.

The pipeline:
1. Queries the web using `SerperSearchEngine`
2. Fetches each search result page via `WebFetcher`
3. Extracts readable text content via `ContentExtractor`
4. Saves the final results to `output/results.json`

## Features

- Search using the Serper API
- Fetch web pages with user-agent headers
- Extract main article text from HTML
- Save structured output as JSON
- Object-oriented design using classes and abstraction
- Inheritance via abstract base classes for search and extraction
- Component composition in the retrieval pipeline

## Prerequisites

- Python 3.11+ (recommended)
- A valid Serper API key

## Setup

1. Clone or copy the repository files.
2. Create and activate a Python virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with your Serper API key:

```text
SERPER_API_KEY=your_serper_api_key_here
```

## File Structure

- `main.py` — main application file that builds and runs the retrieval pipeline
- `requirements.txt` — Python dependencies required by the project
- `output/results.json` — generated output file containing search results and extracted content
- `venv/` — local Python virtual environment (not committed in git)

## How It Works

### `main.py`

The main script is built from several object-oriented components:

- `Document` — model representing a result with `url`, `title`, `snippet`, and `content`
- `BaseSearchEngine` / `SerperSearchEngine` — abstract base class and concrete search implementation
- `WebFetcher` — downloads HTML pages using `requests`
- `BaseExtractor` / `ContentExtractor` — abstract extraction interface with concrete logic and fallback behavior
- `JSONStorage` — writes final output to `output/results.json`
- `RetrievalPipeline` — combines all components and executes the workflow

### Execution Flow

1. User enters a search query.
2. `SerperSearchEngine.search()` retrieves top search results.
3. `WebFetcher.fetch()` downloads each page.
4. `ContentExtractor.extract()` parses and extracts text.
5. Results are saved to `output/results.json`.

## Usage

Run the script from the project root:

```powershell
python main.py
```

Then enter your search query when prompted.

Example:

```text
Enter your query: Tell me about agentic ai
```

After completion, check `output/results.json` for the saved results.

## Output Format

The output JSON includes:

- `query` — the search input
- `results` — list of extracted documents
  - `url`
  - `title`
  - `snippet`
  - `content`

## Dependencies

- `requests` — HTTP requests for API calls and page downloads
- `beautifulsoup4` — HTML parsing fallback
- `python-dotenv` — loads environment variables from `.env`
- `lxml` — HTML parser for BeautifulSoup
- `trafilatura` — content extraction from HTML

## Notes and Recommendations

- Keep the Serper API key private and never commit it to source control.
- Add unit tests for the search, fetch, extract, and storage components.
- Consider adding command-line arguments for query, output path, and number of results.
- Add retry logic and better error handling for network and API failures.

## Improvements

Potential next steps:

- Add CLI options for query, result count, and output file
- Add retries and exponential backoff for HTTP requests
- Replace `print()` statements with structured logging
- Add support for multiple search engine backends
- Add automated tests for components

## License

This project is provided as-is for demonstration and learning purposes.
