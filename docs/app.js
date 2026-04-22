/* =========================================================
   BookReader Mini App — чистый фронтенд, без бэкенда
   Вся логика (грейдер + прогресс) работает в браузере.
   Прогресс хранится в Telegram CloudStorage (если доступен),
   иначе — в localStorage.
   ========================================================= */

const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

// ─── Состояние ────────────────────────────────────────────
const state = {
  content: null,        // загруженный chapters.json
  books: [],            // подготовленные для UI
  progress: {},         // { "book_id:chapter_num": { completed: bool, best_avg: num } }
  currentBook: null,
  currentChapter: null,
  questions: [],
  questionIndex: 0,
  scores: [],
  feedbacks: [],
};

// ─── DOM ──────────────────────────────────────────────────
const screens = {
  loading: document.getElementById("screen-loading"),
  home:    document.getElementById("screen-home"),
  chapter: document.getElementById("screen-chapter"),
  result:  document.getElementById("screen-result"),
};

// ─── Инициализация Telegram ──────────────────────────────
if (tg) {
  tg.ready();
  tg.expand();
  tg.BackButton.onClick(() => showHome());
}

// ─── Хранилище прогресса (CloudStorage с фоллбэком на localStorage) ──
const STORAGE_KEY = "bookreader_progress_v1";

const Storage = {
  async load() {
    // Try Telegram CloudStorage first
    if (tg && tg.CloudStorage && typeof tg.CloudStorage.getItem === "function") {
      try {
        const raw = await new Promise((resolve, reject) => {
          tg.CloudStorage.getItem(STORAGE_KEY, (err, value) => {
            if (err) reject(err); else resolve(value);
          });
        });
        if (raw) return JSON.parse(raw);
      } catch (e) {
        console.warn("CloudStorage load failed, fallback:", e);
      }
    }
    // Fallback
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  },

  async save(data) {
    const json = JSON.stringify(data);
    // CloudStorage
    if (tg && tg.CloudStorage && typeof tg.CloudStorage.setItem === "function") {
      try {
        await new Promise((resolve, reject) => {
          tg.CloudStorage.setItem(STORAGE_KEY, json, (err, ok) => {
            if (err) reject(err); else resolve(ok);
          });
        });
      } catch (e) {
        console.warn("CloudStorage save failed:", e);
      }
    }
    // Всегда дублируем в localStorage
    try { localStorage.setItem(STORAGE_KEY, json); } catch (e) {}
  },
};

// ─── Простой русский стеммер ──────────────────────────────
// Обрезает распространённые окончания (прилагательных, существительных,
// глаголов) и оставляет корневую основу. Не идеален, но работает для
// keyword-оценки без внешних библиотек.
const RU_ENDINGS = [
  // длинные окончания сначала (жадное совпадение)
  "ивший", "ившая", "ившее", "ившие", "ившим", "ившем", "ившей",
  "ующий", "ующая", "ующее", "ующие",
  "ьными", "ьными", "ьного", "ьному",
  "ейший", "ейшая", "ейшее", "ейшие",
  "ности", "ность", "ностью",
  "ение", "ения", "ению", "ением",
  "ание", "ания", "анию", "анием",
  "ация", "ации", "ацию", "ацией",
  "иями", "ями",
  "ыми", "ими", "ого", "его", "ому", "ему",
  "ыми", "ими", "ами", "ями",
  "ешь", "ете", "ешь", "ете", "ишь", "ите",
  "ает", "ают", "ает", "ают", "ует", "уют",
  "ала", "али", "ало", "яла", "яли", "яло",
  "ить", "ать", "ять", "еть", "уть", "оть",
  "ую", "юю", "ие", "ые", "ой", "ей", "ою", "ею",
  "ах", "ях", "ов", "ев", "ёв",
  "ая", "яя", "ий", "ый", "ой", "ее", "ие",
  "ам", "ям", "ом", "ем", "ём",
  "ы", "и", "у", "ю", "а", "я", "о", "е", "ё", "ь"
];
// (есть дубликаты ради читаемости — не страшно, просто лишние пасы)

function stem(word) {
  let w = word.toLowerCase().replace(/ё/g, "е");
  // убрать приставку "не" при длинном слове
  // (осторожно: не трогаем короткие типа "нет")
  for (const end of RU_ENDINGS) {
    if (w.length - end.length >= 3 && w.endsWith(end)) {
      w = w.slice(0, -end.length);
      break;
    }
  }
  // обрежем мягкий/твёрдый знак на конце после стемминга
  if (w.length > 3 && (w.endsWith("ь") || w.endsWith("ъ"))) {
    w = w.slice(0, -1);
  }
  return w;
}

const WORD_RE = /[а-яА-ЯёЁa-zA-Z]+/g;

function stemTokens(text) {
  const tokens = String(text).toLowerCase().match(WORD_RE) || [];
  return tokens.map(stem);
}

// ─── Оценка одного ключевого слова/фразы ──────────────────
function keywordMatches(answerStems, keyword) {
  const kwStems = stemTokens(keyword);
  if (kwStems.length === 0) return false;
  // все корни фразы должны присутствовать в ответе
  return kwStems.every(k => answerStems.includes(k));
}

// ─── Грейдер ──────────────────────────────────────────────
function gradeAnswer(question, userAnswer) {
  if (!userAnswer || !userAnswer.trim()) {
    return { score: 0, feedback: "❌ Пустой ответ." };
  }

  const stems = stemTokens(userAnswer);
  const keywords = question.keywords || [];

  if (keywords.length === 0) {
    // без ключевиков — оцениваем по длине
    const n = stems.length;
    if (n >= 15) return { score: 2, feedback: "✅ Развёрнутый ответ." };
    if (n >= 5)  return { score: 1, feedback: "⚠️ Ответ короткий, раскрой подробнее." };
    return { score: 0, feedback: "❌ Слишком коротко или пусто." };
  }

  const required = Math.max(
    1,
    parseInt(question.required_count, 10) || Math.ceil(keywords.length / 2)
  );
  const matched = keywords.filter(kw => keywordMatches(stems, kw));
  const missing = keywords.filter(kw => !matched.includes(kw));

  if (matched.length >= required) {
    return {
      score: 2,
      feedback: `✅ Уловил ключевые мысли. Найдено: ${matched.length}/${keywords.length}.`,
    };
  }
  if (matched.length === required - 1) {
    const missStr = missing.slice(0, 3).map(m => `«${m}»`).join(", ");
    return {
      score: 1,
      feedback: `⚠️ Частично. Не хватило: ${missStr}.`,
    };
  }

  const ref = question.reference_answer || "";
  const refSnippet = ref.length > 220 ? ref.slice(0, 220) + "…" : ref;
  const missStr = missing.slice(0, 4).map(m => `«${m}»`).join(", ");
  const tail = refSnippet ? `\n\nЭталон: ${refSnippet}` : "";
  return {
    score: 0,
    feedback: `❌ Ключевые смыслы упущены: ${missStr}.${tail}`,
  };
}

// ─── Показ экранов ────────────────────────────────────────
function showScreen(name) {
  Object.values(screens).forEach(s => s.classList.remove("active"));
  screens[name].classList.add("active");
  if (tg && tg.BackButton) {
    tg.BackButton[name === "chapter" ? "show" : "hide"]();
  }
}

// ─── Кольцо прогресса ─────────────────────────────────────
function setRingPercent(percent) {
  const CIRCUMFERENCE = 339.292; // 2π × 54
  const offset = CIRCUMFERENCE - (percent / 100) * CIRCUMFERENCE;
  const fill = document.querySelector(".ring-fill");
  const label = document.querySelector(".ring-percent");
  if (fill)  fill.style.strokeDashoffset = offset;
  if (label) label.textContent = Math.round(percent) + "%";
}

// ─── Подготовка данных книги с прогрессом ────────────────
function buildBookView(book) {
  const total = book.chapters.length;
  let doneCount = 0;
  let prevCompleted = true;
  const chapters = book.chapters.map(ch => {
    const key = `${book.id}:${ch.number}`;
    const p = state.progress[key] || {};
    const completed = !!p.completed;
    if (completed) doneCount++;
    let status;
    if (completed) status = "completed";
    else if (prevCompleted) status = "available";
    else status = "locked";
    prevCompleted = completed;
    return {
      number: ch.number,
      title: ch.title,
      status,
      question_count: (ch.questions || []).length,
    };
  });
  return {
    id: book.id,
    title: book.title,
    author: book.author || "",
    total_chapters: total,
    progress_percent: total > 0 ? (doneCount / total) * 100 : 0,
    chapters,
  };
}

function refreshBooks() {
  state.books = state.content.books.map(buildBookView);
}

// ─── Главный экран ────────────────────────────────────────
function showHome() {
  showScreen("home");
  refreshBooks();
  renderHome();
}

function renderHome() {
  const book = state.books[0]; // MVP: одна книга
  if (!book) return;
  state.currentBook = book;

  document.querySelector(".book-title").textContent  = book.title;
  document.querySelector(".book-author").textContent = book.author;
  setRingPercent(book.progress_percent || 0);

  const list = document.getElementById("chapters-list");
  list.innerHTML = "";
  book.chapters.forEach(ch => {
    const btn = document.createElement("button");
    btn.className = "chapter-item " + ch.status;
    const icons = { completed: "✅", available: "🔓", locked: "🔒" };
    const meta = ch.question_count > 0
      ? `${ch.question_count} вопросов`
      : "Скоро";
    btn.innerHTML = `
      <span class="chapter-icon">${icons[ch.status]}</span>
      <span class="chapter-info">
        <span class="chapter-name">Гл. ${ch.number}. ${esc(ch.title)}</span>
        <span class="chapter-meta">${meta}</span>
      </span>
    `;
    if (ch.status !== "locked" && ch.question_count > 0) {
      btn.addEventListener("click", () => openChapter(book.id, ch.number));
    }
    list.appendChild(btn);
  });
}

// ─── Открыть главу ────────────────────────────────────────
function openChapter(bookId, chapterNum) {
  const book = state.content.books.find(b => b.id === bookId);
  if (!book) return;
  const ch = book.chapters.find(c => c.number === chapterNum);
  if (!ch) return;

  state.currentChapter = { bookId, num: chapterNum, title: ch.title };
  state.questions = (ch.questions || []).map(q => ({
    id: q.id,
    text: q.text,
    keywords: q.keywords || [],
    required_count: q.required_count,
    reference_answer: q.reference_answer || "",
  }));
  state.questionIndex = 0;
  state.scores = [];
  state.feedbacks = [];
  showQuizScreen();
}

// ─── Экран квиза ─────────────────────────────────────────
function showQuizScreen() {
  showScreen("chapter");
  renderQuestion();
}

function renderQuestion() {
  const ch = state.currentChapter;
  const total = state.questions.length;
  const idx = state.questionIndex;
  const q = state.questions[idx];

  document.getElementById("quiz-chapter-title").textContent =
    `Гл. ${ch.num}. ${ch.title}`;
  document.getElementById("quiz-counter").textContent =
    `Вопрос ${idx + 1} из ${total}`;

  const pct = (idx / total) * 100;
  document.getElementById("quiz-progress-fill").style.width = pct + "%";

  document.getElementById("quiz-question").textContent = q.text;

  const textarea = document.getElementById("quiz-answer");
  textarea.value = "";
  textarea.disabled = false;
  textarea.focus();

  const btn = document.getElementById("btn-submit");
  btn.textContent = "Ответить";
  btn.disabled = false;
  btn.onclick = submitAnswer;

  const fb = document.getElementById("quiz-feedback");
  fb.style.display = "none";
  fb.className = "feedback-card";
  fb.textContent = "";
}

function submitAnswer() {
  const textarea = document.getElementById("quiz-answer");
  const answer = textarea.value.trim();
  if (!answer) {
    textarea.style.borderColor = "#ff3b30";
    setTimeout(() => textarea.style.borderColor = "", 800);
    return;
  }

  const q = state.questions[state.questionIndex];
  const result = gradeAnswer(q, answer);

  state.scores.push(result.score);
  state.feedbacks.push(result.feedback);

  const fb = document.getElementById("quiz-feedback");
  fb.textContent = result.feedback;
  fb.className = `feedback-card score-${result.score}`;
  fb.style.display = "block";

  textarea.disabled = true;

  const btn = document.getElementById("btn-submit");
  const isLast = state.questionIndex >= state.questions.length - 1;
  btn.disabled = false;
  btn.textContent = isLast ? "Завершить главу" : "Следующий вопрос";
  btn.onclick = isLast ? finishChapter : nextQuestion;
}

function nextQuestion() {
  state.questionIndex++;
  renderQuestion();
}

// ─── Завершение главы ─────────────────────────────────────
async function finishChapter() {
  const ch = state.currentChapter;
  const btn = document.getElementById("btn-submit");
  btn.disabled = true;
  btn.textContent = "Сохраняю…";

  // Условие прохождения: все вопросы на 2 (как в оригинальном backend)
  const allPerfect = state.scores.length > 0 && state.scores.every(s => s === 2);
  const avg = state.scores.reduce((a, b) => a + b, 0) / state.scores.length;

  const key = `${ch.bookId}:${ch.num}`;
  const prev = state.progress[key] || {};
  const prevBest = typeof prev.best_avg === "number" ? prev.best_avg : 0;
  state.progress[key] = {
    completed: !!prev.completed || allPerfect,
    best_avg: Math.max(prevBest, avg),
    last_attempt_at: new Date().toISOString(),
  };
  await Storage.save(state.progress);

  // пересобираем данные книги для UI
  refreshBooks();
  const book = state.books.find(b => b.id === ch.bookId);
  state.currentBook = book;

  const totalPercent = book ? book.progress_percent : 0;
  const nextChapterExists = state.content.books
    .find(b => b.id === ch.bookId).chapters
    .some(c => c.number === ch.num + 1);

  showResult({
    passed: allPerfect,
    total_percent: totalPercent,
    next_chapter_unlocked: allPerfect && nextChapterExists,
  });
}

// ─── Экран результата ─────────────────────────────────────
function showResult(result) {
  showScreen("result");
  const passed = result.passed;

  document.getElementById("result-icon").textContent    = passed ? "🎉" : "📖";
  document.getElementById("result-title").textContent   = passed
    ? "Глава пройдена!"
    : "Нужно перечитать";
  document.getElementById("result-subtitle").textContent = passed
    ? "Все ответы точные — ты уловил ключевые мысли."
    : "Один или несколько ответов были неточными. Перечитай главу и попробуй снова — смыслы уложатся.";

  document.getElementById("result-percent").textContent = Math.round(result.total_percent) + "%";

  const actions = document.getElementById("result-actions");
  actions.innerHTML = "";

  if (passed && result.next_chapter_unlocked) {
    const ch = state.currentChapter;
    const nextBtn = mkBtn("➡️ Следующая глава", "btn", () => {
      openChapter(ch.bookId, ch.num + 1);
    });
    actions.appendChild(nextBtn);
  }

  if (!passed) {
    const ch = state.currentChapter;
    const retryBtn = mkBtn("🔁 Попробовать снова", "btn", () => {
      openChapter(ch.bookId, ch.num);
    });
    actions.appendChild(retryBtn);
  }

  const homeBtn = mkBtn("🏠 К списку глав", "btn btn-secondary", () => showHome());
  actions.appendChild(homeBtn);
}

function mkBtn(text, cls, handler) {
  const b = document.createElement("button");
  b.className = cls;
  b.textContent = text;
  b.addEventListener("click", handler);
  return b;
}

// ─── Утилиты ─────────────────────────────────────────────
function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ─── Инициализация ────────────────────────────────────────
async function init() {
  showScreen("loading");
  try {
    // 1. Загрузить главы (относительный путь — работает и локально, и на Pages)
    const res = await fetch("chapters.json");
    if (!res.ok) throw new Error("Не удалось загрузить chapters.json");
    state.content = await res.json();

    // 2. Загрузить прогресс
    state.progress = await Storage.load() || {};

    // 3. Показать главный экран
    showHome();
  } catch (e) {
    console.error(e);
    document.getElementById("screen-loading").innerHTML =
      `<div style="padding:32px;text-align:center;color:var(--hint)">
        <div style="font-size:48px">⚠️</div>
        <p style="margin-top:16px;font-size:15px">Ошибка загрузки:<br>${esc(e.message)}</p>
      </div>`;
  }
}

init();
