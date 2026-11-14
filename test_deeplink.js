// Deep-link and airline URL checks. Run: node test_deeplink.js
const fs = require("fs");
const vm = require("vm");

function el() {
  return {
    addEventListener() {},
    appendChild(child) { return child; },
    classList: { toggle() {}, add() {}, remove() {}, contains() { return false; } },
    style: {},
    dataset: {},
    textContent: "",
    innerHTML: "",
    value: "",
    options: [],
    selectedOptions: [],
    setAttribute() {},
    removeAttribute() {},
    getAttribute() { return null; },
    querySelector() { return el(); },
    querySelectorAll() { return []; },
    closest() { return null; },
  };
}
const sandbox = {
  console,
  document: {
    addEventListener() {},
    createElement() { return el(); },
    querySelectorAll() { return []; },
    querySelector() { return null; },
    getElementById() { return el(); },
    body: el(),
    head: el(),
  },
  location: { search: "", pathname: "/", href: "https://holidaychasers.ie/", hostname: "localhost" },
  history: { state: null, pushState() {}, replaceState() {} },
  localStorage: { getItem() { return null; }, setItem() {} },
  scrollY: 0,
  addEventListener() {},
  setInterval() {},
  clearInterval() {},
  Image: function Image() {},
  URL,
  URLSearchParams,
  fetch: () => Promise.reject(new Error("no network")),
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(__dirname + "/app.js", "utf8"), sandbox, { filename: "app.js" });

const { isoDay, flightUrl, aviasalesUrl, matchDeepLink, guideQuery, legUrl } = sandbox;
function fare(city, code, price, dep, ret, airlines) {
  return { city, code, price, depart_date: dep, return_date: ret, airlines, stops: 0 };
}
const cache = {
  travellers: 1,
  airports: {
    DUB: { week_boards: [{ depart_date: "2026-12-05", return_date: "2026-12-12", deals: [
      fare("Porto", "OPO", 46, "2026-12-05", "2026-12-12", "Ryanair"),
      fare("Porto", "OPO", 39, "2026-11-28", "2026-12-05", "Ryanair"),
    ] }], weekend_boards: [] },
    ORK: { week_boards: [{ depart_date: "2026-11-20", return_date: "2026-11-22", deals: [
      fare("Porto", "OPO", 30, "2026-11-20", "2026-11-22", "Ryanair"),
    ] }], weekend_boards: [] },
  },
};

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

assert(isoDay("2026-12-05") === "2026-12-05", "iso day");
assert(isoDay("2026-13-40") === "", "reject impossible day");
assert(isoDay("05-12-2026") === "", "reject non-iso");

const ry = new URL(flightUrl("Ryanair", "DUB", "OPO", "2026-12-05", "2026-12-12", 1, 0));
assert(ry.hostname === "www.ryanair.com", "ryanair host");
assert(ry.searchParams.get("originIata") === "DUB", "ryanair origin");
assert(ry.searchParams.get("destinationIata") === "OPO", "ryanair dest");
assert(ry.searchParams.get("dateOut") === "2026-12-05", "ryanair out");
assert(ry.searchParams.get("dateIn") === "2026-12-12", "ryanair ret");
assert(ry.searchParams.get("isReturn") === "true", "ryanair return flag");

const ei = new URL(flightUrl("Aer Lingus", "DUB", "LHR", "2026-12-05", "2026-12-12", 1, 0));
assert(ei.hostname === "www.aerlingus.com", "aer lingus host");
assert(ei.searchParams.get("sourceAirportCode_0") === "DUB", "aer lingus origin");
assert(ei.searchParams.get("destinationAirportCode_0") === "LHR", "aer lingus dest");
assert(ei.searchParams.get("departureDate_0") === "2026-12-05", "aer lingus out");
assert(ei.searchParams.get("sourceAirportCode_1") === "LHR", "aer lingus return origin");
assert(ei.searchParams.get("destinationAirportCode_1") === "DUB", "aer lingus return dest");
assert(ei.searchParams.get("departureDate_1") === "2026-12-12", "aer lingus ret");

const av = new URL(aviasalesUrl("DUB", "AMS", "2026-11-20", "2026-11-22", 1));
assert(av.hostname === "www.aviasales.com", "aviasales host");
assert(av.pathname === "/search/DUB2011AMS22111", "aviasales dated path");
const bare = new URL(aviasalesUrl("DUB", "AMS", "", "", 1));
assert(bare.pathname === "/search/DUBAMS1", "aviasales omits missing dates");

const oneWay = new URL(legUrl("Ryanair", "DUB", "OPO", "2026-12-05", 1, 0));
assert(oneWay.searchParams.get("dateOut") === "2026-12-05", "one way out");
assert(!oneWay.searchParams.get("dateIn"), "one way has no return date");
assert(oneWay.searchParams.get("isReturn") === "false", "one way flag");

const exact = matchDeepLink(cache, { dest: "OPO", from: "DUB", out: "2026-12-05", ret: "2026-12-12" });
assert(exact && exact.kind === "deal", "exact deal");
assert(exact.ap === "DUB" && exact.dep === "2026-12-05" && exact.ret === "2026-12-12", "exact dates");
assert(exact.deal.price === 46 && exact.deal.airlines === "Ryanair", "exact scanned fare");

const other = matchDeepLink(cache, { dest: "OPO", from: "DUB" });
assert(other && other.kind === "deal" && other.deal.price === 39, "undated link opens the cheapest from that airport");
const either = matchDeepLink(cache, { dest: "porto" });
assert(either && either.deal.price === 30 && either.ap === "ORK", "city slug with no dates opens the cheapest airport");

const gone = matchDeepLink(cache, { dest: "OPO", from: "DUB", out: "2026-12-05", ret: "2026-12-13" });
assert(gone && gone.kind === "route" && gone.dep === "2026-12-05" && gone.ret === "2026-12-13", "missing fare keeps the dates");
assert(!gone.deal, "missing fare does not invent a price");

const junk = matchDeepLink(cache, { dest: "OPO", from: "DUB", out: "yesterday", ret: "2026-12-12" });
assert(junk && junk.kind === "deal", "bad dates fall back to cheapest");

assert(guideQuery("OPO", "DUB", "2026-12-05", "2026-12-12") === "?dest=OPO&from=DUB&out=2026-12-05&ret=2026-12-12", "guide query");

const { withExistingUtms, outboundClickParams, track, destPageLink } = sandbox;
const social = "?dest=OPO&from=DUB&out=2026-12-05&ret=2026-12-12&utm_source=facebook&utm_medium=social&utm_campaign=winter&utm_content=hero&utm_term=porto&gclid=drop-me";
const kept = withExistingUtms(guideQuery("OPO", "DUB", "2026-12-05", "2026-12-12"), social);
const keptParams = new URLSearchParams(kept.slice(1));
assert(keptParams.get("dest") === "OPO" && keptParams.get("from") === "DUB", "rewrite keeps the trip");
assert(keptParams.get("out") === "2026-12-05" && keptParams.get("ret") === "2026-12-12", "rewrite keeps the dates");
for (const key of ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]) {
  assert(keptParams.get(key) === new URLSearchParams(social.slice(1)).get(key), "keeps " + key);
}
assert(!keptParams.has("gclid"), "does not keep unrelated params");
assert(withExistingUtms("?dest=FAO", "?dest=FAO") === "?dest=FAO", "adds no utm when none are present");
assert(withExistingUtms("/", "?utm_source=instagram&utm_medium=social") === "/?utm_source=instagram&utm_medium=social", "tab rewrite keeps utms");
assert(!withExistingUtms("?tab=planner", "").includes("utm_"), "does not invent utms");

function anchor(href, attrs) {
  return {
    getAttribute(name) {
      if (name === "href") return href;
      return attrs && Object.prototype.hasOwnProperty.call(attrs, name) ? attrs[name] : null;
    },
  };
}
const ryan = outboundClickParams(anchor(
  "https://www.ryanair.com/ie/en/trip/flights/select?originIata=DUB&destinationIata=OPO&dateOut=2026-12-05&dateIn=2026-12-12&adults=1",
  { "data-hc-dest": "STALE", "data-hc-from": "ORK" }
));
assert(ryan && ryan.link_domain === "ryanair.com", "ryanair domain");
assert(ryan.destination === "OPO" && ryan.from === "DUB", "ryanair route comes from the link");
assert(ryan.airline === "Ryanair" && ryan.out === "2026-12-05" && ryan.ret === "2026-12-12", "ryanair dates");
const avia = outboundClickParams(anchor(
  "https://www.aviasales.com/search/ORK2011AMS22111?marker=543929",
  { "data-hc-dest": "AMS", "data-hc-from": "ORK", "data-hc-airline": "KLM", "data-hc-out": "2026-11-20", "data-hc-ret": "2026-11-22" }
));
assert(avia && avia.link_domain === "aviasales.com" && avia.destination === "AMS" && avia.from === "ORK", "aviasales route");
assert(avia.airline === "KLM" && avia.out === "2026-11-20" && avia.ret === "2026-11-22", "aviasales stamped dates");
assert(outboundClickParams(anchor("https://www.discovercars.com/search?pickupLocation=Porto", {})) === null, "car hire is not an outbound flight");
assert(outboundClickParams(anchor("", {})) === null, "in-page guide button is not an outbound flight");
assert(destPageLink("BCN", "Barcelona") === '<a class="deal-dest-link" href="/destinations/barcelona.html">Barcelona destination page</a>', "destination page link");
assert(destPageLink("BIO", "Bilbao") === "", "no link when the city has no page");

let sent = null;
sandbox.gtag = (type, name, params) => { sent = { type, name, params }; };
track("outbound_click", { destination: "OPO", link_domain: "ryanair.com" }, true);
assert(sent && sent.name === "outbound_click" && sent.params.transport_type === "beacon", "outbound uses a beacon");
assert(sent.params.destination === "OPO", "beacon keeps the route");
sent = null;
sandbox.gtag = null;
track("outbound_click", { destination: "OPO" }, true);
assert(sent === null, "no event before consent loads gtag");
const appSource = fs.readFileSync(__dirname + "/app.js", "utf8");
assert(!appSource.includes("track('flight_click'"), "homepage does not send a second flight_click");
assert(!appSource.includes('kind = "flight_click"'), "deal-book is not counted as flight_click");

const real = JSON.parse(fs.readFileSync(__dirname + "/deals_cache.json", "utf8"));
let sample = null;
for (const [ap, airport] of Object.entries(real.airports || {})) {
  for (const board of [...(airport.week_boards || []), ...(airport.weekend_boards || [])]) {
    for (const deal of board.deals || []) {
      if (deal.depart_date && deal.return_date && deal.code && deal.price) {
        sample = { ap, deal };
        break;
      }
    }
    if (sample) break;
  }
  if (sample) break;
}
assert(sample, "cache has a dated fare");
const roundTrip = matchDeepLink(real, {
  dest: sample.deal.code, from: sample.ap, out: sample.deal.depart_date, ret: sample.deal.return_date,
});
assert(roundTrip && roundTrip.kind === "deal", "real fare resolves");
assert(roundTrip.ap === sample.ap && roundTrip.deal.code === sample.deal.code, "real fare keeps route");
assert(roundTrip.dep === sample.deal.depart_date && roundTrip.ret === sample.deal.return_date, "real fare keeps its dates");
assert(roundTrip.deal.price <= sample.deal.price, "real fare does not invent a higher price");

console.log("ok");
