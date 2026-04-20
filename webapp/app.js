/* =========================================================
   BookReader Mini App — ванильный JS, без фреймворков
   ========================================================= */

const tg = window.Telegram.WebApp;

// ─── Состояние ────────────────────────────────────────────
const state = {
  books: [],
  currentBook: null,
  currentChapter: null,
  questions: [],
  questionIndex: 0,
  scores: [],         // оценки за каждый вопрос текущей сессии
  feedbacks: [],      // фидбеки
  awaitingNext: false // ждём нажатия "Следующий вопрос" после ответа
};

// ─── DOM ──────────────────────────────────────────────────
const screens = {
  loading: document.getElementById("screen-loading"),
  home:    document.getElementById("screen-home"),
  chapter: document.getElementById("screen-chapter"),
  result:  document.getElementById("screen-result"),
};

// ─── Инициализация Telegram ──────────────────────────────
tg.ready();
tg.expand();
tg.BackButton.onClick(() => showHome());

// ─── API-клиент ───────────────────────────────────────────
const API = {
  headers() {
    return {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": tg.initData || "",
    };
  },
  async post(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  },
  async get(url) {
    const res = await fetch(url, { headers: this.headers() });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  },
};

// ─── Показ экранов ────────────────────────────────────────
function showScreen(name) {
  Object.values(screens).forEach(s => s.classList.remove("active"));
  screens[name].classList.add("active");
  tg.BackButton[name === "chapter" ? "show" : "hide"]();
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

// ─── Главный экран ────────────────────────────────────────
async function showHome() {
  showScreen("home");
  if (state.books.length > 0) renderHome();
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
async function openChapter(bookId, chapterNum) {
  showScreen("loading");
  try {
    const data = await API.get(`/api/chapter/${bookId}/${chapterNum}`);
    state.currentChapter = { bookId, num: chapterNum, title: data.title };
    state.questions = data.questions;
    state.questionIndex = 0;
    state.scores = [];
    state.feedbacks = [];
    state.awaitingNext = false;
    showQuizScreen();
  } catch (e) {
    alert("Ошибка загрузки главы: " + e.message);
    showHome();
  }
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

  // Заголовок
  document.getElementById("quiz-chapter-title").textContent =
    `Гл. ${ch.num}. ${ch.title}`;
  document.getElementById("quiz-counter").textContent =
    `Вопрос ${idx + 1} из ${total}`;

  // Прогресс-бар
  const pct = (idx / total) * 100;
  document.getElementById("quiz-progress-fill").style.width = pct + "%";

  // Вопрос
  document.getElementById("quiz-question").textContent = q.text;

  // Сброс поля и кнопки
  const textarea = document.getElementById("quiz-answer");
  textarea.value = "";
  textarea.disabled = false;
  textarea.focus();

  const btn = document.getElementById("btn-submit");
  btn.textContent = "Ответить";
  btn.disabled = false;
  btn.onclick = submitAnswer;

  // Убираем старый фидбек
  const fb = document.getElementById("quiz-feedback");
  fb.style.display = "none";
  fb.className = "feedback-card";
  fb.textContent = "";

  state.awaitingNext = false;
}

async function submitAnswer() {
  const textarea = document.getElementById("quiz-answer");
  const answer = textarea.value.trim();
  if (!answer) {
    textarea.style.borderColor = "#ff3b30";
    setTimeout(() => textarea.style.borderColor = "", 800);
    return;
  }

  const btn = document.getElementById("btn-submit");
  btn.disabled = true;
  btn.textContent = "Проверяю…";
  textarea.disabled = true;

  const ch = state.currentChapter;
  const q = state.questions[state.questionIndex];

  try {
    const result = await API.post("/api/answer", {
      book_id: ch.bookId,
      chapter_num: ch.num,
      question_id: q.id,
      answer_text: answer,
    });

    state.scores.push(result.score);
    state.feedbacks.push(result.feedback);

    // Показываем фидбек
    const fb = document.getElementById("quiz-feedback");
    fb.textContent = result.feedback;
    fb.className = `feedback-card score-${result.score}`;
    fb.style.display = "block";

    // Меняем кнопку
    const isLast = state.questionIndex >= state.questions.length - 1;
    btn.disabled = false;
    btn.textContent = isLast ? "Завершить главу" : "Следующий вопрос";
    btn.onclick = isLast ? finishChapter : nextQuestion;

  } catch (e) {
    btn.disabled = false;
    btn.textContent = "Ответить";
    textarea.disabled = false;
    alert("Ошибка: " + e.message);
  }
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

  try {
    const result = await API.post("/api/complete_chapter", {
      book_id: ch.bookId,
      chapter_num: ch.num,
      scores: state.scores,
    });

    showResult(result);

    // Обновляем данные книги локально
    if (state.currentBook) {
      state.currentBook.progress_percent = result.total_percent;
      // Обновляем статус главы
      const chData = state.currentBook.chapters.find(c => c.number === ch.num);
      if (chData && result.passed) chData.status = "completed";
      // Открываем следующую
      if (result.next_chapter_unlocked) {
        const next = state.currentBook.chapters.find(c => c.number === ch.num + 1);
        if (next) next.status = "available";
      }
    }
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "Завершить главу";
    alert("Ошибка: " + e.message);
  }
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
    const data = await API.post("/api/init", { initData: tg.initData || "" });
    state.books = data.books || [];
    showHome();
  } catch (e) {
    // Если initData пустой (открыто в браузере без Telegram) — показываем заглушку
    document.getElementById("screen-loading").innerHTML =
      `<div style="padding:32px;text-align:center;color:var(--hint)">
        <div style="font-size:48px">📱</div>
        <p style="margin-top:16px;font-size:15px">Открой через Telegram.<br>Прямой доступ через браузер недоступен.</p>
      </div>`;
  }
}

init();
