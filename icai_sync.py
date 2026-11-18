#!/usr/bin/env python3
"""Studify: download new ICAI PDFs and keep an index. Runs on GitHub Actions (standard library only).
Output: icai-docs/<category>/<file>.pdf and icai-docs/index.json  (the app reads index.json).
Only files hosted on icai.org (and its sub-domains) are downloaded. Edit icai-sources.txt to change the pages that are read."""
import json, os, re, sys, time, hashlib, urllib.request, urllib.parse, html, datetime

OUT = "icai-docs"
MAX_FILE = 40 * 1024 * 1024        # skip files bigger than 40 MB
MAX_TOTAL = 500 * 1024 * 1024      # stop downloading when icai-docs reaches 500 MB (GitHub Pages limit is 1 GB)
MAX_NEW = 30                       # new downloads per run (backlog is filled run by run)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb" "Kit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
DEFAULT_SOURCES = ["https://www.icai.org/", "https://boslive.icai.org/", "https://www.icai.org/post/announcements"]
log = []
def say(*a):
    t = " ".join(str(x) for x in a); print(t); log.append(t)

def ok_host(u):
    try:
        h = urllib.parse.urlparse(u).hostname or ""
        return h == "icai.org" or h.endswith(".icai.org")
    except Exception:
        return False

def get(url, binary=False, limit=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-IN,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=40) as r:
        if limit:
            cl = r.headers.get("Content-Length")
            if cl and int(cl) > limit:
                raise ValueError("too big %s" % cl)
        data = r.read(limit + 1 if limit else -1)
        if limit and len(data) > limit:
            raise ValueError("too big")
        return data if binary else data.decode("utf-8", "replace")

def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", s or ""))).strip()

def links(page, base):
    out = []
    for m in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', page, re.I | re.S):
        try:
            u = urllib.parse.urljoin(base, html.unescape(m.group(1).strip()))
        except Exception:
            continue
        if ok_host(u) and len(u) < 480:
            out.append((u, clean(m.group(2))))
    return out

def levels(t):
    t = t.lower(); o = []
    if re.search(r"foundation|\bcpt\b", t): o.append("foundation")
    if re.search(r"\binter(mediate)?\b|\bipc", t): o.append("inter")
    if re.search(r"\bfinals?\b", t): o.append("final")
    return o or ["foundation", "inter", "final"]

def cat(t, u):
    s = (t + " " + u).lower()
    for name, rx in [("RTP", r"\brtp\b|revisionary"), ("MTP", r"\bmtp\b|mock test"), ("Past paper", r"question paper|past paper|exam paper|suggested answer|\bqp\b"),
                     ("Syllabus", r"syllabus"), ("Study material", r"study material|module|\bchapter\b|\bunit\b"), ("Result", r"result"),
                     ("Announcement", r"announcement|notice|exam form|date sheet|schedule|notification|amendment")]:
        if re.search(rx, s): return name
    return "Other"

def slug(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-")[:70] or "file"

def main():
    os.makedirs(OUT, exist_ok=True)
    idx_path = os.path.join(OUT, "index.json")
    try:
        old = json.load(open(idx_path, encoding="utf-8"))
        items = old.get("items", [])
    except Exception:
        items = []
    have = {x["url"] for x in items}
    total = sum(x.get("s", 0) for x in items)
    src = DEFAULT_SOURCES
    if os.path.exists("icai-sources.txt"):
        src = [l.strip() for l in open("icai-sources.txt", encoding="utf-8") if l.strip().startswith("https://")] or DEFAULT_SOURCES
    found = {}   # url -> title
    pages_ok = 0
    deep = []
    for u in src:
        try:
            pg = get(u); pages_ok += 1
        except Exception as e:
            say("page failed", u, str(e)[:80]); continue
        for lu, lt in links(pg, u):
            if re.search(r"\.pdf(\?|$)", lu, re.I):
                found.setdefault(lu, lt)
            elif re.search(r"/post/|post_id=|announcement|rtp|mtp|study|syllabus|question", lu, re.I) and lu not in deep:
                deep.append((lu, lt))
    say("seed pages ok:", pages_ok, "of", len(src), "| deeper pages:", len(deep))
    for lu, lt in deep[:60]:
        try:
            pg = get(lu)
        except Exception:
            continue
        for pu, pt in links(pg, lu):
            if re.search(r"\.pdf(\?|$)", pu, re.I):
                found.setdefault(pu, pt or lt)
    say("pdf links found:", len(found))
    new = 0
    today = datetime.date.today().isoformat()
    for u, t in found.items():
        if u in have: continue
        if new >= MAX_NEW or total >= MAX_TOTAL: break
        name = urllib.parse.unquote(u.split("?")[0].rsplit("/", 1)[-1])
        title = t if len(t) >= 6 else re.sub(r"[-_+]+", " ", re.sub(r"\.pdf$", "", name, flags=re.I))
        c = cat(title, u)
        folder = os.path.join(OUT, slug(c).lower())
        os.makedirs(folder, exist_ok=True)
        fn = slug(re.sub(r"\.pdf$", "", name, flags=re.I)) + "-" + hashlib.md5(u.encode()).hexdigest()[:6] + ".pdf"
        path = os.path.join(folder, fn)
        try:
            data = get(u, binary=True, limit=MAX_FILE)
        except Exception as e:
            say("skip", u, str(e)[:60]); continue
        if not data.startswith(b"%PDF"):
            say("not a pdf", u); continue
        open(path, "wb").write(data)
        total += len(data); new += 1
        items.append({"t": title[:140], "url": u, "f": path.replace(os.sep, "/"), "lv": levels(title + " " + u), "c": c, "d": today, "s": len(data)})
        say("saved", path, len(data))
        time.sleep(1)
    # announcements without a pdf: keep as links
    for u, t in list(deep):
        if u in have or len(t) < 12: continue
        if cat(t, u) == "Announcement" and not any(x["url"] == u for x in items):
            items.append({"t": t[:140], "url": u, "f": None, "lv": levels(t), "c": "Announcement", "d": today, "s": 0})
    items.sort(key=lambda x: x.get("d", ""), reverse=True)
    json.dump({"updated": datetime.datetime.utcnow().isoformat() + "Z", "items": items[:1500]}, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(OUT, "last_run.txt"), "w").write("\n".join(log[-60:]) + "\n")
    say("new files:", new, "| total size MB:", round(total / 1048576, 1))
    if pages_ok == 0:
        sys.exit("No ICAI page could be reached. See log above.")

if __name__ == "__main__":
    main()
