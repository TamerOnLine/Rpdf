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

const mergeInput = document.querySelector("#merge-files-input");
const mergeAddButton = document.querySelector("#merge-add-files");
const mergeList = document.querySelector("#merge-files-list");
const mergeSummary = document.querySelector("#merge-files-summary");
let mergeFiles = [];

function fileSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} كيلوبايت`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} ميغابايت`;
}

function renderMergeFiles() {
  mergeList.replaceChildren();
  mergeFiles.forEach((file, index) => {
    const item = document.createElement("li");
    const name = document.createElement("span");
    const size = document.createElement("span");
    const ordering = document.createElement("span");
    const moveUp = document.createElement("button");
    const moveDown = document.createElement("button");
    const remove = document.createElement("button");
    name.className = "merge-file-name";
    name.textContent = file.name;
    name.title = file.name;
    size.className = "merge-file-size";
    size.textContent = fileSize(file.size);
    ordering.className = "merge-file-ordering";
    moveUp.type = "button";
    moveUp.className = "merge-move-file";
    moveUp.textContent = "↑";
    moveUp.title = "تحريك لأعلى";
    moveUp.setAttribute("aria-label", `تحريك ${file.name} لأعلى`);
    moveUp.disabled = index === 0;
    moveUp.addEventListener("click", () => {
      [mergeFiles[index - 1], mergeFiles[index]] = [mergeFiles[index], mergeFiles[index - 1]];
      renderMergeFiles();
    });
    moveDown.type = "button";
    moveDown.className = "merge-move-file";
    moveDown.textContent = "↓";
    moveDown.title = "تحريك لأسفل";
    moveDown.setAttribute("aria-label", `تحريك ${file.name} لأسفل`);
    moveDown.disabled = index === mergeFiles.length - 1;
    moveDown.addEventListener("click", () => {
      [mergeFiles[index], mergeFiles[index + 1]] = [mergeFiles[index + 1], mergeFiles[index]];
      renderMergeFiles();
    });
    ordering.append(moveUp, moveDown);
    remove.type = "button";
    remove.className = "merge-remove-file";
    remove.textContent = "حذف";
    remove.setAttribute("aria-label", `حذف ${file.name}`);
    remove.addEventListener("click", () => {
      mergeFiles.splice(index, 1);
      renderMergeFiles();
    });
    item.append(name, size, ordering, remove);
    mergeList.appendChild(item);
  });
  mergeSummary.textContent = mergeFiles.length
    ? `${mergeFiles.length} ${mergeFiles.length === 1 ? "ملف" : "ملفات"} جاهزة للدمج.`
    : "لم تُضف ملفات بعد.";
}

mergeAddButton.addEventListener("click", () => mergeInput.click());
mergeInput.addEventListener("change", () => {
  const knownFiles = new Set(mergeFiles.map((file) => `${file.name}:${file.size}:${file.lastModified}`));
  Array.from(mergeInput.files).forEach((file) => {
    const fingerprint = `${file.name}:${file.size}:${file.lastModified}`;
    if (!knownFiles.has(fingerprint)) {
      mergeFiles.push(file);
      knownFiles.add(fingerprint);
    }
  });
  mergeInput.value = "";
  renderMergeFiles();
});

document.querySelectorAll("form[data-endpoint]").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type='submit']");
    const data = new FormData(form);

    if (form.dataset.endpoint === "merge") {
      if (mergeFiles.length < 2) {
        showStatus("أضف ملفي PDF على الأقل قبل الدمج.", true);
        return;
      }
      mergeFiles.forEach((file) => data.append("files", file, file.name));
    }

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
  file: null, page: 1, totalPages: 1, width: 1, height: 1, tool: "select",
  layers: [], deletedPages: new Set(), selected: null,
  zoom: 1, zoomMode: "fit",
  textDefaults: { fontSize: 10, width: 70, height: 16 },
  savedState: { layers: [], deletedPages: [] },
  restorableSession: null,
  history: [{ layers: [], deletedPages: [] }], historyIndex: 0, imageUrl: null, gesture: null,
};
const editorFile = document.querySelector("#editor-file");
const editorFont = document.querySelector("#editor-font");
const editorShell = document.querySelector(".editor-shell");
const editorStage = document.querySelector("#editor-stage");
const editorCanvasWrap = document.querySelector("#editor-canvas-wrap");
const editorOverlay = document.querySelector("#editor-overlay");
const editorImage = document.querySelector("#editor-page-image");
const editorLoading = document.querySelector(".editor-loading");
const editorText = document.querySelector("#editor-text");
const editorPasteText = document.querySelector("#editor-paste-text");
const editorFontSize = document.querySelector("#editor-font-size");
const editorColor = document.querySelector("#editor-color");
const editorDefaultFontSize = document.querySelector("#editor-default-font-size");
const editorDefaultWidth = document.querySelector("#editor-default-width");
const editorDefaultHeight = document.querySelector("#editor-default-height");
const editorColorPresets = document.querySelector("#editor-color-presets");
const editorColorStorageKey = "pdf-control-editor-colors";
const editorSessionStorageKey = "pdf-control-editor-session";
let editorSavedColors = ["#4b2fd3", "#116b32", "#1735e8"];

try {
  const savedColors = JSON.parse(localStorage.getItem(editorColorStorageKey));
  if (Array.isArray(savedColors) && savedColors.length === 3
      && savedColors.every((color) => /^#[0-9a-f]{6}$/i.test(color))) {
    editorSavedColors = savedColors;
  }
} catch (_) { /* Use the built-in colors when storage is unavailable. */ }

function editorScale() { return editorStage.clientWidth / editor.width; }
function selectedLayer() { return editor.layers.find((layer) => layer.id === editor.selected) || null; }
function cloneEditorState() {
  return { layers: JSON.parse(JSON.stringify(editor.layers)), deletedPages: [...editor.deletedPages] };
}
function editorFileIdentity(file) {
  return { name: file.name, size: file.size, lastModified: file.lastModified };
}
function matchingEditorFile(savedFile, file) {
  return savedFile && file && savedFile.name === file.name && savedFile.size === file.size
    && savedFile.lastModified === file.lastModified;
}
function readEditorSession() {
  try {
    const session = JSON.parse(localStorage.getItem(editorSessionStorageKey));
    if (session?.version !== 1 || !session.file || !Array.isArray(session.layers)
        || !Array.isArray(session.deletedPages)) return null;
    return session;
  } catch (_) {
    return null;
  }
}
function visibleEditorPages() {
  return Array.from({ length: editor.totalPages }, (_, index) => index + 1)
    .filter((page) => !editor.deletedPages.has(page));
}

function applyEditorZoom() {
  if (!editor.file || editor.width <= 1) return;
  if (editor.zoomMode === "fit") {
    const availableWidth = Math.max(280, editorCanvasWrap.clientWidth - 48);
    editor.zoom = Math.max(0.5, Math.min(2.5, availableWidth / editor.width));
  }
  editorStage.style.width = `${Math.round(editor.width * editor.zoom)}px`;
  document.querySelector("#editor-zoom-value").textContent = editor.zoomMode === "fit"
    ? `ملاءمة · ${Math.round(editor.zoom * 100)}٪`
    : `${Math.round(editor.zoom * 100)}٪`;
  document.querySelector("#editor-zoom-out").disabled = editor.zoom <= 0.5;
  document.querySelector("#editor-zoom-in").disabled = editor.zoom >= 2.5;
  renderEditorLayers();
}

function changeEditorZoom(change) {
  editor.zoomMode = "custom";
  editor.zoom = Math.max(0.5, Math.min(2.5, editor.zoom + change));
  applyEditorZoom();
}

function commitEditorHistory() {
  const snapshot = cloneEditorState();
  if (JSON.stringify(snapshot) === JSON.stringify(editor.history[editor.historyIndex])) return;
  editor.history = editor.history.slice(0, editor.historyIndex + 1);
  editor.history.push(snapshot);
  editor.historyIndex += 1;
  updateEditorActions();
}

async function restoreEditorHistory(index) {
  if (index < 0 || index >= editor.history.length) return;
  editor.historyIndex = index;
  const snapshot = editor.history[index];
  editor.layers = JSON.parse(JSON.stringify(snapshot.layers));
  editor.deletedPages = new Set(snapshot.deletedPages);
  if (editor.deletedPages.has(editor.page)) {
    await loadEditorPage(visibleEditorPages()[0]);
    return;
  }
  if (!selectedLayer()) editor.selected = null;
  renderEditorLayers();
  updateEditorActions();
}

function updateEditorActions() {
  document.querySelector("#editor-undo").disabled = editor.historyIndex === 0;
  document.querySelector("#editor-redo").disabled = editor.historyIndex === editor.history.length - 1;
  document.querySelector("#editor-delete").disabled = !selectedLayer();
  document.querySelector("#editor-session-save").disabled =
    JSON.stringify(cloneEditorState()) === JSON.stringify(editor.savedState);
  document.querySelector("#editor-session-restore").disabled = !editor.restorableSession;
  const pages = visibleEditorPages();
  const pageIndex = pages.indexOf(editor.page);
  document.querySelector("#editor-prev").disabled = pageIndex <= 0;
  document.querySelector("#editor-next").disabled = pageIndex < 0 || pageIndex >= pages.length - 1;
  document.querySelector("#editor-delete-page").disabled = pages.length <= 1;
  document.querySelector("#editor-page").textContent = editor.page;
  document.querySelector("#editor-pages").textContent = pages.length;
  const pageInput = document.querySelector("#editor-page-input");
  pageInput.max = editor.totalPages;
  if (document.activeElement !== pageInput) pageInput.value = editor.page;
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
      node.style.textAlign = layer.align || "center";
      node.style.justifyContent = layer.align === "left" ? "flex-start"
        : layer.align === "right" ? "flex-end" : "center";
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
    editor.totalPages = Number(response.headers.get("x-page-count"));
    editor.width = Number(response.headers.get("x-page-width"));
    editor.height = Number(response.headers.get("x-page-height"));
    editorImage.src = editor.imageUrl;
    await editorImage.decode();
    applyEditorZoom();
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
  editor.zoomMode = "fit";
  editor.deletedPages = new Set();
  editor.savedState = { layers: [], deletedPages: [] };
  const storedSession = readEditorSession();
  editor.restorableSession = matchingEditorFile(storedSession?.file, file) ? storedSession : null;
  editor.history = [{ layers: [], deletedPages: [] }];
  editor.historyIndex = 0;
  editorShell.hidden = false;
  showStatus("جارٍ تجهيز محرر الطبقات…");
  await loadEditorPage(1);
  if (editor.totalPages) showStatus("المحرر جاهز. أضف طبقات أو احذف صفحات ثم احفظ نسخة جديدة.");
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
    const defaults = editor.textDefaults;
    const x = Math.min(point.x, Math.max(0, editor.width - 20));
    const y = Math.min(point.y, Math.max(0, editor.height - 12));
    editor.layers.push({
      id, type: "text", page: editor.page, x, y,
      width: Math.max(20, Math.min(defaults.width, editor.width - x)),
      height: Math.max(12, Math.min(defaults.height, editor.height - y)),
      text: "", fontSize: defaults.fontSize, color: "#111111",
      align: "center", verticalAlign: "middle",
    });
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
document.querySelector("#editor-session-save").addEventListener("click", () => {
  commitEditorHistory();
  editor.savedState = cloneEditorState();
  const session = {
    version: 1,
    file: editorFileIdentity(editor.file),
    layers: editor.savedState.layers,
    deletedPages: editor.savedState.deletedPages,
    page: editor.page,
    savedAt: new Date().toISOString(),
  };
  try {
    localStorage.setItem(editorSessionStorageKey, JSON.stringify(session));
    editor.restorableSession = session;
  } catch (_) {
    showStatus("تم الحفظ داخل الصفحة الحالية فقط؛ تعذّر الوصول إلى تخزين المتصفح.", true);
    updateEditorActions();
    return;
  }
  updateEditorActions();
  showStatus("تم حفظ التعديلات في المتصفح، ويمكن استرجاعها بعد اختيار الملف نفسه.");
});
document.querySelector("#editor-session-restore").addEventListener("click", async () => {
  const session = editor.restorableSession;
  if (!session || !matchingEditorFile(session.file, editor.file)) {
    showStatus("اختر ملف PDF الأصلي المطابق للجلسة المحفوظة أولًا.", true);
    return;
  }
  const dirty = JSON.stringify(cloneEditorState()) !== JSON.stringify(editor.savedState);
  if (dirty && !window.confirm("استرجاع النسخة المحفوظة واستبدال التعديلات الحالية؟")) return;
  editor.layers = JSON.parse(JSON.stringify(session.layers));
  editor.deletedPages = new Set(session.deletedPages);
  if (!visibleEditorPages().length) {
    showStatus("الجلسة المحفوظة غير صالحة لأنها تحذف جميع الصفحات.", true);
    return;
  }
  editor.selected = null;
  editor.savedState = cloneEditorState();
  editor.history = [cloneEditorState()];
  editor.historyIndex = 0;
  const requestedPage = Number(session.page);
  const targetPage = Number.isInteger(requestedPage) && !editor.deletedPages.has(requestedPage)
    && requestedPage >= 1 && requestedPage <= editor.totalPages
    ? requestedPage : visibleEditorPages()[0];
  await loadEditorPage(targetPage);
  showStatus("تم استرجاع التعديلات المحفوظة من المتصفح.");
});
document.querySelector("#editor-undo").addEventListener("click", () => restoreEditorHistory(editor.historyIndex - 1));
document.querySelector("#editor-redo").addEventListener("click", () => restoreEditorHistory(editor.historyIndex + 1));
function adjacentEditorPage(offset) {
  const pages = visibleEditorPages();
  const target = pages[pages.indexOf(editor.page) + offset];
  if (target) loadEditorPage(target);
}

document.querySelector("#editor-prev").addEventListener("click", () => adjacentEditorPage(-1));
document.querySelector("#editor-next").addEventListener("click", () => adjacentEditorPage(1));
async function goToEditorPage() {
  const input = document.querySelector("#editor-page-input");
  const page = Number(input.value);
  if (!Number.isInteger(page) || page < 1 || page > editor.totalPages) {
    showStatus(`أدخل رقم صفحة من 1 إلى ${editor.totalPages}.`, true);
    input.focus();
    input.select();
    return;
  }
  if (editor.deletedPages.has(page)) {
    showStatus(`الصفحة ${page} محددة للحذف. تراجع عن الحذف أولًا للانتقال إليها.`, true);
    input.focus();
    input.select();
    return;
  }
  await loadEditorPage(page);
}
document.querySelector("#editor-page-go").addEventListener("click", goToEditorPage);
document.querySelector("#editor-page-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    goToEditorPage();
  }
});
document.querySelector("#editor-zoom-out").addEventListener("click", () => changeEditorZoom(-0.15));
document.querySelector("#editor-zoom-in").addEventListener("click", () => changeEditorZoom(0.15));
document.querySelector("#editor-fit").addEventListener("click", () => {
  editor.zoomMode = "fit";
  applyEditorZoom();
});
document.querySelector("#editor-fullscreen").addEventListener("click", async () => {
  try {
    if (document.fullscreenElement === editorShell) await document.exitFullscreen();
    else await editorShell.requestFullscreen();
  } catch (_) {
    showStatus("لا يدعم المتصفح فتح المحرر بملء الشاشة.", true);
  }
});
document.addEventListener("fullscreenchange", () => {
  const fullscreen = document.fullscreenElement === editorShell;
  document.querySelector("#editor-fullscreen").textContent = fullscreen ? "⛶ إنهاء ملء الشاشة" : "⛶ ملء الشاشة";
  if (editor.zoomMode === "fit") requestAnimationFrame(applyEditorZoom);
});
document.querySelector("#editor-delete-page").addEventListener("click", async () => {
  if (visibleEditorPages().length <= 1) return;
  const deletedPage = editor.page;
  if (!window.confirm(`حذف الصفحة ${deletedPage} من النسخة الناتجة؟`)) return;
  const pagesBefore = visibleEditorPages();
  const deletedIndex = pagesBefore.indexOf(deletedPage);
  editor.deletedPages.add(deletedPage);
  editor.layers = editor.layers.filter((layer) => layer.page !== deletedPage);
  editor.selected = null;
  commitEditorHistory();
  const pagesAfter = visibleEditorPages();
  await loadEditorPage(pagesAfter[Math.min(deletedIndex, pagesAfter.length - 1)]);
  showStatus(`تم تحديد الصفحة ${deletedPage} للحذف. احفظ الملف لتطبيق التغيير.`);
});

function updateSelectedProperty(property, value) {
  const layer = selectedLayer();
  if (!layer) return;
  layer[property] = value;
  renderEditorLayers();
}

function renderEditorColorPresets() {
  editorColorPresets.replaceChildren();
  editorSavedColors.forEach((color, index) => {
    const preset = document.createElement("span");
    const swatch = document.createElement("button");
    const storeButton = document.createElement("button");
    preset.className = "editor-color-preset";
    swatch.type = "button";
    swatch.className = "editor-color-swatch";
    swatch.style.backgroundColor = color;
    swatch.title = `تطبيق اللون المحفوظ ${index + 1}: ${color}`;
    swatch.setAttribute("aria-label", swatch.title);
    swatch.addEventListener("click", () => {
      if (!selectedLayer()) return;
      editorColor.value = color;
      updateSelectedProperty("color", color);
      commitEditorHistory();
    });
    storeButton.type = "button";
    storeButton.className = "editor-color-store";
    storeButton.textContent = "↧";
    storeButton.title = `حفظ اللون الحالي في الحافظة ${index + 1}`;
    storeButton.setAttribute("aria-label", storeButton.title);
    storeButton.addEventListener("click", () => {
      editorSavedColors[index] = editorColor.value;
      try { localStorage.setItem(editorColorStorageKey, JSON.stringify(editorSavedColors)); } catch (_) { /* Storage is optional. */ }
      renderEditorColorPresets();
      showStatus(`تم حفظ اللون في الحافظة ${index + 1}.`);
    });
    preset.append(swatch, storeButton);
    editorColorPresets.appendChild(preset);
  });
}

renderEditorColorPresets();
editorPasteText.addEventListener("click", async () => {
  if (!selectedLayer()) return;
  try {
    if (!navigator.clipboard?.readText) throw new Error("Clipboard API unavailable");
    const text = await navigator.clipboard.readText();
    editorText.value = text;
    updateSelectedProperty("text", text);
    commitEditorHistory();
    editorText.focus();
    showStatus("تم لصق النص من الحافظة.");
  } catch (_) {
    editorText.focus();
    showStatus("تعذّر الوصول إلى الحافظة. استخدم Ctrl+V داخل حقل النص.", true);
  }
});
editorText.addEventListener("input", () => updateSelectedProperty("text", editorText.value));
editorText.addEventListener("change", commitEditorHistory);
editorFontSize.addEventListener("input", () => updateSelectedProperty("fontSize", Math.max(4, Math.min(200, Number(editorFontSize.value) || 16))));
editorFontSize.addEventListener("change", commitEditorHistory);
editorColor.addEventListener("input", () => updateSelectedProperty("color", editorColor.value));
editorColor.addEventListener("change", commitEditorHistory);

function updateTextDefault(property, input, minimum, maximum, fallback) {
  const value = Math.max(minimum, Math.min(maximum, Number(input.value) || fallback));
  editor.textDefaults[property] = value;
  input.value = value;
}
function previewTextDefault(property, input, minimum, maximum) {
  const value = Number(input.value);
  if (Number.isFinite(value) && value >= minimum && value <= maximum) {
    editor.textDefaults[property] = value;
  }
}
editorDefaultFontSize.addEventListener("input", () => {
  previewTextDefault("fontSize", editorDefaultFontSize, 4, 200);
});
editorDefaultFontSize.addEventListener("change", () => {
  updateTextDefault("fontSize", editorDefaultFontSize, 4, 200, 10);
});
editorDefaultWidth.addEventListener("input", () => {
  previewTextDefault("width", editorDefaultWidth, 20, 2000);
});
editorDefaultWidth.addEventListener("change", () => {
  updateTextDefault("width", editorDefaultWidth, 20, 2000, 70);
});
editorDefaultHeight.addEventListener("input", () => {
  previewTextDefault("height", editorDefaultHeight, 12, 1000);
});
editorDefaultHeight.addEventListener("change", () => {
  updateTextDefault("height", editorDefaultHeight, 12, 1000, 16);
});

editorStage.addEventListener("keydown", (event) => {
  if ((event.key === "Delete" || event.key === "Backspace") && event.target === editorStage) deleteEditorLayer();
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
    event.preventDefault();
    restoreEditorHistory(editor.historyIndex + (event.shiftKey ? 1 : -1));
  }
});
window.addEventListener("resize", () => {
  if (editor.zoomMode === "fit") applyEditorZoom();
  else renderEditorLayers();
});

document.querySelector("#editor-save-button").addEventListener("click", async (event) => {
  if (!editor.file) return;
  if (!editor.layers.length && !editor.deletedPages.size) { showStatus("أضف طبقة أو احذف صفحة واحدة على الأقل قبل الحفظ.", true); return; }
  const button = event.currentTarget;
  const data = new FormData();
  data.set("file", editor.file);
  data.set("edits", JSON.stringify(editor.layers.map(({ id, ...layer }) => layer)));
  data.set("deleted_pages", JSON.stringify([...editor.deletedPages]));
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
