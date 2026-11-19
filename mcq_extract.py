# Reads saved ICAI PDFs (GitHub Release) and extracts MCQs into icai-docs/mcq/<level>.json
# Standard library + pdftotext (preinstalled on GitHub runners). Optional fallback: pypdf.
import json, os, re, subprocess, sys, time, hashlib, urllib.request, tempfile, datetime

OUT = "icai-docs"
MQ = os.path.join(OUT, "mcq")
MAX_SECONDS = 40 * 60
MAX_FILES = 80
MAX_BYTES = 90 * 1024 * 1024
MAX_PER_FILE = 500
MAX_PER_SHARD = 8000
T0 = time.time()

def say(*a): print(*a, flush=True)

def jload(p, d):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d

def jsave(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

def fetch(url, dest):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 studify-bot"})
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
            n = 0
            while True:
                b = r.read(1 << 20)
                if not b: break
                n += len(b)
                if n > MAX_BYTES: return False
                f.write(b)
        return True
    except Exception as e:
        say("  download failed", str(e)[:80])
        return False

def text_of(path):
    try:
        r = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, timeout=240)
        t = r.stdout.decode("utf-8", "ignore")
        if len(t.strip()) > 200: return t
    except Exception:
        pass
    try:
        import pypdf
        rd = pypdf.PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in rd.pages[:400])
    except Exception:
        return ""

QSPLIT = re.compile(r"(?m)^[ \t]*(?:Q(?:uestion)?\.?[ \t]*(\d{1,3})[ \t]*[\.\):]?|(\d{1,3})[ \t]*[\.\)])[ \t]+(?=\S)")
OPT = re.compile(r"(?:(?<=\s)|^)\(?([a-dA-D])[\.\)]\s+")
ANS = re.compile(r"(?i)(?:correct\s+)?(?:answer|ans|key)\s*(?:is|option)?\s*[:\-–=]?\s*\(?([a-d])\)?(?![a-z])")
KEYP = re.compile(r"(?<![\d])(\d{1,3})\s*[\.\)\:\-–]?\s*\(?\s*([a-dA-D])\s*\)?(?=\s|,|;|$)")

def norm(s): return re.sub(r"\s+", " ", s).strip()

def parse_block(num, blk):
    m0 = None
    for m in OPT.finditer(blk):
        if m.group(1).lower() == "a":
            m0 = m; break
    if not m0: return None
    stem = norm(blk[:m0.start()])
    rest = blk[m0.start():]
    pos = []; want = "a"
    for m in OPT.finditer(rest):
        if m.group(1).lower() == want:
            pos.append(m); want = chr(ord(want) + 1)
            if want == "e": break
    if len(pos) < 4: return None
    opts = []
    for i, m in enumerate(pos):
        end = pos[i + 1].start() if i + 1 < len(pos) else len(rest)
        opts.append(rest[m.end():end])
    tail = re.split(r"(?i)\banswer\s*keys?\b|\bkey\s*to\s*answers?\b", opts[3])[0]
    a = -1
    opts[3] = tail
    am = ANS.search(tail)
    if am:
        a = "abcd".index(am.group(1).lower()); opts[3] = tail[:am.start()]
    opts = [norm(o) for o in opts]
    opts[3] = re.sub(r"\s*Page\s*\d+.*$", "", opts[3]).strip()
    if len(stem) < 12 or any(not o for o in opts) or len(set(o.lower() for o in opts)) < 4: return None
    if any(len(o) > 400 for o in opts) or len(stem) > 1500: return None
    return {"n": int(num), "q": stem, "o": opts, "a": a}

def key_map(text):
    # answer key region: after a heading containing answer/key, or the last 30% of the file
    i = -1
    for m in re.finditer(r"(?im)^\s*(answer\s*key|answers?|key\s*to\s*answers?|solutions?\s*key)\b", text):
        i = m.start()
    seg = text[i:] if i >= 0 else text[int(len(text) * 0.7):]
    mp = {}
    for m in KEYP.finditer(seg):
        n = int(m.group(1))
        if 1 <= n <= 200 and n not in mp: mp[n] = "abcd".index(m.group(2).lower())
    return mp

def extract(text):
    text = text.replace("\x0c", "\n")
    idx = list(QSPLIT.finditer(text))
    qs = []
    for i, m in enumerate(idx):
        end = idx[i + 1].start() if i + 1 < len(idx) else len(text)
        blk = text[m.end():end]
        if len(blk) > 3000: blk = blk[:3000]
        q = parse_block(m.group(1) or m.group(2), blk)
        if q: qs.append(q)
    # keep a single increasing run per number (drops page numbers / sub-lists)
    seen = {}; res = []
    for q in qs:
        k = (q["n"], q["q"][:40])
        if k in seen: continue
        seen[k] = 1; res.append(q)
    km = key_map(text) if res else {}
    miss = [q for q in res if q["a"] < 0]
    if miss and km and sum(1 for q in miss if q["n"] in km) >= 0.6 * len(miss):
        for q in miss:
            if q["n"] in km: q["a"] = km[q["n"]]
    return res[:MAX_PER_FILE], km

def base_key(t):
    s = t.lower()
    s = re.sub(r"\b(answers?|keys?|solutions?|ans)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)[:60]

def prio(x):
    t = ((x.get("t") or "") + " " + (x.get("f") or "")).lower()
    if "mcq" in t: return 0
    if re.search(r"rtp|mtp|revision|mock|model|test", t): return 1
    if re.search(r"question|paper|exam", t) and "guid" not in t: return 2
    return 3

def main():
    idx = jload(os.path.join(OUT, "index.json"), {}).get("items", [])
    done = jload(os.path.join(MQ, "done.json"), {})
    keys = jload(os.path.join(MQ, "keys.json"), {})
    shards = {}
    def shard(lv):
        if lv not in shards: shards[lv] = jload(os.path.join(MQ, lv + ".json"), {"items": []})
        return shards[lv]
    cand = [x for x in idx if (x.get("f") or "").startswith("http") and (x["f"] not in done or (done[x["f"]].get("n") == -1 and done[x["f"]].get("fail", 0) < 3))]
    cand.sort(key=prio)
    say("pdfs to scan:", len(cand), "| already scanned:", len(done))
    nf = 0; tot = 0
    tmp = tempfile.mkdtemp()
    for x in cand:
        if nf >= MAX_FILES or time.time() - T0 > MAX_SECONDS: break
        nf += 1
        p = os.path.join(tmp, "f.pdf")
        if not fetch(x["f"], p):
            done[x["f"]] = {"n": -1, "fail": done.get(x["f"], {}).get("fail", 0) + 1, "d": str(datetime.date.today())}; continue
        text = text_of(p)
        try: os.remove(p)
        except Exception: pass
        qs, km = extract(text)
        lv = x["lv"][0] if isinstance(x.get("lv"), list) and len(x["lv"]) == 1 else "misc"
        bk = base_key(x.get("t") or "")
        if len(qs) < 3:
            if len(km) >= 10 and re.search(r"(?i)key|answer", (x.get("t") or "") + (x.get("f") or "")):
                keys[bk] = km; say("  key file", x["t"][:60], len(km))
            done[x["f"]] = {"n": 0, "d": str(datetime.date.today())}
            continue
        sh = shard(lv)
        have = {hashlib.md5(q["q"].lower().encode()).hexdigest()[:12] for q in sh["items"]}
        add = 0
        for q in qs:
            h = hashlib.md5(q["q"].lower().encode()).hexdigest()[:12]
            if h in have: continue
            have.add(h)
            sh["items"].append({"i": h, "q": q["q"], "o": q["o"], "a": q["a"], "s": x.get("t", "")[:70], "c": x.get("c", ""), "b": bk, "n": q["n"]})
            add += 1
        sh["items"] = sh["items"][-MAX_PER_SHARD:]
        done[x["f"]] = {"n": add, "d": str(datetime.date.today())}
        tot += add
        say("  mcq", add, "/", len(qs), "answers:", sum(1 for q in qs if q["a"] >= 0), "|", x.get("t", "")[:70])
    # fill missing answers from separate key files
    for sh in shards.values():
        for q in sh["items"]:
            if q["a"] < 0 and q.get("b") in keys:
                a = keys[q["b"]].get(str(q["n"]), keys[q["b"]].get(q["n"]))
                if a is not None: q["a"] = a
    for lv, sh in shards.items():
        sh["updated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        jsave(os.path.join(MQ, lv + ".json"), sh)
    jsave(os.path.join(MQ, "keys.json"), keys)
    jsave(os.path.join(MQ, "done.json"), done)
    stat = {}
    for f in os.listdir(MQ) if os.path.isdir(MQ) else []:
        if f.endswith(".json") and f not in ("done.json", "keys.json", "stats.json"):
            its = jload(os.path.join(MQ, f), {}).get("items", [])
            stat[f[:-5]] = [len(its), sum(1 for q in its if q.get("a", -1) >= 0)]
    jsave(os.path.join(MQ, "stats.json"), {"levels": stat, "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    say("scanned", nf, "files | new MCQs:", tot, "|", stat)

main()
