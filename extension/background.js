const BASE = "https://holidaychasers.ie/";
chrome.runtime.onMessage.addListener((msg, _s, send) => {
  if (msg.type === "poster") {
    fetch(BASE + msg.path + "?t=" + Date.now()).then(r => r.blob()).then(b => {
      const fr = new FileReader();
      fr.onload = () => send({ ok: true, dataUrl: fr.result });
      fr.readAsDataURL(b);
    }).catch(e => send({ ok: false, error: String(e) }));
    return true;
  }
});
