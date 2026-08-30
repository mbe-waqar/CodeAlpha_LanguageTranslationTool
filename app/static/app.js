const $ = (id) => document.getElementById(id);
const [form, input, output, source, target, status, result] =
  ["form", "input", "output", "source", "target", "status", "result"].map($);

const HISTORY_KEY = "linguaalpha.history";
const HISTORY_SIZE = 6;

let languages = {};

const name = (code) => languages[code] ?? code;

const setStatus = (message, isError = false) => {
  status.textContent = message;
  status.classList.toggle("error", isError);
};

async function api(path, options) {
  const res = await fetch(path, options);
  const body = await res.json();
  if (!res.ok) throw new Error(body.detail?.[0]?.msg ?? body.detail ?? "Request failed");
  return body;
}

function speak(text, lang) {
  if (!text) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  speechSynthesis.cancel();
  speechSynthesis.speak(utterance);
}

/* --- history (kept in this browser only) ---------------------------------- */

const readHistory = () => {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY)) ?? [];
  } catch {
    return [];
  }
};

const writeHistory = (entries) => {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
  } catch {
    /* private mode or storage disabled: history is simply not remembered */
  }
};

function renderHistory() {
  const entries = readHistory();
  $("history").hidden = entries.length === 0;
  $("history-list").replaceChildren(
    ...entries.map((entry) => {
      const button = document.createElement("button");
      button.innerHTML = `<span class="pair"></span><span class="text"></span>`;
      button.querySelector(".pair").textContent = `${name(entry.source)} → ${name(entry.target)}`;
      button.querySelector(".text").textContent = entry.text;
      button.onclick = () => restore(entry);
      const item = document.createElement("li");
      item.append(button);
      return item;
    }),
  );
}

function remember(entry) {
  const rest = readHistory().filter((old) => old.text !== entry.text || old.target !== entry.target);
  writeHistory([entry, ...rest].slice(0, HISTORY_SIZE));
  renderHistory();
}

function restore(entry) {
  input.value = entry.text;
  source.value = entry.source;
  target.value = entry.target;
  show(entry);
  count();
}

/* --- translating ----------------------------------------------------------- */

function show({ translated, source: from, target: to, provider }) {
  output.textContent = translated;
  $("meta").textContent = `${name(from)} → ${name(to)} · via ${provider}`;
  result.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return setStatus("Enter some text first.", true);

  $("submit").disabled = true;
  setStatus("Translating…");
  try {
    const reply = await api("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, source: source.value, target: target.value }),
    });

    const entry = { text, translated: reply.text, source: reply.source, target: reply.target, provider: reply.provider };
    show(entry);
    remember(entry);
    setStatus("");
    $("detected").textContent = `Detected source: ${name(reply.source)}`;
    if ($("autospeak").checked) speak(reply.text, reply.target);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    $("submit").disabled = false;
  }
});

/* --- controls -------------------------------------------------------------- */

$("swap").onclick = () => {
  if (source.value === "auto") return setStatus("Pick a source language before swapping.", true);
  [source.value, target.value] = [target.value, source.value];
  input.value = output.textContent || input.value;
  setStatus("");
};

$("copy").onclick = async () => {
  await navigator.clipboard.writeText(output.textContent);
  setStatus("Copied to clipboard.");
};

$("speak").onclick = () => speak(output.textContent, target.value);

$("clear").onclick = () => {
  input.value = "";
  result.hidden = true;
  setStatus("");
  count();
  input.focus();
};

$("clear-history").onclick = () => {
  writeHistory([]);
  renderHistory();
};

$("tab-history").onclick = () =>
  readHistory().length
    ? $("history").scrollIntoView({ behavior: "smooth", block: "center" })
    : setStatus("No translations yet.");

const count = () => ($("count").textContent = `${input.value.length} / 5000`);
input.addEventListener("input", count);

/* --- start ----------------------------------------------------------------- */

(async function init() {
  try {
    languages = await api("/api/languages");
    const options = Object.entries(languages)
      .map(([code, label]) => `<option value="${code}">${label}</option>`)
      .join("");
    source.innerHTML = target.innerHTML = options;
    source.value = "auto";
    target.value = "en";
    $("lang-count").textContent = `${Object.keys(languages).length - 1} languages`;
    renderHistory();

    // Deep link: /?text=hello&to=ur opens with that translation already done.
    const link = new URLSearchParams(location.search);
    if (link.get("text")) {
      input.value = link.get("text");
      source.value = link.get("from") ?? "auto";
      target.value = link.get("to") ?? target.value;
      count();
      form.requestSubmit();
    }
  } catch {
    setStatus("Could not load the language list. Is the server running?", true);
  }
})();
