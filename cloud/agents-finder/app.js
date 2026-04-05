(function () {
  const rootLabel = "agentes";
  let cwd = "";

  const emoji = {
    dir: "📁",
    md: "📝",
    json: "📋",
    py: "🐍",
    txt: "📃",
    csv: "📊",
    yml: "⚙️",
    yaml: "⚙️",
    sh: "⚡",
    env: "🔐",
    gitkeep: "📌",
    default: "📄",
  };

  function extOf(name) {
    const i = name.lastIndexOf(".");
    return i >= 0 ? name.slice(i + 1).toLowerCase() : "";
  }

  function rowEmoji(isDir, name) {
    if (isDir) return emoji.dir;
    const e = extOf(name);
    return emoji[e] || emoji.default;
  }

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function setErr(msg) {
    document.getElementById("err").textContent = msg || "";
  }

  function renderBreadcrumb() {
    const el = document.getElementById("breadcrumb");
    const parts = cwd ? cwd.split("/").filter(Boolean) : [];
    let html = `<a href="#" data-path="">${esc(rootLabel)}</a>`;
    let acc = "";
    for (const p of parts) {
      acc = acc ? acc + "/" + p : p;
      html += ` <span>/</span> <a href="#" data-path="${encodeURIComponent(acc)}">${esc(p)}</a>`;
    }
    el.innerHTML = html;
    el.querySelectorAll("a[data-path]").forEach((a) => {
      a.addEventListener("click", (ev) => {
        ev.preventDefault();
        cwd = decodeURIComponent(a.getAttribute("data-path") || "");
        loadList();
      });
    });
  }

  async function loadList() {
    setErr("");
    const q = cwd ? "?path=" + encodeURIComponent(cwd) : "";
    const r = await fetch("/api/list" + q);
    if (!r.ok) {
      setErr(await r.text());
      return;
    }
    const data = await r.json();
    const tb = document.querySelector("#listing tbody");
    tb.innerHTML = "";
    const entries = data.entries || [];
    entries.sort((a, b) => {
      if (a.kind !== b.kind) return a.kind === "dir" ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    for (const e of entries) {
      const tr = document.createElement("tr");
      tr.dataset.kind = e.kind;
      const em = rowEmoji(e.kind === "dir", e.name);
      tr.innerHTML =
        `<td class="name">${em} ${esc(e.name)}</td>` +
        `<td class="meta">${e.kind === "dir" ? "carpeta" : fmtSize(e.size)}</td>`;
      tr.addEventListener("click", () => {
        if (e.kind === "dir") {
          cwd = cwd ? cwd + "/" + e.name : e.name;
          document.getElementById("preview-wrap").classList.remove("visible");
          loadList();
        } else {
          openFile(cwd ? cwd + "/" + e.name : e.name);
        }
      });
      tb.appendChild(tr);
    }
    renderBreadcrumb();
  }

  function fmtSize(n) {
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
    return (n / (1024 * 1024)).toFixed(1) + " MB";
  }

  async function openFile(relPath) {
    setErr("");
    const q = "?path=" + encodeURIComponent(relPath);
    const r = await fetch("/api/raw" + q);
    if (!r.ok) {
      setErr(await r.text());
      return;
    }
    const wrap = document.getElementById("preview-wrap");
    document.getElementById("preview-name").textContent = relPath;
    const ta = document.getElementById("preview");
    ta.value = await r.text();
    wrap.classList.add("visible");
  }

  async function uploadFile(file) {
    if (!file) return;
    setErr("");
    const rel = cwd ? cwd + "/" + file.name : file.name;
    const buf = await file.arrayBuffer();
    const r = await fetch("/api/raw?path=" + encodeURIComponent(rel), {
      method: "PUT",
      body: buf,
      headers: { "Content-Type": file.type || "application/octet-stream" },
    });
    if (!r.ok) {
      setErr(await r.text());
      return;
    }
    document.getElementById("file").value = "";
    loadList();
  }

  document.getElementById("file").addEventListener("change", (ev) => {
    const f = ev.target.files && ev.target.files[0];
    uploadFile(f);
  });

  document.getElementById("up").addEventListener("click", () => {
    if (!cwd) return;
    const i = cwd.lastIndexOf("/");
    cwd = i < 0 ? "" : cwd.slice(0, i);
    document.getElementById("preview-wrap").classList.remove("visible");
    loadList();
  });

  loadList();
})();
