/**
 * qa-data.js — Daten-Lese-Schicht für Moriahise/Sanhedrin
 * Lädt Q&A aus data/questions/ und fällt automatisch auf die alte Struktur zurück.
 */
(function (global) {
  "use strict";

  const NEW_BASE = "data/questions";
  const state = {
    mode: null,
    manifest: null,
    index: null,
    categories: null,
    aliases: null,
    chunkCache: new Map(),
    byCatCache: new Map(),
    legacyIndexRaw: null,
    fetchLog: []
  };

  async function fetchJSON(url, opts = {}) {
    const optional = !!opts.optional;
    state.fetchLog.push(url);
    let res;
    try {
      res = await fetch(url, { cache: "no-cache" });
    } catch (err) {
      if (optional) return null;
      throw err;
    }
    if (!res.ok) {
      if (optional) return null;
      throw new Error(url + " -> HTTP " + res.status);
    }
    return res.json();
  }

  function chunkFile(n) {
    return `${NEW_BASE}/chunks/qa_${String(n).padStart(4, "0")}.json`;
  }

  async function init() {
    if (state.mode) return { mode: state.mode };
    const manifest = await fetchJSON(`${NEW_BASE}/manifest.json`, { optional: true });
    if (manifest && Number(manifest.schema || 0) >= 2) {
      state.mode = "new";
      state.manifest = manifest;
    } else {
      state.mode = "legacy";
      console.warn("[qa-data] data/questions/ nicht gefunden — Fallback auf alte Datenstruktur.");
    }
    return { mode: state.mode };
  }

  function normalizeNewIndexEntry(e) {
    return {
      id: String(e.id || ""),
      title_he: e.t_he || "",
      title_en: e.t_en || "",
      excerpt: e.x || "",
      answerExcerpt: e.ax || "",
      tags: e.tg || [],
      category: e.c || "general",
      year: e.y ?? null,
      chunk: e.ch,
      source: e.s || "",
      needsReview: !!e.r
    };
  }

  function normalizeLegacyIndexEntry(e) {
    const file = String(e.file || "");
    const idMatch = /[?&]id=([^&]+)/.exec(file);
    const srcMatch = /[?&]src=([^&]+)/.exec(file);
    return {
      id: idMatch ? decodeURIComponent(idMatch[1]) : String(e.source_id || e.number || ""),
      title_he: e.title_he || "",
      title_en: e.title_en || "",
      excerpt: e.summary_he || e.summary_en || "",
      answerExcerpt: "",
      tags: [],
      category: e.category || "other",
      year: e.year ?? null,
      chunk: null,
      source: "legacy",
      needsReview: false,
      legacySrc: srcMatch ? decodeURIComponent(srcMatch[1]) : null,
      legacyNumber: e.number,
      file: file
    };
  }

  async function loadLegacyIndexRaw() {
    if (!state.legacyIndexRaw) {
      state.legacyIndexRaw = (await fetchJSON("responsa.json")) || [];
    }
    return state.legacyIndexRaw;
  }

  async function loadQuestionIndex() {
    await init();
    if (state.index) return state.index;
    if (state.mode === "new") {
      const files = (state.manifest.index_files && state.manifest.index_files.length)
        ? state.manifest.index_files : ["index.json"];
      const out = [];
      for (const file of files) {
        const payload = await fetchJSON(`${NEW_BASE}/${file}`);
        out.push(...(payload.entries || []).map(normalizeNewIndexEntry));
      }
      state.index = out;
      return state.index;
    }
    const raw = await loadLegacyIndexRaw();
    state.index = raw
      .filter((e) => String(e.file || "").startsWith("qa.html"))
      .map(normalizeLegacyIndexEntry);
    return state.index;
  }

  const LEGACY_CATEGORIES = [
    { id: "civil", label_he: "דיני ממונות", label_en: "Civil Law", order: 1 },
    { id: "family", label_he: "דיני משפחה", label_en: "Family Law", order: 2 },
    { id: "ritual", label_he: "הלכות עבודה", label_en: "Ritual Law", order: 3 },
    { id: "kashrut", label_he: "כשרות", label_en: "Kashrut", order: 4 },
    { id: "shabbat", label_he: "שבת וחגים", label_en: "Shabbat & Holidays", order: 5 },
    { id: "conversion", label_he: "גיור", label_en: "Conversion", order: 6 },
    { id: "halacha-history", label_he: "הלכה – תולדות", label_en: "Halacha – History", order: 7 },
    { id: "other", label_he: "אחר", label_en: "Other", order: 8 }
  ];

  async function loadCategories() {
    await init();
    if (state.categories) return state.categories;
    if (state.mode === "new") {
      const payload = await fetchJSON(`${NEW_BASE}/categories.json`);
      state.categories = (payload.categories || [])
        .slice()
        .sort((a, b) => (a.order || 0) - (b.order || 0));
    } else {
      state.categories = LEGACY_CATEGORIES;
    }
    return state.categories;
  }

  async function getQuestionsByCategory(categoryId) {
    await init();
    if (!categoryId || categoryId === "all") return loadQuestionIndex();
    if (state.byCatCache.has(categoryId)) return state.byCatCache.get(categoryId);

    let out;
    if (state.mode === "new") {
      const payload = await fetchJSON(`${NEW_BASE}/by-category/${categoryId}.json`, { optional: true });
      out = payload ? (payload.entries || []).map(normalizeNewIndexEntry)
                    : (await loadQuestionIndex()).filter((e) => e.category === categoryId);
    } else {
      out = (await loadQuestionIndex()).filter((e) => e.category === categoryId);
    }

    state.byCatCache.set(categoryId, out);
    return out;
  }

  async function loadQuestionChunk(chunkName) {
    await init();
    if (state.mode !== "new") throw new Error("Chunks sind nur in der neuen Struktur verfügbar.");
    const no = typeof chunkName === "number"
      ? chunkName
      : parseInt(String(chunkName).replace(/^.*qa_(\d+)\.json$/, "$1"), 10);
    if (!Number.isFinite(no)) throw new Error("Ungültiger Chunk: " + chunkName);
    if (state.chunkCache.has(no)) return state.chunkCache.get(no);
    const payload = await fetchJSON(chunkFile(no));
    state.chunkCache.set(no, payload);
    return payload;
  }

  async function resolveAlias(id) {
    await init();
    if (state.mode !== "new") return null;
    if (!state.aliases) {
      const payload = await fetchJSON(`${NEW_BASE}/aliases.json`, { optional: true });
      state.aliases = (payload && payload.aliases) || {};
    }
    return state.aliases[id] || state.aliases["n" + id] || null;
  }

  function normalizeLegacyContentItem(it, src) {
    if (it.content !== undefined) {
      const parts = String(it.content || "").split(/##\s*Antworten\s*\n/);
      const question = parts[0].replace(/^[\s\S]*?##\s*Frage\s*\n/i, "").trim();
      const answers = [];
      if (parts[1]) {
        const seg = ("\n" + parts[1]).split(/\n###\s*([^\n]*)\n/);
        for (let i = 1; i < seg.length - 1; i += 2) {
          if (seg[i + 1].trim()) {
            answers.push({ text: seg[i + 1].trim(), accepted: seg[i].includes("✅"), author: null, score: null });
          }
        }
        if (!answers.length && parts[1].trim()) {
          answers.push({ text: parts[1].trim(), accepted: true, author: null, score: null });
        }
      }
      const meta = it.metadata || {};
      return {
        id: String(it.id || ""),
        title: it.title || "",
        question: question,
        answers,
        url: meta.url || null,
        tags: meta.tags || [],
        date: meta.date || null,
        score: meta.score,
        views: meta.views,
        category: null,
        source: "miyodea",
        legacySrc: src
      };
    }

    return {
      id: String(it.id || ""),
      title: it.title || (it.question || "").slice(0, 80),
      question: it.question || "",
      answers: [{ text: it.answer || "", accepted: true, author: null, score: null }],
      url: it.url || ("https://www.yeshiva.org.il/ask/" + it.id),
      tags: it.tags || (it.metadata && it.metadata.tags) || [],
      date: it.date || it.saved_at || null,
      category: null,
      source: "yeshiva",
      legacySrc: src
    };
  }

  async function legacyLoadById(id, srcHint) {
    const tryFile = async (src) => {
      if (!src) return null;
      const payload = await fetchJSON(src, { optional: true });
      if (!payload) return null;
      const list = Array.isArray(payload) ? payload : (payload.questions || []);
      const hit = list.find((x) => String(x.id) === String(id) || String(x.id) === "miyodeya_" + String(id));
      return hit ? normalizeLegacyContentItem(hit, src) : null;
    };

    if (srcHint) {
      const direct = await tryFile(srcHint);
      if (direct) return direct;
    }

    const raw = await loadLegacyIndexRaw().catch(() => []);
    const entry = raw.find((e) => {
      const file = String(e.file || "");
      return String(e.source_id || "") === String(id)
        || new RegExp("[?&]id=" + String(id).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "(&|$)").test(file);
    });

    if (entry) {
      const src = (/[?&]src=([^&]+)/.exec(String(entry.file || "")) || [])[1];
      if (src) {
        const bySrc = await tryFile(decodeURIComponent(src));
        if (bySrc) return bySrc;
      }
      if (entry.year) {
        const byYear = await tryFile(`qa_db/${entry.year}.json`);
        if (byYear) return byYear;
      }
    }
    return null;
  }

  async function loadQuestionById(id, srcHint) {
    await init();
    id = String(id || "");
    if (!id) throw new Error("Keine Frage-ID angegeben.");

    if (state.mode === "new") {
      let ref = null;

      if (/^(my|ye|up)-/.test(id)) {
        const found = (await loadQuestionIndex()).find((e) => e.id === id);
        if (found) ref = { id: found.id, ch: found.chunk };
      }

      if (!ref) ref = await resolveAlias(id);
      if (ref) {
        const chunk = await loadQuestionChunk(ref.ch);
        const q = (chunk.questions || []).find((x) => x.id === ref.id);
        if (q) return q;
      }

      const legacy = await legacyLoadById(id.replace(/^(my|ye|up)-/, ""), srcHint);
      if (legacy) return legacy;
      throw new Error("Frage nicht gefunden: " + id);
    }

    const legacy = await legacyLoadById(id, srcHint);
    if (legacy) return legacy;
    throw new Error("Frage nicht gefunden: " + id);
  }

  const norm = (s) => String(s || "").toLowerCase().normalize("NFC");

  function entryHaystack(e) {
    return norm([
      e.id,
      e.title_he,
      e.title_en,
      e.excerpt,
      e.answerExcerpt,
      (e.tags || []).join(" ")
    ].join(" "));
  }

  async function search(query, opts = {}) {
    await init();
    const category = opts.category || null;
    const limit = opts.limit || 200;
    const q = norm(query);
    let pool = category && category !== "all"
      ? await getQuestionsByCategory(category)
      : await loadQuestionIndex();

    if (!q) return pool.slice(0, limit);

    const direct = pool.find((e) => norm(e.id) === q);
    if (direct) return [direct];

    if (state.mode === "new" && /^[\w-]+$/.test(String(query || ""))) {
      const ref = await resolveAlias(String(query).trim());
      if (ref) {
        const aliased = pool.find((e) => e.id === ref.id);
        if (aliased) return [aliased];
      }
    }

    const terms = q.split(/\s+/).filter(Boolean);
    return pool.filter((e) => {
      const hay = entryHaystack(e);
      return terms.every((term) => hay.includes(term));
    }).slice(0, limit);
  }

  async function searchDeep(query, opts = {}) {
    await init();
    const base = await search(query, opts);
    if (state.mode !== "new") return base;

    const q = norm(query);
    if (!q) return base;
    const category = opts.category || null;
    const limit = opts.limit || 200;
    const terms = q.split(/\s+/).filter(Boolean);
    const idx = await loadQuestionIndex();
    const seen = new Set(base.map((e) => e.id));
    const results = base.map((e) => ({ ...e, matchedIn: "index" }));
    const chunks = [...new Set(idx.filter((e) => !category || category === "all" || e.category === category).map((e) => e.chunk))]
      .sort((a, b) => a - b);

    for (const ch of chunks) {
      if (results.length >= limit) break;
      const payload = await loadQuestionChunk(ch);
      for (const full of payload.questions || []) {
        if (seen.has(full.id)) continue;
        if (category && category !== "all" && full.category !== category) continue;
        const hay = norm([full.title, full.title_he, full.title_en, full.question, (full.answers || []).map((a) => a.text).join(" ")].join(" "));
        if (terms.every((term) => hay.includes(term))) {
          const ie = idx.find((e) => e.id === full.id);
          if (ie) {
            results.push({ ...ie, matchedIn: "fulltext" });
            seen.add(full.id);
          }
        }
      }
    }
    return results.slice(0, limit);
  }

  global.QAData = {
    init,
    loadQuestionIndex,
    loadQuestionById,
    loadQuestionChunk,
    getQuestionsByCategory,
    loadCategories,
    search,
    searchDeep,
    _state: state
  };
})(typeof window !== "undefined" ? window : globalThis);
