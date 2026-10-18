const BASE = "https://holidaychasers.ie/";
const PAGE = "https://www.facebook.com/holidaychasersie";
const s = document.getElementById("s"), list = document.getElementById("list"), bar = document.getElementById("designs");
const DESIGNS = [["classic", "Classic navy"], ["ivory", "Ivory"], ["bright", "Bright photo"]];
let design = "classic", mode = "link";
const paths = (p, kind) => (p.posters && p.posters[design] ? p.posters[design][kind] : (kind === "story" ? p.story : p.poster));

function render(d) {
  list.innerHTML = "";
  for (const p of d.posts) {
    const el = document.createElement("div"); el.className = "p";
    const story = paths(p, "story");
    el.innerHTML = `<img src="${BASE + paths(p, "feed")}"><div><div class="t"></div><div class="c"></div>
      <button class="use">Use for post</button>${story ? ' <button class="st">Download Story</button>' : ""}</div>`;
    el.querySelector(".t").textContent = (p.airport ? p.airport + " · " : "") + p.id.replace(/_/g, " ");
    el.querySelector(".c").textContent = p.caption;
    el.querySelector(".use").onclick = async () => {
      const share = p.posters && p.posters[design] && p.posters[design].share;
      const asLink = mode === "link" && share;
      const caption = asLink ? (p.link && p.caption.includes(p.link) ? p.caption.replace(p.link, share) : p.caption + " " + share) : p.caption;
      await chrome.storage.local.set({ pending: { ...p, caption, poster: paths(p, "feed"), mode: asLink ? "link" : "photo" } });
      const tabs = await chrome.tabs.query({ url: "https://www.facebook.com/*" });
      const t = tabs.find(x => x.url.includes("holidaychasersie")) || null;
      if (t) { await chrome.tabs.update(t.id, { active: true }); await chrome.tabs.reload(t.id); }
      else await chrome.tabs.create({ url: PAGE });
      window.close();
    };
    const sb = el.querySelector(".st");
    if (sb) sb.onclick = () => chrome.downloads.download({ url: BASE + story, filename: "HolidayChasers_story_" + p.id + "_" + design + ".png" });
    list.appendChild(el);
  }
}

fetch(BASE + "social/posts.json?t=" + Date.now()).then(r => r.json()).then(async d => {
  const saved = await chrome.storage.local.get(["design", "mode"]);
  if (saved.design) design = saved.design;
  if (saved.mode) mode = saved.mode;
  const mb = document.getElementById("modes");
  for (const [k, label] of [["link", "Clickable link card (recommended)"], ["photo", "Photo post"]]) {
    const b = document.createElement("button"); b.textContent = label; b.className = "d" + (k === mode ? " on" : "");
    b.onclick = async () => { mode = k; await chrome.storage.local.set({ mode }); mb.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b)); };
    mb.appendChild(b);
  }
  s.textContent = "Generated " + (d.generated || "") + ". Pick a design, then a post. You press Post yourself.";
  for (const [k, label] of DESIGNS) {
    const b = document.createElement("button"); b.textContent = label; b.className = "d" + (k === design ? " on" : "");
    b.onclick = async () => {
      design = k; await chrome.storage.local.set({ design });
      bar.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
      render(d);
    };
    bar.appendChild(b);
  }
  render(d);
}).catch(e => s.textContent = "Could not load posts: " + e);
