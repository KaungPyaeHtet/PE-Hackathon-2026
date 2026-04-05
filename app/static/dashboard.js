(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { Accept: "application/json", ...(opts.headers || {}) },
      ...opts,
    });
    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
      const t = await res.text();
      throw new Error(t.slice(0, 200) || res.statusText);
    }
    const data = await res.json();
    if (!res.ok) {
      const msg = data.error || data.message || JSON.stringify(data);
      throw new Error(msg);
    }
    return data;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function truncate(str, n) {
    const t = String(str);
    return t.length <= n ? t : t.slice(0, n - 1) + "…";
  }

  function toast(msg, isErr) {
    const el = $("#toast");
    el.textContent = msg;
    el.hidden = false;
    el.classList.toggle("err", !!isErr);
    clearTimeout(toast._t);
    toast._t = setTimeout(() => {
      el.hidden = true;
    }, 4500);
  }

  async function loadHealth() {
    const pill = $("#health-pill");
    try {
      const h = await api("/health");
      pill.className = "pill ok";
      pill.innerHTML =
        '<span class="dot"></span> API ' + (h.status === "ok" ? "healthy" : h.status);
    } catch {
      pill.className = "pill bad";
      pill.innerHTML = '<span class="dot"></span> API unreachable';
    }
  }

  function renderUsers(users) {
    const tb = $("#tbody-users");
    tb.innerHTML = users
      .map(
        (u) =>
          `<tr><td>${escapeHtml(u.id)}</td><td>${escapeHtml(u.username)}</td><td>${escapeHtml(u.email)}</td></tr>`,
      )
      .join("") || '<tr><td colspan="3">No users</td></tr>';
  }

  function renderUrls(urls) {
    const tb = $("#tbody-urls");
    tb.innerHTML = urls
      .map(
        (r) =>
          `<tr><td>${escapeHtml(r.id)}</td><td><code>${escapeHtml(r.short_code)}</code></td><td>${escapeHtml(truncate(r.original_url, 48))}</td><td>${r.is_active ? "yes" : "no"}</td></tr>`,
      )
      .join("") || '<tr><td colspan="4">No URLs</td></tr>';
  }

  function renderEvents(rows) {
    const tb = $("#tbody-events");
    tb.innerHTML = rows
      .map((e) => {
        const d =
          typeof e.details === "object" && e.details !== null
            ? escapeHtml(truncate(JSON.stringify(e.details), 64))
            : escapeHtml(String(e.details));
        return `<tr><td>${escapeHtml(e.id)}</td><td>${escapeHtml(e.event_type)}</td><td>${escapeHtml(e.url_id)}</td><td>${escapeHtml(e.timestamp || "—")}</td><td>${d}</td></tr>`;
      })
      .join("") || '<tr><td colspan="5">No events</td></tr>';
  }

  async function loadAll() {
    await loadHealth();

    const [usersPage, urls, events] = await Promise.all([
      api("/users?page=1&per_page=500").catch(() => []),
      api("/urls?limit=100").catch(() => []),
      api("/events?limit=80").catch(() => []),
    ]);

    const users = Array.isArray(usersPage) ? usersPage : [];
    $("#stat-users").textContent = users.length >= 500 ? "500+" : String(users.length);
    $("#stat-users-note").textContent =
      users.length >= 500 ? "first page (paginated API)" : "loaded from GET /users";

    $("#stat-urls").textContent = String(urls.length);
    $("#stat-urls-note").textContent = "GET /urls?limit=100";

    $("#stat-events").textContent = String(events.length);
    $("#stat-events-note").textContent = "GET /events?limit=80";

    renderUsers(users);
    renderUrls(urls);
    renderEvents(events);

    const sel = $("#create-user-id");
    const prev = sel.value;
    sel.innerHTML =
      '<option value="">— pick user —</option>' +
      users.map((u) => `<option value="${u.id}">${u.id}: ${escapeHtml(u.username)}</option>`).join("");
    sel.value = prev && [...sel.options].some((o) => o.value === prev) ? prev : "";

    $("#user-page-hint").textContent =
      users.length >= 500
        ? "Showing first 500 users (API pagination)."
        : `${users.length} users in view.`;
  }

  function setupTabs() {
    $$(".tabs button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.tab;
        $$(".tabs button").forEach((b) => b.classList.toggle("active", b === btn));
        $$(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${tab}`));
      });
    });
  }

  async function createShortLink(e) {
    e.preventDefault();
    const userId = $("#create-user-id").value;
    const originalUrl = $("#create-url").value.trim();
    const title = $("#create-title").value.trim();
    const box = $("#create-result");

    if (!userId) {
      toast("Select a user for this short link.", true);
      return;
    }
    try {
      const data = await api("/urls", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: Number(userId),
          original_url: originalUrl,
          title,
        }),
      });
      box.hidden = false;
      box.textContent = JSON.stringify(data, null, 2);
      toast(`Created short code: ${data.short_code}`);
      await loadAll();
    } catch (err) {
      toast(err.message || String(err), true);
      box.hidden = false;
      box.textContent = err.message || String(err);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupTabs();
    $("#form-create-url").addEventListener("submit", createShortLink);
    loadAll().catch((err) => toast(err.message || "Load failed", true));
  });
})();
