"""
scraper.py - Scrapes public business listings from Google Maps with Playwright.

No API key is used. A headless Chromium opens the Google Maps search page,
scrolls the results list, then opens each place to read its details.

NOTE: Google Maps' HTML changes from time to time. All CSS selectors are in the
SELECTORS dict below so they are easy to update if a field stops appearing.
Automated scraping may conflict with Google's Terms of Service - use responsibly.

Tuned for low-memory hosting (e.g. Render free plan, 512 MB RAM).
"""
import asyncio
import os
import re
import threading
from urllib.parse import quote_plus

HARD_LIMIT = 30          # low limit keeps memory use safe on a 512 MB server
NAV_TIMEOUT = 60_000     # a bit longer: free servers are slow / cold-start

# Only one scrape at a time: two Chromium browsers would exceed 512 MB
_SCRAPE_LOCK = threading.Lock()

SELECTORS = {
    "feed": 'div[role="feed"]',
    "place_links": 'div[role="feed"] a.hfpxzc',
    "name": "h1",
    "category": 'button[jsaction*="category"]',
    "address": 'button[data-item-id="address"]',
    "phone": 'button[data-item-id^="phone:tel:"]',
    "website": 'a[data-item-id="authority"]',
    "rating": 'div.F7nice span[aria-hidden="true"]',
    "reviews": 'div.F7nice span[role="img"]',
}


class ScrapeError(Exception):
    """Any scraping problem; carries an HTTP status for the API layer."""

    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


async def _accept_consent(page):
    """Dismiss Google's cookie/consent screen if it appears."""
    for label in ("Accept all", "Reject all", "I agree"):
        try:
            btn = page.get_by_role("button", name=label)
            if await btn.count():
                await btn.first.click(timeout=3000)
                await page.wait_for_load_state("domcontentloaded")
                return
        except Exception:
            continue


async def _collect_links(page, max_results):
    """Scroll the results feed until enough place links are loaded."""
    try:
        await page.wait_for_selector(SELECTORS["feed"], timeout=30_000)
    except Exception:
        # No feed: either zero results or Google went straight to one place
        if "/maps/place/" in page.url:
            return [(page.url, "")]
        return []

    stagnant = 0
    links = {}
    while len(links) < max_results and stagnant < 6:
        for a in await page.query_selector_all(SELECTORS["place_links"]):
            href = await a.get_attribute("href")
            if href and href not in links:
                links[href] = await a.get_attribute("aria-label") or ""
        before = len(links)
        await page.evaluate(
            """(sel) => { const f = document.querySelector(sel);
                          if (f) f.scrollTop = f.scrollHeight; }""",
            SELECTORS["feed"],
        )
        await page.wait_for_timeout(1500)
        if await page.get_by_text("You've reached the end of the list").count():
            break
        stagnant = stagnant + 1 if len(links) == before else 0
    return list(links.items())[:max_results]


async def _text(page, selector, attr=None):
    """Safe getter: returns '' when an element is missing."""
    try:
        el = await page.query_selector(selector)
        if not el:
            return ""
        value = await el.get_attribute(attr) if attr else await el.inner_text()
        return (value or "").strip()
    except Exception:
        return ""


def _strip_label(value):
    """'Address: 12 Main St' -> '12 Main St' (also removes private-use icon chars)."""
    value = re.sub(r"[\ue000-\uf8ff]", "", value or "")
    return value.split(":", 1)[1].strip() if ":" in value[:20] else value.strip()


async def _scrape_place(context, url, fallback_name, sem):
    """Open one place page and extract its details."""
    async with sem:
        page = await context.new_page()
        try:
            await page.goto(url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
            await page.wait_for_selector(SELECTORS["name"], timeout=20_000)
            await page.wait_for_timeout(800)

            reviews_label = await _text(page, SELECTORS["reviews"], "aria-label")
            m = re.search(r"([\d,\.]+)", reviews_label)
            rating = await _text(page, SELECTORS["rating"])
            return {
                "place_id": re.search(r"!1s([^!?]+)", url).group(1) if re.search(r"!1s([^!?]+)", url) else url,
                "name": await _text(page, SELECTORS["name"]) or fallback_name,
                "category": await _text(page, SELECTORS["category"]),
                "address": _strip_label(await _text(page, SELECTORS["address"], "aria-label")),
                "phone": _strip_label(await _text(page, SELECTORS["phone"], "aria-label")),
                "website": await _text(page, SELECTORS["website"], "href"),
                "maps_url": url,
                "rating": float(rating.replace(",", ".")) if re.fullmatch(r"\d([.,]\d)?", rating) else "",
                "reviews": int(re.sub(r"[^\d]", "", m.group(1))) if m else "",
            }
        except Exception:
            # One bad page must never break the whole search
            return {"place_id": url, "name": fallback_name, "category": "", "address": "",
                    "phone": "", "website": "", "maps_url": url, "rating": "", "reviews": ""}
        finally:
            await page.close()


async def _run(category, location, max_results):
    from playwright.async_api import async_playwright  # imported lazily

    headless = os.getenv("HEADLESS", "true").lower() != "false"
    # Default 1 = one page at a time (safe for 512 MB RAM)
    concurrency = max(1, min(int(os.getenv("MAX_CONCURRENCY", 1)), 6))

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-background-networking",
            ],
        )
        try:
            context = await browser.new_context(
                locale="en-US", viewport={"width": 1280, "height": 900},
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"))
            # Skip heavy resources to save memory and time
            await context.route("**/*", lambda r: r.abort()
                                if r.request.resource_type in ("image", "font", "media") else r.continue_())

            page = await context.new_page()
            query = quote_plus(f"{category} in {location}")
            await page.goto(f"https://www.google.com/maps/search/{query}?hl=en",
                            timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
            await _accept_consent(page)
            links = await _collect_links(page, max_results)
            await page.close()
            if not links:
                return []

            sem = asyncio.Semaphore(concurrency)
            rows = await asyncio.gather(*[_scrape_place(context, u, n, sem) for u, n in links])
        finally:
            await browser.close()
    return rows


def search_businesses(category, location, max_results):
    """Return a de-duplicated list of business dicts."""
    # Serialize searches so two users can't open two browsers at once
    with _SCRAPE_LOCK:
        try:
            rows = asyncio.run(_run(category, location, min(int(max_results), HARD_LIMIT)))
        except ImportError:
            raise ScrapeError("Playwright is not installed. Run: pip install -r requirements.txt "
                              "and: playwright install chromium", 500)
        except ScrapeError:
            raise
        except Exception as exc:
            raise ScrapeError(f"Scraping failed: {exc}. Google may be blocking the request; "
                              "try again later or with fewer results.")

    unique, seen = [], set()
    for r in rows:
        key = (r["name"].lower(), r["address"].lower()) if r["address"] else r["place_id"]
        if r["name"] and key not in seen:
            seen.add(key)
            unique.append(r)
    return unique