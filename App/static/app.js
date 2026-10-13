"use strict";

const $ = (id) => document.getElementById(id);
const form = $("search");
const colors = {
  normal: ["#eeeee5", "#65664b"], fire: ["#fff0e6", "#b4481c"], water: ["#e7f1ff", "#2e64a4"],
  electric: ["#fff7d5", "#8b6915"], grass: ["#eaf3df", "#48712b"], ice: ["#e5f5f5", "#367577"],
  fighting: ["#fae7e4", "#a33b34"], poison: ["#f2e8f6", "#855095"], ground: ["#f4ebdc", "#886431"],
  flying: ["#eeebf9", "#6b5c9a"], psychic: ["#fce8f0", "#a54871"], bug: ["#eff1db", "#65721c"],
  rock: ["#f1ecde", "#81703b"], ghost: ["#eee9f4", "#6b5288"], dragon: ["#ebe6fa", "#6750a4"],
  dark: ["#ece8e5", "#695547"], steel: ["#e9eef0", "#526974"], fairy: ["#faeaf3", "#9a5480"],
};
function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function title(value) { return value.split("-").map(part => part.charAt(0).toUpperCase() + part.slice(1)).join(" "); }
function badge(type) {
  const element = node("span", "badge", type);
  const [background, color] = colors[type] || colors.normal;
  element.style.backgroundColor = background;
  element.style.color = color;
  return element;
}
function busy(value) {
  document.querySelector(".results-panel").setAttribute("aria-busy", String(value));
  for (const control of document.querySelectorAll("#search button, #search input, #search select, .quick-picks button")) control.disabled = value;
  $("loading").hidden = !value;
  $("analyze").firstChild.textContent = value ? "Analyzing… " : "Find counters ";
}
function showError(message) {
  $("error").textContent = message;
  $("error").hidden = false;
  $("error").focus();
}
function render(data) {
  $("target-name").textContent = title(data.target);
  $("target-types").replaceChildren(...data.target_types.map(badge));
  $("data-source").textContent = data.source === "fallback" ? "Limited offline data" : data.source === "cache" ? "Cached data" : data.cache_used ? "Live + cached data" : "Live PokéAPI data";
  $("warnings").hidden = data.warnings.length === 0;
  $("warning-list").replaceChildren(...data.warnings.map(w => node("li", "", w)));
  $("weaknesses").replaceChildren(...data.weaknesses.map(w => {
    const card = node("div", w.multiplier >= 4 ? "weakness major" : "weakness");
    card.append(badge(w.type), node("strong", "", `${w.multiplier}×`));
    return card;
  }));
  if (!data.weaknesses.length) $("weaknesses").append(node("p", "no-counters", "No super-effective types for this combination."));
  $("counter-count").textContent = `${data.recommended_pokemon.length} found`;
  $("counters").replaceChildren(...data.recommended_pokemon.map((pick, index) => {
    const row = node("li", "counter");
    const description = node("div");
    description.append(node("h4", "", title(pick.name)), node("p", "", pick.reason));
    const score = node("div", "score");
    score.append(document.createTextNode(pick.score.toFixed(2)), node("small", "", " / 10"));
    const track = node("div", "score-track");
    track.setAttribute("aria-hidden", "true");
    const bar = node("span");
    bar.style.width = `${Math.max(0, Math.min(100, pick.score * 10))}%`;
    track.append(bar);
    score.append(track);
    row.append(node("span", "rank", String(index + 1).padStart(2, "0")), description, score);
    return row;
  }));
  $("no-counters").hidden = data.recommended_pokemon.length > 0;
  $("raw-response").textContent = JSON.stringify(data, null, 2);
  $("results").hidden = false;
  $("status").textContent = `${title(data.target)}: ${data.weaknesses.length} weaknesses and ${data.recommended_pokemon.length} counter recommendations found.`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if ($("analyze").disabled) return;
  $("error").hidden = true;
  const query = $("query").value.trim().toLowerCase();
  if (!query || query.length > 50 || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(query)) {
    showError("Enter an English Pokémon name or type, using letters, numbers and single hyphens (up to 50 characters).");
    return;
  }
  $("query").value = query;
  const payload = {query, input_type: $("input-type").value, limit: Number($("limit").value)};
  $("empty").hidden = true;
  $("results").hidden = true;
  $("status").textContent = "Analyzing your matchup. Please wait.";
  busy(true);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch("/api/v1/analyze", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload), signal: controller.signal,
    });
    if (!response.ok) {
      const messages = {
        404: "No Pokémon or type found. Check the English spelling, or try Auto-detect.",
        422: "That search is not valid. Check the name, search mode and number of counters.",
        413: "This search is too large. Please shorten your input.",
        429: `Too many searches. Try again in ${response.headers.get("Retry-After") || "60"} seconds.`,
        503: "Pokémon data is temporarily unavailable. Try again shortly, or search a type such as water for limited offline results.",
      };
      throw new Error(messages[response.status] || "Something went wrong. Please try again shortly.");
    }
    render(await response.json());
  } catch (error) {
    $("status").textContent = "Search could not be completed.";
    const message = error.name === "AbortError" ? "The search took too long. Please try again." : error instanceof TypeError ? "Cannot reach the API. Check that your local server is running." : error.message;
    showError(message);
  } finally {
    clearTimeout(timeout);
    busy(false);
  }
});
for (const button of document.querySelectorAll("[data-query]")) {
  button.addEventListener("click", () => {
    $("query").value = button.dataset.query;
    $("input-type").value = "auto";
    form.requestSubmit();
  });
}
fetch("/health", {signal: AbortSignal.timeout(5000)})
  .then(response => { if (!response.ok) throw new Error(); $("connection").textContent = "API online"; $("connection").classList.add("online"); })
  .catch(() => { $("connection").textContent = "API unavailable"; });
