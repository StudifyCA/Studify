import os
import re
import hashlib
import time
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag, unquote

import requests
from bs4 import BeautifulSoup


# ============================================================
# STUDIFY ICAI MONITOR
# Discovers ICAI academic PDFs and relevant announcements.
# Saves metadata and links to Supabase.
# ============================================================

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=ignore-duplicates"
}

# Official ICAI starting pages
SOURCE_PAGES = [
    {
        "name": "ICAI Announcements",
        "url": "https://www.icai.org/category/announcements/3",
        "kind": "announcements"
    },
    {
        "name": "ICAI Study Material",
        "url": "https://www.icai.org/post/study-material-nset",
        "kind": "academic"
    },
    {
        "name": "ICAI New Scheme",
        "url": "https://www.icai.org/post/new-scheme-of-education-and-training",
        "kind": "academic"
    },
    {
        "name": "Foundation RTP January 2027",
        "url": "https://www.icai.org/post/rtp-foundation-course-jan2027",
        "kind": "academic"
    },
    {
        "name": "Intermediate RTP January 2027",
        "url": "https://www.icai.org/post/rtp-intermediate-course-jan2027",
        "kind": "academic"
    }
]

ALLOWED_HOSTS = {
    "www.icai.org",
    "icai.org",
    "boslive.icai.org"
}

ACADEMIC_KEYWORDS = [
    "study material",
    "study-material",
    "course",
    "foundation",
    "intermediate",
    "final",
    "rtp",
    "mtp",
    "mock test",
    "mock-test",
    "question paper",
    "question-paper",
    "suggested answer",
    "suggested-answer",
    "answer key",
    "answer-key",
    "revision test",
    "revision-test",
    "case study",
    "case-study",
    "syllabus",
    "new scheme",
    "new-scheme",
    "amendment",
    "amendments",
    "supplementary",
    "academic",
    "bos",
    "mcq",
    "practice"
]

IGNORE_LINK_WORDS = [
    "home",
    "overview",
    "about icai",
    "contact us",
    "members",
    "students",
    "login",
    "register",
    "privacy policy",
    "terms",
    "copyright",
    "sitemap",
    "official directory",
    "facebook",
    "twitter",
    "instagram",
    "linkedin",
    "youtube",
    "tender",
    "career",
    "placement",
    "advertisement"
]

MAX_PAGES = 100
MAX_DEPTH = 3
REQUEST_DELAY = 0.4

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (compatible; Studify-ICAI-Monitor/2.0; "
        "+https://github.com/StudifyCA/Studify)"
    )
})


# ============================================================
# TEXT AND CLASSIFICATION HELPERS
# ============================================================

def clean_text(value):
    return " ".join((value or "").split()).strip()


def classify_course(text):
    t = (text or "").lower()

    if "foundation" in t:
        return "foundation"

    if "intermediate" in t:
        return "intermediate"

    if re.search(r"\bfinal\b", t):
        return "final"

    return "all"


def classify_subject(text):
    t = (text or "").lower()

    subjects = [
        ("advanced accounting", "advanced_accounting"),
        ("accounting", "accounting"),
        ("corporate and other laws", "corporate_and_other_laws"),
        ("corporate law", "corporate_and_other_laws"),
        ("law", "law"),
        ("taxation", "taxation"),
        ("income tax", "income_tax"),
        ("gst", "gst"),
        ("cost and management accounting", "cost_accounting"),
        ("cost accounting", "cost_accounting"),
        ("auditing", "auditing"),
        ("audit", "auditing"),
        ("financial management", "financial_management"),
        ("strategic management", "strategic_management"),
        ("economics", "economics"),
        ("business laws", "business_laws"),
        ("business correspondence", "business_correspondence"),
        ("quantitative aptitude", "quantitative_aptitude"),
        ("business mathematics", "business_mathematics"),
        ("statistics", "statistics"),
        ("financial reporting", "financial_reporting"),
        ("strategic financial management", "strategic_financial_management"),
        ("corporate and economic laws", "corporate_and_economic_laws"),
        ("integrated business solutions", "integrated_business_solutions")
    ]

    for keyword, subject in subjects:
        if keyword in t:
            return subject

    return "general"


def classify_resource_type(text, is_pdf=False):
    t = (text or "").lower()

    if "rtp" in t or "revision test paper" in t:
        return "rtp"

    if "mtp" in t or "mock test paper" in t:
        return "mtp"

    if "suggested answer" in t or "suggested answers" in t:
        return "suggested_answer"

    if "question paper" in t or "previous year" in t:
        return "question_paper"

    if "answer key" in t or "answer keys" in t:
        return "answer_key"

    if "mcq" in t or "multiple choice" in t:
        return "mcq"

    if "amendment" in t or "amendments" in t:
        return "amendment"

    if "supplementary" in t:
        return "supplementary_material"

    if "case study" in t or "case scenario" in t:
        return "case_study"

    if "syllabus" in t:
        return "syllabus"

    if "study material" in t or "study-material" in t:
        return "study_material"

    if is_pdf:
        return "academic_pdf"

    return "academic_resource"


def is_relevant_academic_text(text):
    t = (text or "").lower()

    if any(word in t for word in IGNORE_LINK_WORDS):
        return False

    return any(word in t for word in ACADEMIC_KEYWORDS)


# ============================================================
# URL HELPERS
# ============================================================

def normalize_url(url):
    url = urldefrag(url)[0]
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return None

    if parsed.netloc.lower() not in ALLOWED_HOSTS:
        return None

    return url


def is_pdf_url(url):
    parsed = urlparse(url)
    path = unquote(parsed.path).lower()
    query = parsed.query.lower()

    return (
        path.endswith(".pdf")
        or ".pdf" in query
        or "downloadpdf" in path
    )


def get_file_name(url):
    parsed = urlparse(url)
    name = unquote(parsed.path.split("/")[-1])

    if not name or not name.lower().endswith(".pdf"):
        name = "ICAI_" + hashlib.sha256(
            url.encode("utf-8")
        ).hexdigest()[:16] + ".pdf"

    return name[:500]


# ============================================================
# SUPABASE DATABASE
# ============================================================

def save_record(table, record):
    url = f"{SUPABASE_URL}/rest/v1/{table}"

    try:
        response = session.post(
            url,
            headers=HEADERS,
            json=record,
            timeout=30
        )

        if response.status_code in (200, 201, 204):
            print(
                f"Saved or already exists [{table}]: "
                f"{record.get('title', '')[:100]}"
            )
        else:
            print(
                f"Supabase error [{table}]: "
                f"{response.status_code} {response.text[:500]}"
            )

    except requests.RequestException as exc:
        print(f"Database connection error: {exc}")


def save_pdf(title, url, context=""):
    title = clean_text(title) or get_file_name(url)

    combined_text = f"{title} {url} {context}"

    record = {
        "title": title[:500],
        "resource_type": classify_resource_type(combined_text, True),
        "course": classify_course(combined_text),
        "subject": classify_subject(combined_text),
        "source_url": url,
        "pdf_url": url,
        "file_name": get_file_name(url),
        "content_hash": hashlib.sha256(
            url.encode("utf-8")
        ).hexdigest()
    }

    save_record("icai_resources", record)


def save_announcement(title, url, description=""):
    title = clean_text(title)

    if not title or len(title) < 8:
        return

    record = {
        "title": title[:500],
        "description": clean_text(description)[:2000]
        or "Official ICAI announcement",
        "category": "icai_announcement",
        "course": classify_course(title),
        "source_url": url
    }

    save_record("icai_announcements", record)


# ============================================================
# PAGE FETCHING
# ============================================================

def fetch_page(url):
    try:
        response = session.get(
            url,
            timeout=35,
            allow_redirects=True
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        if "pdf" in content_type:
            return None

        return response.text

    except requests.RequestException as exc:
        print(f"Could not access {url}: {exc}")
        return None


# ============================================================
# PAGE LINK EXTRACTION
# ============================================================

def extract_links(page_url, html):
    soup = BeautifulSoup(html, "html.parser")
    extracted = []

    for anchor in soup.find_all("a", href=True):
        title = clean_text(anchor.get_text(" ", strip=True))
        link = normalize_url(urljoin(page_url, anchor["href"]))

        if not link:
            continue

        # Include surrounding text to identify subject and resource type.
        parent_text = ""
        parent = anchor.parent

        if parent:
            parent_text = clean_text(
                parent.get_text(" ", strip=True)
            )

        context = clean_text(f"{title} {parent_text}")

        if not title:
            title = get_file_name(link)

        extracted.append({
            "title": title[:500],
            "url": link,
            "context": context[:1500]
        })

    return extracted


# ============================================================
# ACADEMIC RESOURCE CRAWLER
# ============================================================

def crawl_academic_pages(source_name, start_url):
    print(f"\nChecking academic source: {source_name}")

    queue = deque()
    queue.append((start_url, 0))

    visited = set()
    pages_checked = 0
    pdfs_found = 0

    while queue and pages_checked < MAX_PAGES:
        page_url, depth = queue.popleft()

        page_url = normalize_url(page_url)

        if not page_url or page_url in visited:
            continue

        visited.add(page_url)
        pages_checked += 1

        print(f"Page {pages_checked}: {page_url}")

        html = fetch_page(page_url)

        if not html:
            continue

        time.sleep(REQUEST_DELAY)

        links = extract_links(page_url, html)

        for item in links:
            title = item["title"]
            link = item["url"]
            context = item["context"]

            if is_pdf_url(link):
                save_pdf(
                    title,
                    link,
                    f"{source_name} {context}"
                )
                pdfs_found += 1
                continue

            # Only follow links that appear academically relevant.
            if depth < MAX_DEPTH and is_relevant_academic_text(
                f"{title} {link} {context}"
            ):
                if link not in visited:
                    queue.append((link, depth + 1))

    print(
        f"Finished {source_name}. "
        f"Pages checked: {pages_checked}. "
        f"PDF links found: {pdfs_found}."
    )


# ============================================================
# ANNOUNCEMENT MONITOR
# ============================================================

def monitor_announcements(source_name, page_url):
    print(f"\nChecking announcements: {source_name}")

    html = fetch_page(page_url)

    if not html:
        return

    links = extract_links(page_url, html)
    saved = 0

    for item in links:
        title = item["title"]
        link = item["url"]
        context = item["context"]

        parsed = urlparse(link)
        path = parsed.path.lower()

        # Avoid saving navigation, category and generic pages.
        if path.startswith("/category/"):
            continue

        if not (
            path.startswith("/post/")
            or "/announcement" in path
            or "/notification" in path
        ):
            continue

        if not title or len(title) < 8:
            continue

        if any(word in title.lower() for word in IGNORE_LINK_WORDS):
            continue

        # If the link is a PDF, store it as a resource instead.
        if is_pdf_url(link):
            save_pdf(title, link, context)
            continue

        save_announcement(
            title,
            link,
            f"Detected from {source_name}. {context}"
        )
        saved += 1

    print(f"Announcement links processed: {saved}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("          STUDIFY ICAI ACADEMIC MONITOR")
    print("=" * 60)

    for source in SOURCE_PAGES:
        if source["kind"] == "announcements":
            monitor_announcements(
                source["name"],
                source["url"]
            )
        else:
            crawl_academic_pages(
                source["name"],
                source["url"]
            )

    print("\n" + "=" * 60)
    print("ICAI monitoring run completed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
