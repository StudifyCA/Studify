
import os
import re
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=ignore-duplicates"
}

SOURCES = {
    "ICAI Announcements": "https://www.icai.org/category/announcements/3",
    "BoS Announcements": "https://boslive.icai.org/",
    "Study Material": "https://www.icai.org/post/study-material-nset"
}

session = requests.Session()
session.headers.update({
    "User-Agent": "Studify-ICAI-Monitor/1.0 (academic resource monitor)"
})

def classify_course(text):
    t = text.lower()
    if "foundation" in t:
        return "foundation"
    if "intermediate" in t:
        return "intermediate"
    if "final" in t:
        return "final"
    return "all"

def save_record(table, record):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    response = session.post(
        url,
        headers=HEADERS,
        json=record,
        timeout=30
    )
    if response.status_code not in (200, 201, 204):
        print(f"Supabase error [{table}]: {response.status_code} "
              f"{response.text[:300]}")
    else:
        print(f"Saved or already exists: {record.get('title', '')[:100]}")

def fetch_page(url):
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        print(f"Could not access {url}: {exc}")
        return None

def monitor_source(source_name, page_url):
    print(f"\nChecking: {source_name}")
    html = fetch_page(page_url)
    if not html:
        return

    soup = BeautifulSoup(html, "html.parser")

    for anchor in soup.find_all("a", href=True):
        title = " ".join(anchor.get_text(" ", strip=True).split())
        link = urljoin(page_url, anchor["href"])
        parsed = urlparse(link)

        if parsed.scheme not in ("http", "https"):
            continue

        if not title or len(title) < 4:
            continue

        if parsed.netloc.lower() not in (
            "www.icai.org", "icai.org", "boslive.icai.org"
        ):
            continue

        is_pdf = (
            parsed.path.lower().endswith(".pdf")
            or ".pdf?" in link.lower()
        )

        if is_pdf:
            record = {
                "title": title[:500],
                "resource_type": "study_material",
                "course": classify_course(title),
                "source_url": link,
                "pdf_url": link,
                "file_name": parsed.path.split("/")[-1][:500],
                "content_hash": hashlib.sha256(
                    link.encode("utf-8")
                ).hexdigest()
            }
            save_record("icai_resources", record)

        elif source_name != "Study Material":
            record = {
                "title": title[:500],
                "description": f"Detected from {source_name}",
                "category": source_name.lower().replace(" ", "_"),
                "course": classify_course(title),
                "source_url": link
            }
            save_record("icai_announcements", record)

def main():
    print("====================================")
    print("       STUDIFY ICAI MONITOR")
    print("====================================")

    for name, url in SOURCES.items():
        monitor_source(name, url)

    print("\nMonitoring run completed.")

if __name__ == "__main__":
    main()
