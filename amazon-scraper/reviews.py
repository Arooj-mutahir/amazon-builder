import asyncio
import re
import json
import html as html_module
import base64
from amazon import fetch


def extract_customers_say(html_doc: str) -> dict:
    """
    Extracts the "Customers say" AI summary and top review snippets from Amazon HTML.
    """
    result = {"summary": None, "reviews": []}
    
    # Amazon "k+b64" tokens mein base64 encoded JSON daalta hai
    tokens = re.findall(r'k\+b64 ([A-Za-z0-9+/=]+)', html_doc)
    
    for token in tokens:
        try:
            decoded = base64.b64decode(token).decode("utf-8", "ignore")
            data = json.loads(decoded)
            
            component = str(data.get("k-component") or "")
            k_data = data.get("k-data") or {}
            
            # 1. Customers say summary
            if component.startswith("SummaryFragments") and not result["summary"]:
                fragments = k_data.get("fragments") or []
                summary_text = " ".join(f.get("inertText") or "" for f in fragments)
                if summary_text.strip():
                    result["summary"] = summary_text.strip()
            
            # 2. Top review snippets
            elif component.startswith("AspectList"):
                aspects = k_data.get("aspectsFlattened") or []
                for aspect in aspects:
                    snippets = aspect.get("snippets") or []
                    for snip in snippets:
                        text_frags = []
                        for f in (snip.get("text") or {}).get("fragments") or []:
                            text_frags.append(f.get("text") or "")
                        snippet_text = "".join(text_frags).strip()
                        if snippet_text:
                            result["reviews"].append({
                                "text": snippet_text,
                                "aspect": aspect.get("label") or "",
                                "sentiment": aspect.get("sentiment") or "",
                            })
        except Exception:
            continue
    
    return result


async def test_product(asin: str, name: str):
    print(f"\n{'='*50}")
    print(f"🔍 Testing: {name} (ASIN: {asin})")
    print(f"{'='*50}")
    
    try:
        html = await asyncio.to_thread(fetch.page, "US", f"/dp/{asin}")
        print(f"✅ HTML loaded. Length: {len(html)}")
    except Exception as e:
        print(f"❌ Failed to fetch: {e}")
        return
    
    data = extract_customers_say(html)
    
    if data["summary"]:
        print(f"\n📝 Summary: {data['summary'][:200]}...")
    else:
        print("\n❌ No summary found.")
    
    if data["reviews"]:
        print(f"\n🎉 Found {len(data['reviews'])} review snippets:")
        for i, r in enumerate(data["reviews"][:3], 1):  # Sirf pehle 3 dikhayein
            print(f"  {i}. [{r['aspect']} - {r['sentiment']}] {r['text'][:100]}...")
    else:
        print("\n❌ No review snippets found.")


async def main():
    # 3 popular products ka test
    products = [
        ("B0BGN2HQHH", "Kikidex Magnetic Drawing Board"),
        ("B095LT69HN", "Hollyhi Washable Cosmetic"),
        ("B08N5WRWNW", "Echo Dot (4th Gen)"), 
    ]
    
    for asin, name in products:
        await test_product(asin, name)
        print()  # Gap between products
        await asyncio.sleep(2)  # Rate limit se bachne ke liye


if __name__ == "__main__":
    asyncio.run(main())