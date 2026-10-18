const BASE = "https://holidaychasers.ie/";
const PAGE = "https://www.facebook.com/holidaychasersie";
const s = document.getElementById("s"), list = document.getElementById("list");
fetch(BASE + "social/posts.json?t=" + Date.now()).then(r => r.json()).then(d => {
  s.textContent = "Generated " + (d.generated || "") + ". Pick one, then press Post yourself.";
  for (const p of d.posts) {
    const el = document.createElement("div"); el.className = "p";
    el.innerHTML = `<img src="${BASE + p.poster}"><div><div class="t"></div><div class="c"></div><button>Use this post</button></div>`;
    el.querySelector(".t").textContent = (p.airport ? p.airport + " · " : "") + p.id.replace(/_/g, " ");
    el.querySelector(".c").textContent = p.caption;
    el.querySelector("button").onclick = async () => {
      await chrome.storage.local.set({ pending: p });
      const tabs = await chrome.tabs.query({ url: "https://www.facebook.com/*" });
      const t = tabs.find(x => x.url.includes("holidaychasersie")) || null;
      if (t) { await chrome.tabs.update(t.id, { active: true }); await chrome.tabs.reload(t.id); }
      else await chrome.tabs.create({ url: PAGE });
      window.close();
    };
    list.appendChild(el);
  }
}).catch(e => s.textContent = "Could not load posts: " + e);
