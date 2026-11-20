# Reads SCANNED (image-only) ICAI MCQ PDFs with Gemini and adds the questions to icai-docs/mcq/<level>.json
# Needs the GitHub secret GEMINI_API_KEY. Without it this script does nothing.
import base64, datetime, hashlib, json, os, re, sys, tempfile, time, urllib.request, urllib.error

sys.argv = sys.argv[:1]
import importlib.util
_spec = importlib.util.spec_from_file_location("mcq_extract", os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcq_extract.py"))
ME = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ME)

KEY = os.environ.get("GEMINI_API_KEY", "").strip()
BASE = os.environ.get("GEMINI_BASE", "https://generativelanguage.googleapis.com")
def pick_models():
    """Ask Google which flash models this key can use (model names change over time)."""
    names = []
    try:
        with urllib.request.urlopen("%s/v1beta/models?key=%s&pageSize=200" % (BASE, KEY), timeout=60) as r:
            j = json.loads(r.read().decode())
        for m in j.get("models", []):
            n = (m.get("name") or "").replace("models/", "")
            if "generateContent" not in (m.get("supportedGenerationMethods") or []): continue
            if "flash" not in n or any(b in n for b in ("image", "tts", "live", "audio", "embed", "robotics", "computer", "-8b", "thinking")): continue
            names.append(n)
    except Exception as e:
        print("model list failed:", str(e)[:120], flush=True)
    def k(n):
        v = re.search(r"(\d+(?:\.\d+)?)", n)
        return (-(float(v.group(1)) if v else 0), "lite" in n, "preview" in n or "exp" in n, n)
    out = [os.environ.get("AI_MODEL", "").strip(), "gemini-flash-latest"] + sorted(set(names), key=k)[:4] + ["gemini-2.5-flash"]
    seen = []
    for m in out:
        if m and m not in seen: seen.append(m)
    return seen
MODELS = []
MAX_FILES = 12
MAX_SECONDS = 30 * 60
MAX_PDF = 14 * 1024 * 1024
T0 = time.time()
OUT = ME.OUT
MQ = ME.MQ

PROMPT = """This is a scanned ICAI (CA course) exam / test paper. Extract EVERY multiple choice question (MCQ) with exactly four options.
Return ONLY a JSON array. Each item: {"n": question number (integer), "q": question text, "o": [option A, option B, option C, option D] (text without the A/B/C/D labels), "a": index of the correct option 0-3, or -1 if the document does not give the answer, "x": the case scenario / passage text this question belongs to (max 600 characters, or "" if none)}.
Rules: copy numbers, amounts and section/standard names exactly; use the rupee sign for rupee amounts; if the document has an answer key table, use it for "a"; never guess an answer; skip descriptive (non-MCQ) questions; no explanations."""

def say(*a): print(*a, flush=True)

FATAL = {"v": False}

def call(pdf_b64):
    last = ""
    soft = False
    for m in MODELS:
        for mt in (30000, 12000):
            body = {"contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "application/pdf", "data": pdf_b64}}, {"text": PROMPT}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": mt, "responseMimeType": "application/json"}}
            for attempt in range(3):
                try:
                    req = urllib.request.Request("%s/v1beta/models/%s:generateContent?key=%s" % (BASE, m, KEY), data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=300) as r:
                        j = json.loads(r.read().decode())
                    parts = ((j.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
                    txt = "".join(p.get("text", "") for p in parts)
                    if txt.strip(): return txt
                    last = "empty answer"; break
                except urllib.error.HTTPError as e:
                    msg = re.sub(r"\s+", " ", e.read().decode("utf-8", "ignore"))[:300]
                    last = "[%s] HTTP %s %s" % (m, e.code, msg)
                    if e.code not in (401, 403, 404): soft = True
                    if e.code == 429: time.sleep(30 * (attempt + 1)); continue
                    if e.code in (400,) and mt == 30000: break      # retry with smaller output
                    if e.code in (404, 403): break                   # try next model
                    time.sleep(5)
                except Exception as e:
                    last = str(e)[:120]; soft = True; time.sleep(5)
    say("  AI failed:", last)
    if not soft: FATAL["v"] = True      # every model refused (bad key / no model): stop instead of burning retries
    return None

def parse(txt):
    t = txt.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    try: arr = json.loads(t)
    except Exception:
        i, j = t.find("["), t.rfind("]")
        if i < 0 or j <= i: return []
        try: arr = json.loads(t[i:j + 1])
        except Exception: return []
    if isinstance(arr, dict): arr = arr.get("questions") or arr.get("items") or []
    out = []
    for q in arr if isinstance(arr, list) else []:
        try:
            o = [str(x).strip() for x in q["o"]]
            if len(o) != 4 or any(not x for x in o) or len(set(x.lower() for x in o)) < 4: continue
            a = int(q.get("a", -1)); a = a if -1 <= a <= 3 else -1
            qq = re.sub(r"\s+", " ", str(q["q"])).strip()
            if len(qq) < 10 or len(qq) > 1500: continue
            out.append({"n": int(q.get("n") or 0), "q": qq, "o": [x[:400] for x in o], "a": a, "x": re.sub(r"\s+", " ", str(q.get("x") or "")).strip()[:600]})
        except Exception:
            continue
    return out

def main():
    if not KEY:
        say("GEMINI_API_KEY not set - skipping scanned MCQ PDFs"); return
    MODELS[:] = pick_models()
    say("models to try:", ", ".join(MODELS))
    idx = ME.jload(os.path.join(OUT, "index.json"), {}).get("items", [])
    done = ME.jload(os.path.join(MQ, "done.json"), {})
    vdone = ME.jload(os.path.join(MQ, "vdone.json"), {})
    shards = {}
    def shard(lv):
        if lv not in shards: shards[lv] = ME.jload(os.path.join(MQ, lv + ".json"), {"items": []})
        return shards[lv]
    cand = []
    for x in idx:
        f = x.get("f") or ""
        if not f.startswith("http") or "mcq" not in (f.rsplit("/", 1)[-1] + (x.get("t") or "")).lower(): continue
        if done.get(f, {}).get("n", 0) > 0: continue                 # text version already gave questions
        v = vdone.get(f)
        if v and (v.get("n", -1) >= 0 or v.get("fail", 0) >= 3): continue
        cand.append(x)
    say("scanned MCQ PDFs to read with AI:", len(cand))
    nf = 0; tot = 0
    tmp = tempfile.mkdtemp()
    for x in cand:
        if nf >= MAX_FILES or time.time() - T0 > MAX_SECONDS: break
        nf += 1
        f = x["f"]; p = os.path.join(tmp, "f.pdf")
        if not ME.fetch(f, p): vdone[f] = {"n": -1, "fail": vdone.get(f, {}).get("fail", 0) + 1}; continue
        raw = open(p, "rb").read(); os.remove(p)
        if len(raw) > MAX_PDF: say("  too big for AI:", f.rsplit("/", 1)[-1]); vdone[f] = {"n": 0, "fail": 3}; continue
        txt = call(base64.b64encode(raw).decode())
        if txt is None:
            if FATAL["v"]:
                say("stopping: no usable Gemini model for this key"); break
            vdone[f] = {"n": -1, "fail": vdone.get(f, {}).get("fail", 0) + 1}
            continue
        qs = parse(txt)
        lv = x["lv"][0] if isinstance(x.get("lv"), list) and len(x["lv"]) == 1 else "misc"
        sh = shard(lv); bk = ME.base_key(x.get("t") or ""); lab = ME.label_of(x)
        have = {hashlib.md5(q["q"].lower().encode()).hexdigest()[:12] for q in sh["items"]}
        add = 0
        for q in qs:
            h = hashlib.md5(q["q"].lower().encode()).hexdigest()[:12]
            if h in have: continue
            have.add(h)
            it = {"i": h, "q": q["q"], "o": q["o"], "a": q["a"], "s": lab, "c": x.get("c", ""), "b": bk, "n": q["n"], "v": 1}
            if q["x"]: it["x"] = q["x"]
            sh["items"].append(it); add += 1
        sh["items"] = sh["items"][-ME.MAX_PER_SHARD:]
        vdone[f] = {"n": add, "d": str(datetime.date.today())}
        tot += add
        say("  AI read", add, "/", len(qs), "answers:", sum(1 for q in qs if q["a"] >= 0), "|", lab, "|", f.rsplit("/", 1)[-1][:50])
        time.sleep(8)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for lv, sh in shards.items():
        sh["updated"] = now
        ME.jsave(os.path.join(MQ, lv + ".json"), sh)
    ME.jsave(os.path.join(MQ, "vdone.json"), vdone)
    stat = {}
    for fn in os.listdir(MQ) if os.path.isdir(MQ) else []:
        if fn.endswith(".json") and fn not in ("done.json", "keys.json", "stats.json", "vdone.json"):
            its = ME.jload(os.path.join(MQ, fn), {}).get("items", [])
            stat[fn[:-5]] = [len(its), sum(1 for q in its if q.get("a", -1) >= 0)]
    ME.jsave(os.path.join(MQ, "stats.json"), {"levels": stat, "updated": now})
    say("AI read", nf, "PDFs | new MCQs:", tot, "|", stat)

if __name__ == "__main__":
    main()
