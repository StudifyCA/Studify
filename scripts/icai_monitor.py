import os
import re
import time
import hashlib
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag, unquote

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# STUDIFY ICAI MONITOR
# Discovers ICAI academic PDFs and relevant announcements.
# Saves PDF links and metadata to Supabase.
#
# IMPORTANT:
# This monitor stores PDF LINKS in Supabase. It does not upload
# PDF file bytes to Supabase Storage and does not create a ZIP.
# ============================================================

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=ignore-duplicates",
}

# ICAI official starting pages. The BoS portal is included as a
# discovery source, but it may deny automated requests (403).
SOURCE_PAGES = [
    {
        "name": "ICAI Announcements",
        "url": "https://www.icai.org/category/announcements/3",
        "kind": "announcements",
    },
    {
        "name": "ICAI Board of Studies Announcements",
        "url": "https://www.icai.org/category/board-of-studies-announcements",
        "kind": "announcements",
    },
    {
        "name": "ICAI Study Material",
        "url": "https://www.icai.org/post/study-material-nset",
        "kind": "academic",
    },
    {
        "name": "ICAI New Scheme",
        "url": "https://www.icai.org/post/new-scheme-of-education-and-training",
        "kind": "academic",
    },
    {
        "name": "Foundation RTP January 2027",
        "url": "https://www.icai.org/post/rtp-foundation-course-jan2027",
        "kind": "academic",
    },
    {
        "name": "Intermediate RTP January 2027",
        "url": "https://www.icai.org/post/rtp-intermediate-course-jan2027",
        "kind": "academic",
    },
    {
        "name": "ICAI BoS Knowledge Portal",
        "url": "https://boslive.icai.org/",
        "kind": "academic",
    },
]

# Permit the root ICAI domains and their subdomains only.
# Examples: www.icai.org, boslive.icai.org, kb.icai.org.
def is_allowed_icai_host(host):
    host = (host or "").lower().split(":")[0].rstrip(".")
    return host == "icai.org" or host.endswith(".icai.org")


ACADEMIC_KEYWORDS = [
    "study material", "study-material", "foundation", "intermediate",
    "final course", "rtp", "revision test", "revision-test",
    "mtp", "mock test", "mock-test", "question paper", "question-paper",
    "suggested answer", "suggested-answer", "answer key", "answer-key",
    "case study", "case-study", "case scenario", "syllabus",
    "new scheme", "new-scheme", "amendment", "supplementary",
    "academic", "board of studies", "bos", "mcq", "practice",
    "statutory update", "judicial update", "saransh",
]

IGNORE_LINK_WORDS = [
    "home", "overview", "about icai", "contact us", "members",
    "privacy policy", "terms", "copyright", "sitemap", "facebook",
    "twitter", "instagram", "linkedin", "youtube", "tender",
    "career", "placement", "advertisement", "certificate course",
    "startup", "cooperative", "mediation", "indas registration",
]
