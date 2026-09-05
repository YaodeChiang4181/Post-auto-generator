from modules.news_aggregator import get_daily_news_candidates
from modules.llm_api import select_top_news_with_llm
import json

def test():
    print("Testing RSS fetching...")
    candidates = get_daily_news_candidates()
    print(f"Fetched {len(candidates)} candidates.")
    
    if candidates:
        print("First 3 candidates:")
        for c in candidates[:3]:
            print(f"- {c['title']} ({c['source']})")
            
        print("\nTesting LLM selection...")
        top_news = select_top_news_with_llm(candidates)
        print("LLM Result:")
        print(json.dumps(top_news, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test()
