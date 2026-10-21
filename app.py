import time
from datetime import datetime
from urllib.parse import urljoin

import requests
import streamlit as st
from bs4 import BeautifulSoup

# ------------------------------------------------------------
# W3_News_Headlines_Scraper — Streamlit dashboard
# ------------------------------------------------------------
URL = "https://edition.cnn.com/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT_SECONDS = 15
HEADLINE_LIMIT = 5

# CNN markup can change. These selectors are attempted in order.
HEADLINE_SELECTORS = [
    ".container__headline-text",
    ".container__headline",
    "[data-editable='headline']",
    "h3.container__title",
    "h2.container__title",
    "main h3",
    "main h2",
]


def clean_text(value: str) -> str:
    """Collapse repeated whitespace and trim the text."""
    return " ".join(value.split())


def scrape_cnn():
    """Fetch CNN and return a structured result for the dashboard."""
    started = time.perf_counter()
    result = {
        "url": URL,
        "status_code": None,
        "elapsed_seconds": None,
        "fetched_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "headlines": [],
        "selector_used": None,
        "html_bytes": 0,
        "page_title": "",
        "error": None,
        "note": None,
    }

    try:
        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=TIMEOUT_SECONDS,
        )
        result["status_code"] = response.status_code
        response.raise_for_status()
        html = response.text
        result["html_bytes"] = len(response.content)

        soup = BeautifulSoup(html, "html.parser")
        result["page_title"] = clean_text(soup.title.get_text()) if soup.title else "Not available"

        seen = set()
        for selector in HEADLINE_SELECTORS:
            found = []
            for element in soup.select(selector):
                text = clean_text(element.get_text(" ", strip=True))
                if not text or len(text) < 12 or len(text) > 300:
                    continue
                normalized = text.casefold()
                if normalized in seen:
                    continue
                seen.add(normalized)

                anchor = element if element.name == "a" else element.find_parent("a")
                href = anchor.get("href") if anchor else None
                link = urljoin(URL, href) if href else None
                found.append({"title": text, "url": link})

                if len(result["headlines"]) + len(found) >= HEADLINE_LIMIT:
                    break

            if found:
                if result["selector_used"] is None:
                    result["selector_used"] = selector
                result["headlines"].extend(found)
            if len(result["headlines"]) >= HEADLINE_LIMIT:
                result["headlines"] = result["headlines"][:HEADLINE_LIMIT]
                break

        if not result["headlines"]:
            result["note"] = (
                "The page was downloaded successfully, but no headlines matched the current selectors. "
                "CNN may have changed its HTML or may render headlines with JavaScript. "
                "Inspect the current page markup and update HEADLINE_SELECTORS; if needed, use Playwright."
            )
        elif len(result["headlines"]) < HEADLINE_LIMIT:
            result["note"] = (
                f"Only {len(result['headlines'])} unique headline(s) were found. "
                "The website markup may have changed or fewer matching headlines were present."
            )

    except requests.exceptions.Timeout:
        result["error"] = f"CNN did not respond within {TIMEOUT_SECONDS} seconds."
    except requests.exceptions.HTTPError as exc:
        result["error"] = f"HTTP error while fetching CNN: {exc}"
    except requests.exceptions.RequestException as exc:
        result["error"] = f"Could not fetch CNN: {exc}"
    except Exception as exc:
        result["error"] = f"Unexpected scraping error: {exc}"
    finally:
        result["elapsed_seconds"] = round(time.perf_counter() - started, 2)

    return result


# ---------- Page setup ----------
st.set_page_config(
    page_title="CNN Headlines Scraper",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp {
        background: linear-gradient(180deg, #f5f8fc 0%, #ffffff 45%, #f7f9fc 100%);
      }
      .block-container { padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1250px; }
      .hero {
        padding: 1.8rem 2rem;
        border-radius: 22px;
        background: linear-gradient(120deg, #101b35 0%, #173d68 60%, #2878a8 100%);
        color: white;
        box-shadow: 0 12px 32px rgba(18, 44, 77, .16);
        margin-bottom: 1.2rem;
      }
      .hero-kicker { color: #b9d9f5; text-transform: uppercase; letter-spacing: .14em; font-size: .75rem; font-weight: 800; }
      .hero h1 { color: white; margin: .4rem 0 .5rem 0; font-size: clamp(2rem, 4vw, 3.2rem); }
      .hero p { color: #e3eef8; margin: 0; font-size: 1.02rem; }
      .headline-card {
        background: white;
        border: 1px solid #e3eaf2;
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
        margin: .7rem 0;
        box-shadow: 0 5px 18px rgba(20, 44, 74, .045);
      }
      .headline-number {
        display: inline-flex; align-items: center; justify-content: center;
        width: 2.25rem; height: 2.25rem; border-radius: 12px;
        background: #e8f2ff; color: #164f91; font-weight: 800; margin-right: .75rem;
      }
      .headline-title { color: #17263d; font-size: 1.04rem; font-weight: 700; line-height: 1.45; }
      .muted { color: #63748a; font-size: .88rem; }
      div[data-testid="stMetric"] {
        background: white; padding: 1rem 1.1rem; border: 1px solid #e5ebf2;
        border-radius: 15px; box-shadow: 0 4px 14px rgba(20,44,74,.035);
      }
      .section-title { color: #17263d; font-size: 1.35rem; font-weight: 800; margin: .6rem 0 .2rem 0; }
      .small-pill {
        display: inline-block; padding: .28rem .65rem; border-radius: 999px;
        background: #e8f7ef; color: #167344; font-weight: 700; font-size: .78rem;
      }
      footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 📰 Scraper controls")
    st.caption("Week 3 · Day 5 assignment")
    st.markdown("---")
    st.markdown("**Source website**")
    st.code(URL, language=None)
    st.markdown("**Scraping stack**")
    st.write("🐍 Python")
    st.write("🌐 Requests")
    st.write("🍜 BeautifulSoup")
    st.markdown("---")
    st.markdown("**What this app does**")
    st.write("1. Fetches CNN's homepage")
    st.write("2. Checks the HTTP status")
    st.write("3. Parses headline elements")
    st.write("4. Removes empty/duplicate results")
    st.write("5. Displays up to five headlines")
    st.markdown("---")
    auto_refresh = st.checkbox("Auto-refresh every 5 minutes", value=False)
    if auto_refresh:
        st.caption("The page will refresh periodically while open.")
        st.markdown(
            '<meta http-equiv="refresh" content="300">',
            unsafe_allow_html=True,
        )

# ---------- Hero ----------
st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">W3 · Day 5 · Web scraping project</div>
      <h1> CNN Headlines Explorer</h1>
      <p>A clean, interactive dashboard to fetch, inspect, and display the latest headlines found in CNN's homepage HTML.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([3, 1])
with left:
    st.markdown("### Discover the top headlines")
    st.caption("Click the button to fetch CNN's homepage and extract up to five unique headlines.")
with right:
    run_scrape = st.button("🔄 Scrape CNN now", type="primary", use_container_width=True)

if "scrape_result" not in st.session_state:
    st.session_state.scrape_result = None

if run_scrape:
    with st.spinner("Connecting to CNN and parsing the page…"):
        st.session_state.scrape_result = scrape_cnn()

result = st.session_state.scrape_result

if result is None:
    st.info("Ready to scrape. Click **Scrape CNN now** to start.")
    st.markdown("#### How it works")
    cols = st.columns(3)
    with cols[0]:
        st.markdown("### ① Fetch")
        st.write("Requests downloads the page using a browser-like User-Agent.")
    with cols[1]:
        st.markdown("### ② Parse")
        st.write("BeautifulSoup searches headline selectors and cleans the text.")
    with cols[2]:
        st.markdown("### ③ Display")
        st.write("Unique results appear as numbered headline cards.")
else:
    status = result["status_code"]
    success = result["error"] is None and status is not None and 200 <= status < 300

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Headlines found", len(result["headlines"]))
    m2.metric("HTTP status", status if status is not None else "N/A")
    m3.metric("Fetch time", f"{result['elapsed_seconds']} s")
    m4.metric("HTML size", f"{result['html_bytes'] / 1024:.1f} KB")

    if success:
        st.success("CNN page fetched successfully.")
    if result["error"]:
        st.error(result["error"])
    if result["note"]:
        st.warning(result["note"])

    st.markdown('<div class="section-title">Top headlines</div>', unsafe_allow_html=True)
    st.caption(f"Fetched at {result['fetched_at']} · Source: {URL}")

    if result["headlines"]:
        for i, headline in enumerate(result["headlines"], start=1):
            st.markdown(
                f"""
                <div class="headline-card">
                  <span class="headline-number">{i}</span>
                  <span class="headline-title">{headline['title']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if headline["url"]:
                st.markdown(f"[Open story ↗]({headline['url']})")
    else:
        st.info("No headlines to display. Review the diagnostic details below.")

    with st.expander("🔍 Scraping diagnostics", expanded=False):
        st.write("**Page title:**", result["page_title"] or "Not available")
        st.write("**Selector that matched:**", result["selector_used"] or "None")
        st.write("**Requested URL:**", result["url"])
        st.write("**Fetch timestamp:**", result["fetched_at"])
        st.write("**Response size:**", f"{result['html_bytes']} bytes")
        st.write("**Elapsed time:**", f"{result['elapsed_seconds']} seconds")
        st.caption(
            "CNN can change its page structure or render content dynamically. "
            "Selectors are best-effort and should be rechecked using browser Inspect when results change."
        )

    if result["headlines"]:
        export_text = "\n".join(
            f"{i}. {item['title']}" for i, item in enumerate(result["headlines"], start=1)
        )
        st.download_button(
            "⬇️ Download headlines as TXT",
            data=export_text,
            file_name="cnn_headlines.txt",
            mime="text/plain",
        )

st.markdown("---")
st.markdown(
    '<p class="muted">Built for <b>W3_News_Headlines_Scraper</b> · Python + Requests + BeautifulSoup · '
    'Headlines belong to CNN. This educational scraper displays only short headline text.</p>',
    unsafe_allow_html=True,
)
