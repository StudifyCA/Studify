(function () {
  var SHOW_TAB = "plan";
  var LEVEL_TAB = "inter";
  var LANG = "en";
  try { LANG = localStorage.getItem("studify_lp_lang") || "en"; } catch (e) {}
  var REF_CODE = "";
  try { REF_CODE = (localStorage.getItem("studify_ref") || "").toUpperCase(); } catch (e) {}
  var AUTH_OPEN = false;
  var AUTH_MODE = "up";

  var ESC = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };

  function calcPromo(base, code) {
    var c = String(code || "").trim().toUpperCase();
    if (!c) return { final: base, off: 0, note: "" };
    if (c === "RANKER50") return { final: Math.max(1, Math.round(base * 0.5)), off: Math.round(base * 0.5), note: "RANKER50: 50% OFF" };
    if (c === "FOUNDATION") return { final: Math.max(1, base - 10), off: 10, note: "FOUNDATION: ₹10 OFF" };
    if (/^[A-Z0-9]{4,10}$/.test(c)) return { final: Math.max(1, Math.round(base * 0.8)), off: Math.round(base * 0.2), note: c + ": 20% Referral / Launch OFF" };
    return { final: base, off: 0, note: "" };
  }

  function injectCss() {
    if (document.getElementById("st-lp-css")) return;
    var st = document.createElement("style");
    st.id = "st-lp-css";
    st.textContent = `
      .st-lp{--lp-bg:var(--bg);--lp-card:var(--card);--lp-tx:var(--tx);--lp-mut:var(--mut);--lp-bd:var(--bd);--lp-ac:var(--ac);max-width:1120px;margin:0 auto;padding:6px 10px 60px;font-family:inherit}
      .st-lp-nav{position:sticky;top:8px;z-index:18;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 14px;border-radius:16px;background:var(--card);border:1px solid var(--bd);box-shadow:0 8px 24px rgba(15,23,42,.08);backdrop-filter:blur(10px);flex-wrap:wrap}
      .st-lp-brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:17px;color:var(--tx);text-decoration:none}
      .st-lp-brand img{width:34px;height:34px;border-radius:10px;object-fit:cover}
      .st-lp-links{display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:13px;font-weight:600}
      .st-lp-links a{color:var(--mut);text-decoration:none}
      .st-lp-links a:hover{color:var(--ac)}
      .st-lp-hero{display:grid;grid-template-columns:1.08fr .92fr;gap:22px;align-items:center;padding:34px 0 24px}
      @media(max-width:860px){.st-lp-hero{grid-template-columns:1fr}.st-lp-links{display:none}}
      .st-pill{display:inline-flex;align-items:center;gap:7px;padding:5px 12px;border-radius:99px;font-size:12px;font-weight:700;background:var(--ac2);color:var(--ac);border:1px solid var(--bd)}
      .st-h1{font-size:clamp(28px,4.5vw,44px);line-height:1.12;margin:14px 0 12px;font-weight:800;letter-spacing:-.02em}
      .st-h1 span{color:var(--ac)}
      .st-sub{font-size:15px;color:var(--mut);line-height:1.55;margin:0 0 18px}
      .st-cta{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
      .st-mock{background:var(--card);border:1px solid var(--bd);border-radius:18px;padding:16px;box-shadow:0 16px 36px rgba(15,23,42,.09)}
      .st-mock-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
      .st-sec{padding:26px 0 10px}
      .st-sec h2{font-size:24px;margin:0 0 6px;font-weight:800}
      .st-grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin-top:14px}
      .st-feat{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:16px}
      .st-feat h3{font-size:16px;margin:0 0 6px}
      .st-price{background:var(--card);border:1px solid var(--bd);border-radius:18px;padding:18px;display:flex;flex-direction:column;justify-content:space-between;position:relative}
      .st-price.pop{border:2px solid var(--ac);box-shadow:0 12px 30px rgba(79,70,229,.14)}
      .st-price-tag{position:absolute;top:-11px;right:16px;background:var(--ac);color:#fff;font-size:11px;font-weight:800;padding:3px 10px;border-radius:99px}
      .st-amt{font-size:30px;font-weight:800;margin:8px 0 4px}
      .st-ul{padding-left:18px;margin:10px 0 16px;font-size:13px;color:var(--mut);line-height:1.7}
      .st-faq details{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:12px 14px;margin-bottom:8px}
      .st-faq summary{font-weight:700;cursor:pointer}
      .st-foot{margin-top:28px;padding:22px 18px;border-radius:18px;background:var(--card);border:1px solid var(--bd);display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px}
      .st-wa-float{position:fixed;right:18px;bottom:18px;z-index:25;background:#16a34a;color:#fff;text-decoration:none;font-weight:700;font-size:13px;padding:10px 16px;border-radius:99px;box-shadow:0 10px 24px rgba(22,163,74,.35);display:inline-flex;align-items:center;gap:6px}
      .st-mdl{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:45;display:flex;align-items:center;justify-content:center;padding:14px}
      .st-mdl-in{background:var(--card);border:1px solid var(--bd);border-radius:18px;padding:18px;width:100%;max-width:440px;max-height:92vh;overflow:auto;box-shadow:0 24px 48px rgba(0,0,0,.28)}
    `;
    document.head.appendChild(st);
  }

  var SHOW_DATA = {
    plan: {
      title: "Today's Dynamic Target · CA Inter",
      badge: "1-2-7 Revision Active",
      rows: [
        ["AS 10 Property, Plant & Equipment", "45m · 1st Revision Due"],
        ["Company Law — Prospectus & Allotment", "60m · High Weightage ★"],
        ["GST — Time & Value of Supply", "40m · 15 MCQs Pending"]
      ],
      foot: "Auto-adjusts daily if you miss a day or change study hours."
    },
    timer: {
      title: "Strict Focus Timer + Buddy Lock",
      badge: "🔒 Buddy Lock ON",
      rows: [
        ["Session", "50m Study / 10m Break"],
        ["Strict Mode", "Switching tabs pauses & logs alert"],
        ["Buddy Lock", "Partner holds the 4-digit unlock PIN"]
      ],
      foot: "Chapters only tick Done after verified timer minutes."
    },
    papers: {
      title: "ICAI Vault · PYQ, MTP & RTP",
      badge: "Weightage Mapped",
      rows: [
        ["Chapter Weightage Stars ★", "Sorted by past-attempt marks frequency"],
        ["Offline PDF Library", "Verified CA students download directly"],
        ["Question Banks (FD/IN/FN)", "Chapter-tagged descriptive + MCQ drills"]
      ],
      foot: "Updated via automated ICAI sync — zero password needed."
    },
    ai: {
      title: "AI Tutor + Photo Homework Check",
      badge: "Studify Pro",
      rows: [
        ["Answer from ICAI Papers", "Grounded answers from past PYQs/RTPs"],
        ["Photo Homework Check", "Snap your written answer for instant step audit"],
        ["Lecture Key Moments", "Extract exam points from 12-hr marathon links"]
      ],
      foot: "Free for Admins & Special Category VIPs · Pro from ₹49/mo."
    }
  };

  var LEVELS_INFO = {
    foundation: {
      name: "CA Foundation",
      papers: ["FD1 Accounting", "FD2 Business Laws", "FD3 Quantitative Aptitude", "FD4 Business Economics"],
      desc: "Strong conceptual base with MCQ drills, daily targets, and negative-marking mock practice."
    },
    inter: {
      name: "CA Intermediate (Group 1 & 2)",
      papers: ["IN1 Advanced Accounting", "IN2 Corporate & Other Laws", "IN3 Taxation (DT + IDT)", "IN4 Cost & Management Acc.", "IN5 Auditing & Ethics", "IN6 FM & Strategic Mgmt"],
      desc: "Supports both Foundation route & Direct Entry, weightage stars, 1-2-7 revisions, and chapter-level PYQ mapping."
    },
    final: {
      name: "CA Final (Group 1 & 2)",
      papers: ["FN1 Financial Reporting", "FN2 Advanced Financial Mgmt", "FN3 Advanced Auditing", "FN4 Direct Tax Laws", "FN5 Indirect Tax Laws", "FN6 IBS Integrated Solutions"],
      desc: "Built for articleship schedules — flexible study-hour planning, rest days, and marathon revision tracking."
    }
  };

  var GUIDES = {
    rev: {
      t: "How 1-2-7 Spaced Revision Works in CA",
      b: "CA syllabus forgets fastest within 48 hours. When you mark a chapter Done in Studify CA, it automatically schedules revisions on Day +1, Day +2, Day +7, and pre-exam cycles so you never lose Ind AS, sections, or tax amendments."
    },
    lock: {
      t: "Buddy Lock & Strict Timer Discipline",
      b: "Enable Strict Focus and set a 4-digit PIN held by your study partner or friend. Switching away to Instagram/YouTube pauses your timer and prevents turning Strict Mode off without your buddy's code."
    },
    weight: {
      t: "ICAI Chapter Weightage ★ Strategy",
      b: "Don't study every chapter equally before exams. Studify maps PYQs, MTPs, and RTPs into chapter stars so 70% of your marks come from the highest-scoring chapters first."
    },
    earn: {
      t: "Referral Rewards & Pro Discount",
      b: "Every student gets a unique Referral Code in Settings. Share it with CA friends: they get 20% OFF Pro Monthly (₹39) or Attempt Pass (₹199), and you get +7 days of Pro added automatically!"
    }
  };

  function openTourModal() {
    var existing = document.getElementById("st-tour-mdl");
    if (existing) existing.remove();
    var m = document.createElement("div");
    m.id = "st-tour-mdl";
    m.className = "st-mdl";
    m.innerHTML = `<div class="st-mdl-in" style="max-width:620px">
      <div class="row sp"><b>🎬 Studify CA — 2-Minute App Tour</b><button class="btn sec sm" id="st-tour-x">Close</button></div>
      <div class="mut" style="margin:6px 0 10px">See how Planner → Strict Timer → Past Papers → Partner Leaderboard → Pro AI work together.</div>
      <canvas id="st-tour-cv" width="560" height="310" style="width:100%;border-radius:12px;border:1px solid var(--bd);background:#0f1220"></canvas>
      <div class="row" style="margin-top:10px">
        <button class="btn sm" id="st-tour-play">▶ Play / Pause</button>
        <button class="btn sec sm" id="st-tour-dl">⬇ Download Tour Video (.webm)</button>
        <span class="mut" id="st-tour-st">Scene 1 / 5</span>
      </div>
    </div>`;
    document.body.appendChild(m);
    var cv = document.getElementById("st-tour-cv"), cx = cv.getContext("2d");
    var scenes = [
      ["1. Dynamic Study Planner", "Set attempt & daily hours — auto-splits papers & rest days", "#4f46e5"],
      ["2. Strict Timer + Buddy Lock", "Partner holds your 4-digit unlock PIN to beat distraction", "#16a34a"],
      ["3. PYQ, MTP & RTP Weightage ★", "High-mark chapters highlighted + offline PDF vault", "#d97706"],
      ["4. Homework & MCQ Drills", "Track daily questions, mistakes ledger & 1-2-7 revisions", "#7c3aed"],
      ["5. AI Tutor & Study Partner", "Doubts grounded in ICAI papers + Global CA Leaderboard", "#0ea5e9"]
    ];
    var f = 0, run = true, raf = 0;
    function draw() {
      var idx = Math.floor(f / 110) % scenes.length, sc = scenes[idx], p = (f % 110) / 110;
      cx.fillStyle = "#0f1220"; cx.fillRect(0, 0, 560, 310);
      cx.fillStyle = sc[2]; cx.fillRect(24, 24, 512, 6);
      cx.fillStyle = "#a5b4fc"; cx.font = "bold 13px system-ui"; cx.fillText("STUDIFY CA • SMART CA PREP OS", 24, 56);
      cx.fillStyle = "#ffffff"; cx.font = "bold 24px system-ui"; cx.fillText(sc[0], 24, 96);
      cx.fillStyle = "#cbd5e1"; cx.font = "15px system-ui"; cx.fillText(sc[1], 24, 128);
      cx.fillStyle = "#181c2e"; cx.strokeStyle = "#2a3050"; cx.lineWidth = 1.5;
      cx.beginPath(); cx.roundRect(24, 154, 512, 112, 12); cx.fill(); cx.stroke();
      cx.fillStyle = sc[2]; cx.fillRect(42, 180, Math.max(30, Math.round(476 * p)), 12);
      cx.fillStyle = "#94a3b8"; cx.font = "13px system-ui";
      cx.fillText("Foundation • Intermediate • Final | Works Offline | Never asks ICAI Password", 42, 224);
      cx.fillStyle = "#4ade80"; cx.font = "bold 13px system-ui";
      cx.fillText("Pro Pass from ₹49/mo • Admin & Special Category VIP = ₹0", 42, 248);
      document.getElementById("st-tour-st").textContent = "Scene " + (idx + 1) + " / " + scenes.length;
      if (run) { f++; raf = requestAnimationFrame(draw); }
    }
    draw();
    document.getElementById("st-tour-play").onclick = function () { run = !run; if (run) draw(); };
    document.getElementById("st-tour-x").onclick = function () { run = false; cancelAnimationFrame(raf); m.remove(); };
    document.getElementById("st-tour-dl").onclick = function () {
      if (!cv.captureStream || !window.MediaRecorder) { alert("Browser video capture not supported here — use Play above!"); return; }
      var chunks = [], rec = new MediaRecorder(cv.captureStream(30));
      rec.ondataavailable = function (e) { if (e.data.size) chunks.push(e.data); };
      rec.onstop = function () {
        var a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob(chunks, { type: "video/webm" }));
        a.download = "studify-ca-tour.webm"; a.click();
      };
      f = 0; run = true; draw(); rec.start();
      setTimeout(function () { if (rec.state === "recording") rec.stop(); }, 6000);
    };
  }

  function openGuideModal(key) {
    var g = GUIDES[key]; if (!g) return;
    var m = document.createElement("div");
    m.className = "st-mdl";
    m.innerHTML = `<div class="st-mdl-in"><b>${ESC(g.t)}</b><p style="line-height:1.6;color:var(--mut)">${ESC(g.b)}</p><button class="btn" onclick="this.closest('.st-mdl').remove()">Got it</button></div>`;
    document.body.appendChild(m);
  }

  window.renderStudifyLanding = function (opts) {
    injectCss();
    opts = opts || {};
    var mk = opts.mk || "";
    if (mk && opts.autoOpenAuth) AUTH_OPEN = true;
    var curTheme = document.documentElement.dataset.theme || "light";
    var sh = SHOW_DATA[SHOW_TAB] || SHOW_DATA.plan;
    var lv = LEVELS_INFO[LEVEL_TAB] || LEVELS_INFO.inter;
    var pMo = calcPromo(49, REF_CODE), pAtt = calcPromo(249, REF_CODE), pYr = calcPromo(449, REF_CODE);

    var authModalHtml = AUTH_OPEN ? `<div class="st-mdl" id="st-auth-mdl">
      <div class="st-mdl-in">
        <div class="row sp" style="margin-bottom:8px">
          <b>${AUTH_MODE === "up" ? "Create Studify CA Account" : "Sign In to Studify CA"}</b>
          <button class="btn sec sm" id="st-auth-close">✕</button>
        </div>
        <div class="row" style="margin-bottom:10px">
          <button class="chip stab ${AUTH_MODE === "in" ? "on" : ""}" id="st-tab-in">Sign In</button>
          <button class="chip stab ${AUTH_MODE === "up" ? "on" : ""}" id="st-tab-up">Create Account</button>
        </div>
        <div class="mut" style="margin-bottom:8px">Cloud sync across phone & laptop, study partner, leaderboard & Pro Pass.</div>
        ${mk}
        <label>Email</label>
        <input type="text" id="cl-email" autocomplete="email" placeholder="you@example.com">
        <label>Password (min 6 characters)</label>
        <input type="password" id="cl-pw" autocomplete="${AUTH_MODE === "up" ? "new-password" : "current-password"}" placeholder="••••••">
        ${AUTH_MODE === "up" ? `<label>Referral / Coupon Code (optional — 20% OFF + 7 days bonus)</label>
        <input type="text" id="cl-ref" maxlength="10" placeholder="e.g. CA20 or Friend Code" value="${ESC(REF_CODE)}" style="text-transform:uppercase">` : ""}
        <div class="row" style="margin-top:12px">
          ${AUTH_MODE === "in"
            ? `<button class="btn" style="flex:1" data-act="signin">Sign in</button>`
            : `<button class="btn" style="flex:1" data-act="signup">Create account</button>`}
        </div>
        <div style="margin-top:10px;text-align:center">
          <button class="btn sec sm" data-act="skiplogin">Or try offline without an account</button>
        </div>
      </div>
    </div>` : "";

    return `<div class="st-lp">
      <nav class="st-lp-nav">
        <a class="st-lp-brand" href="#top"><img src="logo.jpg" alt="Studify CA"><span>Studify CA</span><span class="chip">v1</span></a>
        <div class="st-lp-links">
          <a href="#st-feat">${LANG === "hi" ? "फीचर्स" : "Features"}</a>
          <a href="#st-lv">${LANG === "hi" ? "CA लेवल्स" : "CA Levels"}</a>
          <a href="#st-guides">${LANG === "hi" ? "गाइड्स" : "Guides"}</a>
          <a href="#st-pricing">${LANG === "hi" ? "प्राइसिंग" : "Pricing"}</a>
          <a href="#st-faq">FAQ</a>
          <a href="#st-contact">${LANG === "hi" ? "संपर्क" : "Contact"}</a>
        </div>
        <div class="row">
          <button class="btn sec sm" id="st-lp-thm">${curTheme === "dark" ? "☀️" : "🌙"}</button>
          <button class="btn sec sm" id="st-lp-lng">${LANG === "hi" ? "EN" : "हिं"}</button>
          <button class="btn sec sm" id="st-open-in">Sign in</button>
          <button class="btn sm" id="st-open-up">Start Free →</button>
        </div>
      </nav>

      <section class="st-lp-hero" id="top">
        <div>
          <span class="st-pill">● ICAI CA Foundation • Intermediate • Final</span>
          <h1 class="st-h1">${LANG === "hi"
            ? "CA Exam Pass Karne Ka <span>Smart Study System.</span>"
            : "Your playlist got the vibe. <span>Studify gets the grades.</span>"}</h1>
          <p class="st-sub">${LANG === "hi"
            ? "Dynamic Daily Study Plan, 1-2-7 Spaced Revision, Strict Timer + Buddy Lock, PYQ/MTP/RTP Weightage, AI Tutor aur Global CA Leaderboard — ek lightweight app mein. Offline bhi chalta hai!"
            : "Auto-adjusting daily targets, 1-2-7 spaced revisions, Strict Pomodoro with Buddy Lock, Past Papers (PYQ/MTP/RTP) chapter weightage, Homework MCQ drills, and AI Tutor grounded in ICAI papers."}</p>
          <div class="st-cta">
            <button class="btn" id="st-hero-up">Start Free Account →</button>
            <button class="btn sec" id="st-hero-in">Sign In</button>
            <button class="btn sec" id="st-hero-tour">🎬 Watch 2-Min Tour</button>
          </div>
          <div style="margin-top:10px">
            <button class="btn sec sm" data-act="skiplogin">Try Offline on This Device (No Account Needed)</button>
          </div>
          <div class="mut" style="margin-top:10px">✓ Works offline on Android & Windows • ✓ Never asks for your ICAI password • ✓ Zero ads</div>
        </div>

        <div class="st-mock">
          <div class="row sp" style="margin-bottom:10px"><b>Live App Workspace</b><span class="chip ok">${ESC(sh.badge)}</span></div>
          <div class="st-mock-tabs">
            ${[["plan", "Today Plan"], ["timer", "Strict Timer"], ["papers", "ICAI Papers"], ["ai", "AI & HW"]].map(function (t) {
              return `<button class="chip stab ${SHOW_TAB === t[0] ? "on" : ""}" data-stshow="${t[0]}">${t[1]}</button>`;
            }).join("")}
          </div>
          <div style="font-weight:700;margin-bottom:8px">${ESC(sh.title)}</div>
          ${sh.rows.map(function (r) {
            return `<div class="blk"><span><b>${ESC(r[0])}</b></span><span class="mut">${ESC(r[1])}</span></div>`;
          }).join("")}
          <div class="mut" style="margin-top:10px;border-top:1px solid var(--bd);padding-top:8px">${ESC(sh.foot)}</div>
        </div>
      </section>

      <section class="st-sec" id="st-feat">
        <h2>Everything a Serious CA Aspirant Needs</h2>
        <div class="mut">No generic timers or bloated video ads — built around ICAI attempts and group strategy.</div>
        <div class="st-grid3">
          <div class="st-feat"><h3>📅 Auto-Adjusting Study Plan</h3><div class="mut">Enter exam date, groups & daily hours. Miss a day? Targets rebalance cleanly across weak papers.</div></div>
          <div class="st-feat"><h3>🔒 Strict Focus + Buddy Lock</h3><div class="mut">Timer stops when you leave the app. Hand your 4-digit PIN to a study buddy so discipline never slips.</div></div>
          <div class="st-feat"><h3>🔁 1-2-7 Spaced Revision</h3><div class="mut">Every finished chapter schedules automatic Day +1, +2, +7 and mock revisions before your attempt.</div></div>
          <div class="st-feat"><h3>📚 ICAI Vault & Chapter Stars ★</h3><div class="mut">PYQs, MTPs, RTPs mapped chapter-wise so you focus on high-weightage scoring topics first.</div></div>
          <div class="st-feat"><h3>🤖 AI Tutor & Homework Check</h3><div class="mut">Doubt solving from past papers, written answer photo audits & 12-hour lecture key-moment clipping.</div></div>
          <div class="st-feat"><h3>🏆 Partner & CA Leaderboard</h3><div class="mut">Sync study hours with your study partner, nudge each other, and compete safely via anonymous nicknames.</div></div>
        </div>
      </section>

      <section class="st-sec" id="st-lv">
        <h2>Built for All Three CA Stages</h2>
        <div class="row" style="margin-top:10px">
          ${["foundation", "inter", "final"].map(function (k) {
            return `<button class="chip stab ${LEVEL_TAB === k ? "on" : ""}" data-stlv="${k}">${ESC(LEVELS_INFO[k].name)}</button>`;
          }).join("")}
        </div>
        <div class="card" style="margin-top:12px">
          <h3>${ESC(lv.name)}</h3>
          <div class="mut" style="margin-bottom:10px">${ESC(lv.desc)}</div>
          <div class="row">${lv.papers.map(function (p) { return `<span class="chip">${ESC(p)}</span>`; }).join("")}</div>
        </div>
      </section>

      <section class="st-sec" id="st-guides">
        <h2>CA Strategy & App Guides</h2>
        <div class="st-grid3">
          <div class="st-feat"><h3>How 1-2-7 Revision Works</h3><div class="mut">Stop forgetting Ind AS, Tax amendments & sections before exams.</div><button class="btn sec sm" style="margin-top:10px" data-stgd="rev">Read Guide →</button></div>
          <div class="st-feat"><h3>Buddy Lock Focus Setup</h3><div class="mut">Lock strict mode with your partner's 4-digit PIN.</div><button class="btn sec sm" style="margin-top:10px" data-stgd="lock">Read Guide →</button></div>
          <div class="st-feat"><h3>Weightage Stars & Referrals</h3><div class="mut">Target 60+ exemptions and earn free Pro days via friend referrals.</div><button class="btn sec sm" style="margin-top:10px" data-stgd="earn">Read Guide →</button></div>
        </div>
      </section>

      <section class="st-sec" id="st-pricing">
        <div class="row sp">
          <div>
            <h2>Student-Friendly Pricing</h2>
            <div class="mut">Core study planner is Free Forever. Upgrade only if you want AI Tutor & full Pro tools.</div>
          </div>
          <div class="row">
            <input type="text" id="st-promo-in" maxlength="10" placeholder="Referral / Promo Code (e.g. CA20)" value="${ESC(REF_CODE)}" style="width:220px;text-transform:uppercase">
            <button class="btn sec sm" id="st-promo-apply">Apply</button>
          </div>
        </div>
        ${pMo.note ? `<div class="chip ok" style="margin-top:8px">✓ ${ESC(pMo.note)} active!</div>` : ""}
        <div class="st-grid3">
          <div class="st-price">
            <div>
              <b>Free Forever</b>
              <div class="st-amt">₹0</div>
              <div class="mut">For self-paced planning</div>
              <ul class="st-ul">
                <li>✓ Full Study Plan & 1-2-7 Revisions</li>
                <li>✓ Strict Pomodoro + Buddy Lock</li>
                <li>✓ ICAI Dates & Announcements</li>
                <li>✓ Study Partner & Leaderboard</li>
                <li>✓ Offline PWA (Android & Desktop)</li>
              </ul>
            </div>
            <button class="btn sec" id="st-pr-free">Start Free</button>
          </div>

          <div class="st-price pop">
            <span class="st-price-tag">Student Favorite</span>
            <div>
              <b>Pro Monthly</b>
              <div class="st-amt">${pMo.off ? `<s class="mut" style="font-size:18px">₹49</s> ₹${pMo.final}` : `₹49`} <small class="mut" style="font-size:13px">/mo</small></div>
              <div class="mut">Cost of 1 chai/week — unlocks everything</div>
              <ul class="st-ul">
                <li>✓ Everything in Free Forever</li>
                <li>✓ AI Tutor grounded in PYQ/MTP/RTP</li>
                <li>✓ Homework Photo AI Answer Audit</li>
                <li>✓ Chapter Weightage ★ & Full Vault</li>
                <li>✓ 12-Hr Lecture Key-Moments Clipper</li>
              </ul>
            </div>
            <button class="btn" id="st-pr-mo">Unlock Pro (${pMo.off ? "₹" + pMo.final : "₹49"})</button>
          </div>

          <div class="st-price">
            <span class="st-price-tag" style="background:#16a34a">Save 15%+ • Best Value</span>
            <div>
              <b>Attempt Pass (6 Months)</b>
              <div class="st-amt">${pAtt.off ? `<s class="mut" style="font-size:18px">₹249</s> ₹${pAtt.final}` : `₹249`} <small class="mut" style="font-size:13px">/6 mo</small></div>
              <div class="mut">Annual Pass also available at ₹${pYr.final}/yr</div>
              <ul class="st-ul">
                <li>✓ Full Attempt Cycle (May / Sep / Jan)</li>
                <li>✓ All Pro AI, Homework & Vault tools</li>
                <li>✓ +7 Bonus Pro Days per Referral</li>
                <li>✓ Free for Admins & Special Category VIPs</li>
              </ul>
            </div>
            <button class="btn sec" id="st-pr-att">Get Attempt Pass →</button>
          </div>
        </div>
      </section>

      <section class="st-sec st-faq" id="st-faq">
        <h2>Frequently Asked Questions</h2>
        <details><summary>Does Studify CA ever ask for my ICAI password or SSP login?</summary><div class="mut" style="margin-top:6px">Never. One account uses one ICAI registration number only to keep leaderboard & partner verification fair — never your ICAI password or DOB.</div></details>
        <details><summary>Can I use Studify CA without internet?</summary><div class="mut" style="margin-top:6px">Yes! Studify CA works offline as an installable PWA on Android phones and Windows laptops, and syncs to cloud whenever you sign in.</div></details>
        <details><summary>How do Referral Codes and Special Category Free Access work?</summary><div class="mut" style="margin-top:6px">Share your referral code from Settings: your friend gets 20% off Pro and you earn +7 free Pro days. Admins & Special Category VIP accounts approved in the Admin panel get Pro 100% free.</div></details>
      </section>

      <footer class="st-foot" id="st-contact">
        <div>
          <b>Studify CA</b>
          <div class="mut" style="margin-top:6px">Built by & for Indian CA students. Smart planning, strict discipline & ICAI paper insights. Not affiliated with ICAI.</div>
          <div class="mut" style="margin-top:8px">App v1 • Zero Ads</div>
        </div>
        <div>
          <b>Product</b>
          <div style="display:grid;gap:6px;margin-top:8px;font-size:13px">
            <a href="#st-feat">Features</a>
            <a href="#st-lv">CA Foundation / Inter / Final</a>
            <a href="#st-pricing">Pro Pricing & Discounts</a>
            <a href="privacy.html">Privacy Policy</a>
          </div>
        </div>
        <div>
          <b>Contact Us</b>
          <div style="display:grid;gap:6px;margin-top:8px;font-size:13px">
            <div>📞 <a href="tel:+919509707043">+91 95097 07043</a></div>
            <div>✉️ <a href="mailto:studifyca.official@gmail.com">studifyca.official@gmail.com</a></div>
            <div>🛟 <a href="mailto:studifyca.support@gmail.com">studifyca.support@gmail.com</a></div>
            <div><a href="https://wa.me/919509707043?text=${encodeURIComponent("Hi Studify CA team! Need help with Studify CA.")}" target="_blank" style="color:#16a34a;font-weight:700;text-decoration:none">WhatsApp Us →</a></div>
          </div>
        </div>
      </footer>
      ${authModalHtml}
      <a class="st-wa-float" href="https://wa.me/919509707043?text=${encodeURIComponent("Hi Studify CA! Query about app / Pro pass.")}" target="_blank">💬 WhatsApp Us</a>
    </div>`;
  };

  window.bindStudifyLanding = function (rerender) {
    var q = function (s) { return document.getElementById(s); };
    var openAuth = function (mode) { AUTH_MODE = mode; AUTH_OPEN = true; rerender(); };
    ["st-open-in", "st-hero-in"].forEach(function (id) { if (q(id)) q(id).onclick = function () { openAuth("in"); }; });
    ["st-open-up", "st-hero-up", "st-pr-free", "st-pr-mo", "st-pr-att"].forEach(function (id) { if (q(id)) q(id).onclick = function () { openAuth("up"); }; });
    if (q("st-auth-close")) q("st-auth-close").onclick = function () { AUTH_OPEN = false; rerender(); };
    if (q("st-tab-in")) q("st-tab-in").onclick = function () { AUTH_MODE = "in"; rerender(); };
    if (q("st-tab-up")) q("st-tab-up").onclick = function () { AUTH_MODE = "up"; rerender(); };
    if (q("st-hero-tour")) q("st-hero-tour").onclick = openTourModal;
    if (q("st-lp-thm")) q("st-lp-thm").onclick = function () {
      var nx = (document.documentElement.dataset.theme === "dark") ? "light" : "dark";
      document.documentElement.dataset.theme = nx;
      try { localStorage.setItem("ca_studyos_theme", nx); } catch (e) {}
      rerender();
    };
    if (q("st-lp-lng")) q("st-lp-lng").onclick = function () {
      LANG = LANG === "en" ? "hi" : "en";
      try { localStorage.setItem("studify_lp_lang", LANG); } catch (e) {}
      rerender();
    };
    if (q("st-promo-apply")) q("st-promo-apply").onclick = function () {
      REF_CODE = (q("st-promo-in").value || "").trim().toUpperCase();
      try { if (REF_CODE) localStorage.setItem("studify_ref", REF_CODE); else localStorage.removeItem("studify_ref"); } catch (e) {}
      rerender();
    };
    if (q("cl-ref")) q("cl-ref").oninput = function () {
      REF_CODE = (this.value || "").trim().toUpperCase();
      try { if (REF_CODE) localStorage.setItem("studify_ref", REF_CODE); } catch (e) {}
    };
    document.querySelectorAll("[data-stshow]").forEach(function (b) {
      b.onclick = function () { SHOW_TAB = b.getAttribute("data-stshow"); rerender(); };
    });
    document.querySelectorAll("[data-stlv]").forEach(function (b) {
      b.onclick = function () { LEVEL_TAB = b.getAttribute("data-stlv"); rerender(); };
    });
    document.querySelectorAll("[data-stgd]").forEach(function (b) {
      b.onclick = function () { openGuideModal(b.getAttribute("data-stgd")); };
    });
  };
})();
