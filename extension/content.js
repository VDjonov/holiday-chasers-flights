// Shows a gold button on Facebook when a post is chosen. Click it with the composer open.
(async () => {
  const { pending } = await chrome.storage.local.get("pending");
  if (!pending) return;
  const box = document.createElement("div");
  box.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:999999;background:#0A1B2E;color:#E4D2A0;padding:12px;border-radius:10px;font:13px system-ui;max-width:260px;box-shadow:0 4px 16px #0006";
  box.innerHTML = `<div style="font-weight:600;margin-bottom:6px">Holiday Chasers: ${pending.id.replace(/_/g," ")}</div>
  <div id="hc-msg" style="margin-bottom:8px">1) Click "What's on your mind?" to open the composer. 2) Press Fill.</div>
  <button id="hc-fill" style="background:#C9A24B;border:0;border-radius:6px;padding:6px 10px;font-weight:600;cursor:pointer">Fill post</button>
  <button id="hc-x" style="background:none;border:0;color:#E4D2A0;cursor:pointer">Close</button>`;
  document.body.appendChild(box);
  const msg = t => box.querySelector("#hc-msg").textContent = t;
  box.querySelector("#hc-x").onclick = async () => { await chrome.storage.local.remove("pending"); box.remove(); };

  // Try to open the composer for the user.
  setTimeout(() => {
    const b = [...document.querySelectorAll('[role="button"]')].find(e => /what'?s on your mind|create post/i.test(e.textContent || "") && e.offsetParent);
    if (b) b.click();
  }, 2500);

  box.querySelector("#hc-fill").onclick = async () => {
    const vis = e => e.getClientRects().length > 0;
    const eds = [...document.querySelectorAll('[contenteditable="true"], [contenteditable="plaintext-only"], [role="textbox"]')].filter(vis);
    const tb = eds.find(e => e.closest('[role="dialog"]')) || eds.find(e => /mind|say something|write/i.test((e.getAttribute("aria-label") || "") + (e.getAttribute("aria-placeholder") || "") + (e.textContent || ""))) || eds[0];
    const dlg = (tb && tb.closest('[role="dialog"]')) || document;
    if (!tb) return msg("Composer not open yet. Click \"What's on your mind?\" first.");
    tb.focus();
    document.execCommand("selectAll");
    document.execCommand("insertText", false, pending.caption);
    let done = "Caption filled. ";
    if (pending.mode === "link") return msg(done + "Wait a few seconds for the preview card with the poster to appear, check it, then press Post. (Download the Story image from the extension if you want a Story.)");
    try {
      const r = await chrome.runtime.sendMessage({ type: "poster", path: pending.poster });
      if (!r.ok) throw new Error(r.error);
      const blob = await (await fetch(r.dataUrl)).blob();
      const file = new File([blob], pending.id + ".png", { type: "image/png" });
      const dt = new DataTransfer(); dt.items.add(file);
      let inp = dlg.querySelector('input[type="file"][accept*="image"]');
      if (!inp) {
        const ph = [...dlg.querySelectorAll('[aria-label]')].find(e => /photo\/video/i.test(e.getAttribute("aria-label")));
        if (ph) { ph.click(); await new Promise(r => setTimeout(r, 800)); }
        inp = dlg.querySelector('input[type="file"][accept*="image"]');
      }
      if (!inp) throw new Error("no upload field");
      inp.files = dt.files; inp.dispatchEvent(new Event("change", { bubbles: true }));
      done += "Poster attached. ";
    } catch (e) {
      done += "Poster not attached (" + e.message + "): paste it manually.";
      window.open("https://holidaychasers.ie/" + pending.poster, "_blank");
    }
    msg(done + "Check it, then press Post.");
  };
})();
