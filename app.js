/* عندما تطير الحيتان — قارئ الرواية */
(function () {
  "use strict";

  const BOOK = window.BOOK_DATA;
  const TOTAL = BOOK.pages.length;
  const STORE_KEY = "whale-book-state-v1";

  const el = {
    cover: document.getElementById("cover"),
    reader: document.getElementById("reader"),
    authorPage: document.getElementById("authorPage"),
    authorBack: document.getElementById("authorBackBtn"),
    content: document.getElementById("pageContent"),
    prev: document.getElementById("prevBtn"),
    next: document.getElementById("nextBtn"),
    pageNum: document.getElementById("pageNum"),
    slider: document.getElementById("pageSlider"),
    fill: document.getElementById("progressFill"),
    pWhale: document.getElementById("progressWhale"),
    pct: document.getElementById("progressPct"),
    scene: document.getElementById("sceneName"),
    start: document.getElementById("startBtn"),
    resume: document.getElementById("resumeBtn"),
    tocBtn: document.getElementById("tocBtn"),
    toc: document.getElementById("toc"),
    tocList: document.getElementById("tocList"),
    tocClose: document.getElementById("tocClose"),
    tocOverlay: document.getElementById("tocOverlay"),
    toast: document.getElementById("toast"),
    fontPlus: document.getElementById("fontPlus"),
    fontMinus: document.getElementById("fontMinus"),
  };

  /* ---------- state ---------- */
  let state = { page: 0, font: 21, started: false };
  let current = 0; // 0 = cover, 1..TOTAL = pages
  let animating = false;
  let viewingAuthor = false;

  function load() {
    try {
      const s = JSON.parse(localStorage.getItem(STORE_KEY));
      if (s && typeof s.page === "number") state = Object.assign(state, s);
    } catch (e) { /* fresh start */ }
  }
  function persist() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch (e) { }
  }
  function save() {
    state.page = current;
    persist();
  }

  /* ---------- helpers ---------- */
  const AR_DIGITS = "٠١٢٣٤٥٦٧٨٩";
  const arNum = (n) => String(n).replace(/\d/g, (d) => AR_DIGITS[+d]);

  const QUOTES = ["\"", "“", "”", "«", "»"];
  function isSceneTitle(t) {
    t = t.trim();
    return t.length > 3 && t.length < 45 &&
      QUOTES.some((q) => t.startsWith(q)) && QUOTES.some((q) => t.endsWith(q));
  }

  function sceneFor(page) {
    let name = "";
    for (const item of BOOK.toc) {
      if (item.page <= page) name = item.title;
      else break;
    }
    return name;
  }

  function toast(msg, ms) {
    el.toast.textContent = msg;
    el.toast.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.toast.classList.remove("show"), ms || 3800);
  }

  /* ---------- rendering ---------- */
  function buildPage(n) {
    const frag = document.createDocumentFragment();
    for (const para of BOOK.pages[n - 1]) {
      if (para === "---") {
        const d = document.createElement("div");
        d.className = "divider";
        d.textContent = "🐋";
        frag.appendChild(d);
      } else if (isSceneTitle(para)) {
        const h = document.createElement("h3");
        h.className = "scene-title";
        h.textContent = para.trim().replace(/^["“”«»]+|["“”«»]+$/g, "");
        frag.appendChild(h);
      } else {
        const p = document.createElement("p");
        p.textContent = para;
        frag.appendChild(p);
      }
    }
    return frag;
  }

  function updateChrome() {
    const pct = current === 0 ? 0 : Math.round((current / TOTAL) * 100);
    el.fill.style.width = pct + "%";
    el.pWhale.style.insetInlineStart = pct + "%";
    el.pct.textContent = arNum(pct) + "٪";
    el.pageNum.textContent = current === 0 ? "" : "صفحة " + arNum(current) + " من " + arNum(TOTAL);
    el.slider.value = Math.max(1, current);
    el.scene.textContent = current === 0 ? "" : sceneFor(current);
    el.prev.disabled = current <= 1;
    el.next.textContent = "";
    el.next.append(...nextBtnContent());
    document.title = current === 0
      ? BOOK.title
      : BOOK.title + " — صفحة " + arNum(current);
    updateTocActive();
  }

  function nextBtnContent() {
    const span = document.createElement("span");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", "M15 5l-7 7 7 7");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-width", "2.2");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    svg.appendChild(path);
    if (current >= TOTAL) {
      span.textContent = "النهاية";
      return [span];
    }
    span.textContent = "التالية";
    return [span, svg];
  }

  function showCover() {
    current = 0;
    viewingAuthor = false;
    el.authorPage.hidden = true;
    el.cover.hidden = false;
    el.reader.hidden = true;
    if (state.page > 0) {
      el.resume.hidden = false;
      el.resume.textContent = "متابعة القراءة — صفحة " + arNum(state.page);
    }
    updateChrome();
  }

  function showAuthor() {
    viewingAuthor = true;
    el.cover.hidden = true;
    el.reader.hidden = true;
    el.authorPage.hidden = false;
    document.title = BOOK.title + " — عن المؤلف";
    updateTocActive();
  }

  function hideAuthor() {
    viewingAuthor = false;
    el.authorPage.hidden = true;
    if (current === 0) showCover();
    else { el.reader.hidden = false; updateChrome(); }
  }

  function goTo(n, dir, instant) {
    n = Math.max(1, Math.min(TOTAL, n));
    if (animating || (n === current && !instant)) return;

    viewingAuthor = false;
    el.authorPage.hidden = true;
    el.cover.hidden = true;
    el.reader.hidden = false;

    if (instant || current === 0) {
      el.content.innerHTML = "";
      el.content.appendChild(buildPage(n));
      el.content.scrollTop = 0;
      el.content.classList.remove("page-anim-in-next", "page-anim-in-prev", "page-anim-out-next", "page-anim-out-prev");
      el.content.classList.add(dir === "prev" ? "page-anim-in-prev" : "page-anim-in-next");
      current = n;
      updateChrome();
      save();
      return;
    }

    const d = dir || (n > current ? "next" : "prev");
    animating = true;
    let done = false;
    const swap = () => {
      if (done) return;
      done = true;
      el.content.innerHTML = "";
      el.content.appendChild(buildPage(n));
      el.content.scrollTop = 0;
      el.content.classList.remove("page-anim-out-next", "page-anim-out-prev");
      el.content.classList.add(d === "next" ? "page-anim-in-next" : "page-anim-in-prev");
      current = n;
      updateChrome();
      save();
      animating = false; // ready for the next turn as soon as the new page slides in
    };
    el.content.classList.remove("page-anim-in-next", "page-anim-in-prev");
    el.content.classList.add(d === "next" ? "page-anim-out-next" : "page-anim-out-prev");
    el.content.addEventListener("animationend", function onOut() {
      el.content.removeEventListener("animationend", onOut);
      swap();
    });
    setTimeout(swap, 320); // safety if animationend never fires
  }

  const next = () => { if (current === 0) goTo(1); else if (current < TOTAL) goTo(current + 1, "next"); };
  const prev = () => { if (current > 1) goTo(current - 1, "prev"); };

  /* ---------- TOC ---------- */
  function buildToc() {
    const items = [
      { page: 0, title: "الغلاف" },
      { page: 1, title: "البداية" },
      { page: "author", title: "عن المؤلف" },
    ].concat(BOOK.toc);
    for (const it of items) {
      const li = document.createElement("li");
      li.dataset.page = it.page;
      const t = document.createElement("span");
      t.textContent = it.title;
      const pg = document.createElement("span");
      pg.className = "pg";
      pg.textContent = typeof it.page === "number" && it.page > 0 ? arNum(it.page) : "";
      li.append(t, pg);
      li.addEventListener("click", () => {
        closeToc();
        if (li.dataset.page === "author") showAuthor();
        else if (+li.dataset.page === 0) showCover();
        else goTo(+li.dataset.page);
      });
      el.tocList.appendChild(li);
    }
  }

  function updateTocActive() {
    let best = null;
    for (const li of el.tocList.children) {
      li.classList.remove("active");
      if (li.dataset.page === "author") continue;
      if (+li.dataset.page <= current && +li.dataset.page > 0) best = li;
    }
    if (viewingAuthor) {
      best = [...el.tocList.children].find((li) => li.dataset.page === "author") || best;
    } else if (current === 0) {
      best = el.tocList.firstElementChild;
    }
    if (best) {
      best.classList.add("active");
    }
  }

  const openToc = () => { el.toc.classList.add("open"); el.tocOverlay.classList.add("show"); };
  const closeToc = () => { el.toc.classList.remove("open"); el.tocOverlay.classList.remove("show"); };

  /* ---------- font size ---------- */
  function setFont(px) {
    state.font = Math.max(16, Math.min(28, px));
    document.documentElement.style.setProperty("--font-body", state.font + "px");
    persist();
  }

  /* ---------- bubbles canvas ---------- */
  function initBubbles() {
    const canvas = document.getElementById("bubbles");
    const ctx = canvas.getContext("2d");
    let W, H, dpr;
    const N = 42;
    const bubbles = [];

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = canvas.clientWidth;
      H = canvas.clientHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function spawn(b, first) {
      b.x = Math.random() * W;
      b.y = first ? Math.random() * H : H + 20;
      b.r = 1.5 + Math.random() * 4.5;
      b.v = 0.25 + Math.random() * 0.7;
      b.drift = 0.4 + Math.random() * 1.2;
      b.phase = Math.random() * Math.PI * 2;
      b.alpha = 0.12 + Math.random() * 0.25;
    }

    for (let i = 0; i < N; i++) { const b = {}; bubbles.push(b); }
    resize();
    bubbles.forEach((b) => spawn(b, true));
    window.addEventListener("resize", resize);

    let last = 0;
    function frame(t) {
      requestAnimationFrame(frame);
      if (document.hidden) return;
      const dt = Math.min(32, t - last) / 16.7;
      last = t;
      ctx.clearRect(0, 0, W, H);
      for (const b of bubbles) {
        b.y -= b.v * dt;
        b.phase += 0.02 * dt;
        const x = b.x + Math.sin(b.phase) * 14 * b.drift;
        if (b.y < -20) spawn(b);
        ctx.beginPath();
        ctx.arc(x, b.y, b.r, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(160, 220, 245, " + b.alpha + ")";
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(x - b.r * 0.3, b.y - b.r * 0.3, b.r * 0.3, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(220, 245, 255, " + b.alpha * 0.7 + ")";
        ctx.fill();
      }
    }
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      requestAnimationFrame(frame);
    }
  }

  /* ---------- input ---------- */
  function initInput() {
    el.next.addEventListener("click", next);
    el.prev.addEventListener("click", prev);
    el.start.addEventListener("click", () => goTo(1));
    el.resume.addEventListener("click", () => goTo(state.page));
    el.authorBack.addEventListener("click", hideAuthor);
    el.tocBtn.addEventListener("click", openToc);
    el.tocClose.addEventListener("click", closeToc);
    el.tocOverlay.addEventListener("click", closeToc);
    el.fontPlus.addEventListener("click", () => setFont(state.font + 1));
    el.fontMinus.addEventListener("click", () => setFont(state.font - 1));

    el.slider.addEventListener("input", () => {
      el.pageNum.textContent = "صفحة " + arNum(+el.slider.value) + " من " + arNum(TOTAL);
    });
    el.slider.addEventListener("change", () => goTo(+el.slider.value));

    document.addEventListener("keydown", (e) => {
      if (e.target.tagName === "INPUT") return;
      if (viewingAuthor) {
        if (e.key === "Escape") hideAuthor();
        return;
      }
      switch (e.key) {
        case "ArrowLeft": next(); break;          // RTL: left = forward
        case "ArrowRight": prev(); break;
        case " ": case "PageDown": e.preventDefault(); next(); break;
        case "PageUp": prev(); break;
        case "Home": goTo(1); break;
        case "End": goTo(TOTAL); break;
        case "Escape": closeToc(); break;
      }
    });

    // touch swipe
    let sx = null, sy = null;
    document.addEventListener("touchstart", (e) => {
      sx = e.touches[0].clientX; sy = e.touches[0].clientY;
    }, { passive: true });
    document.addEventListener("touchend", (e) => {
      if (sx === null) return;
      const dx = e.changedTouches[0].clientX - sx;
      const dy = e.changedTouches[0].clientY - sy;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.6) {
        if (dx > 0) next(); else prev();          // RTL flip
      }
      sx = sy = null;
    }, { passive: true });
  }

  /* ---------- boot ---------- */
  load();
  setFont(state.font);
  buildToc();
  el.slider.max = TOTAL;
  initBubbles();
  initInput();

  if (state.page > 0) {
    goTo(state.page, "next", true);
    toast("🐋 عدنا بك إلى حيث توقفت — صفحة " + arNum(state.page));
  } else {
    showCover();
  }
})();
