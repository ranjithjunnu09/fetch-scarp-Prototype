Web Retrieval Prototype (Search → Fetch → Scrape Pipeline)
---
A lightweight backend system that performs web search, HTML fetching, and content extraction to return clean, structured data from the internet.

This project represents the retrieval layer of a modern AI system (without LLMs or embeddings) and is designed as a foundational building block for systems like AI search engines and RAG pipelines.

- Features
 Web search using Serper API
 Fetch top web pages
 Clean content extraction using trafilatura + BeautifulSoup
 FastAPI-based API endpoint
 Structured JSON output
 Secure API key handling using .env
 Project Motivation

Modern AI systems (like AI search engines) rely heavily on retrieval pipelines before reasoning.

This project focuses only on:

Getting high-quality data from the web

Not on:

❌ LLM reasoning
❌ Embeddings
❌ Vector databases

🏗️ Architecture
---------------------------------------------------------------------------------------
🔄 High-Level Flow
User Query
   ↓
Search API (Serper)
   ↓
Top URLs
   ↓
HTML Fetching
   ↓
Content Extraction
   ↓
Clean Structured Output
----------------------------------------------------------------------------------------

Component Breakdown
1. Input Layer
Accepts user query via API
Example:
{
  "query": "AI agents future",
  "num_results": 5
}

2. Search Layer
Uses Serper API to fetch search results
Returns:
URL
Title
Snippet

4. Fetch Layer
Downloads raw HTML from each URL
Handles:
Timeouts
Basic headers (User-Agent)

5. Extraction Layer
Primary: trafilatura (clean extraction)
Fallback: BeautifulSoup
Removes:
Ads
Navigation
Scripts

6. Output Layer
Returns structured JSON
Saves results to output/results.json

📂 Project Structure
web_retrieval_prototype/
│
├── main.py              # FastAPI app (all logic)
├── requirements.txt     # Dependencies
├── .env                 # API key (not committed)
├── .gitignore
├── output/              # Auto-generated (ignored in Git)
└── venv/                # Virtual environment

- Tech Stack
FastAPI → API framework
requests → HTTP calls
BeautifulSoup → HTML parsing
trafilatura → content extraction
python-dotenv → environment variables
lxml → fast parsing backend



4. Setup Environment Variables
Create .env file:
SERPER_API_KEY=your_api_key_here

- API Usage
Endpoint:
POST /search
Request Body:
{
  "query": "AI agents future",
  "num_results": 10
}
Response:
{
  "query": "AI agents future",
  "results": [
    {
      "url": "...",
      "title": "...",
      "snippet": "...",
      "content": "clean extracted text..."
    }
  ]
}

📁 Output
Results are saved automatically to:
output/results.json
