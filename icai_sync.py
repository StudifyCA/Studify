#!/usr/bin/env python3
"""Studify: download new ICAI PDFs and keep an index. Runs on GitHub Actions (standard library only).
Output: icai-docs/<category>/<file>.pdf and icai-docs/index.json  (the app reads index.json).
Only files hosted on icai.org (and its sub-domains) are downloaded. Edit icai-sources.txt to change the pages that are read."""
import json, os, re, sys, time, hashlib, subprocess, urllib.request, urllib.parse, html, datetime

OUT = "icai-docs"
MAX_FILE = 150 * 1024 * 1024       # skip files bigger than 150 MB
TAG = "icai-files"                 # GitHub Release that stores the PDFs (does not count in the repo or Pages size)
REPO = os.environ.get("GITHUB_REPOSITORY", "")
T0 = time.time(); MAX_SECONDS = 150 * 60
MAX_TOTAL = 12 * 1024 * 1024 * 1024  # safety stop at 12 GB of release files
MAX_NEW = 200                       # new downloads per run (backlog is filled run by run)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb" "Kit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
DEFAULT_SOURCES = ["https://www.icai.org/post/study-material-nset", "https://www.icai.org/post/e-resources-study-material-nset", "https://www.icai.org/post/question-papers-new-scheme-of-education-and-training", "https://www.icai.org/category/bos-knowledge-portal", "https://www.icai.org/category/student-examination", "https://www.icai.org/post/exam"]
INC = re.compile(r"exam|foundation|inter|final|rtp|mtp|syllabus|study|question|paper|result|schedule|date.?sheet|guide|mcq|amend|bos[-_]|scheme|revision|mock|announ|notification|time.?table|admit|registration|revised|suggested|capsule|booklet", re.I)
EXC = re.compile(r"brochure|campus|advt|advert|enrol|fellow|membership|cfmip|cabf|grant|removal|cancel|nameres|pay_ann|\bfees?\b|contact|benevolent|tender|vacanc|recruit|newsletter|annual.?report|cfp|esb20|\bmss\d|srsb|cg_|\bpqc|coi|\bm_|elect|council|member|\bbye\b|dialogo|torch|president|annual|journal|\bcpe\b|webinar|branch|region|\bsar\b|\bsabr|manual", re.I)
def relevant(t, u):
    s = t + " " + urllib.parse.unquote(u.split("?")[0].rsplit("/", 1)[-1])
    return bool(INC.search(s)) and not EXC.search(s)
CTXP = re.compile(r"nextca\.in/|/post/(sm-|[a-z]+-nset|study-material|e-resources|self-paced|question-papers|rtp|mtp|mock|model|revision)|post_id=19872|rtp|mtp|capsule", re.I)
GENERIC = re.compile(r"^(click here|here|download|view|pdf|read more|more|link|details|open)\b", re.I)
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
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8", "Accept-Language": "en-IN,en;q=0.9", "Referer": "https://www.icai.org/", "Upgrade-Insecure-Requests": "1", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "same-site"})
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
        if (ok_host(u) or (urllib.parse.urlparse(u).hostname or "").endswith("nextca.in")) and len(u) < 480:
            out.append((u, clean(m.group(2))))
    return out

def levels(t):
    tk = set(re.split(r"[^a-z0-9]+", t.lower())); o = []
    if tk & {"foundation", "fnd", "cpt"}: o.append("foundation")
    if tk & {"inter", "intermediate", "int", "ipc", "ipcc"}: o.append("inter")
    if tk & {"final", "finals", "fin"}: o.append("final")
    return o or ["foundation", "inter", "final"]

def cat(t, u):
    s = re.sub(r"[-_/]+", " ", (t + " " + u).lower())
    for name, rx in [("RTP", r"\brtp\b|revisionary"), ("MTP", r"\bmtp\b|mock test|model test"), ("Past paper", r"question paper|past paper|exam paper|suggested answer|\bqp\b"),
                     ("Syllabus", r"syllabus"), ("Study material", r"study material|\bsm\b|nset|module|\bchapter\b|\bunit\b|capsule|glossary"), ("Result", r"result"),
                     ("Announcement", r"announcement|notice|exam form|date sheet|schedule|notification|amendment|\bexam\b|exam-|admit|guide")]:
        if re.search(rx, s): return name
    return "Other"

def slug(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-")[:70] or "file"


def gh(*a):
    return subprocess.run(["gh"] + list(a), capture_output=True, text=True)

def ensure_release():
    if not REPO: return False
    if gh("release", "view", TAG).returncode == 0: return True
    r = gh("release", "create", TAG, "--title", "ICAI files", "--notes", "PDF files copied from icai.org by the Studify sync. Do not delete.")
    if r.returncode != 0: say("release create failed:", (r.stderr or "")[:150])
    return r.returncode == 0

def upload(path):
    r = gh("release", "upload", TAG, path, "--clobber")
    if r.returncode != 0:
        say("upload failed", os.path.basename(path), (r.stderr or "")[:120]); return None
    return "https://github.com/%s/releases/download/%s/%s" % (REPO, TAG, os.path.basename(path))

def main():
    os.makedirs(OUT, exist_ok=True)
    idx_path = os.path.join(OUT, "index.json")
    try:
        old = json.load(open(idx_path, encoding="utf-8"))
        items = old.get("items", [])
    except Exception:
        items = []
    keep = []
    for x in items:
        drop = False
        if x.get("f"):
            if x.get("k"):
                drop = not x.get("p") or not CTXP.search(x.get("p", ""))
            else:
                drop = not relevant(x["t"], x["url"])
        if drop:
            try: os.remove(x["f"])
            except Exception: pass
            say("removed unrelated", x["f"]); continue
        keep.append(x)
    items = keep
    have = {x["url"] for x in items}
    total = sum(x.get("s", 0) for x in items)
    rel_ok = ensure_release()
    if rel_ok:
        for x in items:
            f = x.get("f")
            if f and f.startswith("icai-docs/") and os.path.exists(f):
                url2 = upload(f)
                if url2:
                    x["f"] = url2
                    try: os.remove(f)
                    except Exception: pass
                    say("moved to release", os.path.basename(f))
    src = DEFAULT_SOURCES
    if os.path.exists("icai-sources.txt"):
        src = [l.strip() for l in open("icai-sources.txt", encoding="utf-8") if l.strip().startswith("https://")] or DEFAULT_SOURCES
    found = {}   # pdf url -> link text
    ctx = {}     # pdf url -> page it was found on
    ptl = {}     # page url -> page title
    pages_ok = 0
    FOLLOW = re.compile(r"nextca\.in/[a-z0-9/_-]*(rtp|mtp|pyq|paper|study|material|notes|question|foundation|inter|final|chapter|subject|revision|mock)[a-z0-9/_-]*|/post/(sm-|foundation-nset|intermediate-nset|final-nset|study-material|e-resources|self-paced|question-papers|rtp|mtp|mock|model|revision|exam-|bos-|suggested)|/category/(bos-knowledge-portal|student-examination|board-of-studies-announcements|examination-students|announcements)|post_id=19872|rtp|mtp|model-test|revision-test|capsule", re.I)
    PAGE_EXC = re.compile(r"elect|president|council|annual|torchbearer|news-and-media|in-news|/media|/rti|right-to-information|donate|appeal|covid|career|homage|green|hon.?ble|statistics|virtual|leadership|region|branch|member|self.service|bosactivities|vacanc|tender|contact|publication\.icai", re.I)
    HIGH = re.compile(r"nextca|sm-|-nset|question-papers|rtp|mtp|model|revision|capsule|study-material", re.I)
    import heapq
    seen = set(); heap = []; n = 0
    for u in src:
        heapq.heappush(heap, (0, n, u, 0)); n += 1
    visited = 0
    while heap and visited < 220:
        pr, _, u, depth = heapq.heappop(heap)
        if u in seen: continue
        seen.add(u)
        try:
            pg = get(u); visited += 1; pages_ok += 1
        except Exception as e:
            say("page failed", u, str(e)[:80]); continue
        tm = re.search(r"<title[^>]*>(.*?)</title>", pg, re.I | re.S)
        ptl[u] = clean(tm.group(1)).split("|")[0].strip()[:80] if tm else ""
        time.sleep(0.3)
        npdf = 0
        for lu, lt in links(pg, u):
            if re.search(r"\.pdf(\?|$)", lu, re.I):
                if not ok_host(lu) or (urllib.parse.urlparse(lu).hostname or "").startswith("publication."): continue
                found.setdefault(lu, lt); ctx.setdefault(lu, u); npdf += 1
            elif depth < 4 and lu not in seen and FOLLOW.search(lu) and not PAGE_EXC.search(lu + " " + lt):
                heapq.heappush(heap, (0 if HIGH.search(lu) else 1, n, lu, depth + 1)); n += 1
        if npdf: say("  pdfs on", u[:90], ":", npdf)
    deep = []
    say("pages read:", visited, "| pdf links found:", len(found))
    new = 0
    today = datetime.date.today().isoformat()
    PRIO = {"MTP": 0, "RTP": 0, "Past paper": 1, "Syllabus": 1, "Announcement": 2, "Result": 2, "Other": 3, "Study material": 4}
    SM_BUDGET = 10 * 1024 * 1024 * 1024   # study-material downloads stop at 200 MB; the rest stay as links to icai.org
    sm_total = sum(x.get("s", 0) for x in items if x.get("c") == "Study material")
    cands = []
    for u, t in found.items():
        name = urllib.parse.unquote(u.split("?")[0].rsplit("/", 1)[-1])
        page = ctx.get(u, "")
        base = t if (len(t) >= 6 and not GENERIC.match(t)) else re.sub(r"[-_+]+", " ", re.sub(r"\.pdf$", "", name, flags=re.I))
        pt = ptl.get(page, "")
        title = base if (not pt or pt.lower() in base.lower()) else base + " | " + pt
        okctx = bool(CTXP.search(page)) and not EXC.search(title + " " + u)
        if not relevant(title, u) and not okctx:
            continue
        c = cat(title, u)
        if c == "Other": c = cat(title, page)
        hindi = bool(re.search(r"hindi", title + " " + u + " " + page, re.I))
        cands.append((PRIO.get(c, 3) + (0.5 if hindi else 0), u, name, page, title, okctx, c, hindi))
    cands.sort(key=lambda z: z[0])
    byurl = {x["url"]: x for x in items}
    for pr, u, name, page, title, okctx, c, hindi in cands:
        ex = byurl.get(u)
        if ex and ex.get("f"): continue
        can = rel_ok and new < MAX_NEW and total < MAX_TOTAL and (time.time() - T0) < MAX_SECONDS
        if can:
            folder = "icai-stage"
            os.makedirs(folder, exist_ok=True)
            fn = slug(re.sub(r"\.pdf$", "", name, flags=re.I)) + "-" + hashlib.md5(u.encode()).hexdigest()[:6] + ".pdf"
            path = os.path.join(folder, fn)
            try:
                data = get(u, binary=True, limit=MAX_FILE)
                if not data.startswith(b"%PDF"):
                    say("not a pdf", u); can = False
            except Exception as e:
                say("skip", u, str(e)[:60]); can = False
            if can:
                open(path, "wb").write(data)
                url2 = upload(path)
                try: os.remove(path)
                except Exception: pass
                if not url2:
                    can = False
            if can:
                total += len(data); new += 1
                if c == "Study material": sm_total += len(data)
                if ex: items.remove(ex)
                it = {"t": title[:140], "url": u, "f": url2, "lv": levels(title + " " + u + " " + page), "c": c, "d": today, "s": len(data), "k": 1 if okctx else 0, "p": page if okctx else ""}
                items.append(it); byurl[u] = it
                say("saved", os.path.basename(path), len(data))
                time.sleep(1)
                continue
        if not ex:
            it = {"t": title[:140], "url": u, "f": None, "lv": levels(title + " " + u + " " + page), "c": c, "d": today, "s": 0, "pdf": 1}
            items.append(it); byurl[u] = it
    say("link-only items:", sum(1 for x in items if not x.get("f")))

    # ---- official announcements list (titles and links as shown on icai.org; ICAI pages show no dates, so we record when we first saw each item)
    ANN_PAGES = ["https://www.icai.org/category/board-of-studies-announcements", "https://www.icai.org/category/examination-students", "https://www.icai.org/post/exam"]
    ann_path = os.path.join(OUT, "announcements.json")
    try:
        oldann = json.load(open(ann_path, encoding="utf-8")); first_run = False
    except Exception:
        oldann = {"items": []}; first_run = True
    known = {x["url"]: x for x in oldann.get("items", [])}
    ordered = []
    for ap in ANN_PAGES:
        try: pg = get(ap)
        except Exception as e:
            say("announcement page failed", ap, str(e)[:60]); continue
        for lu, lt in links(pg, ap):
            if not ok_host(lu) or len(lt) < 12: continue
            isp = bool(re.search(r"\.pdf(\?|$)", lu, re.I))
            if not isp and not re.search(r"/post/(exam|bos|new-scheme)", lu, re.I): continue
            if EXC.search(lt + " " + lu) or re.search(r"contact|checker|observer|member", lt, re.I): continue
            if lu not in [o[0] for o in ordered]: ordered.append((lu, lt, isp))
    newann = 0
    for rank, (lu, lt, isp) in enumerate(ordered):
        if lu in known:
            known[lu]["r"] = rank; continue
        known[lu] = {"t": lt[:160], "url": lu, "pdf": 1 if isp else 0, "d": "" if first_run else today, "r": rank}
        newann += 1
    anns = sorted(known.values(), key=lambda x: (x.get("r", 999), ))[:150]
    json.dump({"updated": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S') + "Z", "items": anns}, open(ann_path, "w", encoding="utf-8"), ensure_ascii=False)
    say("announcements:", len(anns), "| new this run:", 0 if first_run else newann)
    items.sort(key=lambda x: x.get("d", ""), reverse=True)
    items.sort(key=lambda x: 0 if x.get("f") else 1)
    json.dump({"updated": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S') + "Z", "items": items[:4000]}, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(OUT, "last_run.txt"), "w").write("\n".join(log[-60:]) + "\n")
    say("new files:", new, "| total size MB:", round(total / 1048576, 1))
    if pages_ok == 0:
        sys.exit("No ICAI page could be reached. See log above.")

if __name__ == "__main__":
    main()
