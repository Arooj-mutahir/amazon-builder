# Ek chhota probe script — block check karne ke liye
import httpx, random, time

def is_blocked(html: str) -> bool:
    signals = ["captcha", "robot", "automated access", 
               "api-services-support@amazon.com", "Enter the characters"]
    if len(html) < 100_000:  # normal Amazon page 2MB+, captcha ~30KB
        return True
    return any(s.lower() in html.lower() for s in signals)

# 5 variants test karo, delay ke saath
for asin in test_asins[:5]:
    time.sleep(random.uniform(2, 4))
    r = httpx.get(f"https://www.amazon.com/dp/{asin}", headers=REAL_HEADERS)
    print(asin, "BLOCKED" if is_blocked(r.text) else "OK", len(r.text))