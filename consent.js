// Consent-gated GA4, shared by the homepage and destination pages.
// Do not load the homepage app.js on destination pages — this is the whole loader.
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
  var bar = document.getElementById("consentBar");
  if (bar) bar.classList.remove("show");
  if (accepted) loadGA();
}

(function initConsent(){
  let c = null;
  try{ c = localStorage.getItem("hc_consent"); }catch(e){}
  if (c === "yes") loadGA();
  else if (c === null){
    window.addEventListener("load", function(){
      var bar = document.getElementById("consentBar");
      if (bar) bar.classList.add("show");
    });
  }
})();

// Click events for pages that do not load app.js (the destination pages).
// app.js already records these same event names on the homepage — if its
// track() is present, do nothing here so a homepage click is not sent twice.
// Parameter names match app.js: destination + label from the delegated
// listener, and source + dest (IATA code) from the explicit flight_click calls.
// origin is included only when the link carries data-hc-origin (DUB/ORK).
const HC_CLICK_EVENTS = {
  flight_click: true,
  stay_click: true,
  trip_calc_click: true,
  restaurant_click: true
};

function hcTrackDestinationClick(e){
  if (location.hostname !== "holidaychasers.ie") return;
  if (typeof window.track === "function") return;
  if (!window.gtag) return;
  try { if (localStorage.getItem("hc_consent") !== "yes") return; } catch (err) { return; }
  // A click on the link text can target a text node, which has no closest().
  const raw = e.target;
  const el = raw && raw.nodeType === 1 ? raw : (raw && raw.parentElement);
  const a = el && el.closest ? el.closest("a[data-hc-event]") : null;
  if (!a) return;
  const name = a.getAttribute("data-hc-event");
  if (!HC_CLICK_EVENTS[name]) return;
  const params = {};
  const destination = a.getAttribute("data-hc-destination");
  const dest = a.getAttribute("data-hc-dest");
  const source = a.getAttribute("data-hc-source");
  const origin = a.getAttribute("data-hc-origin");
  const out = a.getAttribute("data-hc-out");
  const ret = a.getAttribute("data-hc-ret");
  if (destination) params.destination = destination;
  if (dest) params.dest = dest;
  if (source) params.source = source;
  if (origin) params.origin = origin;
  if (out && /^\d{4}-\d{2}-\d{2}$/.test(out)) params.out = out;
  if (ret && /^\d{4}-\d{2}-\d{2}$/.test(ret)) params.ret = ret;
  const label = (a.textContent || "").trim().slice(0, 40);
  if (label) params.label = label;
  gtag("event", name, params);
}

document.addEventListener("click", hcTrackDestinationClick, { passive: true });
