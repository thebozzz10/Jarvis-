"""Web search and webpage fetching tools."""
import json
from jarvis.core.tool_registry import BaseTool
from jarvis.utils.config import get
from jarvis.utils.logger import get_logger

log = get_logger(__name__)
MAX_RESULTS = int(get("tools", "max_web_results", 5))


class WebSearch(BaseTool):
    name = "web_search"
    description = "Search the web using DuckDuckGo and return top results with titles, URLs, and snippets."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "default": 5},
            "region": {"type": "string", "default": "wt-wt"},
        },
        "required": ["query"],
    }

    def run(self, query: str, max_results: int = MAX_RESULTS, region: str = "wt-wt") -> str:
        try:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, region=region, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
            return json.dumps({"query": query, "results": results, "count": len(results)})
        except Exception as e:
            return json.dumps({"error": str(e)})


class FetchWebpage(BaseTool):
    name = "fetch_webpage"
    description = "Fetch a URL and extract its readable text content. Useful for reading articles, docs, or any web page."
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Full URL to fetch"},
            "extract_links": {"type": "boolean", "default": False},
            "max_chars": {"type": "integer", "default": 8000},
        },
        "required": ["url"],
    }

    def run(self, url: str, extract_links: bool = False, max_chars: int = 8000) -> str:
        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")

            # Remove scripts, styles, nav boilerplate
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            text = "\n".join(line for line in text.splitlines() if line.strip())[:max_chars]

            result: dict = {"url": url, "title": soup.title.string if soup.title else "", "content": text}

            if extract_links:
                links = [{"text": a.get_text(strip=True), "href": a.get("href", "")}
                         for a in soup.find_all("a", href=True)][:30]
                result["links"] = links

            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})
