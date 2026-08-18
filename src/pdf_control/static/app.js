const toolLinks = document.querySelectorAll(".tool-link");
const panels = document.querySelectorAll(".panel");
const statusBox = document.querySelector(".status");
const themeToggle = document.querySelector(".theme-toggle");
const themeIcon = themeToggle.querySelector(".theme-toggle__icon");
const themeLabel = themeToggle.querySelector(".theme-toggle__label");
const themePreference = window.matchMedia("(prefers-color-scheme: dark)");

function currentTheme() {
  return document.documentElement.dataset.theme || (themePreference.matches ? "dark" : "light");
}

function renderTheme(theme) {
  const isDark = theme === "dark";
  document.documentElement.dataset.theme = theme;
  themeToggle.setAttribute("aria-pressed", String(isDark));
  themeToggle.setAttribute("aria-label", isDark ? "تفعيل الوضع الفاتح" : "تفعيل الوضع الداكن");
  themeIcon.textContent = isDark ? "☀" : "☾";
  themeLabel.textContent = isDark ? "الوضع الفاتح" : "الوضع الداكن";
}

renderTheme(currentTheme());
themeToggle.addEventListener("click", () => {
  const theme = currentTheme() === "dark" ? "light" : "dark";
  renderTheme(theme);
  try { localStorage.setItem("pdf-control-theme", theme); } catch (_) { /* Storage is optional. */ }
});

themePreference.addEventListener("change", (event) => {
  try {
    if (localStorage.getItem("pdf-control-theme")) return;
  } catch (_) { /* Follow the system preference when storage is unavailable. */ }
  renderTheme(event.matches ? "dark" : "light");
});

function showTool(toolId) {
  toolLinks.forEach((link) => link.classList.toggle("active", link.dataset.tool === toolId));
  panels.forEach((panel) => panel.classList.toggle("active", panel.id === toolId));
  history.replaceState(null, "", `#${toolId}`);
  statusBox.hidden = true;
}

toolLinks.forEach((link) => link.addEventListener("click", () => showTool(link.dataset.tool)));
if (location.hash && document.querySelector(location.hash)) showTool(location.hash.slice(1));

const previewInput = document.querySelector("#preview-file");
const previewFrame = document.querySelector(".pdf-preview");
let previewUrl = null;
previewInput.addEventListener("change", () => {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  const file = previewInput.files[0];
  if (!file) {
    previewFrame.hidden = true;
    previewFrame.removeAttribute("src");
    return;
  }
  previewUrl = URL.createObjectURL(file);
  previewFrame.src = previewUrl;
  previewFrame.hidden = false;
});
window.addEventListener("beforeunload", () => {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
});

function showStatus(message, error = false) {
  statusBox.textContent = message;
  statusBox.classList.toggle("error", error);
  statusBox.hidden = false;
}

function responseFilename(response, fallback) {
  const disposition = response.headers.get("content-disposition") || "";
  const utf8Match = disposition.match(/filename\*=utf-8''([^;]+)/i);
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  if (utf8Match) return decodeURIComponent(utf8Match[1]);
  if (plainMatch) return plainMatch[1];
  return fallback;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function renderInfo(form, data) {
  const labels = { pages: "عدد الصفحات", encrypted: "مشفّر", title: "العنوان", author: "المؤلف", producer: "المنتج", creator: "المنشئ" };
  const result = form.parentElement.querySelector(".info-result");
  result.replaceChildren();
  Object.entries(data).forEach(([key, value]) => {
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = labels[key] || key;
    description.textContent = value === null || value === "" ? "—" : String(value);
    result.append(term, description);
  });
  result.hidden = false;
}

document.querySelectorAll("form[data-endpoint]").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type='submit']");
    const data = new FormData(form);

    form.querySelectorAll("input[type='checkbox']").forEach((checkbox) => {
      data.set(checkbox.name, checkbox.checked ? "true" : "false");
    });

    button.disabled = true;
    showStatus("جارٍ معالجة الملف… قد تستغرق عمليات OCR بعض الوقت.");

    try {
      const response = await fetch(`/api/${form.dataset.endpoint}`, { method: "POST", body: data });
      if (!response.ok) {
        let message = "تعذّرت معالجة الملف.";
        try { message = (await response.json()).detail || message; } catch (_) { /* response is not JSON */ }
        throw new Error(message);
      }

      if (form.dataset.json === "true") {
        renderInfo(form, await response.json());
        showStatus("تمت قراءة معلومات الملف بنجاح.");
      } else {
        const blob = await response.blob();
        const filename = responseFilename(response, form.dataset.download || "result.pdf");
        downloadBlob(blob, filename);
        showStatus(decodeURIComponent(response.headers.get("x-pdf-control-message") || "اكتملت العملية وبدأ تنزيل النتيجة."));
      }
    } catch (error) {
      showStatus(error.message, true);
    } finally {
      button.disabled = false;
    }
  });
});

// Visual layer editor. Coordinates are stored in PDF points, independent of screen size.
const editor = {
  file: null, page: 1, pages: 1, width: 1, height: 1, tool: "select",
  layers: [], selected: null, history: [[]], historyIndex: 0, imageUrl: null, gesture: null,
};
const editorFile = document.querySelector("#editor-file");
const editorFont = document.querySelector("#editor-font");
const editorShell = document.querySelector(".editor-shell");
const editorStage = document.querySelector("#editor-stage");
const editorOverlay = document.querySelector("#editor-overlay");
const editorImage = document.querySelector("#editor-page-image");
const editorLoading = document.querySelector(".editor-loading");
const editorText = document.querySelector("#editor-text");
const editorFontSize = document.querySelector("#editor-font-size");
const editorColor = document.querySelector("#editor-color");

function editorScale() { return editorStage.clientWidth / editor.width; }
function selectedLayer() { return editor.layers.find((layer) => layer.id === editor.selected) || null; }
function cloneLayers() { return JSON.parse(JSON.stringify(editor.layers)); }

function commitEditorHistory() {
  const snapshot = cloneLayers();
  if (JSON.stringify(snapshot) === JSON.stringify(editor.history[editor.historyIndex])) return;
  editor.history = editor.history.slice(0, editor.historyIndex + 1);
  editor.history.push(snapshot);
  editor.historyIndex += 1;
  updateEditorActions();
}

function restoreEditorHistory(index) {
  if (index < 0 || index >= editor.history.length) return;
  editor.historyIndex = index;
  editor.layers = JSON.parse(JSON.stringify(editor.history[index]));
  if (!selectedLayer()) editor.selected = null;
  renderEditorLayers();
  updateEditorActions();
}

function updateEditorActions() {
  document.querySelector("#editor-undo").disabled = editor.historyIndex === 0;
  document.querySelector("#editor-redo").disabled = editor.historyIndex === editor.history.length - 1;
  document.querySelector("#editor-delete").disabled = !selectedLayer();
  document.querySelector("#editor-prev").disabled = editor.page <= 1;
  document.querySelector("#editor-next").disabled = editor.page >= editor.pages;
}

function renderEditorProperties() {
  const layer = selectedLayer();
  document.querySelector("#editor-empty-properties").hidden = Boolean(layer);
  document.querySelector("#editor-property-fields").hidden = !layer;
  if (!layer) return;
  const isText = layer.type === "text";
  document.querySelector("#editor-text-label").hidden = !isText;
  document.querySelector("#editor-size-label").hidden = !isText;
  editorText.value = layer.text || "";
  editorFontSize.value = layer.fontSize || 16;
  editorColor.value = layer.color || (isText ? "#111111" : "#ffffff");
}

function renderEditorLayers() {
  const scale = editorScale();
  editorOverlay.replaceChildren();
  editor.layers.filter((layer) => layer.page === editor.page).forEach((layer) => {
    const node = document.createElement("div");
    node.className = `editor-layer ${layer.type}${layer.id === editor.selected ? " selected" : ""}`;
    node.dataset.id = layer.id;
    node.style.left = `${layer.x * scale}px`;
    node.style.top = `${layer.y * scale}px`;
    node.style.width = `${layer.width * scale}px`;
    node.style.height = `${layer.height * scale}px`;
    node.style.color = layer.color;
    if (layer.type === "mask") node.style.backgroundColor = layer.color;
    else {
      node.textContent = layer.text;
      node.style.fontSize = `${layer.fontSize * scale}px`;
      node.style.textAlign = layer.align || "right";
    }
    editorOverlay.appendChild(node);
  });
  renderEditorProperties();
  updateEditorActions();
}

function editorPoint(event) {
  const bounds = editorOverlay.getBoundingClientRect();
  const scale = editorScale();
  return {
    x: Math.max(0, Math.min(editor.width, (event.clientX - bounds.left) / scale)),
    y: Math.max(0, Math.min(editor.height, (event.clientY - bounds.top) / scale)),
  };
}

async function loadEditorPage(page = editor.page) {
  if (!editor.file) return;
  editorLoading.hidden = false;
  const data = new FormData();
  data.set("file", editor.file);
  data.set("page", String(page));
  data.set("dpi", "120");
  try {
    const response = await fetch("/api/layer-preview", { method: "POST", body: data });
    if (!response.ok) {
      let message = "تعذّرت معاينة الملف.";
      try { message = (await response.json()).detail || message; } catch (_) { /* Not JSON. */ }
      throw new Error(message);
    }
    const blob = await response.blob();
    if (editor.imageUrl) URL.revokeObjectURL(editor.imageUrl);
    editor.imageUrl = URL.createObjectURL(blob);
    editor.page = page;
    editor.pages = Number(response.headers.get("x-page-count"));
    editor.width = Number(response.headers.get("x-page-width"));
    editor.height = Number(response.headers.get("x-page-height"));
    editorImage.src = editor.imageUrl;
    await editorImage.decode();
    document.querySelector("#editor-page").textContent = editor.page;
    document.querySelector("#editor-pages").textContent = editor.pages;
    renderEditorLayers();
  } catch (error) {
    showStatus(error.message, true);
  } finally {
    editorLoading.hidden = true;
  }
}

editorFile.addEventListener("change", async () => {
  const file = editorFile.files[0];
  if (!file) { editorShell.hidden = true; return; }
  editor.file = file;
  editor.page = 1;
  editor.layers = [];
  editor.selected = null;
  editor.history = [[]];
  editor.historyIndex = 0;
  editorShell.hidden = false;
  showStatus("جارٍ تجهيز محرر الطبقات…");
  await loadEditorPage(1);
  if (editor.pages) showStatus("المحرر جاهز. أضف طبقات الإخفاء أو النص ثم احفظ نسخة جديدة.");
});

document.querySelectorAll("[data-editor-tool]").forEach((button) => button.addEventListener("click", () => {
  editor.tool = button.dataset.editorTool;
  document.querySelectorAll("[data-editor-tool]").forEach((item) => item.classList.toggle("active", item === button));
  editorStage.style.cursor = editor.tool === "select" ? "default" : "crosshair";
}));

editorOverlay.addEventListener("pointerdown", (event) => {
  if (!editor.file || event.button !== 0) return;
  const point = editorPoint(event);
  const node = event.target.closest(".editor-layer");
  if (editor.tool === "select") {
    if (!node) { editor.selected = null; renderEditorLayers(); return; }
    editor.selected = node.dataset.id;
    const layer = selectedLayer();
    const bounds = node.getBoundingClientRect();
    const resize = event.clientX - bounds.left < 18 && bounds.bottom - event.clientY < 18;
    editor.gesture = { kind: resize ? "resize" : "move", start: point, original: { ...layer }, changed: false };
    editorOverlay.setPointerCapture(event.pointerId);
    renderEditorLayers();
    return;
  }

  const id = crypto.randomUUID ? crypto.randomUUID() : `layer-${Date.now()}-${Math.random()}`;
  if (editor.tool === "text") {
    const x = Math.min(point.x, Math.max(0, editor.width - 20));
    const y = Math.min(point.y, Math.max(0, editor.height - 12));
    editor.layers.push({ id, type: "text", page: editor.page, x, y, width: Math.max(20, Math.min(180, editor.width - x)), height: Math.max(12, Math.min(42, editor.height - y)), text: "نص جديد", fontSize: 16, color: "#111111", align: "right" });
    editor.selected = id;
    editor.tool = "select";
    document.querySelectorAll("[data-editor-tool]").forEach((item) => item.classList.toggle("active", item.dataset.editorTool === "select"));
    commitEditorHistory();
    renderEditorLayers();
    editorText.focus();
    editorText.select();
    return;
  }

  editor.layers.push({ id, type: "mask", page: editor.page, x: point.x, y: point.y, width: 1, height: 1, color: "#ffffff" });
  editor.selected = id;
  editor.gesture = { kind: "draw", start: point, changed: false };
  editorOverlay.setPointerCapture(event.pointerId);
  renderEditorLayers();
});

editorOverlay.addEventListener("pointermove", (event) => {
  if (!editor.gesture) return;
  const point = editorPoint(event);
  const layer = selectedLayer();
  if (!layer) return;
  const gesture = editor.gesture;
  if (gesture.kind === "draw") {
    layer.x = Math.min(gesture.start.x, point.x);
    layer.y = Math.min(gesture.start.y, point.y);
    layer.width = Math.max(1, Math.abs(point.x - gesture.start.x));
    layer.height = Math.max(1, Math.abs(point.y - gesture.start.y));
  } else if (gesture.kind === "move") {
    layer.x = Math.max(0, Math.min(editor.width - layer.width, gesture.original.x + point.x - gesture.start.x));
    layer.y = Math.max(0, Math.min(editor.height - layer.height, gesture.original.y + point.y - gesture.start.y));
  } else {
    layer.width = Math.max(5, Math.min(editor.width - layer.x, gesture.original.width + gesture.start.x - point.x));
    layer.x = Math.max(0, gesture.original.x + point.x - gesture.start.x);
    layer.height = Math.max(5, Math.min(editor.height - layer.y, gesture.original.height + point.y - gesture.start.y));
  }
  gesture.changed = true;
  renderEditorLayers();
});

editorOverlay.addEventListener("pointerup", (event) => {
  if (!editor.gesture) return;
  const layer = selectedLayer();
  if (editor.gesture.kind === "draw" && layer && (layer.width < 3 || layer.height < 3)) {
    editor.layers = editor.layers.filter((item) => item.id !== layer.id);
    editor.selected = null;
  } else if (editor.gesture.changed) commitEditorHistory();
  editor.gesture = null;
  if (editorOverlay.hasPointerCapture(event.pointerId)) editorOverlay.releasePointerCapture(event.pointerId);
  renderEditorLayers();
});

function deleteEditorLayer() {
  if (!selectedLayer()) return;
  editor.layers = editor.layers.filter((layer) => layer.id !== editor.selected);
  editor.selected = null;
  commitEditorHistory();
  renderEditorLayers();
}

document.querySelector("#editor-delete").addEventListener("click", deleteEditorLayer);
document.querySelector("#editor-undo").addEventListener("click", () => restoreEditorHistory(editor.historyIndex - 1));
document.querySelector("#editor-redo").addEventListener("click", () => restoreEditorHistory(editor.historyIndex + 1));
document.querySelector("#editor-prev").addEventListener("click", () => loadEditorPage(editor.page - 1));
document.querySelector("#editor-next").addEventListener("click", () => loadEditorPage(editor.page + 1));

function updateSelectedProperty(property, value) {
  const layer = selectedLayer();
  if (!layer) return;
  layer[property] = value;
  renderEditorLayers();
}
editorText.addEventListener("input", () => updateSelectedProperty("text", editorText.value));
editorText.addEventListener("change", commitEditorHistory);
editorFontSize.addEventListener("input", () => updateSelectedProperty("fontSize", Math.max(4, Math.min(200, Number(editorFontSize.value) || 16))));
editorFontSize.addEventListener("change", commitEditorHistory);
editorColor.addEventListener("input", () => updateSelectedProperty("color", editorColor.value));
editorColor.addEventListener("change", commitEditorHistory);

editorStage.addEventListener("keydown", (event) => {
  if ((event.key === "Delete" || event.key === "Backspace") && event.target === editorStage) deleteEditorLayer();
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
    event.preventDefault();
    restoreEditorHistory(editor.historyIndex + (event.shiftKey ? 1 : -1));
  }
});
window.addEventListener("resize", renderEditorLayers);

document.querySelector("#editor-save-button").addEventListener("click", async (event) => {
  if (!editor.file) return;
  if (!editor.layers.length) { showStatus("أضف طبقة واحدة على الأقل قبل الحفظ.", true); return; }
  const button = event.currentTarget;
  const data = new FormData();
  data.set("file", editor.file);
  data.set("edits", JSON.stringify(editor.layers.map(({ id, ...layer }) => layer)));
  data.set("output_name", document.querySelector("#editor-output-name").value || "layered.pdf");
  if (editorFont.files[0]) data.set("font", editorFont.files[0]);
  button.disabled = true;
  showStatus("جارٍ حفظ الطبقات فوق نسخة جديدة من الملف…");
  try {
    const response = await fetch("/api/layer-edit", { method: "POST", body: data });
    if (!response.ok) {
      let message = "تعذّر حفظ التعديلات.";
      try { message = (await response.json()).detail || message; } catch (_) { /* Not JSON. */ }
      throw new Error(message);
    }
    downloadBlob(await response.blob(), responseFilename(response, "layered.pdf"));
    showStatus(decodeURIComponent(response.headers.get("x-pdf-control-message") || "تم حفظ النسخة الجديدة."));
  } catch (error) {
    showStatus(error.message, true);
  } finally {
    button.disabled = false;
  }
});

window.addEventListener("beforeunload", () => {
  if (editor.imageUrl) URL.revokeObjectURL(editor.imageUrl);
});
