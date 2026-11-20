const $ = (s) => document.querySelector(s);
let book = { summary: {}, shipments: [] };

function inr(n) {
  return "₹" + Number(n || 0).toLocaleString("en-IN");
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
    .map(([k, n]) => `<div class="bar"><div class="name">${k}</div><div class="track"><div class="fill" style="width:${(n / max) * 100}%"></div></div><div class="n">${n}</div></div>`)
    .join("") || "No shipments yet.";
}

function renderCities(rows) {
  const top = (rows || []).filter((r) => r.city).slice(0, 8);
  const max = Math.max(1, ...top.map((r) => Number(r.delayed) + Number(r.rto)));
  $("#city-bars").innerHTML = top
    .map((r) => `<div class="bar"><div class="name">${r.city}</div><div class="track"><div class="fill" style="width:${((Number(r.delayed) + Number(r.rto)) / max) * 100}%"></div></div><div class="n">${r.delayed}/${r.rto}</div></div>`)
    .join("") || "No city data yet.";
}

function pill(status, delayed, rto) {
  if (rto) return `<span class="pill risk">${status}</span>`;
  if (delayed) return `<span class="pill">${status}</span>`;
  if (status === "delivered") return `<span class="pill ok">${status}</span>`;
  return `<span class="pill">${status || "unknown"}</span>`;
}

function renderRows() {
  const q = ($("#q").value || "").toLowerCase();
  const rows = book.shipments.filter((r) =>
    !q || [r.awb, r.city, r.carrier, r.order_id, r.status].join(" ").toLowerCase().includes(q)
  );
  $("#rows").innerHTML = rows.map((r) => `<tr>
    <td>${r.awb}</td><td>${r.order_id || ""}</td><td>${r.carrier}</td><td>${r.city || ""}</td>
    <td>${r.raw_status || ""}</td><td>${pill(r.status, r.is_delayed, r.is_rto_risk)}</td>
    <td>${r.age_hours || 0}h</td><td>${r.delay_hours || 0}h</td>
    <td>${r.cod ? "COD" : "Prepaid"}</td><td>${inr(r.value_inr)}</td>
    <td><button class="link" data-awb="${r.awb}" data-carrier="${r.carrier}">Remove</button></td>
  </tr>`).join("") || `<tr><td colspan="11">No AWBs yet. Add a real shipment above.</td></tr>`;
  document.querySelectorAll(".link").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await fetch("/api/shipments/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ awb: btn.dataset.awb, carrier: btn.dataset.carrier }),
      });
      await loadBook();
    });
  });
}

async function loadBook() {
  const res = await fetch("/api/shipments");
  if (!res.ok) {
    console.error("Failed to load shipments", res.status);
    return;
  }
  book = await res.json();
  renderMetrics(book.summary);
  renderStatus(book.summary.by_status);
  renderCities(book.summary.by_city);
  renderRows();
}

async function loadAlerts() {
  const res = await fetch("/api/alerts");
  const rows = await res.json();
  $("#alerts").innerHTML = rows.length
    ? rows.map((a) => `<div>#${a.id} · ${a.channel} · ${a.kind} · ${a.awb} · ${a.message} · ${a.delivered ? "sent" : "logged"}</div>`).join("")
    : "No alerts yet.";
}

$("#btn-refresh").addEventListener("click", async () => {
  $("#form-msg").textContent = "Refreshing…";
  const res = await fetch("/api/refresh", { method: "POST" });
  const body = await res.json();
  $("#form-msg").textContent = `Polled ${body.polled || 0}. OK ${body.succeeded || 0}. Failed ${body.failed || 0}.`;
  await loadBook();
});

$("#btn-alerts").addEventListener("click", async () => {
  await fetch("/api/alerts/fanout", { method: "POST" });
  await loadAlerts();
});

$("#add-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(event.target);
  const body = {
    awb: data.get("awb"),
    carrier: data.get("carrier"),
    order_id: data.get("order_id") || "",
    city: data.get("city") || "",
    sku: data.get("sku") || "",
    value_inr: Number(data.get("value_inr") || 0),
    age_hours: Number(data.get("age_hours") || 0),
    delay_hours: Number(data.get("delay_hours") || 0),
    cod: data.get("cod") === "on",
    raw_status: data.get("raw_status") || "",
    status: data.get("status") || "",
  };
  const res = await fetch("/api/shipments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const result = await res.json();
  $("#form-msg").textContent = result.poll?.ok
    ? `Tracked ${body.awb}: ${result.poll.status}`
    : `Saved ${body.awb}. Poll: ${result.poll?.error || "waiting for credentials"}`;
  event.target.reset();
  await loadBook();
});

$("#q").addEventListener("input", renderRows);
loadBook();
loadAlerts();
