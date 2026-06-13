"""
Ham Radio Daily News Updater - TavaOne.com
==========================================
Scrapes amateur-radio RSS feeds, curates the top headlines with the Claude API,
and writes latest_news.html (dark, Tava One-branded).

Runs daily in GitHub Actions. The workflow commits the regenerated file and
GitHub Pages serves it into the "Amateur Radio News" page on tavaone.com
(embedded at https://w4ggj.github.io/TavaOne/latest_news.html). The page posts
its height to the parent so the iframe auto-sizes with no scrollbar.

SECRETS COME FROM ENVIRONMENT VARIABLES ONLY - never hard-code them.
Required env var:
    ANTHROPIC_API_KEY
"""

import os
import sys
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic

# -- Config -------------------------------------------------------------------
HEADLINE_COUNT = 10
OUTPUT_FILE = Path(__file__).parent / "latest_news.html"

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    sys.exit("[FATAL] ANTHROPIC_API_KEY environment variable is not set. "
             "Add it as a repository secret (Settings -> Secrets and variables "
             "-> Actions) named ANTHROPIC_API_KEY.")

# -- RSS Feeds ----------------------------------------------------------------
RSS_FEEDS = [
    ("ARRL News",           "http://www.arrl.org/news/rss"),
    ("AMSAT News",          "https://www.amsat.org/feed/"),
    ("eHam Articles",       "https://www.eham.net/articles/rss"),
    ("RSGB RadCom",         "https://rsgb.org/main/feed/"),
    ("QRPer Blog",          "https://qrper.com/feed/"),
    ("OnAllBands",          "https://onallbands.com/feed/"),
    ("Hackaday Ham Radio",  "https://hackaday.com/tag/amateur-radio/feed/"),
    ("Reddit AmateurRadio", "https://www.reddit.com/r/amateurradio/top/.rss?t=day"),
    ("Reddit POTA",         "https://www.reddit.com/r/parksontheair/top/.rss?t=day"),
    ("Reddit QRP",          "https://www.reddit.com/r/QRP/top/.rss?t=day"),
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


# -- RSS Fetcher --------------------------------------------------------------
def fetch_rss(name: str, url: str) -> list:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": UA,
                     "Accept": "application/rss+xml, application/xml, text/xml, */*"},
        )
        resp = urllib.request.urlopen(req, timeout=15)
        xml = resp.read().decode("utf-8", errors="ignore")
        root = ET.fromstring(xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)
        results = []
        for item in items[:5]:
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            summary = (item.findtext("description")
                       or item.findtext("atom:summary", namespaces=ns) or "")
            if not link:
                link_el = item.find("atom:link", ns)
                if link_el is not None:
                    link = link_el.get("href", "")
            summary = re.sub(r"<[^>]+>", "", summary).strip()[:300]
            if title.strip():
                results.append({"source": name, "title": title.strip(),
                                "link": link.strip(), "summary": summary})
        print(f"  OK  {name}: {len(results)} articles")
        return results
    except Exception as e:
        print(f"  ERR {name}: {e}")
        return []


def gather_news() -> list:
    print("Fetching RSS feeds...")
    articles = []
    for name, url in RSS_FEEDS:
        articles.extend(fetch_rss(name, url))
    print(f"Total articles: {len(articles)}\n")
    return articles


# -- Claude Curation ----------------------------------------------------------
def curate_with_claude(articles: list) -> str:
    client = anthropic.Anthropic(api_key=API_KEY)

    now_et = datetime.now(ZoneInfo("America/New_York"))
    today = now_et.strftime("%B %d, %Y")
    hour12 = now_et.strftime("%I").lstrip("0") or "12"
    updated_str = now_et.strftime(f"%B %d, %Y at {hour12}:%M %p ET")

    article_text = ""
    for i, a in enumerate(articles, 1):
        article_text += f"{i}. [{a['source']}] {a['title']}\n"
        if a["summary"]:
            article_text += f"   {a['summary'][:200]}\n"
        if a["link"]:
            article_text += f"   URL: {a['link']}\n"
        article_text += "\n"

    prompt = f"""You write the daily amateur radio news digest for TavaOne.com - the ham radio content site of W4GGJ (Joe), a General Class ham in Tampa Bay, FL. Joe loves POTA activations, FT8 digital modes, QRP operating with his Xiegu X6200, and working DX. He has earned Worked All States Mixed and Digital.

Today is {today}.

Articles available today:
{article_text}

Select the TOP {HEADLINE_COUNT} most interesting stories for amateur radio operators. Prioritize: POTA, digital modes, DX, contests, new gear, regulatory news, Florida hams.

Output ONLY clean HTML using exactly this structure:

<div style="font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 820px; margin: 0 auto; padding: 10px;">

<div style="font-size: 26px; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 6px;"><span style="color:#ffffff;">Tava</span><span style="color:#10b981;">One</span><span style="color:#475569;"> // </span><span style="color:#10b981;">News</span></div>

<p style="color: #94a3b8; font-size: 13px; border-bottom: 1px solid #334155; padding-bottom: 14px; margin: 0 0 26px 0;">Amateur radio headlines, curated daily by W4GGJ &mdash; last updated {updated_str}</p>

<div style="background:#1e293b; border:1px solid #334155; border-left:4px solid #10b981; border-radius:8px; padding:16px 18px; margin-bottom:16px;">
<h3 style="margin:0 0 6px 0; font-size:17px; font-weight:700; line-height:1.35;"><a href="ARTICLE_URL" target="_blank" style="color:#f8fafc; text-decoration:none;">ARTICLE HEADLINE</a></h3>
<p style="color:#6ee7b7; font-size:11px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; margin:0 0 8px 0;">SOURCE NAME</p>
<p style="color:#cbd5e1; font-size:14px; line-height:1.6; margin:0;">1-2 sentence summary in Joe's friendly ham radio voice. Sound like a fellow ham sharing news on the air, not a press release.</p>
</div>

</div>

Repeat the inner card div for each headline. Output ONLY the HTML, nothing else."""

    print("Curating with Claude...")
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    html = resp.content[0].text.strip()
    html = re.sub(r"^```html\s*", "", html)
    html = re.sub(r"^```\s*", "", html)
    html = re.sub(r"\s*```$", "", html)
    html = html.strip()
    if not html:
        sys.exit("[FATAL] Claude returned empty content - not overwriting the page.")
    return html


# -- Write HTML ---------------------------------------------------------------
def write_html(html_content: str) -> None:
    # Plain string (not an f-string) so the CSS/JS braces don't need escaping.
    page = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="3600">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Amateur Radio Daily News - Tava One / W4GGJ</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; overflow-x: hidden; }
    body {
      padding: 28px 20px;
      background: #0f172a;
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    a:hover { color: #34d399 !important; text-decoration: none !important; }
  </style>
</head>
<body>
__CONTENT__
<script>
  function tavaonePostHeight() {
    var h = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
    if (window.parent) { window.parent.postMessage({ tavaoneNewsHeight: h }, "*"); }
  }
  window.addEventListener("load", tavaonePostHeight);
  window.addEventListener("resize", tavaonePostHeight);
  document.addEventListener("DOMContentLoaded", tavaonePostHeight);
  setTimeout(tavaonePostHeight, 300);
  setTimeout(tavaonePostHeight, 1200);
</script>
</body>
</html>"""
    OUTPUT_FILE.write_text(page.replace("__CONTENT__", html_content), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}")

# -- Write Fragment (for client-side embed) -----------------------------------
def write_fragment(html_content: str) -> None:
    """Self-contained dark panel, no <html>/<head>/<body>, for a fetch() embed."""
    open_div = (
        '<div style="background:#0f172a; border-radius:12px; padding:28px 20px; '
        "font-family:'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;\">"
    )
    fragment = open_div + "\n" + html_content + "\n</div>\n"
    out = Path(__file__).parent / "news_fragment.html"
    out.write_text(fragment, encoding="utf-8")
    print(f"Wrote {out}")
    
# -- Main ---------------------------------------------------------------------
def main():
    print("=" * 55)
    print("  TavaOne Ham Radio News Updater")
    print(f"  W4GGJ  |  {datetime.now(ZoneInfo('America/New_York')).strftime('%B %d, %Y at %I:%M %p ET')}")
    print("=" * 55 + "\n")

    articles = gather_news()
    if not articles:
        sys.exit("[FATAL] No articles fetched - aborting so the page is not "
                 "overwritten with nothing.")

    html = curate_with_claude(articles)
    write_html(html)
    write_fragment(html)

    print("\n" + "=" * 55)
    print("  Update complete! 73 de W4GGJ")
    print("=" * 55)


if __name__ == "__main__":
    main()
