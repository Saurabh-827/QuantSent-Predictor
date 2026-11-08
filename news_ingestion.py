import os
import json
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


def fetch_news(query="Tesla TSLA stock", days=7, max_results=10):
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    resp = client.search(query=query, topic="news", days=days, max_results=max_results)
    os.makedirs("data", exist_ok=True)
    with open("data/tsla_news.json", "w", encoding="utf-8") as f:
        json.dump(resp, f, ensure_ascii=False, indent=2)
    return resp["results"]


if __name__ == "__main__":
    for r in fetch_news():
        print(r.get("published_date"), "|", r["title"], "|", r["url"])