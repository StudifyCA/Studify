                    is_pdf = probe_pdf_link(link)

            if is_pdf:
                if link not in saved_pdf_urls:
                    save_pdf(title, link, f"{source_name} {context}")
                    saved_pdf_urls.add(link)
                    pdfs_found += 1
                continue

            if depth < MAX_DEPTH and should_crawl_link(title, link, context):
                if link not in visited:
                    queue.append((link, depth + 1))

    print(
        f"Finished {source_name}. Pages checked: {pages_checked}. "
        f"Unique PDF links found: {pdfs_found}."
    )


# ============================================================
# ANNOUNCEMENT MONITOR
# ============================================================

def monitor_announcements(source_name, page_url):
    print(f"\nChecking announcements: {source_name}")

    html = fetch_page(page_url)
    if not html:
        print(f"Announcement source unavailable: {page_url}")
        return

    links = extract_links(page_url, html)
    saved = 0
    seen = set()

    for item in links:
        title = item["title"]
        link = item["url"]
        context = item["context"]

        if link in seen:
            continue
        seen.add(link)

        parsed = urlparse(link)
        path = parsed.path.lower()

        if path.startswith("/category/"):
            continue

        if not (
            path.startswith("/post/")
            or "/announcement" in path
            or "/notification" in path
            or "/newsevent/" in path
        ):
            continue

        if not title or len(title) < 8:
            continue

        if any(word in title.lower() for word in IGNORE_LINK_WORDS):
            continue

        if is_pdf_url(link):
            save_pdf(title, link, context)
            continue

        save_announcement(
            title,
            link,
            f"Detected from {source_name}. {context}",
        )
        saved += 1

    print(f"Announcement links processed: {saved}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 64)
    print("             STUDIFY ICAI ACADEMIC MONITOR v3")
    print("=" * 64)

    total_sources = 0
    for source in SOURCE_PAGES:
        total_sources += 1
        if source["kind"] == "announcements":
            monitor_announcements(source["name"], source["url"])
        else:
            crawl_academic_pages(source["name"], source["url"])

    print("\n" + "=" * 64)
    print(f"ICAI monitoring run completed. Sources attempted: {total_sources}")
    print("PDF links and announcement metadata are sent to Supabase.")
    print("This script does NOT download PDF files or create a ZIP archive.")
    print("=" * 64)


if __name__ == "__main__":
    main()
