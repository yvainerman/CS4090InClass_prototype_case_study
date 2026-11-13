const app = document.querySelector("#app");
const toast = document.querySelector("#toast");
let state = { user: null, facilities: [], page: "overview", dashboard: null };
let toastTimer;

const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[char]));

function localDateTime(date) {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function defaultRange() {
  const start = new Date();
  start.setDate(start.getDate() + 3);
  start.setHours(14, 0, 0, 0);
  const end = new Date(start);
  end.setHours(end.getHours() + 1);
  return [localDateTime(start), localDateTime(end)];
}

function prettyDate(value, options = { dateStyle: "medium", timeStyle: "short" }) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, options).format(date);
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  let payload = {};
  try { payload = await response.json(); } catch { /* non-JSON server response */ }
  if (!response.ok) {
    if (response.status === 401 && state.user) {
      state.user = null;
      renderLogin();
    }
    throw new Error(payload.error || "Something went wrong. Please try again.");
  }
  return payload;
}

function notify(message, error = false) {
  toast.textContent = message;
  toast.classList.toggle("toast-error", error);
  toast.classList.add("toast-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("toast-visible"), 3600);
}

function renderLogin(errorMessage = "") {
  state.user = null;
  app.innerHTML = `
    <main class="login-layout">
      <section class="login-story">
        <div class="brand brand-light"><span class="brand-mark">M</span><span>MINER<span class="brand-light-name"> SPACE</span></span></div>
        <div class="story-copy">
          <div class="eyebrow eyebrow-gold">MISSOURI S&amp;T · CAMPUS SPACES</div>
          <h1>Make room<br>for what’s next.</h1>
          <p>Find the right campus space, bring your event together, and keep every request on track.</p>
        </div>
        <div class="story-foot"><span class="gold-rule"></span><span>Plan well. Meet well. Make it happen.</span></div>
        <div class="story-orbit orbit-one"></div><div class="story-orbit orbit-two"></div>
      </section>
      <section class="login-panel">
        <div class="login-card">
          <div class="eyebrow">WELCOME TO MINER SPACE</div>
          <h2>Sign in to your account</h2>
          <p class="muted">Use your campus email or choose a demo account to explore.</p>
          ${errorMessage ? `<div class="notice notice-error">${esc(errorMessage)}</div>` : ""}
          <form id="login-form" class="form-stack">
            <label>Email address<input name="email" type="email" autocomplete="username" placeholder="you@mst.edu" required></label>
            <label>Password<input name="password" type="password" autocomplete="current-password" placeholder="Enter your password" required></label>
            <button class="button button-primary button-wide" type="submit">Sign in <span aria-hidden="true">→</span></button>
          </form>
          <div class="divider"><span>QUICK DEMO ACCESS</span></div>
          <div class="demo-access">
            <button class="demo-choice" data-demo="student@mst.edu" type="button">
              <span class="demo-icon">↗</span><span><b>Student requester</b><small>Search spaces &amp; manage events</small></span><span class="choice-arrow">→</span>
            </button>
            <button class="demo-choice" data-demo="approver@mst.edu" type="button">
              <span class="demo-icon demo-icon-gold">✓</span><span><b>Event approver</b><small>Review requests &amp; view reports</small></span><span class="choice-arrow">→</span>
            </button>
          </div>
          <p class="demo-password">Demo password for both accounts: <code>Miner2026!</code></p>
          <button class="text-button register-toggle" id="show-register" type="button">New here? Create a requester account</button>
          <form id="register-form" class="form-stack hidden">
            <div class="divider"><span>CREATE ACCOUNT</span></div>
            <label>Your name<input name="name" autocomplete="name" required maxlength="80"></label>
            <label>Campus email<input name="email" type="email" autocomplete="email" required></label>
            <label>Password<input name="password" type="password" minlength="8" autocomplete="new-password" required></label>
            <p class="field-help">New accounts have requester access in this classroom demo.</p>
            <button class="button button-primary button-wide" type="submit">Create account</button>
          </form>
          <p class="security-note">Classroom prototype · Demo sign-in is not university authentication.</p>
        </div>
      </section>
    </main>`;

  document.querySelectorAll("[data-demo]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelector("#login-form [name=email]").value = button.dataset.demo;
      document.querySelector("#login-form [name=password]").value = "Miner2026!";
      document.querySelector("#login-form [name=password]").focus();
    });
  });
  document.querySelector("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const { user } = await request("/api/login", {
        method: "POST",
        body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
      });
      await enterApp(user);
    } catch (error) {
      renderLogin(error.message);
    }
  });
  document.querySelector("#show-register").addEventListener("click", () => {
    document.querySelector("#register-form").classList.toggle("hidden");
  });
  document.querySelector("#register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const { user } = await request("/api/register", {
        method: "POST",
        body: JSON.stringify({
          name: form.get("name"), email: form.get("email"), password: form.get("password"),
        }),
      });
      await enterApp(user);
      notify("Your requester account is ready.");
    } catch (error) {
      notify(error.message, true);
    }
  });
}

async function enterApp(user) {
  state.user = user;
  state.page = "overview";
  await loadDashboard();
  renderApp();
}

async function loadDashboard() {
  state.dashboard = await request("/api/dashboard");
  state.user = state.dashboard.user;
  state.facilities = state.dashboard.facilities;
}

function renderApp() {
  if (!state.user || !state.dashboard) return renderLogin();
  const canApprove = state.user.can_approve;
  const nav = [
    ["overview", "⌂", "Overview"],
    ["search", "⌕", "Find a room"],
    ["bookings", "▤", "My reservations"],
    ...(canApprove ? [["approvals", "✓", "Approvals", state.dashboard.summary.pending_requests] ] : []),
    ...(canApprove ? [["reports", "▥", "Usage reports"] ] : []),
    ...(canApprove ? [["settings", "⚙", "Facility hours"] ] : []),
  ];
  app.innerHTML = `
    <div class="app-shell">
      <header class="topbar">
        <a class="brand" href="#" data-page="overview"><span class="brand-mark">M</span><span>MINER<span class="brand-name"> SPACE</span></span></a>
        <div class="topbar-right">
          <div class="user-chip"><span class="avatar">${esc(state.user.name.slice(0, 1).toUpperCase())}</span><span class="user-chip-copy"><b>${esc(state.user.name)}</b><small>${esc(state.user.role)}</small></span></div>
          <button class="button button-quiet" id="logout">Sign out <span aria-hidden="true">↗</span></button>
        </div>
      </header>
      <div class="workspace">
        <aside class="sidebar">
          <div class="side-label">WORKSPACE</div>
          <nav aria-label="Main navigation">
            ${nav.map(([page, icon, label, badge]) => `
              <button class="nav-link ${state.page === page ? "nav-active" : ""}" data-page="${page}">
                <span class="nav-icon">${icon}</span><span>${label}</span>
                ${badge ? `<span class="nav-badge">${badge}</span>` : ""}
              </button>`).join("")}
          </nav>
          <div class="sidebar-bottom">
            <div class="sidebar-help"><span class="help-icon">?</span><div><b>Demo workspace</b><small>Local classroom prototype</small></div></div>
            <span class="version-label">MISSOURI S&amp;T · CS4090</span>
          </div>
        </aside>
        <main class="content" id="content"></main>
      </div>
    </div>`;
  document.querySelectorAll(".sidebar [data-page], .topbar [data-page]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      state.page = button.dataset.page;
      renderApp();
    });
  });
  document.querySelector("#logout").addEventListener("click", logout);
  renderPage();
}

function pageHeading(eyebrow, title, description, action = "") {
  return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${description}</p></div>${action}</div>`;
}

function reservationCard(reservation, actions = "") {
  const statusClass = reservation.status.toLowerCase().replaceAll(" ", "-");
  const canCancel = reservation.user_id === state.user.user_id
    && ["Pending", "Approved"].includes(reservation.status);
  const cancelAction = canCancel
    ? `<div class="card-actions"><button class="button button-small button-danger" data-cancel="${esc(reservation.reservation_id)}">Cancel request</button></div>`
    : "";
  return `<article class="reservation-card">
    <div class="reservation-card-top"><div class="event-monogram">${esc(reservation.event_title.slice(0, 1).toUpperCase())}</div><span class="status status-${statusClass}">${esc(reservation.status)}</span></div>
    <h3>${esc(reservation.event_title)}</h3>
    <p class="reservation-place">${esc(reservation.facility_name)} <span>·</span> ${esc(reservation.room_id)} ${reservation.room_name ? `— ${esc(reservation.room_name)}` : ""}</p>
    <div class="reservation-meta"><span>◷ &nbsp;${esc(prettyDate(reservation.start_at))}</span><span>♙ &nbsp;${esc(reservation.expected_attendance)} people</span></div>
    ${reservation.requester ? `<p class="requester-label">Requested by ${esc(reservation.requester)}</p>` : ""}
    ${reservation.approvals?.length ? `<div class="approval-note">${esc(reservation.approvals.at(-1).decision)} by ${esc(reservation.approvals.at(-1).reviewer_name)}</div>` : ""}
    ${reservation.support_requests?.length ? `<div class="support-list">${reservation.support_requests.map((item) => `<span>✦ ${esc(item.support_type)}: ${esc(item.details)}</span>`).join("")}</div>` : ""}
    ${actions ? `<div class="card-actions">${actions}</div>` : cancelAction}
    ${["Pending", "Approved"].includes(reservation.status) && reservation.user_id === state.user.user_id ? supportForm(reservation) : ""}
  </article>`;
}

function supportForm(reservation) {
  return `<form class="support-form" data-reservation="${esc(reservation.reservation_id)}">
    <label class="sr-only" for="support-${esc(reservation.reservation_id)}">Support details</label>
    <select name="support_type" aria-label="Support type"><option value="equipment">Equipment</option><option value="security">Security</option><option value="event_support">Event support</option></select>
    <input id="support-${esc(reservation.reservation_id)}" name="details" maxlength="300" placeholder="Add event support…" required>
    <button class="button button-small button-outline" type="submit">Add</button>
  </form>`;
}

function renderPage() {
  const content = document.querySelector("#content");
  const data = state.dashboard;
  if (state.page === "overview") {
    const next = data.reservations.filter((item) => ["Approved", "Pending"].includes(item.status)).slice(0, 3);
    content.innerHTML = `
      ${pageHeading("YOUR CAMPUS, IN REACH", `Good ${greeting()}, ${esc(state.user.name.split(" ")[0])}.`, "A clear view of your spaces, requests, and upcoming events.", `<button class="button button-primary" data-page="search">＋ &nbsp; Find a room</button>`)}
      <section class="welcome-banner"><div class="welcome-copy"><span class="banner-kicker">SPACE FOR WHAT MATTERS</span><h2>Bring your next idea<br>to the table.</h2><p>Discover a room that fits your event and get your request moving.</p><button class="button button-gold" data-page="search">Explore spaces <span>→</span></button></div><div class="banner-art"><div class="art-ring ring-a"></div><div class="art-ring ring-b"></div><div class="art-shape">M</div><span class="art-caption">ROLLA · MO</span></div></section>
      <section class="stat-grid">
        ${statCard("MY RESERVATIONS", data.summary.my_reservations, "All your event requests", "▤")}
        ${statCard("UPCOMING EVENTS", data.summary.upcoming_events, "Approved and on the calendar", "◷")}
        ${state.user.can_approve ? statCard("NEEDS REVIEW", data.summary.pending_requests, "Requests awaiting a decision", "✓") : statCard("CAMPUS FACILITY", "1", "Curtis Laws Wilson Library", "⌂")}
      </section>
      <section class="section-block"><div class="section-title"><div><div class="eyebrow">YOUR ACTIVITY</div><h2>Recent reservations</h2></div><button class="text-button" data-page="bookings">View all →</button></div>
        ${next.length ? `<div class="reservation-grid">${next.map((item) => reservationCard(item)).join("")}</div>` : `<div class="empty-state"><span>▤</span><h3>Your next event starts here</h3><p>Search available rooms and send your first request.</p><button class="button button-primary" data-page="search">Find a room</button></div>`}
      </section>
      ${data.notifications.length ? `<section class="section-block notification-block"><div class="section-title"><div><div class="eyebrow">UPDATES</div><h2>Recent notifications</h2></div></div><div class="notification-list">${data.notifications.slice(0, 4).map((item) => `<div class="notification-row"><span class="notification-dot"></span><span>${esc(item.message)}</span><time>${esc(prettyDate(item.created_at))}</time></div>`).join("")}</div></section>` : ""}`;
  } else if (state.page === "search") {
    const [start, end] = defaultRange();
    content.innerHTML = `${pageHeading("ROOM DIRECTORY", "Find your space.", "Search by date, time, and group size to find a room that fits.")}<section class="panel search-panel"><form id="search-form" class="search-fields">
      ${facilitySelect("facility_id", state.facilities)}
      <label>Start date &amp; time<input name="start_at" type="datetime-local" value="${start}" required></label>
      <label>End date &amp; time<input name="end_at" type="datetime-local" value="${end}" required></label>
      <label>Minimum capacity<input name="capacity" type="number" min="1" value="15" required></label>
      <button class="button button-primary search-submit" type="submit">Search rooms <span>→</span></button>
    </form><div class="search-help">Search results honor facility hours and current pending or approved room requests.</div></section>
    <div id="search-results" class="results-area"><div class="quiet-empty"><span class="search-illustration">⌕</span><b>Your next great meeting place is waiting.</b><span>Choose your time and group size to see available spaces.</span></div></div>`;
    document.querySelector("#search-form").addEventListener("submit", searchRooms);
  } else if (state.page === "bookings") {
    content.innerHTML = `${pageHeading("YOUR EVENT PLANS", "My reservations.", "Track request status and add event support details.")}${data.reservations.length ? `<div class="reservation-grid">${data.reservations.map((item) => reservationCard(item)).join("")}</div>` : `<div class="empty-state"><span>▤</span><h3>No reservations yet</h3><p>Find an available space to start your event request.</p><button class="button button-primary" data-page="search">Find a room</button></div>`}`;
  } else if (state.page === "approvals") {
    const pending = data.pending_requests;
    content.innerHTML = `${pageHeading("APPROVER WORKSPACE", "Requests to review.", "Review event details, then approve or reject each pending request.")}${pending.length ? `<div class="reservation-grid">${pending.map((item) => reservationCard(item, `<button class="button button-small button-primary" data-decision="approve" data-id="${esc(item.reservation_id)}">Approve</button><button class="button button-small button-danger" data-decision="reject" data-id="${esc(item.reservation_id)}">Reject</button>`)).join("")}</div>` : `<div class="empty-state"><span>✓</span><h3>You’re all caught up</h3><p>There are no pending reservation requests.</p></div>`}`;
    document.querySelectorAll("[data-decision]").forEach((button) => button.addEventListener("click", decide));
  } else if (state.page === "reports") {
    const [start, end] = defaultRange();
    content.innerHTML = `${pageHeading("FACILITY ANALYTICS", "Usage report.", "Review reservations overlapping a selected date and time range.")}<section class="panel"><form id="report-form" class="report-fields">${facilitySelect("facility_id", state.facilities)}<label>From<input type="datetime-local" name="start_at" value="${start}" required></label><label>To<input type="datetime-local" name="end_at" value="${end}" required></label><button class="button button-primary" type="submit">Run report →</button></form></section><div id="report-results" class="results-area"></div>`;
    document.querySelector("#report-form").addEventListener("submit", runReport);
  } else if (state.page === "settings") {
    content.innerHTML = `${pageHeading("FACILITY ADMINISTRATION", "Facility hours.", "Manage when campus spaces are available for reservation.")}<section class="panel settings-panel">${state.facilities.map((facility) => `<form class="hours-form" data-facility="${esc(facility.facility_id)}"><div><div class="eyebrow">CAMPUS FACILITY</div><h2>${esc(facility.name)}</h2><p>${esc(facility.location)} · Current hours ${esc(facility.open_time)}–${esc(facility.close_time)}</p></div><label>Opens<input type="time" name="open_time" value="${esc(facility.open_time)}" required></label><label>Closes<input type="time" name="close_time" value="${esc(facility.close_time)}" required></label><button class="button button-primary" type="submit">Save hours</button><div class="field-help full-span">Hours cannot be narrowed if an active reservation would fall outside the new window.</div></form>`).join("")}</section>`;
    document.querySelectorAll(".hours-form").forEach((form) => form.addEventListener("submit", updateHours));
  }
  content.querySelectorAll("[data-page]").forEach((button) => button.addEventListener("click", () => {
    state.page = button.dataset.page;
    renderApp();
  }));
  content.querySelectorAll("[data-cancel]").forEach((button) => button.addEventListener("click", cancelReservation));
  content.querySelectorAll(".support-form").forEach((form) => form.addEventListener("submit", addSupport));
}

function greeting() {
  const hour = new Date().getHours();
  return hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening";
}

function statCard(label, value, detail, icon) {
  return `<article class="stat-card"><span class="stat-icon">${icon}</span><div class="stat-label">${label}</div><div class="stat-value">${esc(value)}</div><div class="stat-detail">${esc(detail)}</div></article>`;
}

function facilitySelect(name, facilities) {
  return `<label>Facility<select name="${name}" required>${facilities.map((facility) => `<option value="${esc(facility.facility_id)}">${esc(facility.name)}</option>`).join("")}</select></label>`;
}

async function searchRooms(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const params = new URLSearchParams(Object.fromEntries(form.entries()));
  const results = document.querySelector("#search-results");
  results.innerHTML = `<div class="loading-state">Checking space availability…</div>`;
  try {
    const { rooms } = await request(`/api/search?${params}`);
    if (!rooms.length) {
      results.innerHTML = `<div class="empty-state"><span>⌕</span><h3>No rooms available for that search</h3><p>Try a different time or a smaller group size. The library is open 08:00–22:00.</p></div>`;
      return;
    }
    const values = Object.fromEntries(form.entries());
    results.innerHTML = `<div class="section-title results-title"><div><div class="eyebrow">AVAILABLE SPACES</div><h2>${rooms.length} room${rooms.length === 1 ? "" : "s"} match your search</h2></div><span class="result-time">${esc(prettyDate(values.start_at))}</span></div><div class="room-grid">${rooms.map((room) => `<article class="room-card"><div class="room-card-top"><span class="room-icon">▦</span><span class="capacity-tag">Up to ${esc(room.capacity)} people</span></div><div class="eyebrow">${esc(room.facility_name)}</div><h3>${esc(room.room_id)} <span>·</span> ${esc(room.room_name)}</h3><p>Available for your selected time</p><button class="button button-outline button-wide" data-book-room="${esc(room.room_id)}">Request this room <span>→</span></button></article>`).join("")}</div>`;
    results.querySelectorAll("[data-book-room]").forEach((button) => button.addEventListener("click", () => {
      openBookingForm(values, rooms.find((room) => room.room_id === button.dataset.bookRoom));
    }));
  } catch (error) {
    results.innerHTML = `<div class="notice notice-error">${esc(error.message)}</div>`;
  }
}

function openBookingForm(search, room) {
  const result = document.querySelector("#search-results");
  result.insertAdjacentHTML("beforeend", `<section class="panel booking-panel"><div class="section-title"><div><div class="eyebrow">NEW EVENT REQUEST</div><h2>Request ${esc(room.room_id)} — ${esc(room.room_name)}</h2></div><span class="capacity-tag">${esc(room.capacity)} person capacity</span></div>
    <form id="booking-form" class="booking-fields"><input type="hidden" name="facility_id" value="${esc(room.facility_id)}"><input type="hidden" name="room_id" value="${esc(room.room_id)}">
      <label>Event title<input name="event_title" maxlength="120" placeholder="e.g. Robotics club planning session" required></label>
      <label>Expected attendance<input name="expected_attendance" type="number" min="1" max="${esc(room.capacity)}" value="${Math.min(15, room.capacity)}" required></label>
      <label>Start date &amp; time<input name="start_at" type="datetime-local" value="${esc(search.start_at)}" required></label>
      <label>End date &amp; time<input name="end_at" type="datetime-local" value="${esc(search.end_at)}" required></label>
      <div class="full-span form-actions"><span class="field-help">Requests are pending until an approver reviews them. Pending requests hold the room in this prototype.</span><button class="button button-primary" type="submit">Submit for approval <span>→</span></button></div>
    </form></section>`);
  document.querySelector("#booking-form").addEventListener("submit", submitBooking);
}

async function submitBooking(event) {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
  try {
    const { reservation } = await request("/api/reservations", {
      method: "POST", body: JSON.stringify(payload),
    });
    await loadDashboard();
    notify(`${reservation.event_title} submitted for approval.`);
    state.page = "bookings";
    renderApp();
  } catch (error) {
    notify(error.message, true);
  }
}

async function decide(event) {
  const button = event.currentTarget;
  const decision = button.dataset.decision;
  if (!window.confirm(`${decision === "approve" ? "Approve" : "Reject"} this reservation?`)) return;
  try {
    const { reservation } = await request(`/api/reservations/${encodeURIComponent(button.dataset.id)}/decision`, {
      method: "POST", body: JSON.stringify({ decision }),
    });
    await loadDashboard();
    renderApp();
    notify(`${reservation.event_title} ${decision === "approve" ? "approved" : "rejected"}. Requester notified.`);
  } catch (error) { notify(error.message, true); }
}

async function addSupport(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    await request(`/api/reservations/${encodeURIComponent(form.dataset.reservation)}/support`, {
      method: "POST", body: JSON.stringify(payload),
    });
    await loadDashboard();
    renderApp();
    notify("Support request attached to your event.");
  } catch (error) { notify(error.message, true); }
}

async function cancelReservation(event) {
  const button = event.currentTarget;
  if (!window.confirm("Cancel this reservation? The room will become available again.")) return;
  try {
    const { reservation } = await request(
      `/api/reservations/${encodeURIComponent(button.dataset.cancel)}/cancel`,
      { method: "POST", body: "{}" },
    );
    await loadDashboard();
    renderApp();
    notify(`${reservation.event_title} cancelled.`);
  } catch (error) { notify(error.message, true); }
}

async function runReport(event) {
  event.preventDefault();
  const params = new URLSearchParams(Object.fromEntries(new FormData(event.currentTarget).entries()));
  const target = document.querySelector("#report-results");
  target.innerHTML = `<div class="loading-state">Building your report…</div>`;
  try {
    const { reservations } = await request(`/api/reports?${params}`);
    target.innerHTML = reservations.length
      ? `<div class="section-title results-title"><div><div class="eyebrow">REPORT RESULTS</div><h2>${reservations.length} reservation${reservations.length === 1 ? "" : "s"} overlap this range</h2></div><span class="report-note">All statuses included</span></div><div class="reservation-grid">${reservations.map((item) => reservationCard(item)).join("")}</div>`
      : `<div class="empty-state"><span>▥</span><h3>No reservations in this period</h3><p>Try broadening your date range.</p></div>`;
  } catch (error) { target.innerHTML = `<div class="notice notice-error">${esc(error.message)}</div>`; }
}

async function updateHours(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    await request(`/api/facilities/${encodeURIComponent(form.dataset.facility)}/hours`, {
      method: "POST", body: JSON.stringify(payload),
    });
    await loadDashboard();
    renderApp();
    notify("Facility hours updated.");
  } catch (error) { notify(error.message, true); }
}

async function logout() {
  try { await request("/api/logout", { method: "POST", body: "{}" }); } catch { /* best-effort local session cleanup */ }
  state.user = null;
  state.dashboard = null;
  renderLogin();
}

async function start() {
  try {
    const bootstrap = await request("/api/bootstrap");
    state.facilities = bootstrap.facilities;
    const { user } = await request("/api/me");
    await enterApp(user);
  } catch {
    renderLogin();
  }
}

start();
