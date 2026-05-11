import os
import re
import sys
import asyncio
import aiohttp
import trafilatura

# Fix Windows cp1252 emoji encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from bs4 import BeautifulSoup
from urllib.parse import urlparse

from dotenv import load_dotenv


# =====================================================
# LOAD ENV
# =====================================================

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


# =====================================================
# WEB SCRAPER
# =====================================================

class WebScraper:

    def __init__(self):

        # =============================================
        # HEADERS
        # =============================================

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        # =============================================
        # TRUSTED DOMAINS
        # =============================================

        self.trusted_domains = [
            "wikipedia.org",
            "github.com",
            "arxiv.org",
            "openai.com",
            "anthropic.com",
            "google.com",
            "microsoft.com",
            "aws.amazon.com",
            "huggingface.co",
            "medium.com",
            "stackoverflow.com",
            "docs.python.org",
            "pytorch.org",
            "tensorflow.org",
        ]

    # =================================================
    # CLEAN TEXT
    # =================================================

    def clean_text(self, text):
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    # =================================================
    # DOMAIN QUALITY
    # =================================================

    def calculate_source_quality(self, url):
        domain = urlparse(url).netloc.lower()
        score = 1.0
        for trusted in self.trusted_domains:
            if trusted in domain:
                score += 0.3
        return round(score, 2)

    # =================================================
    # SEARCH WEB
    # =================================================

    async def search_web(self, query, num_results=6):
        url = "https://google.serper.dev/search"

        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "q": query,
            "num": num_results
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)  # ← FIXED: was int
                ) as response:
                    data = await response.json()
        except Exception as e:
            print(f"\n❌ Serper Search Error: {e}\n")
            return []

        results = []

        for item in data.get("organic", []):
            source = item.get("link")
            title = item.get("title", "")
            snippet = item.get("snippet", "")

            if not source:
                continue

            quality_score = self.calculate_source_quality(source)

            results.append({
                "title": title,
                "source": source,
                "snippet": snippet,
                "quality_score": quality_score
            })

        results = sorted(
            results,
            key=lambda x: x["quality_score"],
            reverse=True
        )

        return results

    # =================================================
    # FETCH HTML  ← FIXED: ClientTimeout object
    # =================================================

    async def fetch_html(self, session, url):
        try:
            async with session.get(
                url,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=12),  # ← FIXED
                ssl=False
            ) as response:
                if response.status == 200:
                    return await response.text()
        except Exception as e:
            print(f"\n❌ Fetch Error: {url} → {type(e).__name__}")

        return None

    # =================================================
    # EXTRACT CONTENT
    # =================================================

    def extract_content(self, html):
        try:
            # Try trafilatura first (best quality)
            text = trafilatura.extract(html)

            if text:
                text = self.clean_text(text)
                return text

            # Fallback to BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            paragraphs = [p.get_text() for p in soup.find_all("p")]
            text = " ".join(paragraphs)
            text = self.clean_text(text)

            return text

        except Exception as e:
            print(f"\n❌ Extraction Error: {e}\n")
            return ""

    # =================================================
    # CONTENT QUALITY
    # =================================================

    def is_valid_content(self, text):
        if not text:
            return False

        text = text.strip()

        if len(text) < 200:
            return False

        words = text.split()

        if len(words) < 40:
            return False

        return True

    # =================================================
    # PARALLEL SCRAPING
    # =================================================

    async def scrape(self, query):
        print("\n🌐 Web Search Started...\n")

        search_results = await self.search_web(query)

        if not search_results:
            return []

        documents = []

        connector = aiohttp.TCPConnector(limit=10)

        # ← FIXED: outer session uses ClientTimeout object, not int
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=25)
        ) as session:

            tasks = [
                self.fetch_html(session, result["source"])
                for result in search_results
            ]

            html_results = await asyncio.gather(*tasks, return_exceptions=True)

        for idx, html in enumerate(html_results):

            if isinstance(html, Exception) or not html:
                # ← Snippet fallback: use Serper snippet as content
                result = search_results[idx]
                snippet = result.get("snippet", "")
                if snippet and len(snippet) > 50:
                    documents.append({
                        "source": result["source"],
                        "title": result["title"],
                        "snippet": snippet,
                        "content": snippet,
                        "quality_score": result["quality_score"] * 0.5,
                        "domain": urlparse(result["source"]).netloc
                    })
                continue

            content = self.extract_content(html)

            if not self.is_valid_content(content):
                # Try snippet fallback
                result = search_results[idx]
                snippet = result.get("snippet", "")
                if snippet and len(snippet) > 50:
                    documents.append({
                        "source": result["source"],
                        "title": result["title"],
                        "snippet": snippet,
                        "content": snippet,
                        "quality_score": result["quality_score"] * 0.5,
                        "domain": urlparse(result["source"]).netloc
                    })
                continue

            result = search_results[idx]

            documents.append({
                "source": result["source"],
                "title": result["title"],
                "snippet": result["snippet"],
                "content": content[:7000],
                "quality_score": result["quality_score"],
                "domain": urlparse(result["source"]).netloc
            })

        documents = sorted(
            documents,
            key=lambda x: x["quality_score"],
            reverse=True
        )

        print(
            f"\n✅ Retrieved {len(documents)} "
            f"web documents\n"
        )

        return documents