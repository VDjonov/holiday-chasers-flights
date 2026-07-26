// Holiday Chasers Ireland — main application script
// Extracted from index.html for maintainability (CSS/JS split)

// Bump this on every deploy so staging shows what's actually live.
// Only ever displayed on non-production domains — see showDevBadge() below.
const APP_VERSION = "v1.5 — Google Places key moved server-side (2026-07-26)";

// --- Back-to-top button behaviour ---
  (function(){
    const btn = () => document.getElementById("hcTopBtn");
    const overlay = () => document.getElementById("detailOverlay");
    function update(){
      const o = overlay();
      const inGuide = o && o.classList.contains("open");
      const pos = inGuide ? o.scrollTop : scrollY;
      const b = btn();
      if (b) b.classList.toggle("show", pos > 600);
    }
    addEventListener("scroll", update, { passive: true });
    document.addEventListener("DOMContentLoaded", () => {
      const o = overlay();
      if (o) o.addEventListener("scroll", update, { passive: true });
    });
    window.hcScrollTop = function(){
      const o = overlay();
      if (o && o.classList.contains("open")) o.scrollTo({ top: 0, behavior: "smooth" });
      else window.scrollTo({ top: 0, behavior: "smooth" });
    };
  })();

// --- Main app logic (search, deals, calculator, restaurants, etc.) ---
// ══════════════════════════════════════════════════════════════════════════════
// CONFIG — set your backend URL here after starting Cloudflare Tunnel
// ══════════════════════════════════════════════════════════════════════════════
// Backend for live search (Phase 2: Cloudflare Worker URL goes here).
// Empty = cache + affiliate mode: tabs are powered by deals_cache.json and
// Aviasales affiliate links. Deal Board is always unaffected.
const BACKEND_URL = "https://hc-live-search.djonov.workers.dev";  // Cloudflare Worker (Phase 2)

// ── Travelpayouts affiliate (Aviasales flight search) ────────────────────────
const TP_MARKER = "543929";
function aviasalesUrl(origin, destCode, dep, ret, adults = 1) {
  const d1 = (destCode || "").split(",")[0].trim();
  const ddmm = (iso) => iso ? iso.slice(8,10) + iso.slice(5,7) : "";
  const seg = ret ? `${origin}${ddmm(dep)}${d1}${ddmm(ret)}${adults}`
                  : `${origin}${ddmm(dep)}${d1}${adults}`;
  return `https://www.aviasales.com/search/${seg}?marker=${TP_MARKER}&currency=eur&locale=en`;
}
const NGROK_BYPASS = "?ngrok-skip-browser-warning=true";
const DEALS_JSON = "./deals_cache.json"; // static file, always available

// ── Destination data ─────────────────────────────────────────────────────────
// Confirmed direct routes from Cork ORK (Ryanair + Aer Lingus + others, June 2026)
// ── Editor's notes — one honest line per featured destination (v3) ──────────
const EDITOR_NOTES = {
  FAO: "27° and the beach twenty minutes from the airport — the easiest sun swap Ireland has.",
  AGP: "The Costa del Sol workhorse: reliable heat, cheap tapas, and a beach town for every mood.",
  BCN: "Gaudí, beach and late dinners — the classic weekend that never misses.",
  ALC: "Benidorm's quieter neighbour — all the sun at half the volume.",
  PMI: "Mallorca out of season is Ireland's best-kept secret: warm, calm, half the price.",
  LIS: "Hills, pastel tiles and €4 lunches — Europe's friendliest capital break.",
  FCO: "Rome in the shoulder season: fewer queues, same eternal city.",
  STN: "The cheapest hop over — theatre, museums and a Sunday roast by tea-time.",
  MAN: "Match tickets, gigs and shopping — the quick fix across the water.",
  EDI: "Castle views and cosy pubs — autumn in Edinburgh is a postcard.",
};

// Cork Airport's real non-stop network (47 routes, July 2026 — flightsfrom.com).
// Dublin serves everything on our lists, so only Cork needs filtering.
const CORK_ROUTES = new Set(["CDG","FRA","AMS","MUC","BCN","LHR","ZRH","LGW","MAN",
  "STN","DUB","PMI","AGP","EDI","PRG","BGY","ALC","GVA","LPA","LTN","BHX","NCE",
  "CRL","LYS","TFS","BRS","VLC","RHO","VCE","SVQ","ADB","FAO","BOD","GLA","PSA",
  "BVA","ACE","LPL","BIO","FUE","ZAD","GRO","AHO","SCQ","REU","LRH","CCF"]);
function servedFrom(ap, codeStr){
  if (ap !== "ORK") return true;   // Dublin: full network
  return (codeStr || "").split(",").some(c => CORK_ROUTES.has(c.trim()));
}

const DIRECT = [
  // Spain — Ryanair & Aer Lingus
  {code:"ALC",city:"Alicante",country:"Spain",airlines:"Ryanair"},
  {code:"BCN",city:"Barcelona",country:"Spain",airlines:"Ryanair"},
  {code:"BIO",city:"Bilbao",country:"Spain",airlines:"Aer Lingus"},
  {code:"ACE",city:"Lanzarote",country:"Spain",airlines:"Ryanair, Aer Lingus"},
  {code:"FUE",city:"Fuerteventura",country:"Spain",airlines:"Ryanair"},
  {code:"LPA",city:"Las Palmas",country:"Spain",airlines:"Ryanair"},
  {code:"FCO",city:"Rome",country:"Italy",airlines:"Ryanair, Aer Lingus"},
  {code:"VCE",city:"Venice",country:"Italy",airlines:"Ryanair, Aer Lingus"},
  {code:"BER",city:"Berlin",country:"Germany",airlines:"Ryanair"},
  {code:"MUC",city:"Munich",country:"Germany",airlines:"Aer Lingus, Lufthansa"},
  {code:"BUD",city:"Budapest",country:"Hungary",airlines:"Ryanair, Aer Lingus"},
  {code:"KRK",city:"Krakow",country:"Poland",airlines:"Ryanair"},
  {code:"WAW",city:"Warsaw",country:"Poland",airlines:"Aer Lingus, Ryanair"},
  {code:"GVA",city:"Geneva",country:"Switzerland",airlines:"Aer Lingus"},
  {code:"VIE",city:"Vienna",country:"Austria",airlines:"Ryanair, Aer Lingus"},
  {code:"ATH",city:"Athens",country:"Greece",airlines:"Ryanair, Aer Lingus"},
  {code:"CPH",city:"Copenhagen",country:"Denmark",airlines:"Ryanair"},
  {code:"AGP",city:"Malaga",country:"Spain",airlines:"Ryanair, Aer Lingus"},
  {code:"MAD",city:"Madrid",country:"Spain",airlines:"Ryanair"},
  {code:"PMI",city:"Palma Mallorca",country:"Spain",airlines:"Ryanair, Aer Lingus"},
  {code:"SVQ",city:"Seville",country:"Spain",airlines:"Ryanair"},
  {code:"TFS",city:"Tenerife South",country:"Spain",airlines:"Ryanair, Aer Lingus"},
  {code:"VLC",city:"Valencia",country:"Spain",airlines:"Ryanair"},
  // Portugal
  {code:"FAO",city:"Faro",country:"Portugal",airlines:"Ryanair, Aer Lingus"},
  {code:"LIS",city:"Lisbon",country:"Portugal",airlines:"Ryanair, Aer Lingus"},
  {code:"OPO",city:"Porto",country:"Portugal",airlines:"Ryanair"},
  // Italy
  {code:"BGY",city:"Milan Bergamo",country:"Italy",airlines:"Ryanair"},
  {code:"PSA",city:"Pisa",country:"Italy",airlines:"Ryanair"},
  // France
  {code:"BOD",city:"Bordeaux",country:"France",airlines:"Aer Lingus"},
  {code:"BVA",city:"Paris Beauvais",country:"France",airlines:"Ryanair"},
  {code:"CDG",city:"Paris CDG",country:"France",airlines:"Air France"},
  {code:"CCF",city:"Carcassonne",country:"France",airlines:"Ryanair"},
  {code:"LRH",city:"La Rochelle",country:"France",airlines:"Ryanair"},
  {code:"LYS",city:"Lyon",country:"France",airlines:"Aer Lingus"},
  {code:"NCE",city:"Nice",country:"France",airlines:"Aer Lingus"},
  // UK & Ireland
  {code:"BRS",city:"Bristol",country:"England",airlines:"Aer Lingus"},
  {code:"EDI",city:"Edinburgh",country:"Scotland",airlines:"Ryanair"},
  {code:"LGW",city:"London Gatwick",country:"England",airlines:"Aer Lingus"},
  {code:"LHR",city:"London Heathrow",country:"England",airlines:"Aer Lingus"},
  {code:"LTN",city:"London Luton",country:"England",airlines:"Ryanair"},
  {code:"STN",city:"London Stansted",country:"England",airlines:"Ryanair"},
  {code:"MAN",city:"Manchester",country:"England",airlines:"Ryanair"},
  // Germany
  {code:"FRA",city:"Frankfurt",country:"Germany",airlines:"Lufthansa"},
  // Netherlands
  {code:"AMS",city:"Amsterdam",country:"Netherlands",airlines:"KLM"},
  // Czech Republic
  {code:"PRG",city:"Prague",country:"Czech Republic",airlines:"Aer Lingus"},
  // Croatia (seasonal)
  {code:"ZAD",city:"Zadar",country:"Croatia",airlines:"Ryanair (seasonal)"},
  // Malta
  {code:"MLA",city:"Malta",country:"Malta",airlines:"Ryanair"},
  // Switzerland
  {code:"ZRH",city:"Zurich",country:"Switzerland",airlines:"SWISS"},
  // Turkey
  {code:"ADB",city:"Izmir",country:"Turkey",airlines:"SunExpress"},
  // Greece
  {code:"RHO",city:"Rhodes",country:"Greece",airlines:"Ryanair"},
];
const EUROPE = [
  {code:"VIE",city:"Vienna",country:"Austria"},{code:"BRU,CRL",city:"Brussels",country:"Belgium"},
  {code:"SOF",city:"Sofia",country:"Bulgaria"},{code:"DBV",city:"Dubrovnik",country:"Croatia"},
  {code:"ZAG",city:"Zagreb",country:"Croatia"},{code:"SPU",city:"Split",country:"Croatia"},
  {code:"LCA",city:"Larnaca",country:"Cyprus"},{code:"PRG",city:"Prague",country:"Czech Republic"},
  {code:"CPH",city:"Copenhagen",country:"Denmark"},{code:"TLL",city:"Tallinn",country:"Estonia"},
  {code:"HEL",city:"Helsinki",country:"Finland"},{code:"CDG,ORY",city:"Paris",country:"France"},
  {code:"NCE",city:"Nice",country:"France"},{code:"LYS",city:"Lyon",country:"France"},
  {code:"MRS",city:"Marseille",country:"France"},{code:"BER",city:"Berlin",country:"Germany"},
  {code:"MUC",city:"Munich",country:"Germany"},{code:"FRA",city:"Frankfurt",country:"Germany"},
  {code:"HAM",city:"Hamburg",country:"Germany"},{code:"ATH",city:"Athens",country:"Greece"},
  {code:"SKG",city:"Thessaloniki",country:"Greece"},{code:"JTR",city:"Santorini",country:"Greece"},
  {code:"HER",city:"Heraklion",country:"Greece"},{code:"BUD",city:"Budapest",country:"Hungary"},
  {code:"KEF",city:"Reykjavik",country:"Iceland"},{code:"FCO",city:"Rome",country:"Italy"},
  {code:"MXP,LIN",city:"Milan",country:"Italy"},{code:"VCE",city:"Venice",country:"Italy"},
  {code:"NAP",city:"Naples",country:"Italy"},{code:"BLQ",city:"Bologna",country:"Italy"},
  {code:"CTA",city:"Catania",country:"Italy"},{code:"RIX",city:"Riga",country:"Latvia"},
  {code:"VNO",city:"Vilnius",country:"Lithuania"},{code:"MLA",city:"Malta",country:"Malta"},
  {code:"AMS",city:"Amsterdam",country:"Netherlands"},{code:"OSL",city:"Oslo",country:"Norway"},
  {code:"WAW",city:"Warsaw",country:"Poland"},{code:"KRK",city:"Krakow",country:"Poland"},
  {code:"GDN",city:"Gdansk",country:"Poland"},{code:"LIS",city:"Lisbon",country:"Portugal"},
  {code:"OPO",city:"Porto",country:"Portugal"},{code:"FAO",city:"Faro",country:"Portugal"},
  {code:"OTP",city:"Bucharest",country:"Romania"},{code:"BTS",city:"Bratislava",country:"Slovakia"},
  {code:"LJU",city:"Ljubljana",country:"Slovenia"},{code:"BCN",city:"Barcelona",country:"Spain"},
  {code:"MAD",city:"Madrid",country:"Spain"},{code:"AGP",city:"Malaga",country:"Spain"},
  {code:"VLC",city:"Valencia",country:"Spain"},{code:"SVQ",city:"Seville",country:"Spain"},
  {code:"BIO",city:"Bilbao",country:"Spain"},{code:"ARN",city:"Stockholm",country:"Sweden"},
  {code:"GOT",city:"Gothenburg",country:"Sweden"},{code:"GVA",city:"Geneva",country:"Switzerland"},
  {code:"ZRH",city:"Zurich",country:"Switzerland"},{code:"IST",city:"Istanbul",country:"Turkey"},
  {code:"LHR,LGW,STN",city:"London",country:"United Kingdom"},
  {code:"EDI",city:"Edinburgh",country:"United Kingdom"},
  {code:"MAN",city:"Manchester",country:"United Kingdom"},
];

// ── City photos: fetched live from Wikipedia (CORS-enabled, no key, always resolves) ──
// We map each airport code to a Wikipedia article title, then fetch that page's
// lead image. This avoids fragile hardcoded filenames and covers every city.
const CITY_WIKI = {
  VIE:"Vienna", ATH:"Athens", CPH:"Copenhagen", VCE:"Venice",
  FUE:"Fuerteventura", LPA:"Las_Palmas_de_Gran_Canaria",
  MAN:"Manchester", LHR:"London", LGW:"London", STN:"London", LTN:"London",
  EDI:"Edinburgh", BRS:"Bristol",
  FAO:"Faro,_Portugal", LIS:"Lisbon", OPO:"Porto",
  BCN:"Barcelona", MAD:"Madrid", AGP:"Málaga", ALC:"Alicante",
  ACE:"Lanzarote", PMI:"Palma_de_Mallorca", TFS:"Tenerife", VLC:"Valencia",
  SVQ:"Seville", BIO:"Bilbao",
  BGY:"Milan", MXP:"Milan", PSA:"Pisa", FCO:"Rome",
  CDG:"Paris", BVA:"Paris", NCE:"Nice", LYS:"Lyon", BOD:"Bordeaux",
  AMS:"Amsterdam", FRA:"Frankfurt", PRG:"Prague", ZRH:"Zurich",
  MLA:"Valletta", ZAD:"Zadar", RHO:"Rhodes_(city)", ADB:"İzmir",
  GVA:"Geneva", MUC:"Munich", BER:"Berlin", BUD:"Budapest",
  KRK:"Kraków", WAW:"Warsaw",
};

const photoUrlCache = {};
async function fetchCityPhoto(code, cityName, preferHiRes) {
  const title = CITY_WIKI[code] || cityName;
  if (!title) return "";
  const cacheKey = preferHiRes ? code + ":hi" : code;
  if (photoUrlCache[cacheKey] !== undefined) return photoUrlCache[cacheKey];
  try {
    const r = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${title}`);
    const d = await r.json();
    const thumb = (d.thumbnail && d.thumbnail.source) || "";
    const orig  = (d.originalimage && d.originalimage.source) || "";
    // Board cards want the light thumbnail; the full-width hero wants the original.
    const url = preferHiRes ? (orig || thumb) : (thumb || orig);
    photoUrlCache[cacheKey] = url;
    return url;
  } catch(e) {
    photoUrlCache[cacheKey] = "";
    return "";
  }
}

// ── City coordinates (for weather) ───────────────────────────────────────────
const CITY_COORDS = {
  VIE:[48.21,16.37], ATH:[37.98,23.73], CPH:[55.68,12.57],
  VCE:[45.44,12.34], FUE:[28.50,-13.86], LPA:[28.12,-15.43],
  MAN:[53.48,-2.24], LHR:[51.51,-0.13], LGW:[51.51,-0.13], STN:[51.51,-0.13], LTN:[51.51,-0.13],
  EDI:[55.95,-3.19], BRS:[51.45,-2.59],
  FAO:[37.02,-7.93], LIS:[38.72,-9.14], OPO:[41.16,-8.62],
  BCN:[41.39,2.17], MAD:[40.42,-3.70], AGP:[36.72,-4.42], ALC:[38.35,-0.48],
  ACE:[28.96,-13.55], PMI:[39.57,2.65], TFS:[28.05,-16.57], VLC:[39.47,-0.38],
  SVQ:[37.39,-5.99], BIO:[43.26,-2.93],
  BGY:[45.46,9.19], MXP:[45.46,9.19], PSA:[43.72,10.40], FCO:[41.90,12.50],
  CDG:[48.86,2.35], BVA:[48.86,2.35], NCE:[43.70,7.27], LYS:[45.76,4.84], BOD:[44.84,-0.58],
  AMS:[52.37,4.90], FRA:[50.11,8.68], PRG:[50.08,14.44], ZRH:[47.37,8.54],
  MLA:[35.90,14.51], ZAD:[44.12,15.23], RHO:[36.43,28.22], ADB:[38.42,27.14],
  BER:[52.52,13.40], BUD:[47.50,19.04], GVA:[46.20,6.14], KRK:[50.06,19.94],
  MUC:[48.14,11.58], WAW:[52.23,21.01],
};

// Map Open-Meteo weather codes to emoji + label
function weatherIcon(code) {
  if (code === 0) return ["☀️","Clear"];
  if (code <= 2) return ["🌤️","Partly cloudy"];
  if (code === 3) return ["☁️","Cloudy"];
  if (code <= 48) return ["🌫️","Foggy"];
  if (code <= 67) return ["🌧️","Rainy"];
  if (code <= 77) return ["❄️","Snowy"];
  if (code <= 82) return ["🌦️","Showers"];
  if (code <= 99) return ["⛈️","Stormy"];
  return ["🌡️",""];
}

// Fetch weather for a city on a date. Forecast if within 16 days; otherwise
// the average of the same date across the last 3 years ("typical").
const weatherCache = {};
async function getWeather(code, dateStr) {
  const coords = CITY_COORDS[code];
  if (!coords) return null;
  const key = code + dateStr;
  if (weatherCache[key] !== undefined) return weatherCache[key];

  const [lat, lon] = coords;
  const target = new Date(dateStr + "T12:00:00");
  const today = new Date();
  const daysOut = Math.round((target - today) / 86400000);

  try {
    // Near-term: real forecast
    if (daysOut >= 0 && daysOut <= 15) {
      const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&start_date=${dateStr}&end_date=${dateStr}&timezone=auto`;
      const d = await (await fetch(url)).json();
      if (d.daily && d.daily.temperature_2m_max && d.daily.temperature_2m_max[0] != null) {
        const result = {
          tmax: Math.round(d.daily.temperature_2m_max[0]),
          tmin: Math.round(d.daily.temperature_2m_min[0]),
          code: d.daily.weather_code[0],
          rain: d.daily.precipitation_probability_max ? d.daily.precipitation_probability_max[0] : null,
          typical: false,
        };
        weatherCache[key] = result; return result;
      }
    }

    // Far-out: average the same date over the last 3 years from the archive.
    const mmdd = dateStr.slice(5); // "08-07"
    const years = [target.getFullYear()-1, target.getFullYear()-2, target.getFullYear()-3];
    const maxes = [], mins = [], codes = [];
    for (const y of years) {
      const ds = `${y}-${mmdd}`;
      const url = `https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}&daily=weather_code,temperature_2m_max,temperature_2m_min&start_date=${ds}&end_date=${ds}&timezone=auto`;
      try {
        const d = await (await fetch(url)).json();
        if (d.daily && d.daily.temperature_2m_max && d.daily.temperature_2m_max[0] != null) {
          maxes.push(d.daily.temperature_2m_max[0]);
          mins.push(d.daily.temperature_2m_min[0]);
          if (d.daily.weather_code && d.daily.weather_code[0] != null) codes.push(d.daily.weather_code[0]);
        }
      } catch(e) {}
    }
    if (maxes.length) {
      const avg = a => a.reduce((s,x)=>s+x,0)/a.length;
      // most common weather code
      const code2 = codes.length ? codes.sort((a,b)=>
        codes.filter(v=>v===a).length - codes.filter(v=>v===b).length).pop() : 1;
      const result = {
        tmax: Math.round(avg(maxes)),
        tmin: Math.round(avg(mins)),
        code: code2,
        rain: null,
        typical: true,
      };
      weatherCache[key] = result; return result;
    }
  } catch(e) {}

  weatherCache[key] = null;
  return null;
}
const BACKEND_HEADERS = {
  "Content-Type": "application/json",
  "ngrok-skip-browser-warning": "true"
};
let cachedDeals = null;

// ── Deep links from the SEO destination pages ───────────────────────────────
// /?dest=EDI (or a slug like edinburgh) opens that city's guide with its best
// current deal, so Google visitors land on the real product, not just the top
// of the page.
function openDeepLink() {
  try {
    const q = new URLSearchParams(location.search).get("dest");
    if (!q) return;
    const want = q.trim().toUpperCase();
    let best = null, bestAp = null;
    for (const [apCode, ap] of Object.entries(cachedDeals.airports || {})) {
      for (const b of [...(ap.weekend_boards || []), ...(ap.week_boards || [])]) {
        for (const dl of (b.deals || [])) {
          const code = (dl.code || "").toUpperCase();
          const city = (dl.city || "").toUpperCase().replace(/[^A-Z]/g, "");
          if (code === want || city === want.replace(/[^A-Z]/g, "")) {
            if (!best || dl.price < best.deal.price) best = { deal: dl, board: b }, bestAp = apCode;
          }
        }
      }
    }
    if (best) {
      openDetail({ ...best.deal, origin_airport: bestAp },
                 best.deal.depart_date || best.board.depart_date,
                 best.deal.return_date || best.board.return_date,
                 1, cachedDeals.travellers || 1, false);
    }
  } catch (e) { /* deep link is best-effort */ }
}
let currentBoard = "week";  // default landing view: one-week deals
let selectedAirport = "ORK";  // ORK, DUB, or BEST (best of both)

// ── Airport selector ─────────────────────────────────────────────────────────
function switchAirport(code) {
  selectedAirport = code;
  document.querySelectorAll(".ap-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.ap === code);
  });
  const labels = {ORK:"Cork Airport (ORK)", DUB:"Dublin Airport (DUB)", BEST:"Best deal — both airports"};
  const sub = {
    ORK: "Return fares from Cork — shown per person. Group totals are estimated from the per-person fare.",
    DUB: "Return fares from Dublin — shown per person. Group totals are estimated from the per-person fare.",
    BEST: "The cheapest fare per destination across Cork and Dublin — we pick the best for you."
  };
  document.getElementById("boardHeading").textContent = "Cheapest escapes · " + labels[code];
  document.getElementById("boardSubtitle").textContent = sub[code];
  applyBestBoardDefaults();
  populateBoardPicker();
  renderDeals();
}
let budgetMax = 0;
// Traveller selection (default: 1 adult, 0 children)
let selAdults = 1;
let selChildren = 0;

function travellerLabel(){
  const a = selAdults, c = selChildren;
  const parts = [];
  parts.push(a + " adult" + (a>1?"s":""));
  if (c>0) parts.push(c + " child" + (c>1?"ren":""));
  const total = a + c;
  if (total === 1) return "1 traveller";
  return parts.join(" + ");
}

function changeTravellers(kind, delta){
  if (kind === "adults") selAdults = Math.min(6, Math.max(1, selAdults + delta));
  else selChildren = Math.min(5, Math.max(0, selChildren + delta));
  // Update every traveller display that's present (deal board + plan tab share state).
  const setTxt = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  setTxt("tvAdults", selAdults);
  setTxt("tvChildren", selChildren);
  setTxt("tvSummary", travellerLabel());
  setTxt("planAdults", selAdults);
  setTxt("planChildren", selChildren);
  setTxt("planTvSummary", travellerLabel());
  renderDeals();
}
let backendOnline = false;

// ── Affiliate IDs ────────────────────────────────────────────────────────────
// Paste your affiliate IDs here once approved. Empty = plain link (still works,
// just no commission). See notes in chat for where to sign up.
const AFFILIATE = {
  booking:     "",   // Booking.com (hotels) — your aid, e.g. "1234567"
  discovercars:"",   // DiscoverCars — your affiliate code
  rentalcars:  "",   // Rentalcars.com — your affiliate/partner code
  autoeurope:  "",   // Auto Europe — your affiliate code
  welcomepickups:""  // Welcome Pickups (airport transfers) — your ref code
};

// ── Booking deep-links ───────────────────────────────────────────────────────
function hotelUrl(city, dep, ret) {
  // Booking.com public search using the selected group. Children default to age 8.
  const a = selAdults, c = selChildren;
  let url = `https://www.booking.com/searchresults.html?ss=${encodeURIComponent(city)}`
    + `&checkin=${dep}&checkout=${ret}`
    + `&group_adults=${a}&no_rooms=1&group_children=${c}`
    + `&req_adults=${a}&req_children=${c}`;
  for (let i=0;i<c;i++) url += `&age=8&req_age=8`;
  if (AFFILIATE.booking) url += `&aid=${AFFILIATE.booking}`;
  return url;
}
function airbnbUrl(city, dep, ret) {
  const a = selAdults, c = selChildren;
  return `https://www.airbnb.com/s/${encodeURIComponent(city)}/homes?checkin=${dep}&checkout=${ret}&adults=${a}&children=${c}`;
}

// Three car-hire comparison sites — pre-filled with city + dates.
function carUrlDiscover(city, dep, ret) {
  let u = `https://www.discovercars.com/search?pickupLocation=${encodeURIComponent(city)}&pickupDate=${dep}&dropoffDate=${ret}`;
  if (AFFILIATE.discovercars) u += `&aff=${AFFILIATE.discovercars}`;
  return u;
}
function carUrlRentalcars(city, dep, ret) {
  let u = `https://www.rentalcars.com/SearchResults.do?location=${encodeURIComponent(city)}&puDay=${dep.slice(8)}&puMonth=${dep.slice(5,7)}&puYear=${dep.slice(0,4)}&doDay=${ret.slice(8)}&doMonth=${ret.slice(5,7)}&doYear=${ret.slice(0,4)}`;
  if (AFFILIATE.rentalcars) u += `&affiliateCode=${AFFILIATE.rentalcars}`;
  return u;
}
function carUrlAutoEurope(city, dep, ret) {
  let u = `https://www.autoeurope.eu/en/car-rental/${encodeURIComponent(city.toLowerCase().replace(/\s+/g,'-'))}/`;
  if (AFFILIATE.autoeurope) u += `?aid=${AFFILIATE.autoeurope}`;
  return u;
}
// Back-compat: existing calls to carUrl() default to DiscoverCars
function carUrl(city, dep, ret){ return carUrlDiscover(city, dep, ret); }

// Airport transfer (taxi rows link here — a real bookable transfer service).
function transferUrl(city) {
  let u = `https://www.welcomepickups.com/${encodeURIComponent(city.toLowerCase().replace(/\s+/g,'-'))}/`;
  if (AFFILIATE.welcomepickups) u += `?ref=${AFFILIATE.welcomepickups}`;
  return u;
}

// ── Brand wordmark logos (styled text, no external assets) ───────────────────
// Clean, recognisable brand-style logos drawn in CSS/SVG. Once you're an
// approved affiliate you can swap these for the official logo images they give
// you — just replace the returned markup with an <img src="logo.svg">.
const BRAND = {
  booking: `<span class="brand brand-booking">Booking<span class="dot">.</span>com</span>`,
  airbnb: `<span class="brand brand-airbnb"><svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M12 1.5c1.6 0 2.7 1.1 3.8 3.1.7 1.3 2.6 5.2 4.4 9.4.3.7.5 1.4.5 2.1 0 2.4-1.9 4.4-4.3 4.4-1.4 0-2.7-.7-4.4-2.5-1.7 1.8-3 2.5-4.4 2.5C5.2 20 3.3 18 3.3 15.6c0-.7.2-1.4.5-2.1 1.8-4.2 3.7-8.1 4.4-9.4C9.3 2.6 10.4 1.5 12 1.5zm0 2c-.6 0-1.1.5-1.9 2C9.4 7 7.6 10.7 5.9 14.7c-.2.5-.3.9-.3 1.3 0 1.3 1 2.3 2.3 2.3.9 0 1.9-.6 3.2-2-.9-1.1-1.7-2.4-1.7-3.7 0-1.6 1.2-2.8 2.6-2.8s2.6 1.2 2.6 2.8c0 1.3-.8 2.6-1.7 3.7 1.3 1.4 2.3 2 3.2 2 1.3 0 2.3-1 2.3-2.3 0-.4-.1-.8-.3-1.3-1.7-4-3.5-7.7-4.2-9.2-.8-1.5-1.3-2-1.9-2zm0 8.7c-.5 0-.9.4-.9 1 0 .6.4 1.4.9 2 .5-.6.9-1.4.9-2 0-.6-.4-1-.9-1z"/></svg>airbnb</span>`,
  discovercars: `<span class="brand brand-dc">Discover<span class="b">Cars</span></span>`,
  rentalcars: `<span class="brand brand-rc">Rentalcars<span class="b">.com</span></span>`,
  autoeurope: `<span class="brand brand-ae">Auto<span class="b">Europe</span></span>`
};

// ── Airline deeplinks — routes users directly to the airline's own site ────────
// Ryanair and Aer Lingus have reliable deeplink URL formats.
// KLM, Transavia, easyJet etc. have unstable/broken deeplink formats that
// change without notice — for those we use Skyscanner Ireland (trusted in
// Ireland, reliable pre-fill, and the user still ends up booking on the airline).
const AIRLINE_URLS = {
  // Ryanair — dateOut/dateIn confirmed working from real Ryanair URLs
  ryanair: (origin, dest, dep, ret, adults, children) => {
    const p = new URLSearchParams({
      originIata: origin, destinationIata: dest,
      dateOut: dep,
      adults, teens: 0, children, infants: 0,
    });
    if (ret) p.set("dateIn", ret);            // omit for one-way
    return `https://www.ryanair.com/ie/en/trip/flights/select?${p}`;
  },
  // Aer Lingus — return flight search with pre-filled route and dates
  "aer lingus": (origin, dest, dep, ret, adults, children) => {
    const p = new URLSearchParams({
      fareType: ret ? "RETURN" : "ONEWAY", fareCategory: "ECONOMY",
      numAdults: adults, numYoungAdults: 0,
      numChildren: children, numInfants: 0, groupBooking: false,
      sourceAirportCode_0: origin, destinationAirportCode_0: dest, departureDate_0: dep,
    });
    if (ret) {
      p.set("sourceAirportCode_1", dest);
      p.set("destinationAirportCode_1", origin);
      p.set("departureDate_1", ret);
    }
    return `https://www.aerlingus.com/app/make/flight-search-result?${p}`;
  },
};

// One-way booking link for a single selected leg. Known airlines get their
// pre-filled site; everything else goes to our partner Aviasales (one-way).
function legUrl(airlinesStr, origin, dest, date, adults, children) {
  const primary = (airlinesStr || "").split(/[,/]/)[0].trim().toLowerCase();
  if (primary === "ryanair") {
    const p = new URLSearchParams({
      originIata: origin, destinationIata: dest, dateOut: date,
      adults, teens: 0, children, infants: 0, isReturn: false,
    });
    return `https://www.ryanair.com/ie/en/trip/flights/select?${p}`;
  }
  if (primary === "aer lingus") {
    const p = new URLSearchParams({
      fareType: "ONEWAY", fareCategory: "ECONOMY",
      numAdults: adults, numYoungAdults: 0,
      numChildren: children, numInfants: 0, groupBooking: false,
      sourceAirportCode_0: origin, destinationAirportCode_0: dest, departureDate_0: date,
    });
    return `https://www.aerlingus.com/app/make/flight-search-result?${p}`;
  }
  return aviasalesUrl(origin, dest, date, null, Math.max(1, adults || 1));
}

// Skyscanner Ireland — reliable pre-filled fallback for all other airlines.
// Converts date "2026-08-28" → "20260828" for Skyscanner URL format.
function skyscanner(origin, dest, dep, ret, adults, children) {
  const d1 = dep.replace(/-/g, "");
  const d2 = ret.replace(/-/g, "");
  const pax = `adults=${adults}&children=${children}`;
  return `https://www.skyscanner.ie/transport/flights/${origin.toLowerCase()}/${dest.toLowerCase()}/${d1}/${d2}/?${pax}&currency=EUR`;
}

// Returns the deeplink for the primary airline on a deal.
function flightUrl(airlinesStr, origin, dest, dep, ret, adults, children) {
  const primary = (airlinesStr || "").split(/[,/]/)[0].trim().toLowerCase();
  const builder = AIRLINE_URLS[primary];
  if (builder) return builder(origin, dest, dep, ret, adults, children);
  // All other airlines → Aviasales (our partner): all carriers + connections
  return aviasalesUrl(origin, dest, dep, ret, Math.max(1, adults || 1));
}

// Returns the button label — honest about Skyscanner for non-direct links.
function flightBtnLabel(airlinesStr, fallback="Search flights") {
  const primary = (airlinesStr || "").split(/[,/]/)[0].trim();
  if (!primary) return fallback;
  const lower = primary.toLowerCase();
  // Airlines with reliable direct deeplinks get "Book on [airline]"
  if (lower === "ryanair" || lower === "aer lingus") return `✈ Book on ${primary}`;
  // Others go via our partner Aviasales — honest label
  return `✈ Search on Aviasales`;
}

function activateTab(name){
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
  const el = document.getElementById("tab-" + name);
  if (el) el.classList.add("active");
}
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    activateTab(btn.dataset.tab);
    // Shareable URL per tab (Deal Board stays clean "/")
    const url = btn.dataset.tab === "deals" ? location.pathname : `?tab=${btn.dataset.tab}`;
    history.replaceState({ hcTab: btn.dataset.tab }, "", url);
  });
});

// Back/forward: close the guide like an app instead of leaving the site.
window.addEventListener("popstate", (e) => {
  const overlay = document.getElementById("detailOverlay");
  const guideOpen = overlay && overlay.classList.contains("open");
  const wantsGuide = e.state && e.state.hcGuide;
  if (guideOpen && !wantsGuide) {
    overlay.classList.remove("open");
    document.body.style.overflow = "";
  }
  if (e.state && e.state.hcTab) activateTab(e.state.hcTab);
});

// ── Board toggle ─────────────────────────────────────────────────────────────
document.querySelectorAll("#boardToggle button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#boardToggle button").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentBoard = btn.dataset.board;
    populateBoardPicker();   // rebuild picker for the active board type
    renderDeals();
  });
});

// ── Board picker (works for both weekend and week boards) ────────────────────
let selectedWeekendIdx = 0;
let selectedWeekIdx = 0;

function currentBoardList() {
  if (!cachedDeals) return [];
  // Resolve which airport's boards to use
  let apCode = selectedAirport === "BEST" ? "ORK" : selectedAirport;
  const apData = cachedDeals.airports?.[apCode];
  if (apData) {
    return currentBoard === "weekend"
      ? (apData.weekend_boards || [])
      : (apData.week_boards || []);
  }
  // Legacy fallback for old cache format (ORK only, no airports key)
  if (currentBoard === "weekend") return cachedDeals.weekend_boards || [];
  return cachedDeals.week_boards || (cachedDeals.week_board ? [cachedDeals.week_board] : []);
}

function getAltAirportData() {
  // Returns the other airport's data for the comparison mini-card.
  if (!cachedDeals?.airports || selectedAirport === "BEST") return null;
  const altCode = selectedAirport === "ORK" ? "DUB" : "ORK";
  return {code: altCode, data: cachedDeals.airports[altCode]};
}

function getBestOfBothBoard(boardIdx) {
  // For "Best of both": merge deals from both airports, pick cheapest per destination.
  if (!cachedDeals?.airports) return null;
  const combined = {};
  for (const [code, ap] of Object.entries(cachedDeals.airports)) {
    const list = currentBoard === "weekend"
      ? (ap.weekend_boards || []) : (ap.week_boards || []);
    const board = list[boardIdx] || list[0];
    if (!board) continue;
    for (const deal of board.deals || []) {
      if (!combined[deal.code] || deal.price < combined[deal.code].price) {
        combined[deal.code] = {...deal, origin_airport: code, origin_name: ap.name};
      }
    }
  }
  // Use ORK board for dates/label
  const orkBoards = currentBoard === "weekend"
    ? (cachedDeals.airports.ORK?.weekend_boards || [])
    : (cachedDeals.airports.ORK?.week_boards || []);
  const refBoard = orkBoards[boardIdx] || orkBoards[0] || {};
  return {
    ...refBoard,
    deals: Object.values(combined).sort((a, b) => a.price - b.price)
  };
}

// Fills the airport pill counts and the "who wins today" summary line.
function updateAirportCounts() {
  if (!cachedDeals?.airports) return;
  const idx = currentBoard === "weekend" ? selectedWeekendIdx : selectedWeekIdx;
  const getBoard = (code) => {
    const ap = cachedDeals.airports[code];
    if (!ap) return null;
    const list = currentBoard === "weekend" ? (ap.weekend_boards||[]) : (ap.week_boards||[]);
    return list[idx] || list[0] || null;
  };
  const ork = getBoard("ORK"), dub = getBoard("DUB");
  const orkDeals = ork?.deals || [], dubDeals = dub?.deals || [];
  const el = (id) => document.getElementById(id);
  if (el("cntORK")) el("cntORK").textContent = orkDeals.length ? `${orkDeals.length} deals` : "";
  if (el("cntDUB")) el("cntDUB").textContent = dubDeals.length ? `${dubDeals.length} deals` : "";

  // Who wins today: per destination, which airport is cheaper
  const dubByCode = Object.fromEntries(dubDeals.map(d => [d.code, d]));
  let orkWins = 0, dubWins = 0, bestSave = 0, bestCity = "", bestAp = "";
  for (const d of orkDeals) {
    const alt = dubByCode[d.code];
    if (!alt) continue;
    const diff = alt.price - d.price;
    if (diff > 0) { orkWins++; if (diff > bestSave) { bestSave = diff; bestCity = d.city; bestAp = "Cork"; } }
    else if (diff < 0) { dubWins++; if (-diff > bestSave) { bestSave = -diff; bestCity = d.city; bestAp = "Dublin"; } }
  }
  if (el("cntBEST")) el("cntBEST").textContent = (orkWins+dubWins) ? `compare ${orkWins+dubWins}` : "";

  const wins = el("winsLine");
  if (wins) {
    if (selectedAirport === "BEST" && (orkWins || dubWins)) {
      const trav = cachedDeals.travellers || 4;
      const savePP = Math.round(bestSave / trav);
      wins.innerHTML = `Today <b>Dublin wins ${dubWins}</b> destination${dubWins!==1?'s':''}, <b>Cork wins ${orkWins}</b>` +
        (bestSave ? ` — biggest saving <b>€${savePP}/pp</b> flying from ${bestAp} to ${bestCity}.` : ".");
      wins.style.display = "block";
    } else {
      wins.style.display = "none";
    }
  }
}

function selectBoard(idx) {
  if (currentBoard === "weekend") selectedWeekendIdx = idx;
  else selectedWeekIdx = idx;
  document.querySelectorAll("#weekendPicker .weekend-btn").forEach((b, i) => {
    b.classList.toggle("active", i === idx);
  });
  renderDeals();
}

// Index of the "best" board: cheapest top deal among boards that have
// enough offers to be worth landing on. Sparse boards (e.g. a glitchy scan
// that returned 1 offer) can never become the default view. If no board
// meets the threshold, fall back to the fullest board available.
const MIN_BOARD_DEALS = 5;
function bestBoardIdx(list){
  list = list || [];
  let bi = -1, bp = Infinity;
  list.forEach((b, i) => {
    const deals = b.deals || [];
    if (deals.length < MIN_BOARD_DEALS) return;   // sparse — not eligible
    const p = Math.min(...deals.map(d => d.price));
    if (p < bp){ bp = p; bi = i; }
  });
  if (bi !== -1) return bi;
  // No board qualifies (bad scan day) — land on the board with the MOST deals
  let mi = 0, mc = -1;
  list.forEach((b, i) => {
    const c = (b.deals || []).length;
    if (c > mc){ mc = c; mi = i; }
  });
  return mi;
}

function applyBestBoardDefaults(){
  // Called on data load and airport switch — picks the cheapest week/weekend
  const saveBoard = currentBoard;
  currentBoard = "weekend"; selectedWeekendIdx = bestBoardIdx(currentBoardList());
  currentBoard = "week";    selectedWeekIdx    = bestBoardIdx(currentBoardList());
  currentBoard = saveBoard;
}

function populateBoardPicker() {
  const picker = document.getElementById("weekendPicker");
  const row = document.getElementById("weekendPickerRow");
  const label = document.getElementById("pickerLabel");
  const list = currentBoardList();
  // Hide the picker entirely if there's only one (or zero) option
  if (list.length <= 1) { row.style.display = "none"; return; }
  row.style.display = "block";
  if (label) label.textContent = currentBoard === "weekend" ? "Choose your weekend:" : "Choose your week:";
  const activeIdx = currentBoard === "weekend" ? selectedWeekendIdx : selectedWeekIdx;
  const trav = cachedDeals.travellers || 4;
  picker.innerHTML = "";
  list.forEach((b, i) => {
    const btn = document.createElement("button");
    btn.className = "weekend-btn" + (i === activeIdx ? " active" : "");
    btn.onclick = () => selectBoard(i);
    const cheapest = b.deals && b.deals.length
      ? Math.round([...b.deals].sort((a,c)=>a.price-c.price)[0].price / trav) : null;
    const fallback = currentBoard === "weekend" ? `Weekend ${i+1}` : `Week ${i+1}`;
    const isBest = i === bestBoardIdx(list);
    btn.innerHTML = `<span class="wb-label">${b.label || fallback}${isBest ? " ⭐" : ""}</span>` +
      (cheapest != null ? `<span class="wb-price">from €${cheapest}pp${isBest ? " · best" : ""}</span>` : "");
    picker.appendChild(btn);
  });
}
// Back-compat alias (called from loadDeals)
function populateWeekendPicker(){ populateBoardPicker(); }

// ── Budget filter ────────────────────────────────────────────────────────────
document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    budgetMax = parseInt(btn.dataset.max) || 0;
    renderDeals();
  });
});

// ── Load deals ───────────────────────────────────────────────────────────────

// ── Analytics (GA4, consent-gated — GDPR) ───────────────────────────────────
const GA_ID = "G-ZL57HH33JG";

function loadGA(){
  if (location.hostname !== "holidaychasers.ie") return;
  if (window.gtag) return;
  const s = document.createElement("script");
  s.async = true;
  s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  window.gtag = function(){ dataLayer.push(arguments); };
  gtag("js", new Date());
  gtag("config", GA_ID, { anonymize_ip: true });
}

function hcConsent(accepted){
  try{ localStorage.setItem("hc_consent", accepted ? "yes" : "no"); }catch(e){}
  document.getElementById("consentBar").classList.remove("show");
  if (accepted) loadGA();
}

(function initConsent(){
  let c = null;
  try{ c = localStorage.getItem("hc_consent"); }catch(e){}
  if (c === "yes") loadGA();
  else if (c === null){
    window.addEventListener("load", () =>
      document.getElementById("consentBar").classList.add("show"));
  }
})();

function track(name, params){
  if (window.gtag) gtag("event", name, params || {});
}

// Affiliate & booking click events — delegated, covers every board and page
document.addEventListener("click", (e) => {
  const a = e.target.closest("a");
  if (!a) return;
  let kind = null;
  if (a.classList.contains("deal-book")) kind = "flight_click";
  else if (a.classList.contains("stay-btn")) kind = "stay_click";
  else if (a.classList.contains("tc-row")) kind = "trip_calc_click";
  else if (a.classList.contains("rest-row")) kind = "restaurant_click";
  if (!kind) return;
  // Work out which destination the click belongs to
  let dest = "";
  const card = a.closest(".deal-card");
  if (card){
    const n = card.querySelector(".pc-name");
    dest = n ? n.textContent.trim() : "";
  } else {
    const t = document.querySelector(".dt-city-title");
    dest = t ? t.textContent.trim() : "";
  }
  track(kind, { destination: dest, label: (a.textContent || "").trim().slice(0, 40) });
}, { passive: true });

async function loadDeals() {
  // Load the static GitHub file first — always works, instant, no backend needed
  try {
    const r = await fetch(DEALS_JSON);
    if (r.ok) {
      cachedDeals = await r.json();
      // Boards promise DIRECT flights — drop any connection fares the scanner
      // may have stored (legacy data; the scanner itself is direct-only now).
      for (const ap of Object.values(cachedDeals.airports || {})) {
        for (const list of [ap.weekend_boards, ap.week_boards]) {
          (list || []).forEach(b => { b.deals = (b.deals || []).filter(x => x.stops === 0); });
        }
      }
      applyBestBoardDefaults();     // default to the best-priced week/weekend
      populateWeekendPicker();
      renderDeals();
      populateTimelineDest();       // fill the trip-planner destination list
      openDeepLink();               // /?dest=EDI from SEO pages lands on the guide
      const tabQ = new URLSearchParams(location.search).get("tab");
      if (tabQ && document.getElementById("tab-" + tabQ)) activateTab(tabQ);
      return;
    } else {
      document.getElementById("dealsLoading").innerHTML = "No deals found yet. Check back soon.";
    }
  } catch(e) {
    document.getElementById("dealsLoading").innerHTML = "Could not load deals: " + e.message;
  }
}

// ── Favourites / watchlist ───────────────────────────────────────────────────
// Saved destinations persist in the browser (localStorage). Pairs with the
// email signup: people save cities, then subscribe to hear when they drop.
function getFavs(){
  try { return JSON.parse(localStorage.getItem("hc_favs") || "{}"); }
  catch(e){ return {}; }
}
function setFavs(f){
  try { localStorage.setItem("hc_favs", JSON.stringify(f)); } catch(e){}
}
function toggleFav(code, city){
  const f = getFavs();
  if (f[code]) delete f[code]; else f[code] = city;
  setFavs(f);
  refreshFavUI();
}
function refreshFavUI(){
  const f = getFavs();
  document.querySelectorAll(".deal-fav").forEach(btn => {
    const code = btn.getAttribute("data-fav");
    const on = !!f[code];
    btn.textContent = on ? "♥" : "♡";
    btn.classList.toggle("on", on);
  });
  const chip = document.getElementById("favChip");
  if (chip){
    const n = Object.keys(f).length;
    if (n === 0){ chip.style.display = "none"; }
    else {
      chip.style.display = "inline-flex";
      chip.querySelector(".fav-count").textContent = n;
    }
  }
}

function renderDeals() {
  const grid = document.getElementById("dealCards");
  const loading = document.getElementById("dealsLoading");
  const empty = document.getElementById("dealsEmpty");
  const updated = document.getElementById("dealsUpdated");
  loading.style.display = "none";

  if (!cachedDeals) {
    empty.style.display = "block"; empty.textContent = "No deals loaded.";
    grid.innerHTML = ""; return;
  }

  // Resolve which board to show
  const list = currentBoardList();
  const idx = currentBoard === "weekend" ? selectedWeekendIdx : selectedWeekIdx;
  let board = selectedAirport === "BEST"
    ? getBestOfBothBoard(idx)
    : (list[idx] || list[0] || null);

  if (!board || !board.deals) {
    empty.style.display = "block"; empty.textContent = "No deals available for this trip type.";
    grid.innerHTML = ""; return;
  }

  // Build a lookup of the alt airport's prices for the same board dates
  // (used for the comparison mini-card below each deal)
  const altAp = getAltAirportData();
  const altLookup = {};  // dest_code -> {price, airportCode, airportName}
  if (altAp?.data) {
    const altList = currentBoard === "weekend"
      ? (altAp.data.weekend_boards || [])
      : (altAp.data.week_boards || []);
    const altBoard = altList[idx] || altList[0];
    for (const d of altBoard?.deals || []) {
      altLookup[d.code] = {
        deal: d,
        price: d.price,
        airportCode: altAp.code,
        airportName: altAp.code === "ORK" ? "Cork" : "Dublin"
      };
    }
  }

  const cacheTravellers = cachedDeals.travellers || 4;
  const groupSize = selAdults + selChildren;
  let deals = [...board.deals].sort((a,b) => a.price - b.price);
  if (budgetMax > 0) deals = deals.filter(d => (d.price / cacheTravellers) <= budgetMax);

  if (cachedDeals.updated_utc) {
    try {
      const d = new Date(cachedDeals.updated_utc);
      const today = new Date();
      const isToday = d.toDateString() === today.toDateString();
      const yest = new Date(today); yest.setDate(yest.getDate()-1);
      const isYest = d.toDateString() === yest.toDateString();
      if (isToday) { updated.textContent = "✓ Prices checked today"; updated.classList.add("fresh"); }
      else if (isYest) { updated.textContent = "✓ Prices checked yesterday"; updated.classList.add("fresh"); }
      else { updated.textContent = "Updated " + d.toLocaleDateString("en-IE",{day:"numeric",month:"short",year:"numeric"}); updated.classList.remove("fresh"); }
    } catch(e) { updated.textContent = ""; }

  // Default each view to its best-priced board
  applyBestBoardDefaults();

  // Airport pill deal counts + "who wins today" summary
  updateAirportCounts();
  }

  const dep = board.depart_date, ret = board.return_date;
  const perPerson = d => Math.round(d.price / cacheTravellers);
  const groupTotal = d => perPerson(d) * groupSize;

  // ── Honest "great value" flag ──
  // We can't claim "cheaper than last week" (the scanner doesn't store history),
  // so instead we flag fares that are notably below the median of THIS board —
  // a true, defensible "stands out as good value right now" signal.
  const pps = deals.map(perPerson).sort((a,b)=>a-b);
  const median = pps.length ? pps[Math.floor(pps.length/2)] : 0;
  const valueThreshold = median * 0.7;  // 30%+ below median = great value
  function valueBadge(d){
    // Priority 0: midweek saver — the scanner found Tue→Tue beating the weekend
    if (d.midweek_saver && d.weekend_price) {
      const save = Math.round((d.weekend_price - d.price) / (cachedDeals?.travellers || 1));
      return `<div class="deal-badge cheaper">💡 Midweek saver · €${save} less</div>`;
    }
    // Priority 1: real price-history flags from the scanner (genuinely true)
    if (d.is_cheaper) return '<div class="deal-badge cheaper">↓ Cheaper than usual</div>';
    if (d.is_new) return '<div class="deal-badge newbadge">✦ New route</div>';
    // Priority 2: fallback heuristic for when no history exists yet — flags fares
    // notably below this board's median ("stands out right now")
    const pp = perPerson(d);
    if (median && pp <= valueThreshold) return '<div class="deal-badge value">★ Great value</div>';
    return '';
  }

  // Format dates nicely: "Fri 3 Jul → Sun 5 Jul"
  function fmtD(ds) {
    return new Date(ds + "T12:00:00").toLocaleDateString("en-IE", {weekday:"short", day:"numeric", month:"short"});
  }
  const depFmt = fmtD(dep), retFmt = fmtD(ret);

  // Hero stats
  if (deals.length) {
    document.getElementById("heroStats").innerHTML = `
      <div class="hero-stat"><div class="val">€${perPerson(deals[0])}</div><div class="lbl">Cheapest · per person</div></div>
      <div class="hero-stat"><div class="val">${deals.length}</div><div class="lbl">Destinations</div></div>
      <div class="hero-stat"><div class="val">${board.nights}n</div><div class="lbl">${currentBoard==="weekend"?"Weekend":"Week"} trip</div></div>
      <div class="hero-stat hero-stat-dates"><div class="val" style="font-size:16px">${depFmt} → ${retFmt}</div><div class="lbl">Travel dates</div></div>`;
  }

  if (!deals.length) {
    empty.style.display = "block";
    empty.textContent = budgetMax ? `No deals under €${budgetMax} per person. Try a higher budget.` : "No deals available.";
    grid.innerHTML = ""; return;
  }
  empty.style.display = "none";

  grid.innerHTML = deals.map((d, i) => {
    const originCode = d.origin_airport || selectedAirport;
    const showOrigin = selectedAirport === "BEST";
    const flightOrigin = (showOrigin && d.origin_airport) ? d.origin_airport : (selectedAirport === "BEST" ? "ORK" : selectedAirport);
    const banner = `<div class="deal-photo noimg" id="photo-${d.code}-${i}">
           <span class="deal-route-on-photo">${flightOrigin} → ${d.code}</span>
           ${showOrigin && d.origin_airport ? `<span class="origin-badge">${d.origin_airport}</span>` : ''}
           <span class="photo-city"><span class="pc-name">${d.city}</span><span class="pc-country" style="display:block">${d.country}</span></span>
         </div>`;

    // Comparison mini-card: the other airport's price for this same destination —
    // a real, tappable option, not just a comparison note.
    const alt = altLookup[d.code];
    let altCard = '';
    if (alt && selectedAirport !== "BEST") {
      const altPP = Math.round(alt.price / cacheTravellers);
      const thisPP = perPerson(d);
      const diff = altPP - thisPP;
      const diffLabel = diff < 0
        ? `<span class="alt-cheaper">€${Math.abs(diff)} cheaper</span>`
        : diff === 0 ? `<span class="alt-pricier">same price</span>`
        : `<span class="alt-pricier">€${diff} more</span>`;
      const altDealJson = JSON.stringify({...alt.deal, origin_airport: alt.airportCode}).replace(/'/g, "&#39;");
      altCard = `
      <div class="alt-card" role="button" tabindex="0" aria-label="View this trip from ${alt.airportName} instead"
           onclick='event.stopPropagation(); openDetail(${altDealJson}, "${alt.deal.depart_date || dep}", "${alt.deal.return_date || ret}", ${groupSize}, ${cacheTravellers})'>
        <span class="alt-badge">${alt.airportCode}</span>
        <span class="alt-info">Or fly from ${alt.airportName} instead</span>
        <span class="alt-price">€${altPP}/pp</span>
        ${diffLabel}
        <span class="alt-arrow">→</span>
      </div>`;
    }

    return `
    <div class="deal-card${i === 0 ? ' cheapest' : ''}">
      <button class="deal-fav" onclick='event.stopPropagation();toggleFav("${d.code}","${d.city.replace(/"/g,'')}")' aria-label="Save ${d.city}" data-fav="${d.code}">♡</button>
      <button type="button" class="deal-clickable" aria-label="View full details for ${d.city}" onclick='openDetail(${JSON.stringify(d).replace(/'/g,"&#39;")}, "${d.depart_date || dep}", "${d.return_date || ret}", ${groupSize}, ${cacheTravellers})'>
        ${banner}
        <div class="deal-card-top">
          ${i === 0 ? '<div class="deal-badge">Best fare</div>' : valueBadge(d)}
          <div class="deal-city">${d.city}</div>
          <div class="deal-country">${d.country}</div>
        </div>
        <div class="deal-perf"></div>
        ${EDITOR_NOTES[d.code] ? `<div class="ed-note">"${EDITOR_NOTES[d.code]}"</div>` : '<div class="ed-note empty"></div>'}
        <div class="deal-card-bottom">
          <div class="deal-price-block">
            <div class="deal-dates">${fmtD(d.depart_date || dep)} — ${fmtD(d.return_date || ret)}${d.nights && d.nights !== board.nights ? ` · ${d.nights}n` : ""}</div>
            <div class="deal-price"><sup>€</sup>${perPerson(d)}<small>per person</small></div>
          </div>
          ${groupSize > 1 ? `<div class="deal-perperson">
            <div class="pp-amount">€${groupTotal(d)}</div>
            <div class="pp-label">${travellerLabel()}</div>
          </div>` : ''}
        </div>
        <div class="deal-meta">
          <span class="${d.stops === 0 ? 'tag-direct' : ''}">${d.stops === 0 ? '✦ Direct' : d.stops + ' stop' + (d.stops>1?'s':'')}</span>
          <span>${d.total_time || '—'}</span>
          <span>${d.airlines || '—'}</span>
        </div>
        <div class="deal-weather" id="weather-${d.code}-${i}"><span class="wx-loading">Checking weather…</span></div>
        <div class="deal-viewmore">View full details &amp; guide →</div>
      </button>
      <div class="deal-actions">
        <a class="deal-book primary" href="${flightUrl(d.airlines, flightOrigin, d.code, d.depart_date || dep, d.return_date || ret, selAdults, selChildren)}" target="_blank" rel="noopener noreferrer">${flightBtnLabel(d.airlines)}</a>
        <a class="deal-book secondary" href="${carUrl(d.city, d.depart_date || dep, d.return_date || ret)}" target="_blank" rel="noopener">🚗 ${BRAND.discovercars}</a>
      </div>
      <div class="deal-stays">
        <span class="stay-label">Where to stay</span>
        <a class="stay-btn" href="${hotelUrl(d.city, d.depart_date || dep, d.return_date || ret)}" target="_blank" rel="noopener">${BRAND.booking}</a>
        <a class="stay-btn" href="${airbnbUrl(d.city, d.depart_date || dep, d.return_date || ret)}" target="_blank" rel="noopener">${BRAND.airbnb}</a>
      </div>
      <div class="stay-nudge">🏨 ${d.nights || board.nights} night${(d.nights || board.nights)>1?'s':''} in ${d.city} from <b>~€${cityCosts(d.code).airbnb * (d.nights || board.nights)}</b> — tap to compare</div>
      ${altCard}
    </div>`;
  }).join("");

  refreshFavUI();  // sync star states with saved favourites

  // Load photo + weather for each card asynchronously (doesn't block render)
  deals.forEach((d, i) => {
    // City photo from Wikipedia
    fetchCityPhoto(d.code, d.city).then(url => {
      if (!url) return;
      const ph = document.getElementById(`photo-${d.code}-${i}`);
      if (!ph) return;
      const img = new Image();
      img.alt = d.city;
      img.onload = () => {
        ph.classList.remove("noimg");
        ph.insertBefore(img, ph.firstChild);
        requestAnimationFrame(() => ph.classList.add("loaded"));
      };
      img.src = url;
    });
    // Weather
    getWeather(d.code, dep).then(w => {
      const el = document.getElementById(`weather-${d.code}-${i}`);
      if (!el) return;
      if (!w) { el.innerHTML = ""; return; }
      const [icon, label] = weatherIcon(w.code);
      el.innerHTML = `
        <span class="wx-icon">${icon}</span>
        <span class="wx-temp">${w.tmax}° <span class="wx-min">/ ${w.tmin}°</span></span>
        <span class="wx-label">${label}${w.rain != null && w.rain >= 30 ? ' · ' + w.rain + '% rain' : ''}</span>
        <span class="wx-tag">${w.typical ? 'typical for these dates' : 'forecast'}</span>`;
    });
  });
}

// ── In-guide trip planner: dates → live flights → leg booking ────────────────

// Return can only be after departure: keep the min in sync and bump if needed.
function syncRetMin(){
  const depEl = document.getElementById("dtDep");
  const retEl = document.getElementById("dtRet");
  if (!depEl || !retEl || !depEl.value) return;
  const minRet = new Date(depEl.value + "T12:00:00");
  minRet.setDate(minRet.getDate() + 1);
  const minIso = minRet.toISOString().slice(0, 10);
  retEl.min = minIso;
  if (retEl.value && retEl.value < minIso) retEl.value = minIso;
}

// Debounced auto-search: fires shortly after either date changes, no button
// press needed. A short delay just absorbs rapid back-to-back edits so we
// don't fire two overlapping searches — the guide's generation counter
// (window._gGen) already discards any in-flight request a newer one supersedes.
let _dateChangeTimer = null;
function scheduleAutoSearch(){
  clearTimeout(_dateChangeTimer);
  _dateChangeTimer = setTimeout(applyGuideDates, 250);
}

// Outbound date changed: auto-fill the return date to keep the same trip
// length (nights) as the trip currently on screen, rather than leaving the
// visitor to pick both dates by hand. Then search immediately.
function onDepChange(){
  const depEl = document.getElementById("dtDep");
  const retEl = document.getElementById("dtRet");
  const g = window._guide;
  if (!depEl || !retEl || !depEl.value) return;
  let nights = 7;
  if (g && g.dep && g.ret) {
    const n = Math.round((new Date(g.ret + "T12:00:00") - new Date(g.dep + "T12:00:00")) / 86400000);
    if (n > 0) nights = n;
  }
  const newDep = new Date(depEl.value + "T12:00:00");
  const newRet = new Date(newDep);
  newRet.setDate(newRet.getDate() + nights);
  retEl.value = newRet.toISOString().slice(0, 10);
  syncRetMin();
  scheduleAutoSearch();
}

function applyGuideDates(){
  const g = window._guide;
  if (!g) return;
  const dep = document.getElementById("dtDep")?.value;
  const ret = document.getElementById("dtRet")?.value;
  if (!dep || !ret || ret <= dep) { alert("Pick an outbound date and a later return date."); return; }
  const changed = dep !== g.dep || ret !== g.ret;
  const d = {...g.d};
  if (changed) { d.price = null; d.stops = null; d.total_time = ""; }  // old fare no longer applies
  window._gAutoSearch = true;   // the button press IS the search request
  const freshGroup = (typeof selAdults === "number" ? selAdults : 1) + (typeof selChildren === "number" ? selChildren : 0);
  openDetail(d, dep, ret, freshGroup || g.groupSize, changed ? 1 : g.cacheTravellers, g.planner !== false);
}

// Timeline of all scanned boards for this destination, inside the guide.
function guideTimeline(d){
  const box = document.getElementById("dtTimeline");
  const section = document.getElementById("dtTimelineSection");
  if (!box || !section || !cachedDeals) return;
  const trav = _cacheTrav();
  const found = [];
  for (const apCode of ["ORK","DUB"]) {
    for (const b of _allBoards(apCode)) {
      const deal = _findDeal(b, d.code);
      if (deal) found.push({ apCode, b, deal, pp: Math.round(deal.price / trav) });
    }
  }
  if (!found.length) { section.style.display = "none"; return; }
  found.sort((a,c) => (a.b.depart_date||"").localeCompare(c.b.depart_date||""));
  const minPP = Math.min(...found.map(r => r.pp));
  const fmtD = iso => new Date(iso+"T00:00:00").toLocaleDateString("en-IE",{day:"numeric",month:"short"});
  // Collapsed view: the 6 cheapest fares (kept in date order) + the row being
  // viewed. One tap expands to every scanned date.
  const SHOW = 6;
  const cheapIdx = new Set(
    found.map((r,i) => [r.pp, i]).sort((a,b) => a[0]-b[0]).slice(0, SHOW).map(([,i]) => i)
  );
  section.style.display = "";
  box.innerHTML = `
    <table class="results-table">
      <thead><tr><th>From</th><th>Trip</th><th>Dates</th><th>Per person</th><th>Airline</th></tr></thead>
      <tbody>${found.map((r,i) => {
        const g = window._guide || {};
        const viewing = (r.deal.depart_date || r.b.depart_date) === g.dep
                     && r.apCode === (g.d && g.d.origin_airport);
        const hidden = !cheapIdx.has(i) && !viewing && found.length > SHOW + 2;
        return `
        <tr class="${hidden ? 'tl-hidden' : ''}" style="cursor:pointer${viewing ? ';background:var(--gold-soft)' : ''}" title="See the full trip on these dates"
            onclick="guidePickBoard(${i})">
          <td>${r.apCode === "ORK" ? "Cork" : "Dublin"}</td>
          <td>${r.b._type === "weekend" ? "🏖️ Weekend" : "✈️ Week"}</td>
          <td>${fmtD(r.deal.depart_date || r.b.depart_date)} → ${fmtD(r.deal.return_date || r.b.return_date)}</td>
          <td class="price-cell">€${r.pp}${r.pp === minPP ? " ⭐" : ""}</td>
          <td>${r.deal.airlines || "—"}${viewing ? ' <span style="font-size:10px;color:var(--muted)">· viewing</span>' : ''}</td>
        </tr>`;}).join("")}</tbody>
    </table>` +
    (found.length > SHOW + 2
      ? `<button class="rest-more" onclick="this.parentElement.querySelectorAll('.tl-hidden').forEach(e=>e.classList.remove('tl-hidden'));this.remove()">Show all ${found.length} scanned dates ↓</button>`
      : "");
  window._gTimeline = found;
}

function guidePickBoard(i){
  const r = (window._gTimeline || [])[i];
  const g = window._guide;
  if (!r || !g) return;
  // Keep the visitor in the world they came from: board guides stay board-style,
  // planner guides stay planner-style.
  openDetail({...r.deal, origin_airport: r.apCode},
             r.deal.depart_date || r.b.depart_date, r.deal.return_date || r.b.return_date,
             g.groupSize, _cacheTrav(), g.planner === true);
}

// Live flights inside the guide.
function guideLiveInit(d, dep, ret, hasPrice){
  const box = document.getElementById("dtLive");
  if (!box) return;
  const origin = d.origin_airport || "ORK";
  if (!backendOnline) {
    const avia = aviasalesUrl(origin, d.code, dep, ret);
    box.innerHTML = `<a class="deal-book primary" href="${avia}" target="_blank" rel="noopener noreferrer sponsored"
        onclick="track('flight_click',{source:'guide_aviasales',dest:'${d.code}'})">🔎 Search live prices on Aviasales →</a>`;
    return;
  }
  if (window._gAutoSearch) {
    window._gAutoSearch = false;   // consumed — set by "Update trip"
    guideGrids();
    return;
  }
  // Never search without an explicit action — the visitor picks dates first.
  box.innerHTML = `<div style="font-size:14px;color:var(--muted);margin-bottom:10px">👆 ${hasPrice ? "Happy with the scanned fare above, or want to compare nearby days?" : "Set your dates above, then search live prices."}</div>
    <button class="deal-book primary" style="border:none;cursor:pointer"
        onclick="guideGrids()">🔎 Search flights for these dates</button>
    <div style="font-size:12px;color:var(--muted);margin-top:8px">Compares ±3 days around your dates, per person.</div>`;
}

async function guideGrids(){
  const g = window._guide;
  const box = document.getElementById("dtLive");
  if (!g || !box) return;
  const origin = g.d.origin_airport || "ORK";
  const code = (g.d.code || "").split(",")[0];
  const dates = (centre) => {
    const out = [];
    for (let o = -3; o <= 3; o++) {
      const dt = new Date(centre + "T12:00:00"); dt.setDate(dt.getDate() + o);
      const iso = dt.toISOString().slice(0,10);
      if (iso > new Date().toISOString().slice(0,10)) out.push(iso);
    }
    return out;
  };
  const outDates = dates(g.dep), retDates = dates(g.ret).filter(x => x > g.dep);
  box.innerHTML = `<div id="gProg" style="font-size:13px;color:var(--muted);margin-bottom:10px">⏳ Checking real prices for every date — takes about 20 seconds… <span id="gProgN">0</span>/${outDates.length + retDates.length} done</div>
    <div style="display:flex;gap:12px;align-items:flex-start">
      <div style="flex:1;min-width:0">
        <div style="font-weight:700;font-size:13px;margin:6px 0">🛫 Out — ${origin === "ORK" ? "Cork" : "Dublin"} → ${g.d.city.split(" ")[0]}</div>
        <div id="gOutGrid" style="display:flex;flex-direction:column;gap:6px"></div>
      </div>
      <div style="flex:1;min-width:0">
        <div style="font-weight:700;font-size:13px;margin:6px 0">🛬 Return — ${g.d.city.split(" ")[0]} → ${origin === "ORK" ? "Cork" : "Dublin"}</div>
        <div id="gRetGrid" style="display:flex;flex-direction:column;gap:6px"></div>
      </div>
    </div>
    <div id="gPick" style="margin-top:14px"></div>`;
  window._gPrices = { out: {}, ret: {} };
  window._gDone = false;
  window._gSel = { out: null, ret: null };            // stale picks reference old prices
  const gen = window._gGen = (window._gGen || 0) + 1;  // newer search invalidates this one
  let done = 0;
  const bump = () => { const el = document.getElementById("gProgN"); if (el) el.textContent = ++done; };
  const fetchOne = async (from, to, date, bucket) => {
    try {
      const r = await fetch(BACKEND_URL + "/api/search/direct", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ dest_code: to, outbound_date: date, return_date: null,
                               // Always explicit — never rely on the Worker's default
                               // origin (which is hardcoded to Cork and silently broke
                               // every Dublin-origin outbound search).
                               departure_override: from }),
        signal: AbortSignal.timeout(60000)
      });
      if (gen !== window._gGen) return;   // a newer search took over — discard
      if (r.ok) {
        const f = await r.json();
        // Direct fares ONLY — each leg must be bookable on the shown airline.
        // Connections belong to "Anywhere in Europe" via Aviasales, not here.
        if (f && f.price && f.stops === 0) window._gPrices[bucket][date] = f;
      }
    } catch(e) {}
    if (gen !== window._gGen) return;
    bump();
    guideRenderGrid(bucket);
  };
  // outbound: origin → dest; return: dest → origin (departure_override).
  // 4 requests in parallel — the Worker + cache handle it easily, and the
  // full grid lands in ~15-20s instead of a minute.
  const jobs = [
    ...outDates.map(dt => ({ from: origin, to: code, dt, bucket: "out" })),
    ...retDates.map(dt => ({ from: code, to: origin, dt, bucket: "ret" })),
  ];
  const workers = Array.from({ length: 4 }, async () => {
    while (jobs.length) {
      if (gen !== window._gGen) return;
      const j = jobs.shift();
      await fetchOne(j.from, j.to, j.dt, j.bucket);
    }
  });
  await Promise.all(workers);
  if (gen !== window._gGen) return;
  window._gDone = true;
  guideRenderGrid("out"); guideRenderGrid("ret");

  // Pre-pick the cheapest sensible combo so the booking bar is ready to go —
  // the visitor can tap any other date to change either leg.
  const outEntries = Object.entries(window._gPrices.out);
  if (outEntries.length && !window._gSel.out) {
    const bestOut = outEntries.sort((a,b) => a[1].price - b[1].price)[0][0];
    const retEntries = Object.entries(window._gPrices.ret).filter(([d]) => d > bestOut);
    if (retEntries.length) {
      const bestRet = retEntries.sort((a,b) => a[1].price - b[1].price)[0][0];
      guideSelect("out", bestOut);
      guideSelect("ret", bestRet);
      const pk = document.getElementById("gPick");
      if (pk) pk.insertAdjacentHTML("afterbegin",
        `<div style="font-size:12px;color:var(--muted);margin-bottom:8px">✨ We pre-picked the cheapest combination — tap any other date above to change it.</div>`);
    }
  }
  const prog = document.getElementById("gProg");
  if (prog) prog.textContent = "Prices are per person · tap a departure and a return to build your booking.";
  if (!Object.keys(window._gPrices.out).length && !Object.keys(window._gPrices.ret).length) {
    box.innerHTML = `<p style="font-size:14px;color:var(--muted)">No live fares found around these dates.</p>
      <a class="deal-book primary" href="${aviasalesUrl(origin, code, g.dep, g.ret)}" target="_blank" rel="noopener noreferrer sponsored">🔎 Try Aviasales for these dates →</a>`;
  }
}

function guideRenderGrid(bucket){
  // Empty column → explain, don't just show blank space
  {
    const el = document.getElementById(bucket === "out" ? "gOutGrid" : "gRetGrid");
    const prices = window._gPrices && window._gPrices[bucket];
    if (el && prices && Object.keys(prices).length === 0 && window._gDone) {
      el.innerHTML = `<div style="font-size:12px;color:var(--muted);border:1px dashed var(--line);border-radius:10px;padding:12px">No direct-flight prices available for these dates yet — airlines load new-season schedules gradually. Try the Aviasales comparison below, or check back in a little while.</div>`;
      return;
    }
  }
  const grid = document.getElementById(bucket === "out" ? "gOutGrid" : "gRetGrid");
  if (!grid) return;
  const prices = window._gPrices[bucket];
  const entries = Object.entries(prices).sort((a,b) => a[0].localeCompare(b[0]));
  if (!entries.length) { grid.innerHTML = ""; return; }
  const minP = Math.min(...entries.map(([,f]) => f.price));
  const sel = window._gSel[bucket];
  const fmtD = iso => new Date(iso+"T00:00:00").toLocaleDateString("en-IE",{weekday:"short",day:"numeric",month:"short"});
  grid.innerHTML = entries.map(([date,f]) => {
    const isSel = sel && sel.date === date;
    const isMin = f.price === minP;
    return `
    <button type="button" onclick="guideSelect('${bucket}','${date}')" aria-pressed="${isSel ? 'true' : 'false'}" aria-label="${fmtD(date)}, €${f.price}${isMin ? ', cheapest' : ''}" style="cursor:pointer;border-radius:10px;padding:8px 10px;transition:.15s;position:relative;display:flex;align-items:center;justify-content:space-between;gap:6px;width:100%;font:inherit;color:inherit;text-align:left;appearance:none;-webkit-appearance:none;margin:0;
        border:${isSel ? '2px solid var(--ink)' : '1px solid var(--line)'};
        background:${isSel ? 'var(--gold-soft)' : 'var(--paper, #fff)'}">
      <div style="min-width:0">
        <div style="font-size:11px;font-weight:600">${isSel ? '✓ ' : ''}${fmtD(date)}</div>
        <div style="font-size:9px;color:${isMin ? '#1B7A53' : 'var(--muted)'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${isMin ? '💚 cheapest · ' : ''}${(f.airlines||"—").split(",")[0]}</div>
      </div>
      <div style="font-weight:800;font-size:15px;flex:none">€${f.price}</div>
    </button>`;}).join("");
}

function guideSelect(bucket, date){
  window._gSel[bucket] = { date, ...window._gPrices[bucket][date] };
  guideRenderGrid("out"); guideRenderGrid("ret");
  const g = window._guide, s = window._gSel;
  const pick = document.getElementById("gPick");
  if (!pick) return;
  if (!(s.out && s.ret)) {
    pick.innerHTML = `<div style="font-size:13px;color:var(--muted)">Selected ${s.out ? "departure ✓" : ""}${s.ret ? "return ✓" : ""} — pick the other leg to see your total.</div>`;
    return;
  }
  const origin = g.d.origin_airport || "ORK";
  const code = (g.d.code || "").split(",")[0];
  const pp = s.out.price + s.ret.price;
  const groupTot = pp * g.groupSize;
  const outUrl = legUrl(s.out.airlines, origin, code, s.out.date, selAdults, selChildren);
  const retUrl = legUrl(s.ret.airlines, code, origin, s.ret.date, selAdults, selChildren);
  const outAir = (s.out.airlines||"").split(",")[0].trim();
  const retAir = (s.ret.airlines||"").split(",")[0].trim();
  const sameAir = outAir && outAir.toLowerCase() === retAir.toLowerCase()
                  && ["ryanair","aer lingus"].includes(outAir.toLowerCase());
  const buttons = sameAir
    ? `<a class="deal-book primary" href="${flightUrl(outAir, origin, code, s.out.date, s.ret.date, selAdults, selChildren)}" target="_blank" rel="noopener noreferrer"
         onclick="track('flight_click',{source:'guide_roundtrip',dest:'${code}'})">✈ Book both flights on ${outAir} · €${pp} →</a>`
    : `<a class="deal-book primary" href="${outUrl}" target="_blank" rel="noopener noreferrer"
         onclick="track('flight_click',{source:'guide_leg_out',dest:'${code}'})">Book departure · €${s.out.price} →</a>
       <a class="deal-book secondary" href="${retUrl}" target="_blank" rel="noopener noreferrer"
         onclick="track('flight_click',{source:'guide_leg_ret',dest:'${code}'})">Book return · €${s.ret.price} →</a>`;
  pick.innerHTML = `
    <div style="border:1px solid var(--line);border-radius:14px;padding:16px">
      <div style="font-weight:800;font-size:18px">Your trip: €${pp} <span style="font-weight:400;font-size:13px;color:var(--muted)">per person · €${groupTot} for ${g.groupSize}</span></div>
      <div style="font-size:13px;color:var(--muted);margin:4px 0 12px">${s.out.date} (${outAir}) → ${s.ret.date} (${retAir})</div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">${buttons}</div>
      <div style="font-size:11px;color:var(--muted);margin-top:8px">${sameAir
        ? `One booking, both dates pre-filled on ${outAir}.`
        : "Each leg books separately — that's how these prices are possible."}</div>
    </div>`;
  // Sync the price strip and the trip calculator with the live selection
  const pp2 = document.getElementById("dtPP"); if (pp2) pp2.textContent = "€" + pp;
  const gt = document.getElementById("dtGroupTot"); if (gt) gt.textContent = "€" + groupTot;
  const val = document.getElementById("tcFlightVal"); if (val) val.textContent = "€" + groupTot;
  const lbl = document.getElementById("tcFlightLbl"); if (lbl) lbl.textContent = "Flights · live selection";
  const row = document.getElementById("tcFlightRow"); if (row) row.href = outUrl;
}

// ── Cache-powered tabs (Phase 1: no backend needed) ──────────────────────────
// Everything below reads deals_cache.json (already loaded as cachedDeals) and
// links out via airline deeplinks + Aviasales affiliate search.

function _cacheTrav(){ return (cachedDeals && cachedDeals.travellers) || 1; }

// All scanned boards for one airport, tagged with their trip type.
function _allBoards(apCode){
  const ap = cachedDeals?.airports?.[apCode];
  if (!ap) return [];
  const tag = (list, type) => (list || []).map(b => ({...b, _type: type}));
  return [...tag(ap.weekend_boards, "weekend"), ...tag(ap.week_boards, "week")];
}

// Find a deal for a destination code (handles multi-codes like "CDG,ORY").
function _findDeal(board, codeStr){
  const codes = (codeStr || "").split(",").map(s => s.trim());
  return (board.deals || []).find(d => codes.includes(d.code)) || null;
}

// Cheapest cached per-person fare from EACH airport for a destination.
// Returns { ORK: {pp, deal, board} | null, DUB: {...} | null } — pure cache
// read, zero API cost. Used for the smart default airport and the guide's
// "cheaper from the other airport" banner.
function cheapestByAirport(code){
  const trav = _cacheTrav();
  const out = { ORK: null, DUB: null };
  for (const ap of ["ORK", "DUB"]) {
    for (const b of _allBoards(ap)) {
      const deal = _findDeal(b, code);
      if (!deal) continue;
      const pp = Math.round(deal.price / trav);
      if (!out[ap] || pp < out[ap].pp) out[ap] = { pp, deal, board: b };
    }
  }
  return out;
}

// Which airport is cheaper for this destination per the cache? Returns
// "ORK" | "DUB" | null (null when only one or neither is scanned).
function cheaperAirport(code){
  const c = cheapestByAirport(code);
  if (c.ORK && c.DUB) return c.ORK.pp <= c.DUB.pp ? "ORK" : "DUB";
  return c.ORK ? "ORK" : (c.DUB ? "DUB" : null);
}

function openPlanner(){
  const apSel = document.getElementById("tlAirport");
  const destSel = document.getElementById("tlDest");
  populateTimelineDest();
  const code = destSel.value;
  const entry = DIRECT.find(x => x.code === code) || {};
  const dep = new Date(Date.now() + 21*864e5).toISOString().slice(0,10);
  const ret = new Date(Date.now() + 28*864e5).toISOString().slice(0,10);
  openDetail({
    city: entry.city || code, country: entry.country || "",
    code, price: null, stops: null, total_time: "", airlines: "",
    origin_airport: apSel.value
  }, dep, ret, selAdults + selChildren, 1, true);
  track("view_destination", { source: "planner", dest: code });
}

const COUNTRY_FLAG = {
  Spain:"🇪🇸", Portugal:"🇵🇹", Italy:"🇮🇹", France:"🇫🇷", England:"🇬🇧",
  Scotland:"🏴󠁧󠁢󠁳󠁣󠁴󠁿", Germany:"🇩🇪", Netherlands:"🇳🇱", "Czech Republic":"🇨🇿",
  Croatia:"🇭🇷", Malta:"🇲🇹", Switzerland:"🇨🇭", Turkey:"🇹🇷", Greece:"🇬🇷",
  Hungary:"🇭🇺", Poland:"🇵🇱", Austria:"🇦🇹", Denmark:"🇩🇰",
};

function populateTimelineDest(){
  const sel = document.getElementById("tlDest");
  const ap = document.getElementById("tlAirport")?.value || "ORK";
  if (!sel) return;
  const keep = sel.value;
  sel.innerHTML = "";
  // Group by country (A→Z), cities A→Z inside — with flag headers.
  const served = DIRECT.filter(d => servedFrom(ap, d.code));
  const byCountry = {};
  served.forEach(d => { (byCountry[d.country] = byCountry[d.country] || []).push(d); });
  Object.keys(byCountry).sort().forEach(country => {
    const grp = document.createElement("optgroup");
    grp.label = `${COUNTRY_FLAG[country] || "🌍"} ${country}`;
    byCountry[country].sort((a,b) => a.city.localeCompare(b.city)).forEach(d => {
      const o = document.createElement("option");
      o.value = d.code; o.textContent = d.city;
      grp.appendChild(o);
    });
    sel.appendChild(grp);
  });
  // keep the previous pick if the new airport also serves it
  if (keep && [...sel.options].some(o => o.value === keep)) sel.value = keep;
}

function renderDirectTimeline(){
  const box = document.getElementById("tlResults");
  if (!box || !cachedDeals) return;
  populateTimelineDest();
  const apCode = document.getElementById("tlAirport").value;
  const destSel = document.getElementById("tlDest");
  const code = destSel.value;
  const cityName = destSel.selectedOptions[0]?.textContent?.split(",")[0] || code;
  const trav = _cacheTrav();

  const rows = [];
  for (const b of _allBoards(apCode)) {
    const d = _findDeal(b, code);
    if (d) rows.push({ b, d, pp: Math.round(d.price / trav) });
  }
  rows.sort((a, c) => (a.b.depart_date || "").localeCompare(c.b.depart_date || ""));

  const avia = aviasalesUrl(apCode, code,
    rows[0]?.b.depart_date || new Date(Date.now()+21*864e5).toISOString().slice(0,10),
    rows[0]?.b.return_date  || new Date(Date.now()+28*864e5).toISOString().slice(0,10));
  const aviaCta = `
    <div style="margin-top:18px;text-align:center">
      <a class="deal-book primary" href="${avia}" target="_blank" rel="noopener noreferrer sponsored"
         onclick="track('flight_click',{source:'timeline_aviasales',dest:'${code}'})"
         style="display:inline-flex;padding:12px 22px">🔎 Need different dates? Search live on Aviasales →</a>
      <div style="font-size:11px;color:var(--muted);margin-top:8px">Opens our partner Aviasales — comparing all airlines and dates.</div>
    </div>`;

  if (!rows.length) {
    box.innerHTML = `<p style="color:var(--muted);font-size:14px">No scanned fares for ${cityName} from ${apCode === "ORK" ? "Cork" : "Dublin"} right now — it may not be a direct route from this airport.</p>` + aviaCta;
    return;
  }

  const minPP = Math.min(...rows.map(r => r.pp));
  const fmtD = iso => new Date(iso + "T00:00:00").toLocaleDateString("en-IE", {day:"numeric", month:"short"});
  box.innerHTML = `
    <div style="font-weight:700;font-size:15px;margin:6px 0 4px">Every scanned date for ${cityName} — cheapest first-glance planner</div>
    <div style="font-size:12px;color:var(--muted);margin-bottom:12px">Real return fares per person, refreshed automatically every few days.</div>
    <table class="results-table">
      <thead><tr><th>Trip</th><th>Dates</th><th>Per person</th><th>Airline</th><th></th></tr></thead>
      <tbody>${rows.map(r => {
        const dd = {...r.d, origin_airport: apCode};
        const ddJson = JSON.stringify(dd).replace(/'/g, "&#39;");
        return `
        <tr class="${r.pp === minPP ? 'cheapest-row' : ''}" style="cursor:pointer" title="Open full trip guide"
            onclick='openDetail(${ddJson}, "${r.d.depart_date || r.b.depart_date}", "${r.d.return_date || r.b.return_date}", ${selAdults + selChildren}, ${_cacheTrav()}, true)'>
          <td>${r.b._type === "weekend" ? "🏖️ Weekend" : "✈️ Week"}</td>
          <td>${fmtD(r.d.depart_date || r.b.depart_date)} → ${fmtD(r.d.return_date || r.b.return_date)}${r.d.nights ? ` · ${r.d.nights}n` : ""}</td>
          <td class="price-cell">€${r.pp}${r.pp === minPP ? " ⭐" : ""}</td>
          <td>${r.d.airlines || "—"}</td>
          <td><a class="deal-book secondary" style="padding:6px 12px;font-size:12px"
                 href="${flightUrl(r.d.airlines || "", apCode, r.d.code, r.d.depart_date || r.b.depart_date, r.d.return_date || r.b.return_date, 1, 0)}"
                 target="_blank" rel="noopener noreferrer"
                 onclick="event.stopPropagation();track('flight_click',{source:'timeline',dest:'${code}'})">Book</a></td>
        </tr>`;}).join("")}</tbody>
    </table>
    <div style="font-size:12px;color:var(--muted);margin-top:8px">💡 Tap any row for the full trip guide — hotels, car hire, food and sights for those dates.</div>` + aviaCta;
}

// "Anywhere in Europe" without a backend: show any cached fares for the city,
// then hand off to Aviasales (affiliate) for the exact dates chosen.
function searchEuropeFromCache(){
  const citySel = document.getElementById("europeCity");
  const code = citySel.value;
  const city = citySel.selectedOptions[0]?.textContent || code;
  const cityName = city.replace(/\s*\([^)]*\)\s*$/, "");
  const country = document.getElementById("europeCountry").value;
  const out = document.getElementById("europeDate").value;
  const ret = document.getElementById("europeReturn").value;
  const box = document.getElementById("europeResults");
  const trav = _cacheTrav();

  // "Build this trip" — full destination guide for the EXACT dates picked.
  // No cached fare for those dates, so the flight line links to live prices.
  const synth = origin => JSON.stringify({
    city: cityName, country, code: (code||"").split(",")[0].trim(),
    price: null, stops: null, total_time: "", airlines: "", origin_airport: origin
  }).replace(/'/g, "&#39;");
  const buildBtns = (out && ret) ? `
    <div style="margin-top:14px">
      <div style="font-weight:700;font-size:14px;margin-bottom:8px">🧳 Plan the full trip for your dates (${new Date(out+"T12:00:00").toLocaleDateString("en-IE",{day:"numeric",month:"short"})} → ${new Date(ret+"T12:00:00").toLocaleDateString("en-IE",{day:"numeric",month:"short"})})</div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <a class="deal-book primary" style="cursor:pointer"
           onclick='openDetail(${synth("DUB")}, "${out}", "${ret}", selAdults + selChildren, 1, true)'>from Dublin — hotels, cars &amp; guide →</a>
        <a class="deal-book secondary" style="cursor:pointer"
           onclick='openDetail(${synth("ORK")}, "${out}", "${ret}", selAdults + selChildren, 1, true)'>from Cork →</a>
      </div>
    </div>` : "";

  const found = [];
  for (const apCode of ["ORK", "DUB"]) {
    for (const b of _allBoards(apCode)) {
      const d = _findDeal(b, code);
      if (d) found.push({ apCode, b, d, pp: Math.round(d.price / trav) });
    }
  }
  found.sort((a, c) => a.pp - c.pp);

  const cta = (out && ret) ? "" : `
    <div style="font-size:13px;color:var(--muted);margin-top:12px">Pick an outbound and return date above to plan the full trip.</div>`;

  if (!found.length) {
    if (out && ret) {
      // No scanned data for this city — don't make the visitor tap again.
      // Open the full trip guide straight away, defaulting to Dublin (by far
      // the wider network of the two airports). The guide's own "Same trip
      // from Cork" strip lets them switch in one tap if Cork also flies there.
      const dublinDeal = { city: cityName, country, code: (code || "").split(",")[0].trim(),
                            price: null, stops: null, total_time: "", airlines: "", origin_airport: "DUB" };
      openDetail(dublinDeal, out, ret, selAdults + selChildren, 1, true);
      return;
    }
    box.innerHTML = `
      <p style="font-size:14px;color:var(--muted)">We don't scan ${city} regularly (it's beyond our direct-route boards) — pick your outbound and return dates above and we'll open the full trip planner straight away.</p>`;
    return;
  }

  const fmtD = iso => new Date(iso + "T00:00:00").toLocaleDateString("en-IE", {day:"numeric", month:"short"});
  const top = found.slice(0, 6);
  box.innerHTML = `
    <div style="font-weight:700;font-size:15px;margin-bottom:4px">Recently scanned fares to ${city}</div>
    <div style="font-size:12px;color:var(--muted);margin-bottom:12px">From our automatic scans — your exact dates may differ, check live below.</div>
    <table class="results-table">
      <thead><tr><th>From</th><th>Dates</th><th>Per person</th><th>Airline</th><th></th></tr></thead>
      <tbody>${top.map(r => {
        const dd = {...r.d, origin_airport: r.apCode};
        const ddJson = JSON.stringify(dd).replace(/'/g, "&#39;");
        return `
        <tr style="cursor:pointer" title="Open full trip guide"
            onclick='openDetail(${ddJson}, "${r.d.depart_date || r.b.depart_date}", "${r.d.return_date || r.b.return_date}", selAdults + selChildren, _cacheTrav(), true)'>
          <td>${r.apCode === "ORK" ? "Cork" : "Dublin"}</td>
          <td>${fmtD(r.d.depart_date || r.b.depart_date)} → ${fmtD(r.d.return_date || r.b.return_date)}${r.d.nights ? ` · ${r.d.nights}n` : ""}</td>
          <td class="price-cell">€${r.pp}</td>
          <td>${r.d.airlines || "—"}</td>
          <td><a class="deal-book secondary" style="padding:6px 12px;font-size:12px"
                 href="${flightUrl(r.d.airlines || "", r.apCode, r.d.code, r.d.depart_date || r.b.depart_date, r.d.return_date || r.b.return_date, 1, 0)}"
                 target="_blank" rel="noopener noreferrer"
                 onclick="event.stopPropagation();track('flight_click',{source:'europe_cache',dest:'${code}'})">Book</a></td>
        </tr>`;}).join("")}</tbody>
    </table>
    <div style="font-size:12px;color:var(--muted);margin-top:8px">💡 Tap any row for the full trip guide for those dates.</div>` + buildBtns + cta;
}

// ── Newsletter signup: native form, AJAX-enhanced, blocker-proof ─────────────
(function(){
  const f = document.getElementById("hcSignup");
  if (!f) return;
  f.addEventListener("submit", async function(ev){
    ev.preventDefault();
    const btn = f.querySelector(".hc-signup-btn");
    const msg = document.getElementById("hcSignupMsg");
    const email = f.querySelector('input[name="fields[email]"]').value.trim();
    if (!email) return;
    btn.disabled = true; btn.textContent = "Subscribing…";
    try {
      const r = await fetch(f.action, { method: "POST", body: new FormData(f) });
      if (!r.ok) throw new Error("HTTP " + r.status);
      msg.textContent = "You're in! 🎉 Watch your inbox for the next deals round-up.";
      msg.className = "ok";
      f.querySelector(".hc-signup-row").style.display = "none";
      track("newsletter_signup", { location: "homepage" });
    } catch(e) {
      // Network/CORS hiccup → fall back to a native post in a new tab
      msg.textContent = "One more step — confirm in the tab that just opened.";
      msg.className = "ok";
      f.submit();  // programmatic submit bypasses this listener — no loop
    } finally {
      btn.disabled = false; btn.textContent = "Subscribe";
    }
  });
})();

// ── Backend health check ─────────────────────────────────────────────────────
// Silent health probe — sets backendOnline so the planner knows whether live
// search is available. No nav badge: that was a relic of the run-from-my-PC era.
async function checkBackend() {
  if (!BACKEND_URL) { backendOnline = false; return; }
  try {
    const r = await fetch(BACKEND_URL + "/api/health", { signal: AbortSignal.timeout(4000) });
    backendOnline = r.ok;
  } catch(e) { backendOnline = false; }
}

function setLiveUi(online) {
  // Live search now lives inside the trip guide; the legacy standalone form
  // stays hidden in all cases. europeSearch stays enabled (cache + Aviasales).
}

// ── Populate dropdowns ───────────────────────────────────────────────────────
// Build the merged, grouped "Plan a Trip" city picker.
// One <select> with <optgroup> per country. Countries that have at least one
// direct route from Cork/Dublin float to the top (A–Z), then the rest (A–Z).
// Direct-served cities get a ✈ marker in the option text.
function planCityList() {
  // Merge DIRECT (tracked routes, carry airline info) with EUROPE (wider list).
  // Key by the primary IATA code so a city appears once even if both lists hold it.
  const byCode = new Map();
  const primary = code => (code || "").split(",")[0].trim();
  DIRECT.forEach(d => {
    const key = primary(d.code);
    byCode.set(key, { code: d.code, city: d.city, country: d.country, direct: true });
  });
  EUROPE.forEach(d => {
    const key = primary(d.code);
    if (!byCode.has(key)) byCode.set(key, { code: d.code, city: d.city, country: d.country, direct: false });
  });
  return [...byCode.values()];
}

function populateSelects() {
  const sel = document.getElementById("planCity");
  const cities = planCityList();

  // Group by country; track which countries have any direct route.
  const groups = {};        // country -> [city objects]
  const directCountry = {}; // country -> bool
  cities.forEach(c => {
    (groups[c.country] = groups[c.country] || []).push(c);
    if (c.direct) directCountry[c.country] = true;
  });

  // Country order tuned for Irish holidaymakers: top sun + city-break
  // destinations first, roughly by how many Irish travellers go there.
  // Direct-route countries still rank ahead of connection-only ones within
  // the same popularity band. Any country not listed falls to the end, A–Z,
  // so nothing is ever dropped from the picker.
  const POPULAR_ORDER = [
    "Spain", "Portugal", "Italy", "Greece", "France",
    "United Kingdom", "England", "Scotland", "Netherlands", "Germany",
    "Poland", "Czech Republic", "Hungary", "Austria", "Croatia",
    "Malta", "Switzerland", "Denmark", "Turkey", "Cyprus",
  ];
  const rank = c => {
    const i = POPULAR_ORDER.indexOf(c);
    return i === -1 ? POPULAR_ORDER.length : i;
  };
  const allCountries = Object.keys(groups);
  // Direct-route countries first, then the rest; within each, by popularity
  // rank, then alphabetically for anything past the ranked list.
  const byPref = list => list.sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
  const directFirst = byPref(allCountries.filter(c => directCountry[c] && c));
  const theRest     = byPref(allCountries.filter(c => !directCountry[c] && c));
  const ordered = [...directFirst, ...theRest];

  sel.innerHTML = "";
  ordered.forEach(country => {
    const og = document.createElement("optgroup");
    og.label = country;
    groups[country].sort((a, b) => a.city.localeCompare(b.city)).forEach(c => {
      const o = document.createElement("option");
      o.value = c.code;
      o.textContent = c.direct ? `${c.city} ✈` : c.city;
      og.appendChild(o);
    });
    sel.appendChild(og);
  });

  // Default dates: 3 weeks out, 7 nights.
  const today = new Date();
  const out = new Date(today); out.setDate(out.getDate() + 21);
  const ret = new Date(out); ret.setDate(ret.getDate() + 7);
  const fmt = d => d.toISOString().split("T")[0];
  const outEl = document.getElementById("planOut");
  const retEl = document.getElementById("planRet");
  outEl.value = fmt(out); retEl.value = fmt(ret);
  outEl.min = fmt(today); retEl.min = fmt(today);

  // Seed the range picker with those defaults and paint the summary field.
  pdSeed('plan', outEl.value, retEl.value);

  // Reflect the shared traveller state (may already be set on the deal board).
  const setTxt = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  setTxt("planAdults", selAdults);
  setTxt("planChildren", selChildren);
  setTxt("planTvSummary", travellerLabel());

  onPlanCityChange();
}

// ── Plan a Trip: badge resolver + handlers ──────────────────────────────────
// The gold badge under the picker resolves from data we already have:
// DIRECT membership + CORK_ROUTES tell us the route status; the cache gives a
// "from €X" teaser when we've scanned it. No API call — pure lookups.
function planSelectedCode() {
  const sel = document.getElementById("planCity");
  return (sel.value || "").split(",")[0].trim();
}

function planCityMeta(code) {
  return DIRECT.find(d => (d.code || "").split(",")[0].trim() === code) || null;
}

function planCheapestCached(code) {
  const trav = _cacheTrav();
  let best = null;
  for (const ap of ["ORK", "DUB"]) {
    for (const b of _allBoards(ap)) {
      const d = _findDeal(b, code);
      if (d) { const pp = Math.round(d.price / trav); if (best === null || pp < best) best = pp; }
    }
  }
  return best;
}

function onPlanCityChange() {
  const badge = document.getElementById("planRouteBadge");
  if (!badge) return;
  const code = planSelectedCode();
  const meta = planCityMeta(code);
  document.getElementById("planResults").innerHTML = "";

  if (meta) {
    const corkToo = servedFrom("ORK", meta.code);
    const where = corkToo ? "Cork &amp; Dublin" : "Dublin";
    const price = planCheapestCached(code);
    const teaser = price !== null ? ` · from €${price}pp` : "";
    badge.innerHTML = `<span style="display:inline-flex;align-items:center;gap:9px;background:var(--gold-soft);border:1px solid var(--gold);border-radius:100px;padding:8px 16px;font-size:13px;font-weight:600;color:var(--ink)"><span style="font-size:14px">✈</span> Direct from ${where}${teaser}</span>`;
  } else {
    badge.innerHTML = `<span style="font-size:13px;color:var(--muted)">We don't fly here direct — we'll open the full planner and search live prices for your dates.</span>`;
  }
}

function onPlanDateChange() {
  // Both dates are picked manually — we never auto-touch the return date.
  // (Validation that return is after outbound happens at "Build my trip".)
}

// ── Reusable range date picker ──────────────────────────────────────────
// One tap for the outbound, one for the return; the nights between highlight.
// Two instances share this code: the Plan a Trip tab and the destination guide.
// Each writes to hidden inputs so the existing downstream code is unchanged.
const PD_INST = {
  plan:  { start:null, end:null, month:null, btn:'planDatesBtn', panel:'planCalPanel', out:'planOut', ret:'planRet' },
  guide: { start:null, end:null, month:null, btn:'gdDatesBtn',   panel:'gdCalPanel',   out:'dtDep',   ret:'dtRet'   }
};

function pdToday(){ const n = new Date(); return new Date(Date.UTC(n.getFullYear(), n.getMonth(), n.getDate())).toISOString().slice(0,10); }
function pdNights(a, b){
  const [y1,m1,d1] = a.split('-').map(Number), [y2,m2,d2] = b.split('-').map(Number);
  return Math.round((Date.UTC(y2,m2-1,d2) - Date.UTC(y1,m1-1,d1)) / 86400000);
}

function pdSummary(key){
  const S = PD_INST[key];
  if (S.start && S.end){
    const n = pdNights(S.start, S.end);
    return `${fmtDateShort(S.start)} → ${fmtDateShort(S.end)} · ${n} night${n===1?'':'s'}`;
  }
  if (S.start) return `${fmtDateShort(S.start)} → pick your return`;
  return 'Choose your dates';
}

function pdPaintField(key){
  const S = PD_INST[key];
  const btn = document.getElementById(S.btn);
  if (btn){ const t = btn.querySelector('.pd-text'); if (t) t.textContent = pdSummary(key); }
  const o = document.getElementById(S.out), r = document.getElementById(S.ret);
  if (o) o.value = S.start || '';
  if (r) r.value = S.end   || '';
}

function pdSeed(key, startIso, endIso){
  const S = PD_INST[key];
  S.start = startIso || null; S.end = endIso || null; S.month = null;
  pdPaintField(key);
}

function pdToggle(key, force){
  const S = PD_INST[key];
  const p = document.getElementById(S.panel);
  if (!p) return;
  const open = (force !== undefined) ? force : (p.style.display === 'none' || !p.style.display);
  p.style.display = open ? 'block' : 'none';
  const btn = document.getElementById(S.btn);
  if (btn) btn.classList.toggle('open', open);
  if (open) pdRender(key);
}

function pdShift(key, delta){
  const S = PD_INST[key];
  S.month = new Date(Date.UTC(S.month.getUTCFullYear(), S.month.getUTCMonth() + delta, 1));
  pdRender(key);
}

function pdGrid(key, y, m){
  const S = PD_INST[key];
  const first = new Date(Date.UTC(y, m, 1));
  const startDow = (first.getUTCDay() + 6) % 7;              // Monday-first
  const daysInMonth = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
  const today = pdToday();
  let cells = '';
  for (let i = 0; i < startDow; i++) cells += '<span class="pd-cell pd-empty"></span>';
  for (let d = 1; d <= daysInMonth; d++){
    const iso = `${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    const past = iso < today;
    let cls = 'pd-cell';
    if (past) cls += ' pd-past';
    if (iso === S.start) cls += S.end ? ' pd-start' : ' pd-start pd-solo';
    else if (iso === S.end) cls += ' pd-end';
    else if (S.start && S.end && iso > S.start && iso < S.end) cls += ' pd-in';
    cells += `<button type="button" class="${cls}"${past ? ' disabled' : ''} onclick="pdPick('${key}','${iso}')">${d}</button>`;
  }
  return `<div class="pd-dow"><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span></div>
          <div class="pd-grid">${cells}</div>`;
}

function pdRender(key){
  const S = PD_INST[key];
  const panel = document.getElementById(S.panel);
  if (!panel) return;
  if (!S.month){
    const base = S.start ? S.start.split('-').map(Number) : null;
    const n = new Date();
    S.month = base ? new Date(Date.UTC(base[0], base[1]-1, 1))
                   : new Date(Date.UTC(n.getFullYear(), n.getMonth(), 1));
  }
  const y = S.month.getUTCFullYear(), m = S.month.getUTCMonth();
  const next = new Date(Date.UTC(y, m + 1, 1));
  const label = d => d.toLocaleDateString('en-IE', { month:'long', year:'numeric', timeZone:'UTC' });

  const nowM = new Date();
  const curKey  = `${nowM.getFullYear()}-${String(nowM.getMonth()+1).padStart(2,'0')}`;
  const thisKey = `${y}-${String(m+1).padStart(2,'0')}`;
  const prevDisabled = thisKey <= curKey;

  const hint = (S.start && !S.end) ? 'Now tap your return date'
             : (S.start && S.end)  ? `${pdNights(S.start, S.end)} nights selected`
             : 'Tap your outbound date';

  panel.innerHTML = `
    <div class="pd-navrow">
      <button type="button" class="pd-nav" onclick="pdShift('${key}',-1)"${prevDisabled ? ' disabled' : ''} aria-label="Previous month">‹</button>
      <div class="pd-labels">
        <span class="pd-month">${label(S.month)}</span>
        <span class="pd-month pd-month2">${label(next)}</span>
      </div>
      <button type="button" class="pd-nav" onclick="pdShift('${key}',1)" aria-label="Next month">›</button>
    </div>
    <div class="pd-months">
      <div class="pd-mo">${pdGrid(key, y, m)}</div>
      <div class="pd-mo pd-mo2">${pdGrid(key, next.getUTCFullYear(), next.getUTCMonth())}</div>
    </div>
    <div class="pd-hint">${hint}</div>`;
}

function pdPick(key, iso){
  const S = PD_INST[key];
  if (!S.start || S.end){          // start a fresh range
    S.start = iso; S.end = null;
  } else if (iso > S.start){       // completes the range
    S.end = iso;
  } else {                         // tapped on/before the start → new start
    S.start = iso; S.end = null;
  }
  pdPaintField(key);
  pdRender(key);
  if (S.start && S.end) setTimeout(() => pdToggle(key, false), 280);
}

// "Build my trip" — one destination for every path: the full guide.
function planBuildTrip() {
  const sel = document.getElementById("planCity");
  const code = planSelectedCode();
  const opt = sel.selectedOptions[0];
  const cityName = (opt ? opt.textContent : code).replace(/\s*✈\s*$/, "").trim();
  const meta = planCityMeta(code);
  const country = meta ? meta.country : (EUROPE.find(d => (d.code||"").split(",")[0].trim() === code) || {}).country || "";
  const out = document.getElementById("planOut").value;
  const ret = document.getElementById("planRet").value;

  // Default airport: if the cache knows which of Cork/Dublin is cheaper for
  // this destination, open on that one (fixes "shows Dublin when Cork is
  // cheaper"). Otherwise fall back to Dublin (wider network). The guide's
  // banner + timeline still surface the other airport either way.
  const defaultAp = cheaperAirport(code) || "DUB";
  const deal = { city: cityName, country, code, price: null, stops: null,
                 total_time: "", airlines: meta ? meta.airlines : "", origin_airport: defaultAp };
  // Dates were already chosen on this tab, so run the live flight search on
  // arrival — no need to make the visitor press a button again in the guide.
  window._gAutoSearch = true;
  openDetail(deal, out, ret, selAdults + selChildren, 1, true);
  track("view_destination", { source: "plan", dest: code });
}

function updateCities() {
  const country = document.getElementById("europeCountry").value;
  const sel = document.getElementById("europeCity");
  sel.innerHTML = "";
  EUROPE.filter(d => d.country === country).forEach(d => {
    const o = document.createElement("option"); o.value = d.code;
    o.textContent = `${d.city} (${d.code})`; sel.appendChild(o);
  });
  refreshEuropeResults();
}

// Keep the results (and their affiliate links) in sync with the inputs —
// stale results with old destinations must never linger on screen.
function refreshEuropeResults() {
  const box = document.getElementById("europeResults");
  if (!box || !box.innerHTML.trim()) return;   // nothing rendered yet
  if (!backendOnline) searchEuropeFromCache(); // instant, cache-only
  else box.innerHTML = "";                     // live mode: clear, ask to re-search
}

// ── Live search: Direct ±5 days — separate out/return grids ─────────────────
function addDays(dateStr, n) {
  const d = new Date(dateStr + "T12:00:00");
  d.setDate(d.getDate() + n);
  return d.toISOString().split("T")[0];
}
function fmtDateShort(ds) {
  return new Date(ds+"T12:00:00").toLocaleDateString("en-IE",{weekday:"short",day:"numeric",month:"short"});
}

// State for the two selected dates
let selectedOut = null, selectedRet = null;
let outboundPrices = {}, returnPrices = {};

function updateCombinedTotal() {
  const box = document.getElementById("combinedTotal");
  if (!box) return;
  if (selectedOut && selectedRet) {
    const op = outboundPrices[selectedOut];
    const rp = returnPrices[selectedRet];
    if (op && rp) {
      const total = op.price + rp.price;
      const destCode = document.getElementById("directDest").value;
      const info = DIRECT.find(x => x.code === destCode) || {code:destCode, city:destCode, country:"", airlines:op.airlines||""};
      // Build a deal-style object so the full detail page can open from live search.
      // Live search is per-person, so price = combined total, cacheTravellers = 1.
      const liveDeal = {
        code: info.code, city: info.city, country: info.country,
        price: total, stops: 0, total_time: "Direct",
        airlines: op.airlines || info.airlines || "—",
        is_cheaper: false, is_new: false, hist_typical: null
      };
      const dealJson = JSON.stringify(liveDeal).replace(/'/g,"&#39;").replace(/"/g,"&quot;");
      box.innerHTML = `
        <div class="live-combo">
          <div class="live-combo-top">
            <div>
              <div class="live-combo-lbl">Your selected combination</div>
              <div class="live-combo-dates">${fmtDateShort(selectedOut)} → ${fmtDateShort(selectedRet)}</div>
              <div class="live-combo-sub">€${op.price} out (${op.airlines||'—'}) · €${rp.price} back (${rp.airlines||'—'})</div>
            </div>
            <div class="live-combo-price">
              <div class="live-combo-price-lbl">Return · per person</div>
              <div class="live-combo-price-val">€${total}</div>
            </div>
          </div>
          <button class="live-combo-btn" onclick='openLiveDetail("${dealJson}","${selectedOut}","${selectedRet}")'>
            View full trip guide — weather, things to do, hotels &amp; more →
          </button>
        </div>`;
    }
  } else {
    box.innerHTML = `<div class="live-combo-empty">👆 Pick an outbound date above and a return date below to build your trip and see the full guide</div>`;
  }
}

// Opens the rich detail overlay from a live Direct-Flights selection.
function openLiveDetail(dealJson, dep, ret){
  try {
    const d = JSON.parse(dealJson.replace(/&quot;/g,'"').replace(/&#39;/g,"'"));
    // Live search is per person → groupSize 1, cacheTravellers 1 (price already per person)
    openDetail(d, dep, ret, selAdults + selChildren, 1, true);
  } catch(e){ console.error("Could not open detail", e); }
}

function renderDateGrid(prices, type) {
  const gridId = type === "out" ? "outGrid" : "retGrid";
  const grid = document.getElementById(gridId);
  if (!grid) return;
  const entries = Object.entries(prices).sort((a,b) => a[0].localeCompare(b[0]));
  if (!entries.length) { grid.innerHTML = `<p style="color:var(--gray);font-size:13px">No flights found for this window.</p>`; return; }
  const minPrice = Math.min(...entries.map(([,f]) => f.price));
  grid.innerHTML = "";
  entries.forEach(([date, f]) => {
    const isCheapest = f.price === minPrice;
    const isSelected = type === "out" ? selectedOut === date : selectedRet === date;
    const card = document.createElement("div");
    card.style.cssText = `cursor:pointer;border-radius:10px;padding:10px 8px;text-align:center;border:${isSelected?'2px solid var(--blue)':isCheapest?'2px solid var(--green)':'1px solid var(--border)'};background:${isSelected?'rgba(11,110,197,.08)':isCheapest?'rgba(0,179,104,.06)':'var(--card)'};transition:.15s;`;
    card.innerHTML = `
      <div style="font-size:10px;color:var(--gray);margin-bottom:2px">${fmtDateShort(date)}</div>
      <div style="font-weight:800;font-size:18px;color:${isCheapest?'var(--green)':isSelected?'var(--blue)':'var(--navy)'}">€${f.price}</div>
      <div style="font-size:10px;color:var(--gray);margin-top:2px">${f.airlines||'—'}</div>
      ${isCheapest?'<div style="font-size:9px;color:var(--green);font-weight:700">CHEAPEST</div>':''}`;
    card.onclick = () => {
      if (type === "out") selectedOut = date; else selectedRet = date;
      renderDateGrid(outboundPrices, "out");
      renderDateGrid(returnPrices, "ret");
      updateCombinedTotal();
    };
    grid.appendChild(card);
  });
}

async function searchDirectWindow() {
  if (!backendOnline) return;
  const dest    = document.getElementById("directDest").value;
  const centre  = document.getElementById("directDate").value;
  const nights  = parseInt(document.getElementById("directNights").value) || 7;
  const box     = document.getElementById("directResults");
  const prog    = document.getElementById("directProgress");
  const progBar = document.getElementById("directProgressBar");
  const progTxt = document.getElementById("directProgressText");
  const progCnt = document.getElementById("directProgressCount");
  const destName = document.getElementById("directDest").selectedOptions[0]?.textContent?.split("—")[0]?.trim() || dest;

  const today = new Date().toISOString().split("T")[0];
  const outDates = [], retDates = [];
  for (let i = -5; i <= 5; i++) {
    const d = addDays(centre, i);
    if (d >= today) outDates.push(d);
    const r = addDays(addDays(centre, nights), i);
    if (r > centre) retDates.push(r);
  }

  // Reset state
  selectedOut = null; selectedRet = null;
  outboundPrices = {}; returnPrices = {};

  // Show skeleton UI
  box.innerHTML = `
    <div id="combinedTotal" style="margin-bottom:16px">
      <div style="text-align:center;padding:16px;color:var(--gray);font-size:13px;border:1px dashed var(--border);border-radius:10px">
        👆 Select an outbound and return date to see the combined total</div>
    </div>
    <div style="font-weight:700;font-size:15px;margin-bottom:8px">✈️ Outbound: Cork → ${destName}</div>
    <div style="font-size:12px;color:var(--gray);margin-bottom:10px">Pick your departure date (±5 days around ${fmtDateShort(centre)})</div>
    <div id="outGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:8px;margin-bottom:24px">
      <div style="color:var(--gray);font-size:13px">Searching outbound dates...</div>
    </div>
    <div style="font-weight:700;font-size:15px;margin-bottom:8px">🔄 Return: ${destName} → Cork</div>
    <div style="font-size:12px;color:var(--gray);margin-bottom:10px">Pick your return date (±5 days around ${fmtDateShort(addDays(centre,nights))})</div>
    <div id="retGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:8px">
      <div style="color:var(--gray);font-size:13px">Searching return dates...</div>
    </div>`;

  prog.style.display = "block";
  document.getElementById("directSearch").disabled = true;

  const total = outDates.length + retDates.length;
  let done = 0;
  let consecutiveFails = 0;
  let quotaHit = false;

  // Helper: fetch one date with a timeout so it can't hang forever
  async function searchOne(body){
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 15000);  // 15s per request
    try {
      const r = await fetch(BACKEND_URL + "/api/search/direct" + NGROK_BYPASS, {
        method:"POST", headers:BACKEND_HEADERS, body: JSON.stringify(body), signal: ctrl.signal
      });
      clearTimeout(t);
      if (r.status === 502) { quotaHit = true; return null; }  // keys exhausted on backend
      return await r.json();
    } catch(e) { clearTimeout(t); return null; }
  }

  function bailIfStuck(){
    // If many calls in a row fail (offline / all keys exhausted), stop and explain
    if (quotaHit || consecutiveFails >= 4) {
      prog.style.display = "none";
      document.getElementById("directSearch").disabled = false;
      const msg = quotaHit
        ? "Live search is temporarily out of quota — the daily search limit was reached. Please try again later."
        : "Live search isn't responding — your backend may be offline. The Deal Board above always works without it.";
      const box = document.getElementById("directResults") || progTxt.parentElement;
      box.innerHTML = `<div style="text-align:center;padding:30px;color:var(--muted);font-size:14px">⚠️ ${msg}</div>`;
      return true;
    }
    return false;
  }

  // Search outbound dates
  for (const date of outDates) {
    progTxt.textContent = `Outbound ${fmtDateShort(date)}…`;
    progCnt.textContent = `${++done}/${total}`;
    progBar.style.width = `${Math.round((done/total)*100)}%`;
    const data = await searchOne({dest_code:dest, outbound_date:date, return_date:null});
    if (data && data.price) { outboundPrices[date] = data; renderDateGrid(outboundPrices, "out"); consecutiveFails = 0; }
    else { consecutiveFails++; }
    if (bailIfStuck()) return;
    await new Promise(r => setTimeout(r, 250));
  }

  // Search return dates (reverse direction: dest → ORK)
  for (const date of retDates) {
    progTxt.textContent = `Return ${fmtDateShort(date)}…`;
    progCnt.textContent = `${++done}/${total}`;
    progBar.style.width = `${Math.round((done/total)*100)}%`;
    const data = await searchOne({dest_code:dest, outbound_date:addDays(date,-nights), return_date:date});
    if (data && data.price) {
      returnPrices[date] = { price: data.price, airlines: data.airlines, arrival_airport: "ORK" };
      renderDateGrid(returnPrices, "ret"); consecutiveFails = 0;
    } else { consecutiveFails++; }
    if (bailIfStuck()) return;
    await new Promise(r => setTimeout(r, 250));
  }

  prog.style.display = "none";
  document.getElementById("directSearch").disabled = false;
  updateCombinedTotal();
}

// ── Live search: Europe (all options) ────────────────────────────────────────
async function searchEurope() {
  // Guide-first design: the planner (with live flights inside) handles all cases.
  searchEuropeFromCache(); return;
  const dest = document.getElementById("europeCity").value;
  const out = document.getElementById("europeDate").value;
  const ret = document.getElementById("europeReturn").value;
  const city = document.getElementById("europeCity").selectedOptions[0]?.textContent || dest;
  const box = document.getElementById("europeResults");
  box.innerHTML = '<div class="loading"><div class="spinner"></div><br>Searching all routes…</div>';

  try {
    const r = await fetch(BACKEND_URL + "/api/search/all" + NGROK_BYPASS, {
      method:"POST", headers:BACKEND_HEADERS,
      body: JSON.stringify({dest_code:dest, outbound_date:out, return_date:ret||null})
    });
    const data = await r.json();
    if (!data.length) { box.innerHTML = '<p style="color:var(--coral)">No routes found. Try a different date.</p>'; return; }
    const minP = Math.min(...data.map(d=>d.price));
    box.innerHTML = `
      <table class="results-table">
        <thead><tr><th>Price</th><th>Stops</th><th>Total time</th><th>Airlines</th><th>Route</th><th>Dep</th><th>Arr</th><th></th></tr></thead>
        <tbody>${data.map(d => `
          <tr class="${d.price===minP?'cheapest-row':''}">
            <td class="price-cell">€${d.price}</td>
            <td><span class="tag ${d.stops===0?'tag-direct-pill':'tag-stops'}">${d.stops===0?'Direct':d.stops+' stop(s)'}</span></td>
            <td>${d.total_time}</td>
            <td>${d.airlines}</td>
            <td style="font-size:11px;color:var(--gray)">${d.via}</td>
            <td>${d.departure}</td>
            <td>${d.arrival}</td>
            <td><a class="deal-book secondary" style="padding:6px 12px;font-size:12px" href="${flightUrl(data.airlines||'', d.arrival_airport||dest, 'ORK', out, ret||'', 1, 0)}" target="_blank" rel="noopener noreferrer">Book</a></td>
          </tr>`).join("")}</tbody>
      </table>
      <p style="margin-top:12px;font-size:12px;color:var(--gray)">Prices are ${ret?'full return':'one-way'}. Confirmed at booking.</p>`;
  } catch(e) { box.innerHTML = `<p style="color:var(--coral)">Search failed: ${e.message}</p>`; }
}

// ── Backend URL config (stored in localStorage) ──────────────────────────────
function setBackendUrl() {
  const modal = document.getElementById("connectModal");
  const input = document.getElementById("modalUrlInput");
  input.value = BACKEND_URL || "";
  modal.style.display = "flex";
  setTimeout(() => input.focus(), 100);
}
function closeModal() {
  document.getElementById("connectModal").style.display = "none";
}
function saveModalUrl() {
  const url = document.getElementById("modalUrlInput").value.trim();
  localStorage.setItem("hc_backend", url);
  closeModal();
  location.reload();
}
// Close modal on background click
document.getElementById("connectModal").addEventListener("click", function(e) {
  if (e.target === this) closeModal();
});
// Enter key submits
document.getElementById("modalUrlInput").addEventListener("keydown", function(e) {
  if (e.key === "Enter") saveModalUrl();
});

// ══════════════════════════════════════════════════════════════════════════════
// DESTINATION DETAIL PAGE
// ══════════════════════════════════════════════════════════════════════════════

// Typical daily costs by price tier (EUR). Cities mapped to a tier below.
// These are honest ballpark figures for trip budgeting, not live prices.
const COST_TIERS = {
  budget:  {meal:12, coffee:2.0, beer:3.0, transit:1.5, attraction:8,  hotel:70,  airbnb:55},
  mid:     {meal:18, coffee:3.0, beer:5.0, transit:2.0, attraction:14, hotel:110, airbnb:85},
  high:    {meal:28, coffee:4.0, beer:7.0, transit:3.0, attraction:20, hotel:160, airbnb:120},
  premium: {meal:38, coffee:5.5, beer:9.0, transit:4.0, attraction:26, hotel:220, airbnb:160},
};
const CITY_TIER = {
  // budget
  KRK:"budget", WAW:"budget", BUD:"budget", PRG:"budget", SVQ:"budget", ALC:"budget",
  ZAD:"budget", RHO:"budget", ADB:"budget", FAO:"budget", OPO:"budget",
  // mid
  LIS:"mid", MAD:"mid", BCN:"mid", AGP:"mid", VLC:"mid", BIO:"mid", PMI:"mid", ACE:"mid",
  TFS:"mid", BER:"mid", FCO:"mid", BGY:"mid", MXP:"mid", PSA:"mid", MLA:"mid", BRS:"mid",
  MAN:"mid", EDI:"mid", BOD:"mid", LYS:"mid",
  // high
  AMS:"high", FRA:"high", MUC:"high", NCE:"high", LHR:"high", LGW:"high", STN:"high", LTN:"high",
  CDG:"high", BVA:"high",
  // premium
  ZRH:"premium", GVA:"premium",
};
function cityCosts(code){ return COST_TIERS[CITY_TIER[code] || "mid"]; }

// ── Ticketmaster Events API ──────────────────────────────────────────────────
// Proxied through the hc-live-search Worker (/api/events) so the Ticketmaster
// key stays server-side and is never shipped to the browser.
// Map airport codes to Ticketmaster city names for the events search
const TM_CITY = {
  MAN:"Manchester", LHR:"London", LGW:"London", STN:"London", LTN:"London",
  EDI:"Edinburgh", BRS:"Bristol", FAO:"Faro", LIS:"Lisbon", OPO:"Porto",
  BCN:"Barcelona", MAD:"Madrid", AGP:"Malaga", ALC:"Alicante", PMI:"Palma",
  TFS:"Tenerife", ACE:"Arrecife", VLC:"Valencia", SVQ:"Seville", BIO:"Bilbao",
  BGY:"Milan", MXP:"Milan", PSA:"Pisa", FCO:"Rome", CDG:"Paris", BVA:"Paris",
  NCE:"Nice", LYS:"Lyon", BOD:"Bordeaux", AMS:"Amsterdam", FRA:"Frankfurt",
  PRG:"Prague", ZRH:"Zurich", MLA:"Valletta", ZAD:"Zadar", RHO:"Rhodes",
  ADB:"Izmir", GVA:"Geneva", MUC:"Munich", BER:"Berlin", BUD:"Budapest",
  KRK:"Krakow", WAW:"Warsaw", VIE:"Vienna", ATH:"Athens", CPH:"Copenhagen",
  VCE:"Venice", FUE:"Fuerteventura", LPA:"Las Palmas de Gran Canaria",
};

// ── Curated top sights per city (v3.1) ───────────────────────────────────────
// [Wikipedia title (for the photo), display name, one-line why-go]
const CITY_SIGHTS = {
  STN: [["Tower of London","Tower of London","900 years of history, the Crown Jewels and the ravens."],
        ["British Museum","British Museum","The Rosetta Stone and world treasures — free entry."],
        ["Buckingham Palace","Buckingham Palace","The King's residence; catch the Changing of the Guard."],
        ["London Eye","London Eye","The slow wheel with the best skyline view in London."]],
  MAN: [["Old Trafford","Old Trafford","The Theatre of Dreams — tour Man United's home."],
        ["Science and Industry Museum","Science & Industry Museum","Hands-on halls in the world's first industrial city."],
        ["John Rylands Research Institute and Library","John Rylands Library","A neo-Gothic cathedral of books."],
        ["Northern Quarter (Manchester)","Northern Quarter","Street art, record shops and the city's best coffee."]],
  EDI: [["Edinburgh Castle","Edinburgh Castle","The rock fortress that dominates the skyline."],
        ["Royal Mile","Royal Mile","The historic spine from castle to palace."],
        ["Arthur's Seat","Arthur's Seat","An extinct volcano with a summit view of the whole city."],
        ["National Museum of Scotland","National Museum of Scotland","From dinosaurs to Dolly the sheep — free."]],
  FAO: [["Ria Formosa Natural Park","Ria Formosa lagoons","Boat trips through island sandbars and flamingo waters."],
        ["Faro Cathedral","Faro Old Town & Cathedral","Cobbled lanes, storks' nests and a rooftop view."],
        ["Praia de Faro","Praia de Faro","The city's own long golden beach, 20 min from town."],
        ["Benagil","Benagil Cave (day trip)","The Algarve's famous sea cave — kayak in at dawn."]],
  LIS: [["Belém Tower","Belém Tower","The riverside fortress of the Age of Discoveries."],
        ["Jerónimos Monastery","Jerónimos Monastery","Manueline stone lacework — and pastéis de nata next door."],
        ["Alfama","Alfama","Fado music drifting through Lisbon's oldest maze of lanes."],
        ["Tram 28 (Lisbon)","Tram 28","The rattling yellow tram that does the greatest hits."]],
  OPO: [["Dom Luís I Bridge","Dom Luís I Bridge","Walk the top deck at sunset over the Douro."],
        ["Livraria Lello","Livraria Lello","The world's most beautiful bookshop."],
        ["Ribeira","Ribeira","Tumbling riverside quarter, UNESCO-listed."],
        ["Vila Nova de Gaia","Port wine cellars, Gaia","Taste port where it has aged for centuries."]],
  BCN: [["Sagrada Família","Sagrada Família","Gaudí's unfinished masterpiece — book ahead."],
        ["Park Güell","Park Güell","Mosaic terraces with the classic Barcelona view."],
        ["Gothic Quarter, Barcelona","Gothic Quarter","Roman walls and medieval lanes in the old heart."],
        ["La Boqueria","La Boqueria market","Juice, jamón and the city's loudest colours."]],
  AGP: [["Alcazaba of Málaga","Alcazaba","A Moorish hilltop palace above the old town."],
        ["Museo Picasso Málaga","Picasso Museum","The master's works in the city of his birth."],
        ["La Malagueta","La Malagueta beach","City sand a ten-minute walk from the centre."],
        ["Caminito del Rey","Caminito del Rey (day trip)","The cliff-hugging walkway — book well ahead."]],
  ALC: [["Santa Bárbara Castle","Santa Bárbara Castle","Ride the lift up for the full coastline panorama."],
        ["Explanada de España","Explanada de España","The wavy marble promenade made for evening strolls."],
        ["Postiguet Beach","Postiguet Beach","The city beach right under the castle."],
        ["Tabarca","Tabarca Island (boat trip)","Spain's smallest inhabited island, clear-water snorkelling."]],
  PMI: [["Palma Cathedral","Palma Cathedral","The seafront Gothic giant, glowing at sunset."],
        ["Bellver Castle","Bellver Castle","A rare circular castle with bay views."],
        ["Serra de Tramuntana","Serra de Tramuntana","UNESCO mountains — drive to Valldemossa."],
        ["Formentor","Cap de Formentor","The wild lighthouse cape at the island's tip."]],
  MAD: [["Museo del Prado","Prado Museum","Velázquez and Goya in one of the world's great galleries."],
        ["Buen Retiro Park","Retiro Park","Row a boat by the glass palace."],
        ["Royal Palace of Madrid","Royal Palace","Europe's largest royal palace, 3,000+ rooms."],
        ["Puerta del Sol","Puerta del Sol & Gran Vía","The buzzing centre — churros at San Ginés."]],
  TFS: [["Teide National Park","Mount Teide","Spain's highest peak — cable car above the clouds."],
        ["Los Gigantes","Los Gigantes cliffs","600m sea cliffs, best from a boat."],
        ["Siam Park","Siam Park","Europe's best-rated water park, made for families."],
        ["Masca","Masca village","A hamlet in a gorge on the island's wildest road."]],
  ACE: [["Timanfaya National Park","Timanfaya volcanoes","Martian landscapes and geyser demonstrations."],
        ["Jameos del Agua","Jameos del Agua","César Manrique's lava-cave concert hall."],
        ["Papagayo","Papagayo beaches","Golden coves in the island's south."],
        ["La Geria","La Geria wine valley","Vines growing in black volcanic ash."]],
  FCO: [["Colosseum","Colosseum","The arena of the gladiators — skip-the-line is worth it."],
        ["Trevi Fountain","Trevi Fountain","Toss a coin to guarantee your return."],
        ["Vatican Museums","Vatican & Sistine Chapel","Michelangelo's ceiling — book the first slot."],
        ["Trastevere","Trastevere","Ivy-hung lanes and Rome's best evening tables."]],
  BGY: [["Milan Cathedral","Duomo di Milano","Walk the marble rooftop among the spires."],
        ["Galleria Vittorio Emanuele II","Galleria Vittorio Emanuele II","The world's most elegant shopping arcade."],
        ["The Last Supper (Leonardo)","The Last Supper","Leonardo's fresco — reserve weeks ahead."],
        ["Navigli","Navigli canals","Aperitivo hour along Leonardo's waterways."]],
  CDG: [["Eiffel Tower","Eiffel Tower","Book the summit at sunset."],
        ["Louvre","The Louvre","The Mona Lisa and 9 miles of art."],
        ["Montmartre","Montmartre & Sacré-Cœur","Artists' square and the white basilica view."],
        ["Musée d'Orsay","Musée d'Orsay","Impressionists inside a Belle Époque station."]],
  NCE: [["Promenade des Anglais","Promenade des Anglais","The palm-lined seafront that defines the Riviera."],
        ["Castle Hill, Nice","Castle Hill","The waterfall park with the bay panorama."],
        ["Old Town of Nice","Old Town (Vieux Nice)","Ochre lanes, socca stalls and flower markets."],
        ["Èze","Èze village (day trip)","A stone eagle's-nest village above the sea."]],
  AMS: [["Rijksmuseum","Rijksmuseum","Rembrandt's Night Watch and the Dutch masters."],
        ["Anne Frank House","Anne Frank House","The secret annex — book exactly 6 weeks ahead."],
        ["Jordaan","Jordaan district","Canal-side cafés and Saturday markets."],
        ["Van Gogh Museum","Van Gogh Museum","The world's largest Van Gogh collection."]],
  BER: [["Brandenburg Gate","Brandenburg Gate","The symbol of a reunited city."],
        ["East Side Gallery","East Side Gallery","The longest surviving stretch of the Wall, painted."],
        ["Museum Island","Museum Island","Five world-class museums on one island."],
        ["Reichstag building","Reichstag dome","Free rooftop dome — register online first."]],
  MUC: [["Marienplatz","Marienplatz","The Glockenspiel show at 11am sharp."],
        ["Englischer Garten","English Garden","Surfers on the river wave, beer gardens beyond."],
        ["Nymphenburg Palace","Nymphenburg Palace","Bavaria's baroque summer palace."],
        ["Neuschwanstein Castle","Neuschwanstein (day trip)","The fairytale castle — 2h away and worth it."]],
  BUD: [["Hungarian Parliament Building","Parliament Building","Best seen from a Danube evening cruise."],
        ["Fisherman's Bastion","Fisherman's Bastion","Fairytale turrets with the classic river view."],
        ["Széchenyi thermal bath","Széchenyi Baths","Outdoor thermal pools, steaming in any weather."],
        ["Szimpla Kert","Ruin bars (Szimpla Kert)","Budapest's famous bars in crumbling courtyards."]],
  KRK: [["Main Square, Kraków","Main Market Square","Europe's largest medieval square, trumpeter and all."],
        ["Wawel Castle","Wawel Castle","Kings, a cathedral and a dragon's den."],
        ["Kazimierz","Kazimierz","The old Jewish quarter — zapiekanka at Plac Nowy."],
        ["Wieliczka Salt Mine","Wieliczka Salt Mine","Chapels carved from salt, 135m underground."]],
  WAW: [["Old Town Market Square, Warsaw","Old Town","Rebuilt brick-by-brick — a UNESCO story of defiance."],
        ["Łazienki Park","Łazienki Park","Peacocks, palaces and free Chopin concerts in summer."],
        ["Warsaw Uprising Museum","Uprising Museum","Moving, brilliant telling of 1944."],
        ["Palace of Culture and Science","Palace of Culture","Love it or hate it — the view deck settles it."]],
  PRG: [["Charles Bridge","Charles Bridge","Cross at dawn before the crowds."],
        ["Prague Castle","Prague Castle","The world's largest ancient castle complex."],
        ["Old Town Square (Prague)","Old Town Square","The Astronomical Clock's hourly show."],
        ["Petřín","Petřín Hill","Funicular up to a mini Eiffel Tower."]],
  GVA: [["Jet d'Eau","Jet d'Eau","The 140m lake fountain — Geneva's exclamation mark."],
        ["St. Pierre Cathedral, Geneva","Old Town & Cathedral","Climb the towers of St Pierre."],
        ["CERN","CERN","Tour the home of the Large Hadron Collider — free."],
        ["Salève","Mont Salève","Cable car to the balcony over the lake and Mont Blanc."]],
  MLA: [["Valletta","Valletta","The honey-stone capital, all of it UNESCO-listed."],
        ["Mdina","Mdina","The silent walled city — magic after dark."],
        ["Blue Lagoon (Malta)","Blue Lagoon, Comino","The turquoise swim of the Mediterranean."],
        ["St. John's Co-Cathedral","St John's Co-Cathedral","Caravaggio's masterpiece behind a plain facade."]],
};

// ── Curated transport guide per city ─────────────────────────────────────────
// Structured: airport→centre options (with best pick), getting-around note,
// family tip, and official transport site. Map uses CITY_COORDS.
const CITY_TRANSPORT = {
  VIE:{options:[{mode:"🚆 CAT train",detail:"to Wien Mitte",time:"~16 min",price:"~€15",best:true},{mode:"🚆 S7 train",detail:"to centre",time:"~25 min",price:"~€4.30"},{mode:"🚕 Taxi",detail:"to centre",time:"~25 min",price:"~€40"}],around:"U-Bahn, trams and buses run everywhere. Single ~€2.40; 24h pass ~€8.",family:"Children under 6 travel free; under-15s free on Sundays and holidays.",official:{name:"Wiener Linien",url:"https://www.wienerlinien.at/web/wl-en"}},
  ATH:{options:[{mode:"🚇 Metro L3",detail:"to Syntagma",time:"~40 min",price:"~€9",best:true},{mode:"🚌 X95 bus",detail:"24h to Syntagma",time:"~50 min",price:"~€5.50"},{mode:"🚕 Taxi",detail:"flat fare, daytime",time:"~40 min",price:"~€40"}],around:"Metro, tram and buses. A 90-minute ticket ~€1.20; 24h pass ~€4.10.",family:"Children under 6 travel free; 6–18s pay reduced fare.",official:{name:"Athens Transport (OASA)",url:"https://www.oasa.gr/en/"}},
  VLC:{options:[{mode:"🚇 Metro L3/L5",detail:"to centre",time:"~25 min",price:"~€4.90",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~20 min",price:"~€25"}],around:"Metro, trams and buses; single ~€1.50, SUMA 10-trip ~€8. The old town and Turia park are very walkable.",family:"Under-10s travel free on EMT buses with a Xiquets card.",official:{name:"Metrovalencia",url:"https://www.metrovalencia.es/en/"}},
  CPH:{options:[{mode:"🚇 Metro M2",detail:"to Kongens Nytorv",time:"~15 min",price:"~DKK 30",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~20 min",price:"~DKK 300"}],around:"Driverless metro runs 24/7; buses and harbour buses too. City Pass 24h ~DKK 90. Cycling is everywhere.",family:"Two children under 12 travel free with each paying adult.",official:{name:"Copenhagen Metro",url:"https://m.dk/en/"}},
  SVQ:{options:[{mode:"🚌 EA bus",detail:"to Plaza de Armas",time:"~35 min",price:"~€4",best:true},{mode:"🚕 Taxi",detail:"flat fare to centre",time:"~20 min",price:"~€25"}],around:"The centre is wonderfully walkable; trams and TUSSAM buses fill gaps, single ~€1.40.",family:"Under-5s free on buses; the tram through the centre is a hit with kids.",official:{name:"TUSSAM Sevilla",url:"https://www.tussam.es/"}},
  VCE:{options:[{mode:"🚌 ATVO/ACTV bus",detail:"to Piazzale Roma",time:"~20 min",price:"~€10",best:true},{mode:"⛴️ Alilaguna boat",detail:"to San Marco",time:"~1h 15m",price:"~€15"},{mode:"🚤 Water taxi",detail:"direct to hotel",time:"~30 min",price:"~€120"}],around:"Vaporetto water buses: single ~€9.50, 24h pass ~€25 — the pass pays for itself quickly. Otherwise, walk.",family:"Under-6s travel free on vaporetti.",official:{name:"ACTV Venezia",url:"https://actv.avmspa.it/en"}},
  PSA:{options:[{mode:"🚝 PisaMover",detail:"to Pisa Centrale",time:"~8 min",price:"~€5",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~10 min",price:"~€12"}],around:"Pisa is compact and walkable; regional trains reach Florence (~1h, ~€9) and the Cinque Terre.",family:"Under-4s free on Trenitalia; kids ride the PisaMover free under 6.",official:{name:"PisaMover",url:"https://pisa-mover.com/en/"}},
  ZAD:{options:[{mode:"🚌 Airport bus",detail:"to old town",time:"~25 min",price:"~€3",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~15 min",price:"~€20"}],around:"The old town peninsula is car-free and walkable; Liburnija city buses ~€1.30 reach the beaches.",family:"Small children travel free on city buses.",official:{name:"Liburnija Zadar",url:"https://www.liburnija-zadar.hr/"}},
  RHO:{options:[{mode:"🚌 Airport bus",detail:"to Rhodes Town",time:"~30 min",price:"~€2.60",best:true},{mode:"🚕 Taxi",detail:"to Rhodes Town",time:"~25 min",price:"~€25"}],around:"KTEL buses run the east and west coasts cheaply; the medieval Old Town is walk-only.",family:"Under-6s free on buses; agree taxi fares before longer island trips.",official:{name:"KTEL Rhodes",url:"https://ktelrodou.gr/en/"}},
  FUE:{options:[{mode:"🚌 Bus L3/L10",detail:"to Puerto del Rosario / Caleta",time:"~20–30 min",price:"~€2–3",best:true},{mode:"🚕 Taxi",detail:"to nearby resorts",time:"~15 min",price:"~€15–25"}],around:"Tiadhe buses link the resorts, but they're infrequent — most visitors hire a car for the beaches.",family:"Under-4s free on buses; car seats should be booked with hire cars in advance.",official:{name:"Tiadhe Fuerteventura buses",url:"https://www.tiadhe.com/"}},
  LPA:{options:[{mode:"🚌 Bus 60",detail:"to Las Palmas (San Telmo)",time:"~35 min",price:"~€2.95",best:true},{mode:"🚕 Taxi",detail:"to Las Palmas",time:"~25 min",price:"~€35"}],around:"Yellow Guaguas city buses ~€1.40 cover the city; Vegueta old town and Las Canteras beach are walkable.",family:"Under-4s free; the beachfront promenade is perfect for buggies.",official:{name:"Guaguas Municipales",url:"https://www.guaguas.com/"}},
  ZRH:{options:[{mode:"🚆 Train",detail:"to Zürich HB",time:"~12 min",price:"~CHF 7",best:true},{mode:"🚊 Tram 10",detail:"to centre",time:"~35 min",price:"~CHF 7"},{mode:"🚕 Taxi",detail:"to centre",time:"~25 min",price:"~CHF 70"}],around:"Trams and trains (ZVV zones) are superb; a 24h city pass ~CHF 9. Lake boats are included on day passes.",family:"A Junior Card lets kids under 16 travel free with a parent.",official:{name:"ZVV Zürich",url:"https://www.zvv.ch/zvv/en/home.html"}},
  MAN:{options:[{mode:"🚆 Train",detail:"to Manchester Piccadilly",time:"~20 min",price:"~£5",best:true},{mode:"🚌 Bus 43",detail:"frequent to centre",time:"~35 min",price:"~£3"},{mode:"🚕 Taxi",detail:"to city centre",time:"~25 min",price:"~£25"}],around:"Trams (Metrolink) and buses cover the city. Single tram ~£1.40–£3; day ticket ~£5.",family:"Up to 2 kids under 11 travel free with a paying adult on Metrolink.",official:{name:"Transport for Greater Manchester",url:"https://tfgm.com/"}},
  FAO:{options:[{mode:"🚌 Bus 14/16",detail:"to bus station",time:"~20 min",price:"~€2.40",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~10 min",price:"~€15"}],around:"Faro centre is walkable. Próximo buses reach the beach; cheap regional trains link Algarve towns.",family:"Children under 4 travel free on regional trains; under-12s get reduced fares.",official:{name:"CP Trains Portugal",url:"https://www.cp.pt/passageiros/en"}},
  BCN:{options:[{mode:"🚌 Aerobús",detail:"to Plaça Catalunya",time:"~35 min",price:"~€7.25",best:true},{mode:"🚇 Metro L9 Sud",detail:"+ transfer",time:"~45 min",price:"~€5.50"},{mode:"🚆 R2 Train",detail:"to Sants/Passeig",time:"~30 min",price:"~€4.90"}],around:"Excellent Metro & bus network. A T-casual 10-trip ticket (~€12.55) is best value; single ~€2.65.",family:"Children under 4 ride free. The T-familiar multi-person ticket suits groups.",official:{name:"TMB Barcelona",url:"https://www.tmb.cat/en/home"}},
  MAD:{options:[{mode:"🚇 Metro L8",detail:"to centre",time:"~30 min",price:"~€4.50–5",best:true},{mode:"🚌 Exprés Aeropuerto",detail:"24h bus to Atocha",time:"~40 min",price:"~€5"},{mode:"🚕 Taxi",detail:"fixed fare to centre",time:"~25 min",price:"~€30"}],around:"Metro is fast and cheap; 10-trip ticket ~€12.20. Buses and Cercanías trains fill gaps.",family:"Under-4s travel free. A 10-trip Multi card can be shared by the whole family.",official:{name:"Metro de Madrid",url:"https://www.metromadrid.es/en"}},
  LIS:{options:[{mode:"🚇 Metro (red line)",detail:"to centre",time:"~20 min",price:"~€1.80",best:true},{mode:"🚌 Aerobus",detail:"to centre",time:"~30 min",price:"~€4"},{mode:"🚕 Taxi",detail:"to centre",time:"~15 min",price:"~€12"}],around:"Metro, trams (incl. tram 28), buses and funiculars. A Viva Viagem card with 'zapping' credit is best.",family:"Under-4s free. The reusable Viva Viagem card works for the whole family.",official:{name:"Metro Lisboa",url:"https://www.metrolisboa.pt/en/"}},
  OPO:{options:[{mode:"🚇 Metro Line E",detail:"to centre (violet)",time:"~30 min",price:"~€2.60",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~20 min",price:"~€25"}],around:"Metro and buses (Andante card). The historic tram 1 runs along the river.",family:"Under-4s free; the Andante card is shareable for short hops.",official:{name:"Metro do Porto",url:"https://en.metrodoporto.pt/"}},
  AMS:{options:[{mode:"🚆 Train",detail:"to Amsterdam Centraal",time:"~17 min",price:"~€5.90",best:true},{mode:"🚌 Bus 397",detail:"to centre",time:"~30 min",price:"~€6.50"},{mode:"🚕 Taxi",detail:"to centre",time:"~25 min",price:"~€45"}],around:"Trams, metro and buses (GVB). A 24h GVB ticket ~€9. Cycling is huge here.",family:"Under-4s free. A GVB family/group day ticket is good value for sightseeing.",official:{name:"GVB Amsterdam",url:"https://en.gvb.nl/"}},
  CDG:{options:[{mode:"🚆 RER B",detail:"to centre",time:"~35 min",price:"~€11.45",best:true},{mode:"🚌 Roissybus",detail:"to Opéra",time:"~60 min",price:"~€16.60"},{mode:"🚕 Taxi",detail:"fixed fare to Right Bank",time:"~45 min",price:"~€56"}],around:"Metro, RER, bus and tram. A carnet of 10 t+ tickets (~€17) or a Navigo Easy card is best.",family:"Under-4s free; 4–9s pay half on RER. Kids love the front of the driverless Metro 1 & 14.",official:{name:"RATP Paris",url:"https://www.ratp.fr/en"}},
  BVA:{options:[{mode:"🚌 Official shuttle",detail:"to Porte Maillot, Paris",time:"~1h15",price:"~€16.90",best:true},{mode:"🚕 Taxi",detail:"long trip into Paris",time:"~1h15",price:"~€110+"}],around:"Beauvais is ~85km from Paris — plan extra time. In Paris: Metro, RER, bus, tram; carnet of 10 ~€17.",family:"Buy shuttle tickets in advance; under-4s free on Paris transport.",official:{name:"Beauvais Airport buses",url:"https://www.aeroportparisbeauvais.com/en/access/by-shuttle"}},
  NCE:{options:[{mode:"🚊 Tram L2",detail:"to centre/port",time:"~25 min",price:"~€1.70",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~15 min",price:"~€32"}],around:"Trams and buses (Lignes d'Azur); a single ~€1.70 covers transfers. Centre is walkable.",family:"Under-6s travel free. A 10-trip pass is shareable across the family.",official:{name:"Lignes d'Azur",url:"https://www.lignesdazur.com/"}},
  FCO:{options:[{mode:"🚆 Leonardo Express",detail:"to Termini",time:"~32 min",price:"~€14",best:true},{mode:"🚌 SIT/Terravision bus",detail:"to Termini",time:"~55 min",price:"~€6–7"},{mode:"🚕 Taxi",detail:"fixed fare to centre",time:"~45 min",price:"~€55"}],around:"Metro (3 lines), buses and trams (ATAC). A single BIT ticket ~€1.50 (100 min); 24h ~€7.",family:"Under-10s travel free on Rome public transport — great for families.",official:{name:"ATAC Roma",url:"https://www.atac.roma.it/en"}},
  PRG:{options:[{mode:"🚌 Bus 119",detail:"+ Metro A",time:"~30 min",price:"~40 CZK",best:true},{mode:"🚌 Airport Express",detail:"to main train station",time:"~40 min",price:"~100 CZK"},{mode:"🚕 Taxi",detail:"to centre",time:"~25 min",price:"~600 CZK"}],around:"Metro, trams and buses (PID). A 30-min ticket ~30 CZK; 24h ~120 CZK. Trams are great for sightseeing.",family:"Children under 6 travel free; 6–15s pay half fare.",official:{name:"Prague Transport (PID)",url:"https://pid.cz/en/"}},
  EDI:{options:[{mode:"🚊 Tram",detail:"to centre",time:"~35 min",price:"~£7",best:true},{mode:"🚌 Airlink 100",detail:"to centre",time:"~30 min",price:"~£5.50"},{mode:"🚕 Taxi",detail:"to centre",time:"~25 min",price:"~£25"}],around:"Buses (Lothian) and trams; single ~£2, day ticket ~£5.50. The Old Town is very walkable.",family:"Up to 2 under-5s free per adult; a family day ticket covers bus + tram.",official:{name:"Lothian Buses",url:"https://www.lothianbuses.com/"}},
  AGP:{options:[{mode:"🚆 Cercanías C1",detail:"to centre",time:"~12 min",price:"~€1.80",best:true},{mode:"🚌 Bus A Express",detail:"to centre",time:"~25 min",price:"~€4"},{mode:"🚕 Taxi",detail:"to centre",time:"~15 min",price:"~€20"}],around:"Walkable centre; buses (EMT) and Cercanías trains reach the Costa del Sol resorts cheaply.",family:"Under-4s free; the Cercanías is an easy step-free option with buggies.",official:{name:"Renfe Cercanías",url:"https://www.renfe.com/es/en"}},
  ALC:{options:[{mode:"🚌 Bus C-6",detail:"to centre",time:"~25 min",price:"~€3.85",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~15 min",price:"~€20"}],around:"Compact, walkable centre. The TRAM (light rail) runs up the coast to Benidorm.",family:"Under-4s free; the TRAM to the beaches is a fun ride for kids.",official:{name:"TRAM Alicante",url:"https://www.tramalicante.es/"}},
  VLC:{options:[{mode:"🚇 Metro L3/L5",detail:"to centre",time:"~20 min",price:"~€4.80",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~15 min",price:"~€20"}],around:"Metro, trams and buses. Valencia is famously flat and bike-friendly (Valenbisi).",family:"Under-10s travel free on Metrovalencia with an adult.",official:{name:"Metrovalencia",url:"https://www.metrovalencia.es/"}},
  FRA:{options:[{mode:"🚆 S-Bahn S8/S9",detail:"to centre",time:"~15 min",price:"~€5.80",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~20 min",price:"~€30"}],around:"U-Bahn, S-Bahn, trams and buses (RMV). A single ~€3.65; day ticket ~€6.80.",family:"Children under 6 free; a Gruppentageskarte (group day ticket) is great value.",official:{name:"RMV Frankfurt",url:"https://www.rmv.de/c/en/homepage"}},
  MUC:{options:[{mode:"🚆 S-Bahn S1/S8",detail:"to centre",time:"~40 min",price:"~€13",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~35 min",price:"~€70"}],around:"U-Bahn, S-Bahn, trams and buses (MVV). Single ~€3.90; day ticket ~€9.20 (great value).",family:"The MVV day ticket covers up to 2 adults + 3 kids — ideal for a family.",official:{name:"MVV Munich",url:"https://www.mvv-muenchen.de/en/"}},
  BER:{options:[{mode:"🚆 FEX / S-Bahn",detail:"to centre (ABC ticket)",time:"~30–45 min",price:"~€4.40",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~40 min",price:"~€50"}],around:"U-Bahn, S-Bahn, trams and buses (BVG). An AB single ~€3.50; day ticket ~€9.90.",family:"Up to 3 kids (6–14) travel cheap; under-6s free. A day ticket covers the family.",official:{name:"BVG Berlin",url:"https://www.bvg.de/en"}},
  BUD:{options:[{mode:"🚌 Bus 100E",detail:"direct to Deák tér",time:"~40 min",price:"~€4.40",best:true},{mode:"🚌 200E + Metro M3",detail:"cheaper combo",time:"~50 min",price:"~€1.50"},{mode:"🚕 Taxi (Főtaxi)",detail:"to centre",time:"~30 min",price:"~€25"}],around:"Metro (4 lines), trams and buses (BKK). A single ~€1; 24h travelcard ~€6.50. Tram 2 is scenic.",family:"Under-6s travel free; a 24h group travelcard suits families.",official:{name:"BKK Budapest",url:"https://bkk.hu/en/"}},
  KRK:{options:[{mode:"🚆 Train",detail:"to Kraków Główny",time:"~20 min",price:"~12 PLN",best:true},{mode:"🚌 Bus 252/208",detail:"to centre",time:"~40 min",price:"~6 PLN"},{mode:"🚕 Taxi",detail:"to centre",time:"~25 min",price:"~90 PLN"}],around:"Trams and buses (MPK). A 20-min ticket ~4 PLN; the Old Town is pedestrian-friendly.",family:"Under-4s free; family day tickets available on MPK.",official:{name:"MPK Kraków",url:"https://www.mpk.krakow.pl/en/"}},
  WAW:{options:[{mode:"🚆 Train S2/S3",detail:"to centre",time:"~25 min",price:"~4.40 PLN",best:true},{mode:"🚌 Bus 175",detail:"to centre",time:"~35 min",price:"~4.40 PLN"},{mode:"🚕 Taxi",detail:"to centre",time:"~25 min",price:"~50 PLN"}],around:"Metro (2 lines), trams and buses (ZTM). A 20-min ticket ~3.40 PLN; 24h ~15 PLN.",family:"Under-7s travel free; a family weekend ticket is great value.",official:{name:"ZTM Warsaw",url:"https://www.wtp.waw.pl/en/"}},
  ZRH:{options:[{mode:"🚆 Train",detail:"to main station",time:"~10 min",price:"~€7",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~20 min",price:"~€55"}],around:"Trams, buses and S-Bahn (ZVV). Short hops ~€2.70; a 24h pass ~€8.80. The centre is walkable.",family:"Children 6–16 travel half-price; under-6s free with an adult.",official:{name:"ZVV Zurich",url:"https://www.zvv.ch/zvv/en/home.html"}},
  GVA:{options:[{mode:"🚆 Train (free ticket)",detail:"grab the free ticket at the airport",time:"~10 min",price:"Free",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~15 min",price:"~€35"}],around:"Trams, buses and trains (TPG). Hotels give a free Geneva Transport Card for your whole stay.",family:"The free airport ticket + hotel transport card make Geneva very family-friendly.",official:{name:"TPG Geneva",url:"https://www.tpg.ch/en"}},
  MLA:{options:[{mode:"🚌 Bus X4",detail:"to Valletta",time:"~30 min",price:"~€2",best:true},{mode:"🚕 Taxi (fixed)",detail:"to centre",time:"~20 min",price:"~€15"}],around:"Buses (Tallinja) cover the islands; a single ~€2 (2h). No rail — buses or ferries between towns.",family:"A Tallinja Explore card gives unlimited family travel for a week.",official:{name:"Tallinja Malta",url:"https://www.publictransport.com.mt/"}},
  PSA:{options:[{mode:"🚊 PisaMover",detail:"to train station",time:"~5 min",price:"~€5",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~10 min",price:"~€15"}],around:"Pisa is small and walkable. Trains link to Florence, Lucca and the coast cheaply.",family:"Under-4s free on trains; Florence is an easy ~1h family day trip by rail.",official:{name:"Trenitalia",url:"https://www.trenitalia.com/en.html"}},
  BGY:{options:[{mode:"🚌 Shuttle bus",detail:"to Milano Centrale",time:"~1h",price:"~€10",best:true},{mode:"🚕 Taxi",detail:"long trip to Milan",time:"~50 min",price:"~€110"}],around:"In Milan: Metro (4 lines), trams and buses (ATM). A single ~€2.20; 24h ~€7.60.",family:"Under-6s free on Milan transport; a day ticket covers the family for sightseeing.",official:{name:"ATM Milano",url:"https://www.atm.it/en"}},
  MXP:{options:[{mode:"🚆 Malpensa Express",detail:"to Cadorna/Centrale",time:"~50 min",price:"~€13",best:true},{mode:"🚌 Shuttle bus",detail:"to Centrale",time:"~60 min",price:"~€10"},{mode:"🚕 Taxi",detail:"to Milan",time:"~50 min",price:"~€110"}],around:"Metro, trams and buses (ATM). A single ~€2.20; 24h ~€7.60.",family:"Under-6s free; the Malpensa Express is buggy-friendly and step-free.",official:{name:"ATM Milano",url:"https://www.atm.it/en"}},
  SVQ:{options:[{mode:"🚌 Bus EA",detail:"to centre",time:"~35 min",price:"~€4",best:true},{mode:"🚕 Taxi (fixed)",detail:"to centre",time:"~20 min",price:"~€22"}],around:"Walkable historic centre; one tram line, buses, and a metro line. Bike hire (Sevici) is popular.",family:"Under-5s travel free; the centre is compact and pram-friendly.",official:{name:"TUSSAM Sevilla",url:"https://www.tussam.es/en"}},
  BIO:{options:[{mode:"🚌 Bizkaibus A3247",detail:"to centre",time:"~25 min",price:"~€3",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~20 min",price:"~€30"}],around:"Metro, trams and buses. The centre is compact; the Metro is clean and easy.",family:"Under-4s free; the Barik card is shareable across the family.",official:{name:"Metro Bilbao",url:"https://www.metrobilbao.eus/en"}},
  BOD:{options:[{mode:"🚌 30'Direct shuttle",detail:"to centre",time:"~30 min",price:"~€8",best:true},{mode:"🚊 Liane 1 + Tram A",detail:"cheaper combo",time:"~45 min",price:"~€1.80"},{mode:"🚕 Taxi",detail:"to centre",time:"~25 min",price:"~€35"}],around:"Trams (A–D) and buses (TBM); a single ~€1.80. The centre is very walkable.",family:"Under-5s free; a TBM day ticket covers tram + bus for the family.",official:{name:"TBM Bordeaux",url:"https://www.infotbm.com/en"}},
  LYS:{options:[{mode:"🚊 Rhônexpress",detail:"to centre",time:"~30 min",price:"~€16.30",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~30 min",price:"~€55"}],around:"Metro, trams, buses and funiculars (TCL); a single ~€2. Compact, walkable centre.",family:"Under-4s free on Rhônexpress; under-11s get a big discount.",official:{name:"TCL Lyon",url:"https://www.tcl.fr/en"}},
  TFS:{options:[{mode:"🚌 Bus (TITSA)",detail:"to resorts/Santa Cruz",time:"~30–60 min",price:"~€3–9",best:true},{mode:"🚕 Taxi / transfer",detail:"to resort",time:"~20–40 min",price:"~€30–60"}],around:"Buses (TITSA) cover the island; a tenmás card saves money. A car helps for exploring.",family:"Under-3s free on TITSA; the tenmás card is shareable for family trips.",official:{name:"TITSA Tenerife",url:"https://www.titsa.com/en"}},
  ACE:{options:[{mode:"🚌 Bus 22/23",detail:"to Arrecife",time:"~20 min",price:"~€1.40",best:true},{mode:"🚕 Taxi / transfer",detail:"to resort",time:"~15–30 min",price:"~€20–40"}],around:"Buses (Intercity Bus Lanzarote) link the resorts; renting a car is popular for the volcanic sights.",family:"Cheap buses and short distances make Lanzarote easy with kids; car seats via rental.",official:{name:"Lanzarote Buses",url:"https://www.arrecifebus.com/"}},
  PMI:{options:[{mode:"🚌 Bus A1",detail:"to centre",time:"~20 min",price:"~€5",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~15 min",price:"~€20"}],around:"Buses (EMT) and a metro line; the old town is walkable. Buses reach the island's beaches.",family:"Under-6s free on EMT buses; a rechargeable card is shareable.",official:{name:"EMT Palma",url:"https://www.emtpalma.cat/en"}},
  RHO:{options:[{mode:"🚌 Bus",detail:"to Rhodes Town/resorts",time:"~20–40 min",price:"~€2.40",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~20 min",price:"~€25"}],around:"Buses link the main resorts and Lindos; the medieval old town is pedestrian-only.",family:"The walled old town is magical for kids (but cobbled — a baby carrier beats a buggy).",official:{name:"Rhodes Buses (RODA)",url:"https://www.rodasamg.gr/"}},
  ZAD:{options:[{mode:"🚌 Liburnija shuttle",detail:"meets flights to centre",time:"~25 min",price:"~€4",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~15 min",price:"~€25"}],around:"Compact, walkable peninsula old town. Buses (Liburnija) reach the suburbs and beaches.",family:"The sea organ and old town are great for kids; distances are short.",official:{name:"Liburnija Zadar",url:"https://www.liburnija-zadar.hr/"}},
  ADB:{options:[{mode:"🚆 İZBAN train",detail:"to centre (İzmirimkart)",time:"~40 min",price:"Cheap",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~30 min",price:"~€20"}],around:"Metro, trams, buses and ferries (ESHOT). The bay ferries are a lovely way to get around.",family:"Buy an İzmirimkart to share across the family; ferries are a fun, cheap kid-pleaser.",official:{name:"İzmir Transport",url:"https://www.eshot.gov.tr/en"}},
  LHR:{options:[{mode:"🚇 Piccadilly line",detail:"to central London",time:"~50 min",price:"~£5.60",best:true},{mode:"🚆 Elizabeth line",detail:"faster to centre",time:"~35 min",price:"~£12"},{mode:"🚕 Taxi",detail:"to centre",time:"~50 min",price:"~£70"}],around:"The Tube, buses, Overground and DLR (TfL). Use contactless — fares cap daily (~£8.50 central).",family:"Up to 4 under-11s travel free with an adult on TfL — excellent for families.",official:{name:"Transport for London",url:"https://tfl.gov.uk/"}},
  LGW:{options:[{mode:"🚆 Thameslink/Southern",detail:"to centre (cheaper)",time:"~30 min",price:"~£12",best:true},{mode:"🚆 Gatwick Express",detail:"to Victoria",time:"~30 min",price:"~£20"},{mode:"🚕 Taxi",detail:"to centre",time:"~70 min",price:"~£100"}],around:"In London: Tube, buses, Overground (TfL). Contactless with daily fare caps is best.",family:"Up to 4 under-11s travel free with an adult on TfL.",official:{name:"Transport for London",url:"https://tfl.gov.uk/"}},
  STN:{options:[{mode:"🚌 National Express",detail:"to centre (cheaper)",time:"~70 min",price:"~£12",best:true},{mode:"🚆 Stansted Express",detail:"to Liverpool St",time:"~50 min",price:"~£20"}],around:"In London: Tube, buses, Overground (TfL). Contactless with daily fare caps is best.",family:"Up to 4 under-11s travel free with an adult on TfL.",official:{name:"Transport for London",url:"https://tfl.gov.uk/"}},
  LTN:{options:[{mode:"🚆 Shuttle + Thameslink",detail:"to central London",time:"~45 min",price:"~£16",best:true},{mode:"🚌 Coach",detail:"to centre (cheaper)",time:"~70 min",price:"~£11"}],around:"In London: Tube, buses, Overground (TfL). Contactless with daily fare caps is best.",family:"Up to 4 under-11s travel free with an adult on TfL.",official:{name:"Transport for London",url:"https://tfl.gov.uk/"}},
  BRS:{options:[{mode:"🚌 Bristol Flyer A1",detail:"to centre & Temple Meads",time:"~30 min",price:"~£8",best:true},{mode:"🚕 Taxi",detail:"to centre",time:"~25 min",price:"~£30"}],around:"Buses (First) cover the city; the centre and harbourside are walkable.",family:"Under-5s travel free on First buses; a family day ticket is available.",official:{name:"First Bus Bristol",url:"https://www.firstbus.co.uk/bristol-bath-and-west"}},
};
function cityTransport(code){ return CITY_TRANSPORT[code] || null; }

function addDaysISO(ds, n){ const d=new Date(ds+"T12:00:00"); d.setDate(d.getDate()+n); return d.toISOString().split("T")[0]; }

async function openDetail(d, dep, ret, groupSize, cacheTravellers, planner = false){
  window._guide = { d: {...d}, dep, ret, groupSize, cacheTravellers, planner };
  window._gSel = { out: null, ret: null };   // live-grid leg selections
  const overlay = document.getElementById("detailOverlay");
  const body = document.getElementById("detailBody");
  // Shareable URL for this guide; in-guide re-renders replace instead of stack
  try {
    const url = `?dest=${encodeURIComponent(d.code)}`;
    if (history.state && history.state.hcGuide) history.replaceState({ hcGuide: d.code }, "", url);
    else history.pushState({ hcGuide: d.code }, "", url);
  } catch (e) {}
  window.scrollTo(0,0);
  overlay.classList.add("open");
  document.body.style.overflow = "hidden";

  cacheTravellers = cacheTravellers || 4;
  groupSize = groupSize || 1;

  // Resolve which airport this deal flies from
  const flightOrigin = d.origin_airport
    || (selectedAirport === "BEST" ? "ORK" : (selectedAirport || "ORK"));
  const hasPrice = d.price != null;
  const perP = hasPrice ? Math.round(d.price / cacheTravellers) : null;
  const groupTot = hasPrice ? perP * groupSize : null;
  const liveFlightUrl = aviasalesUrl(flightOrigin, d.code, dep, ret, Math.max(1, selAdults));
  const groupLbl = travellerLabel();
  const flightPax = `${selAdults}+adults${selChildren>0?'+'+selChildren+'+children':''}`;
  const nights = Math.round((new Date(ret) - new Date(dep)) / 86400000);
  const costs = cityCosts(d.code);
  const depFmt = new Date(dep+"T12:00:00").toLocaleDateString("en-IE",{weekday:"long",day:"numeric",month:"long"});
  const retFmt = new Date(ret+"T12:00:00").toLocaleDateString("en-IE",{weekday:"long",day:"numeric",month:"long"});

  // Skeleton with sections; async parts fill in after
  body.innerHTML = `
    <div class="dt-hero" id="dtHero">
      <div class="dt-hero-text">
        <div class="dt-hero-eyebrow">${flightOrigin === 'DUB' ? 'Dublin (DUB)' : 'Cork (ORK)'} → ${d.code} · ${nights} night${nights>1?'s':''}</div>
        <h2 class="dt-city-title">${d.city}</h2>
        <div class="dt-country">${d.country}</div>
      </div>
    </div>
    <div class="dt-pricestrip">
      <div class="dt-priceitem"><div class="lbl">Per person</div><div class="val" id="dtPP">${hasPrice ? '€'+perP : '<a href="'+liveFlightUrl+'" target="_blank" rel="noopener noreferrer sponsored" style="font-size:15px">Check live →</a>'}</div></div>
      <div class="dt-priceitem"><div class="lbl">${groupLbl}</div><div class="val" id="dtGroupTot">${hasPrice ? '€'+groupTot : '—'}</div></div>
      <div class="dt-priceitem"><div class="lbl">Flight</div><div class="val">${d.stops==null ? '<small>' + (dep && ret ? new Date(dep+"T12:00:00").toLocaleDateString("en-IE",{day:"numeric",month:"short"}) + " – " + new Date(ret+"T12:00:00").toLocaleDateString("en-IE",{day:"numeric",month:"short"}) : "your dates") + '</small>' : (d.stops===0?'Direct':d.stops+' stop'+(d.stops>1?'s':'')) + ' <small>'+(d.total_time||'')+'</small>'}</div></div>
      <div class="dt-priceitem"><div class="lbl">Airline</div><div class="val" style="font-size:16px">${d.airlines||'—'}</div></div>
    </div>

    <div id="dtAltAirport"></div>

    <div class="rainsun" style="margin:0 -0px"></div>

    ${planner ? `
    <div class="dt-section" style="padding-top:16px">
      <h2>📅 Your dates</h2>
      <div class="dt-sub">Change the dates and the whole trip — flights, hotels, costs — updates.</div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
        <button type="button" class="pd-field" id="gdDatesBtn" style="flex:0 1 320px;min-width:210px" onclick="pdToggle('guide')">
          <span class="pd-text">Choose your dates</span><span class="pd-ic">📅</span>
        </button>
        <input type="hidden" id="dtDep" value="${dep}"><input type="hidden" id="dtRet" value="${ret}">
        <button class="hc-signup-btn" onclick="applyGuideDates()">Update trip</button>
      </div>
      <div class="pd-panel" id="gdCalPanel" style="display:none"></div>
    </div>

    <div class="dt-section">
      <h2>✈️ Flights for your dates</h2>
      <div class="dt-sub">Pick a departure and a return below — real prices per person, book each leg directly.</div>
      <div id="dtLive"><span class="dt-loading">Preparing flight search…</span></div>
      <a href="${liveFlightUrl}" target="_blank" rel="noopener noreferrer sponsored"
         onclick="track('flight_click',{source:'guide_aviasales_more',dest:'${d.code}'})"
         style="display:flex;align-items:center;gap:12px;margin-top:14px;padding:12px 16px;border:1px dashed var(--gold);border-radius:12px;background:var(--cream);text-decoration:none;color:var(--ink)">
        <span style="font-size:22px;flex:none">🔀</span>
        <span style="flex:1;min-width:0">
          <span style="display:block;font-weight:700;font-size:14px">Not seeing the right flight?</span>
          <span style="display:block;font-size:12px;color:var(--muted)">Aviasales compares 100+ airlines — including connecting flights and different carriers, sometimes cheaper.</span>
        </span>
        <span style="flex:none;font-weight:700;color:var(--gold);font-size:13px;white-space:nowrap">Compare all →</span>
      </a>
    </div>

` : ""}

    <div class="dt-section dt-complete">
      <h2>🧳 Complete the trip</h2>
      <div class="dt-sub">Everything for ${nights} night${nights>1?'s':''} in ${d.city} — tap any line to compare live prices.</div>
      <div class="trip-calc">
        <a class="tc-row tc-flight" id="tcFlightRow" href="${hasPrice ? flightUrl(d.airlines, flightOrigin, d.code, dep, ret, selAdults, selChildren) : liveFlightUrl}" target="_blank" rel="noopener noreferrer${hasPrice ? '' : ' sponsored'}">
          <span class="tc-ic">✈️</span><span class="tc-lbl" id="tcFlightLbl">Flights · ${groupLbl}${hasPrice ? '' : ' · live on Aviasales'}</span>
          <span class="tc-val" id="tcFlightVal">${hasPrice ? '€'+groupTot : 'Check →'}</span>
        </a>
        <a class="tc-row" href="${hotelUrl(d.city, dep, ret)}" target="_blank" rel="noopener noreferrer">
          <span class="tc-ic">🏨</span><span class="tc-lbl">${nights} night${nights>1?'s':''} hotel <span class="tc-brand">${BRAND.booking}</span></span>
          <span class="tc-val">≈ €${costs.hotel*nights}</span>
        </a>
        <a class="tc-row" href="${airbnbUrl(d.city, dep, ret)}" target="_blank" rel="noopener noreferrer">
          <span class="tc-ic">🏠</span><span class="tc-lbl">or ${nights} night${nights>1?'s':''} on <span class="tc-brand">${BRAND.airbnb}</span></span>
          <span class="tc-val">≈ €${costs.airbnb*nights}</span>
        </a>
        <a class="tc-row" href="${carUrlDiscover(d.city, dep, ret)}" target="_blank" rel="noopener noreferrer">
          <span class="tc-ic">🚗</span><span class="tc-lbl">Optional: car hire <span class="tc-brand">${BRAND.discovercars}</span> <small style="color:var(--muted)">(not in total)</small></span>
          <span class="tc-val">Check →</span>
        </a>
        <div class="tc-total">
          <span class="tc-lbl">Estimated trip total <small>(flights + hotel)</small></span>
          <span class="tc-val">~ €${(hasPrice ? groupTot : 0) + costs.hotel*nights}${hasPrice ? '' : ' + flights'}</span>
        </div>
      </div>
      <div class="tc-note">Estimates from typical ${d.city} prices — live prices shown when you tap through. Book each part with the provider directly.</div>
    </div>

    <div class="dt-section" id="dtTimelineSection" style="display:none">
      <h2>🗓️ Every scanned date for ${d.city} — cheapest first-glance planner</h2>
      <div class="dt-sub">From our automatic scans of the next weeks — tap any row to see the full trip on those dates.</div>
      <div id="dtTimeline"></div>
    </div>

    ${hasPrice ? `<div class="dt-section">
      <h2>✈️ Your flights</h2>
      <div class="dt-sub">${depFmt} → ${retFmt}</div>
      ${d.is_cheaper && d.hist_typical ? `<div class="dt-cheaper-note">↓ This fare is cheaper than usual for ${d.city} — typically around €${Math.round(d.hist_typical/cacheTravellers)} per person.</div>` : ''}
      ${d.midweek_saver && d.weekend_price ? `<div class="dt-cheaper-note">💡 Midweek saver — these ${new Date(dep+"T12:00:00").toLocaleDateString("en-IE",{weekday:"long"})} dates cost €${Math.round((d.weekend_price - d.price)/cacheTravellers)} less per person than the same trip on weekend dates.</div>` : ''}
      <div class="dt-leg">
        <div class="dt-leg-dir">OUT</div>
        <div class="dt-leg-main">
          <div class="dt-leg-route">Cork (ORK) → ${d.city} (${d.code})</div>
          <div class="dt-leg-info">${depFmt} · ${d.stops===0?'Direct':d.stops+' stop'+(d.stops>1?'s':'')} · ${d.total_time||''} · ${d.airlines||''}</div>
        </div>
      </div>
      <div class="dt-leg">
        <div class="dt-leg-dir">RETURN</div>
        <div class="dt-leg-main">
          <div class="dt-leg-route">${d.city} (${d.code}) → Cork (ORK)</div>
          <div class="dt-leg-info">${retFmt} · same airline · price shown for ${groupLbl} (estimated from per-person fare)</div>
        </div>
      </div>
      <div style="margin-top:18px">
        <a class="deal-book primary" style="display:inline-flex;padding:12px 24px;border-radius:10px" href="${flightUrl(d.airlines, flightOrigin||'ORK', d.code, dep, ret, selAdults, selChildren)}" target="_blank" rel="noopener noreferrer">${flightBtnLabel(d.airlines, 'Search flights')} →</a>
      </div>
    </div>` : ""}

    <div class="dt-section">
      <h2>🌤️ Weather around your trip</h2>
      <div class="dt-sub" id="dtWxSub">Loading forecast…</div>
      <div class="dt-wx-grid" id="dtWxGrid"></div>
    </div>

    <div class="dt-section">
      <h2>📍 About ${d.city}</h2>
      <p id="dtAbout" class="dt-loading">Loading city guide…</p>
    </div>

    <div class="dt-section">
      <h2>🎟️ What to see</h2>
      <div class="dt-sub">Top sights near the city centre</div>
      <div class="dt-attractions" id="dtAttractions"><span class="dt-loading">Finding attractions…</span></div>
    </div>

    <div class="dt-section">
      <h2>🍽️ Where to eat</h2>
      <div class="dt-sub">The most popular spots in ${d.city} — tap any for directions & booking</div>
      <div class="dt-rest" id="dtRestaurants"><span class="dt-loading" style="display:block;padding:14px 16px">Finding the good tables…</span></div>
    </div>

    <div class="dt-section">
      <h2>💶 Typical costs</h2>
      <div class="dt-sub">Rough per-person guide to help you budget</div>
      <div class="dt-cost-grid">
        <div class="dt-cost"><div class="c-ic">🍽️</div><div class="c-lbl">Meal out</div><div class="c-val">€${costs.meal}</div></div>
        <div class="dt-cost"><div class="c-ic">☕</div><div class="c-lbl">Coffee</div><div class="c-val">€${costs.coffee.toFixed(2)}</div></div>
        <div class="dt-cost"><div class="c-ic">🍺</div><div class="c-lbl">Beer</div><div class="c-val">€${costs.beer.toFixed(2)}</div></div>
        <div class="dt-cost"><div class="c-ic">🚌</div><div class="c-lbl">Transit ticket</div><div class="c-val">€${costs.transit.toFixed(2)}</div></div>
        <div class="dt-cost"><div class="c-ic">🏛️</div><div class="c-lbl">Attraction entry</div><div class="c-val">€${costs.attraction}</div></div>
      </div>
    </div>

    <div class="dt-section">
      <h2>🎉 What's on during your trip</h2>
      <div class="dt-sub">Concerts, sport &amp; major ticketed events around your dates</div>
      <div id="dtEvents"><span class="dt-loading">Checking for events…</span></div>
    </div>

    <div class="dt-section">
      <h2>🚍 Getting around</h2>
      <div class="dt-sub">Airport transfer &amp; public transport</div>
      <div id="dtTransport"></div>
    </div>

    <div class="dt-section">
      <h2>🛏️ Where to stay</h2>
      <div class="dt-sub">Typical nightly prices for ${nights} night${nights>1?'s':''}. Tap to see live options &amp; book.</div>
      <div class="dt-stay-cards">
        <div class="dt-stay">
          <div class="s-logo">${BRAND.booking}</div>
          <div class="s-price">typically <b>€${costs.hotel}</b> / night<br><span style="font-size:11px">≈ €${costs.hotel*nights} for ${nights} night${nights>1?'s':''}</span></div>
          <a href="${hotelUrl(d.city, dep, ret)}" target="_blank" rel="noopener">Search hotels →</a>
        </div>
        <div class="dt-stay">
          <div class="s-logo">${BRAND.airbnb}</div>
          <div class="s-price">typically <b>€${costs.airbnb}</b> / night<br><span style="font-size:11px">≈ €${costs.airbnb*nights} for ${nights} night${nights>1?'s':''}</span></div>
          <a href="${airbnbUrl(d.city, dep, ret)}" target="_blank" rel="noopener">Search Airbnb →</a>
        </div>
      </div>
      <p style="font-size:12px;color:var(--muted);margin-top:14px">Nightly prices are typical estimates for a family room/place. Live prices and photos are on Booking.com and Airbnb.</p>
    </div>

    <div class="dt-section">
      <h2>🚗 Hire a car</h2>
      <div class="dt-sub">Compare prices across these trusted car-hire sites — pre-filled with ${d.city} and your dates</div>
      <div class="dt-car-cards">
        <a class="dt-car" href="${carUrlDiscover(d.city, dep, ret)}" target="_blank" rel="noopener">
          <div class="dt-car-name">${BRAND.discovercars}</div>
          <div class="dt-car-sub">Compare 650+ suppliers · free cancellation</div>
          <div class="dt-car-go">Search cars →</div>
        </a>
        <a class="dt-car" href="${carUrlRentalcars(d.city, dep, ret)}" target="_blank" rel="noopener">
          <div class="dt-car-name">${BRAND.rentalcars}</div>
          <div class="dt-car-sub">Part of Booking.com · Avis, Hertz, Enterprise &amp; more</div>
          <div class="dt-car-go">Search cars →</div>
        </a>
        <a class="dt-car" href="${carUrlAutoEurope(d.city, dep, ret)}" target="_blank" rel="noopener">
          <div class="dt-car-name">${BRAND.autoeurope}</div>
          <div class="dt-car-sub">Europe specialist · 180+ countries</div>
          <div class="dt-car-go">Search cars →</div>
        </a>
      </div>
    </div>
  `;

  // Unknown city (beyond the 26 curated destinations)? Geocode it once so
  // weather, restaurants and the map light up for ANY city.
  if (!CITY_COORDS[d.code]) {
    try {
      const g = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(d.city)}&count=1&language=en`);
      const gj = await g.json();
      const hit = gj.results && gj.results[0];
      if (hit) CITY_COORDS[d.code] = [hit.latitude, hit.longitude];
    } catch(e) {}
  }

  // Hero photo
  fetchCityPhoto(d.code, d.city, true).then(url => {
    if (!url) return;
    const hero = document.getElementById("dtHero");
    const img = new Image(); img.alt = d.city;
    img.onload = () => hero.insertBefore(img, hero.firstChild);
    img.src = url;
  });

  // Weather: 5 days centred on departure
  loadDetailWeather(d.code, dep);
  // City description + attractions
  loadCityAbout(d.code, d.city);
  loadAttractions(d.code);
  loadRestaurants(d.code);
  track("view_destination", { destination: d.city, origin: flightOrigin });
  loadTransport(d.code);
  loadEvents(d.code, dep, ret, d.city);
  guideTimeline(d);
  guideAltAirportBanner(d, dep, ret);
  pdSeed('guide', dep, ret);
  if (planner) {
    guideLiveInit(d, dep, ret, hasPrice);
  }
}

// "Cheaper from the other airport" banner — pure cache read, zero API cost.
// If the airport you're NOT viewing is cheaper for this destination, show a
// tappable strip near the top so the saving isn't buried in the timeline.
function guideAltAirportBanner(d, dep, ret){
  const box = document.getElementById("dtAltAirport");
  if (!box || !cachedDeals) return;
  box.innerHTML = "";
  const here = d.origin_airport || "DUB";
  const other = here === "ORK" ? "DUB" : "ORK";
  const c = cheapestByAirport(d.code);
  const hereBest = c[here], otherBest = c[other];
  // Only worth showing when the other airport is scanned AND cheaper than here.
  if (!otherBest) return;
  if (hereBest && otherBest.pp >= hereBest.pp) return;
  const save = hereBest ? (hereBest.pp - otherBest.pp) : null;
  const otherName = other === "ORK" ? "Cork" : "Dublin";
  const g = window._guide || {};
  const ad = otherBest.deal, ab = otherBest.board;
  const dealJson = JSON.stringify({...ad, origin_airport: other}).replace(/'/g, "&#39;");
  box.innerHTML = `
    <div class="alt-airport-banner" role="button" tabindex="0"
         onclick='openDetail(${dealJson}, "${ad.depart_date || ab.depart_date}", "${ad.return_date || ab.return_date}", ${g.groupSize || 1}, ${_cacheTrav()}, ${g.planner === true})'>
      <span class="aab-plane">✈</span>
      <span class="aab-text">${save ? `<b>${otherName} is €${save} cheaper</b> for this trip` : `<b>Also flies from ${otherName}</b>`} — from <b>€${otherBest.pp}pp</b> on scanned dates</span>
      <span class="aab-cta">See ${otherName} dates →</span>
    </div>`;
}

function closeDetail(){
  if (history.state && history.state.hcGuide) { history.back(); return; }
  document.getElementById("detailOverlay").classList.remove("open");
  document.body.style.overflow = "";
}
document.addEventListener("keydown", e => { if (e.key === "Escape") closeDetail(); });

function cityTransportName(code){
  // Resolve a human city name for transfer links (reuse the events city map)
  return (typeof TM_CITY !== "undefined" && TM_CITY[code]) || code;
}
function loadTransport(code){
  const el = document.getElementById("dtTransport");
  if (!el) return;
  const t = cityTransport(code);
  if (!t){ el.innerHTML = "<p style='color:var(--muted)'>Transport details coming soon for this city.</p>"; return; }

  const officialUrl = t.official ? t.official.url : null;
  const tCity = (cityTransportName(code) || code);
  const opts = (t.options||[]).map(o => {
    const isTaxi = /taxi|transfer|shuttle/i.test(o.mode);
    const href = isTaxi ? transferUrl(tCity) : (officialUrl || "#");
    const cta = isTaxi ? "Book a transfer →" : "Tickets & times →";
    return `
    <a class="dt-tr-opt${o.best?' best':''}" href="${href}" target="_blank" rel="noopener">
      ${o.best?'<span class="dt-tr-badge">Best pick</span>':''}
      <div class="dt-tr-mode">${o.mode}</div>
      <div class="dt-tr-detail">${o.detail}</div>
      <div class="dt-tr-stats"><span>🕒 ${o.time}</span><span>💶 ${o.price}</span></div>
      <div class="dt-tr-cta">${cta}</div>
    </a>`;
  }).join("");

  // Map: a clean link out to Google Maps (the embed added little)
  const coords = CITY_COORDS[code];
  let mapHtml = "";
  if (coords){
    const [lat, lon] = coords;
    mapHtml = `
      <a class="dt-tr-official" style="margin-top:12px"
         href="https://www.google.com/maps/@${lat},${lon},13z" target="_blank" rel="noopener">
         📍 Open ${cityTransportName(code) || "the city"} in Google Maps →</a>`;
  }

  el.innerHTML = `
    <div class="dt-tr-block">
      <div class="dt-tr-h2">✈️ → 🏙️ From the airport</div>
      <div class="dt-tr-opts">${opts}</div>
    </div>
    <div class="dt-tr-item">
      <div class="dt-tr-ic">🚇</div>
      <div><div class="dt-tr-h">Getting around the city</div><div class="dt-tr-b">${t.around}</div></div>
    </div>
    ${t.family?`<div class="dt-tr-item dt-tr-fam">
      <div class="dt-tr-ic">👨‍👩‍👧‍👦</div>
      <div><div class="dt-tr-h">Family tip</div><div class="dt-tr-b">${t.family}</div></div>
    </div>`:''}
    ${mapHtml}
  `;
}

async function loadEvents(code, dep, ret, cityName){
  const el = document.getElementById("dtEvents");
  if (!el) return;
  const city = TM_CITY[code] || cityName;
  if (!BACKEND_URL){
    el.innerHTML = `<p style="color:var(--muted)">Live events feed isn't switched on yet.</p>`;
    return;
  }
  if (!city){ el.innerHTML = "<p style='color:var(--muted)'>No event listings for this city.</p>"; return; }
  try{
    // Start from the second day of the trip — arrival day (often a Friday) is
    // usually travel/settling-in, so events default to the first full day.
    const secondDay = addDaysISO(dep, 1);
    // Don't go past the return day; if the trip is only 1 night, fall back to dep.
    const eventStart = (new Date(secondDay) <= new Date(ret)) ? secondDay : dep;
    const start = eventStart + "T00:00:00Z";
    const end = ret + "T23:59:59Z";
    const url = `${BACKEND_URL}/api/events?city=${encodeURIComponent(city)}&start=${start}&end=${end}`;
    const r = await fetch(url);
    const events = await r.json();
    if (!Array.isArray(events) || !events.length){
      el.innerHTML = `<p style="color:var(--muted)">No major ticketed events found for these dates. Local festivals and markets may still be on — worth checking the city's tourism site closer to your trip.</p>`;
      return;
    }
    el.innerHTML = `<div class="dt-events">` + events.map(ev => {
      const date = ev.date
        ? new Date(ev.date+"T12:00:00").toLocaleDateString("en-IE",{weekday:"short",day:"numeric",month:"short"})
        : "";
      return `<a class="dt-event" href="${ev.url}" target="_blank" rel="noopener">
        ${ev.image?`<img class="dt-event-img" src="${ev.image}" alt="${(ev.name||"").replace(/"/g,'&quot;')}" loading="lazy">`:""}
        <span class="dt-event-body">
          <span class="dt-event-date">${date}</span>
          <span class="dt-event-name">${ev.name}</span>
          ${ev.venue?`<span class="dt-event-venue">${ev.venue}</span>`:""}
        </span>
      </a>`;
    }).join("") + `</div>
    <p style="font-size:12px;color:var(--muted);margin-top:12px">Events from Ticketmaster — concerts, sport &amp; major venues. Local festivals may not appear.</p>`;
  }catch(e){
    el.innerHTML = `<p style="color:var(--muted)">Couldn't load events right now. You can check Ticketmaster directly for ${city}.</p>`;
  }
}

async function loadDetailWeather(code, dep){
  const grid = document.getElementById("dtWxGrid");
  const sub = document.getElementById("dtWxSub");
  const dates = [-1,0,1,2,3].map(o => addDaysISO(dep, o));
  let anyTypical = false, html = "";
  for (const ds of dates){
    const w = await getWeather(code, ds);
    const lbl = new Date(ds+"T12:00:00").toLocaleDateString("en-IE",{weekday:"short",day:"numeric",month:"short"});
    if (w){
      if (w.typical) anyTypical = true;
      const [ic] = weatherIcon(w.code);
      html += `<div class="dt-wx-day"><div class="d">${lbl}</div><div class="ic">${ic}</div><div class="t">${w.tmax}° <small>/ ${w.tmin}°</small></div></div>`;
    } else {
      html += `<div class="dt-wx-day"><div class="d">${lbl}</div><div class="ic">·</div><div class="t">—</div></div>`;
    }
  }
  grid.innerHTML = html;
  sub.textContent = anyTypical ? "Typical conditions for these dates (based on recent years)" : "Forecast for your travel dates";
}

async function loadCityAbout(code, city){
  const el = document.getElementById("dtAbout");
  const title = CITY_WIKI[code] || city;
  try{
    const r = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${title}`);
    const d = await r.json();
    el.classList.remove("dt-loading");
    el.textContent = d.extract || "No description available.";
  }catch(e){ el.classList.remove("dt-loading"); el.textContent = "Could not load city information."; }
}


// ── Where to eat — proxied through the hc-live-search Worker (/api/places)
// so the Google Places key stays server-side and is never shipped to the browser.

async function loadRestaurants(code){
  const box = document.getElementById("dtRestaurants");
  if (!box) return;
  const coords = CITY_COORDS[code];
  if (!coords || !BACKEND_URL){ box.parentElement.style.display = "none"; return; }

  // 7-day localStorage cache — one API call per city per visitor per week
  const ck = "hc_rest2_" + code;   // v2: includes photos + cuisine
  let places = null;
  try{
    const cached = JSON.parse(localStorage.getItem(ck) || "null");
    if (cached && Date.now() - cached.ts < 7*24*3600*1000) places = cached.data;
  }catch(e){}

  if (!places){
    try{
      const url = `${BACKEND_URL}/api/places?kind=restaurant&lat=${coords[0]}&lng=${coords[1]}`;
      const r = await fetch(url);
      if (!r.ok) throw new Error("HTTP " + r.status);
      places = await r.json();
      if (!Array.isArray(places)) throw new Error("bad payload");
      try{ localStorage.setItem(ck, JSON.stringify({ts: Date.now(), data: places})); }catch(e){}
    }catch(e){
      // Honest graceful fallback: link out instead of an empty error box
      box.innerHTML = `<a class="rest-row" target="_blank" rel="noopener"
        href="https://www.google.com/maps/search/restaurants/@${coords[0]},${coords[1]},14z">
        <span class="rest-name">Browse the best restaurants on Google Maps →</span></a>`;
      return;
    }
  }
  if (!places.length){ box.parentElement.style.display = "none"; return; }

  const VISIBLE = 3;
  box.innerHTML = places.map((p, i) => {
    const img = (p.photo && i < 6)
      ? `<img class="rest-photo" src="${BACKEND_URL}/api/places/photo?name=${encodeURIComponent(p.photo)}&w=200" alt="${(p.name||"").replace(/"/g,'&quot;')}" loading="lazy">`
      : `<span class="rest-photo rest-photo-empty">🍽️</span>`;
    return `
    <a class="rest-row${i >= VISIBLE ? ' rest-hidden' : ''}" href="${p.url}" target="_blank" rel="noopener">
      ${img}
      <span class="rest-body">
        <span class="rest-name">${p.name}</span>
        <span class="rest-sub">${p.cuisine || "Restaurant"}${p.price ? " · " + p.price : ""}</span>
      </span>
      <span class="rest-meta">${p.rating ? `<span class="rest-star">★</span> <b>${p.rating.toFixed(1)}</b><br><small>${p.count.toLocaleString()} reviews</small>` : ""}</span>
    </a>`;}).join("") +
    (places.length > VISIBLE
      ? `<button class="rest-more" onclick="this.parentElement.querySelectorAll('.rest-hidden').forEach(e=>e.classList.remove('rest-hidden'));this.remove()">Show ${places.length - VISIBLE} more restaurants ↓</button>`
      : "");
}

// Fallback sights for cities beyond the curated 26: top-rated attractions
// from Google Places, proxied through the same Worker, cached 7 days.
async function loadAttractionsFromPlaces(code, box){
  const coords = CITY_COORDS[code];
  if (!coords || !BACKEND_URL){
    box.innerHTML = "<span class='dt-loading'>City guide coming soon.</span>"; return;
  }
  const ck = "hc_attr_" + code;
  let spots = null;
  try{
    const cached = JSON.parse(localStorage.getItem(ck) || "null");
    if (cached && Date.now() - cached.ts < 7*24*3600*1000) spots = cached.data;
  }catch(e){}

  if (!spots){
    try{
      const url = `${BACKEND_URL}/api/places?kind=attraction&lat=${coords[0]}&lng=${coords[1]}`;
      const r = await fetch(url);
      if (!r.ok) throw new Error("HTTP " + r.status);
      spots = await r.json();
      if (!Array.isArray(spots)) throw new Error("bad payload");
      try{ localStorage.setItem(ck, JSON.stringify({ts: Date.now(), data: spots})); }catch(e){}
    }catch(e){
      box.innerHTML = "<span class='dt-loading'>City guide coming soon.</span>"; return;
    }
  }

  if (!spots || !spots.length){
    box.innerHTML = "<span class='dt-loading'>City guide coming soon.</span>"; return;
  }

  box.innerHTML = spots.slice(0, 6).map((s, i) => {
    const imgHtml = (s.photo && i < 4)
      ? `<img class="dt-attraction-img" src="${BACKEND_URL}/api/places/photo?name=${encodeURIComponent(s.photo)}&w=400" alt="${(s.name||"").replace(/"/g,'&quot;')}" loading="lazy">`
      : "";   // no photo → compact card, no empty block
    return `
    <div class="dt-attraction">
      ${imgHtml}
      <div class="dt-attraction-body">
        <div class="a-name"><a href="${s.url}" target="_blank" rel="noopener" style="color:inherit;text-decoration:none">${s.name}</a></div>
        <div class="a-desc">${s.rating ? '★ ' + s.rating + ' · ' + s.count.toLocaleString() + ' reviews' : 'Popular spot'}</div>
      </div>
    </div>`;}).join("");
}

async function loadAttractions(code){
  const box = document.getElementById("dtAttractions");
  const sights = CITY_SIGHTS[code];
  if (!sights || !sights.length){
    loadAttractionsFromPlaces(code, box); return;
  }
  // Render curated sights immediately (text first, photos fill in)
  box.innerHTML = sights.map(([wiki, name, blurb], i) => `
    <div class="dt-attraction">
      <span class="dt-attraction-img" id="sight-${code}-${i}"
            style="display:flex;align-items:center;justify-content:center;color:var(--gold)">✦</span>
      <div class="dt-attraction-body">
        <div class="a-name">${name}</div>
        <div class="a-desc">${blurb}</div>
      </div>
    </div>`).join("");
  // Fetch each sight's photo from its own Wikipedia page (reliable, title-based)
  sights.forEach(async ([wiki], i) => {
    try{
      const r = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(wiki)}`);
      const d = await r.json();
      const url = (d.thumbnail && d.thumbnail.source) ||
                  (d.originalimage && d.originalimage.source) || "";
      const el = document.getElementById(`sight-${code}-${i}`);
      if (url && el){
        el.style.backgroundImage = `url('${url}')`;
        el.style.color = "transparent";
      }
    }catch(e){/* keep the ✦ placeholder */}
  });
}

// ── Dev/staging version badge ───────────────────────────────────────────────
// Shows a small fixed badge with the current APP_VERSION on any domain that
// is NOT the production site. Never renders on holidaychasers.ie.
function showDevBadge(){
  if (location.hostname === "holidaychasers.ie" || location.hostname === "www.holidaychasers.ie") return;
  const el = document.createElement("div");
  el.textContent = APP_VERSION;
  el.style.cssText = "position:fixed;left:8px;bottom:8px;z-index:99999;"
    + "background:#111;color:#fff;font:12px/1.4 -apple-system,sans-serif;"
    + "padding:6px 10px;border-radius:6px;opacity:0.85;pointer-events:none;"
    + "max-width:70vw;box-shadow:0 2px 8px rgba(0,0,0,.3)";
  document.body.appendChild(el);
}

// ── Init ─────────────────────────────────────────────────────────────────────
populateSelects();
loadDeals();
checkBackend();
showDevBadge();
// Re-check backend every 30s
setInterval(checkBackend, 30000);
