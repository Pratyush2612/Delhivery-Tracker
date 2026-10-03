const $ = (s) => document.querySelector(s);
let book = { summary: {}, shipments: [] };

function inr(n) {
  return "\u20b9" + Number(n || 0).toLocaleString("en-IN");
}

function renderMetrics(s) {
  const items = [
    ["In book", s.total],
    ["In transit+", s.in_flight],
    ["Delayed", s.delayed],
    ["RTO / NDR", s.rto],
    ["At-risk value", inr(s.at_risk_value)],
  ];
  $("#metrics").innerHTML = items
    .map(([lbl, val]) => `<div class="metric"><div class="lbl">${lbl}</div><div class="val">${val ?? 0}</div></div>`)
    .join("");
}

function renderStatus(by) {
  const max = Math.max(1, ...Object.values(by || {}));
  $("#status-bars").innerHTML = Object.entries(by || {})
    .filter(([, n]) => n > 0)
    .map(
      ([k, n]) =>
        `<div class="bar"><div class="name">${k}</div><div class="track"><div class="fill" style="width:${(n / max) * 100}%"></div></div><div class="n">${n}</div></div>`
    )
    .join("");
}

function renderCities(rows) {
  const top = (rows || []).slice(0, 8);
  const max = Math.max(1, ...top.map((r) => r.delayed + r.rto));
  $("#city-bars").innerHTML = top
    .map((r) => {
      const w = ((r.delayed + r.rto) / max) * 100;
      return `<div class="bar"><div class="name">${r.city}</div><div class="track"><div class="fill" style="width:${w}%"></div></div><div class="n">${r.delayed}/${r.rto}</div></div>`;
    })
    .join("");
}

function pill(status, delayed, rto) {
  if (rto) return `<span class="pill risk">${status}</span>`;
  if (delayed) return `<span class="pill">${status}</span>`;
  if (status === "delivered") return `<span class="pill ok">${status}</span>`;
  return `<span class="pill">${status}</span>`;
}

function renderRows() {
  const q = ($("#q").value || "").toLowerCase();
  const rows = book.shipments
    .filter((r) => r.is_delayed || r.is_rto_risk)
    .filter((r) =>
      !q
        ? true
        : [r.awb, r.city, r.carrier, r.order_id, r.status].join(" ").toLowerCase().includes(q)
    )
    .sort((a, b) => b.is_rto_risk - a.is_rto_risk || b.delay_hours - a.delay_hours);

  $("#rows").innerHTML = rows
    .map(
      (r) => `<tr>
        <td>${r.awb}</td><td>${r.order_id}</td><td>${r.carrier}</td><td>${r.city}</td>
        <td>${r.raw_status}</td><td>${pill(r.status, r.is_delayed, r.is_rto_risk)}</td>
        <td>${r.age_hours}h</td><td>${r.delay_hours}h</td>
        <td>${r.cod ? "COD" : "Prepaid"}</td><td>${inr(r.value_inr)}</td>
      </tr>`
    )
    .join("");
}

async function loadBook() {
  const res = await fetch("/api/shipments");
  book = await res.json();
  renderMetrics(book.summary);
  renderStatus(book.summary.by_status);
  renderCities(book.summary.by_city);
  renderRows();
}

async function loadAlerts() {
  const res = await fetch("/api/alerts");
  const rows = await res.json();
  if (!rows.length) return;
  $("#alerts").innerHTML = rows
    .map(
      (a) =>
        `<div class="alert-row">#${a.id} \u00b7 ${a.channel} \u00b7 ${a.kind} \u00b7 ${a.awb} \u00b7 ${a.message}</div>`
    )
    .join("");
}

$("#btn-poll").addEventListener("click", async () => {
  await fetch("/api/poll", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ n: 180, seed: Math.floor(Math.random() * 40) + 1 }),
  });
  await loadBook();
});

$("#btn-alerts").addEventListener("click", async () => {
  await fetch("/api/alerts/fanout?delay_channel=slack&rto_channel=whatsapp", { method: "POST" });
  await loadAlerts();
});

$("#q").addEventListener("input", renderRows);
loadBook();
loadAlerts();
