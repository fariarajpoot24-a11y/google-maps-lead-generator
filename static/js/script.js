// Frontend logic: calls the Flask API; no API keys live here.
const $ = (id) => document.getElementById(id);
let currentResults = [];

function setStatus(text, cls) {
  const s = $("status");
  s.textContent = text;
  s.className = "status " + (cls || "");
}

function showError(msg) {
  const e = $("error");
  e.textContent = msg;
  e.classList.toggle("hidden", !msg);
}

function cell(tr, text) {
  const td = document.createElement("td");
  td.textContent = text === "" || text == null ? "—" : text;
  tr.appendChild(td);
}

function linkCell(tr, url, label) {
  const td = document.createElement("td");
  if (url) {
    const a = document.createElement("a");
    a.href = url; a.target = "_blank"; a.rel = "noopener noreferrer";
    a.textContent = label;
    td.appendChild(a);
  } else td.textContent = "—";
  tr.appendChild(td);
}

function render(results, searched) {
  const body = $("results");
  body.innerHTML = "";
  results.forEach((r, i) => {
    const tr = document.createElement("tr");
    cell(tr, i + 1); cell(tr, r.name); cell(tr, r.category); cell(tr, r.address); cell(tr, r.phone);
    linkCell(tr, r.website, "Website");
    linkCell(tr, r.maps_url, "Open");
    cell(tr, r.rating); cell(tr, r.reviews);
    body.appendChild(tr);
  });
  const has = results.length > 0;
  $("table-wrap").classList.toggle("hidden", !has);
  $("empty").classList.toggle("hidden", has || searched === "error");
  if (!has && searched === "ok") $("empty").textContent = "No businesses found. Try a different category or location.";
  $("csv-btn").disabled = $("xlsx-btn").disabled = !has;
  $("total").textContent = results.length;
}

$("search-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  showError("");
  const payload = {
    category: $("category").value.trim(),
    location: $("location").value.trim(),
    max_results: parseInt($("max_results").value, 10),
  };
  if (payload.category.length < 2 || payload.location.length < 2) {
    return showError("Please enter a category and a location (min 2 characters).");
  }
  $("loader").classList.remove("hidden");
  $("search-btn").disabled = true;
  $("empty").classList.add("hidden");
  setStatus("Searching…", "working");
  try {
    const res = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || "Search failed.");
    currentResults = data.results;
    render(currentResults, "ok");
    setStatus("Completed", "ok");
  } catch (err) {
    currentResults = [];
    render([], "error");
    showError(err.message);
    setStatus("Failed", "fail");
  } finally {
    $("loader").classList.add("hidden");
    $("search-btn").disabled = false;
  }
});

async function download(kind) {
  showError("");
  try {
    const res = await fetch("/api/export/" + kind, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ results: currentResults }),
    });
    if (!res.ok) throw new Error((await res.json()).message || "Export failed.");
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "leads." + kind;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(a.href);
  } catch (err) { showError(err.message); }
}
$("csv-btn").addEventListener("click", () => download("csv"));
$("xlsx-btn").addEventListener("click", () => download("xlsx"));
