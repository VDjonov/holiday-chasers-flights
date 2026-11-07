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
