import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import trafilatura

# ------------------ CONFIG ------------------ #
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    raise ValueError("❌ SERPER_API_KEY not found in .env file")

OUTPUT_DIR = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "results.json")

# ------------------ SEARCH ------------------ #
def search_serper(query, num_results=10):
    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "q": query,
        "num": num_results
    }

    response = requests.post(url, headers=headers, json=payload)

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


# ------------------ FETCH ------------------ #
def fetch_html(url):
    try:
        response = requests.get(url, timeout=5, headers={
            "User-Agent": "Mozilla/5.0"
        })
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}")
    return None


# ------------------ EXTRACT ------------------ #
def extract_text(html):
    try:
        # Try trafilatura first (clean extraction)
        text = trafilatura.extract(html)
        if text:
            return text

        # Fallback to BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        paragraphs = [p.get_text() for p in soup.find_all("p")]
        return " ".join(paragraphs)

    except Exception as e:
        print("⚠️ Extraction error:", e)
        return ""


# ------------------ PIPELINE ------------------ #
def run_pipeline(query):
    print(f"\n🔍 Searching for: {query}\n")

    search_results = search_serper(query)

    final_results = []

    for i, result in enumerate(search_results):
        url = result["url"]
        print(f"🌐 Fetching ({i+1}/{len(search_results)}): {url}")

        html = fetch_html(url)
        if not html:
            continue

        content = extract_text(html)
        if not content or len(content.strip()) < 50:
            continue

        final_results.append({
            "url": url,
            "title": result["title"],
            "snippet": result["snippet"],
            "content": content[:3000]  # limit size
        })

    return {
        "query": query,
        "results": final_results
    }


# ------------------ SAVE OUTPUT ------------------ #
def save_output(data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Results saved to {OUTPUT_FILE}")


# ------------------ MAIN ------------------ #
if __name__ == "__main__":
    user_query = input("Enter your query: ")

    results = run_pipeline(user_query)
    save_output(results)

    print("\n🎯 Done!")