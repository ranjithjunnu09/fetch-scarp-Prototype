import os
import json
import requests
import trafilatura

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from dotenv import load_dotenv


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    raise ValueError("❌ SERPER_API_KEY not found in .env file")


OUTPUT_DIR = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "results.json")


# =========================================================
# DOCUMENT MODEL
# =========================================================

class Document:
    def __init__(self, url, title, snippet, content):
        self.url = url
        self.title = title
        self.snippet = snippet
        self.content = content

    def to_dict(self):
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "content": self.content
        }


# =========================================================
# ABSTRACT SEARCH ENGINE
# =========================================================

class BaseSearchEngine(ABC):

    @abstractmethod
    def search(self, query, num_results=10):
        pass


# =========================================================
# SERPER SEARCH ENGINE
# =========================================================

class SerperSearchEngine(BaseSearchEngine):

    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://google.serper.dev/search"

    def search(self, query, num_results=10):

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "q": query,
            "num": num_results
        }

        try:
            response = requests.post(
                self.url,
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                print("❌ Search API Error:", response.text)
                return []

            data = response.json()

            results = []

            for item in data.get("organic", []):

                results.append({
                    "url": item.get("link"),
                    "title": item.get("title"),
                    "snippet": item.get("snippet")
                })

            return results

        except Exception as e:
            print("❌ Search Error:", e)
            return []


# =========================================================
# FETCHER
# =========================================================

class WebFetcher:

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0"
        }

    def fetch(self, url):

        try:
            response = requests.get(
                url,
                timeout=5,
                headers=self.headers
            )

            if response.status_code == 200:
                return response.text

        except Exception as e:
            print(f"⚠️ Error fetching {url}: {e}")

        return None


# =========================================================
# ABSTRACT EXTRACTOR
# =========================================================

class BaseExtractor(ABC):

    @abstractmethod
    def extract(self, html):
        pass


# =========================================================
# CONTENT EXTRACTOR
# =========================================================

class ContentExtractor(BaseExtractor):

    def extract(self, html):

        try:
            # Try trafilatura first
            text = trafilatura.extract(html)

            if text:
                return text

            # Fallback to BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            paragraphs = [
                p.get_text()
                for p in soup.find_all("p")
            ]

            return " ".join(paragraphs)

        except Exception as e:
            print("⚠️ Extraction error:", e)
            return ""


# =========================================================
# STORAGE
# =========================================================

class JSONStorage:

    def __init__(self, output_dir, output_file):

        self.output_dir = output_dir
        self.output_file = output_file

    def save(self, data):

        os.makedirs(self.output_dir, exist_ok=True)

        with open(
            self.output_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False
            )

        print(f"\n✅ Results saved to {self.output_file}")


# =========================================================
# PIPELINE
# =========================================================

class RetrievalPipeline:

    def __init__(
        self,
        search_engine,
        fetcher,
        extractor,
        storage
    ):

        self.search_engine = search_engine
        self.fetcher = fetcher
        self.extractor = extractor
        self.storage = storage

    def run(self, query):

        print(f"\n🔍 Searching for: {query}\n")

        search_results = self.search_engine.search(query)

        documents = []

        for i, result in enumerate(search_results):

            url = result["url"]

            print(
                f"🌐 Fetching ({i+1}/{len(search_results)}): {url}"
            )

            html = self.fetcher.fetch(url)

            if not html:
                continue

            content = self.extractor.extract(html)

            if not content or len(content.strip()) < 50:
                continue

            document = Document(
                url=url,
                title=result["title"],
                snippet=result["snippet"],
                content=content[:3000]
            )

            documents.append(document)

        final_output = {
            "query": query,
            "results": [
                doc.to_dict()
                for doc in documents
            ]
        }

        self.storage.save(final_output)

        return final_output


# =========================================================
# MAIN
# =========================================================

def main():

    # Create Components

    search_engine = SerperSearchEngine(
        api_key=SERPER_API_KEY
    )

    fetcher = WebFetcher()

    extractor = ContentExtractor()

    storage = JSONStorage(
        output_dir=OUTPUT_DIR,
        output_file=OUTPUT_FILE
    )

    # Create Pipeline

    pipeline = RetrievalPipeline(
        search_engine=search_engine,
        fetcher=fetcher,
        extractor=extractor,
        storage=storage
    )

    # User Input

    query = input("Enter your query: ")

    # Run Pipeline

    pipeline.run(query)

    print("\n🎯 Done!")


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()