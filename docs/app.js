let allPosts = [];
let activePlatform = "";
let activeMember = "";

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString("ja-JP", { dateStyle: "medium", timeStyle: "short" });
}

function render() {
  const list = document.getElementById("posts");
  const empty = document.getElementById("empty");
  list.innerHTML = "";

  const filtered = allPosts.filter((p) => {
    if (activePlatform && p.platform !== activePlatform) return false;
    if (activeMember && p.member !== activeMember) return false;
    return true;
  });

  empty.hidden = filtered.length > 0;

  for (const post of filtered) {
    const li = document.createElement("li");
    li.className = `post platform-${post.platform}`;

    if (post.image_url) {
      const img = document.createElement("img");
      img.className = "thumb";
      img.loading = "lazy";
      img.src = post.image_url;
      img.alt = "";
      li.appendChild(img);
    }

    const body = document.createElement("div");
    body.className = "body";

    const meta = document.createElement("div");
    meta.className = "meta";

    const platformTag = document.createElement("span");
    platformTag.className = "platform-tag";
    platformTag.textContent = post.platform;
    meta.appendChild(platformTag);

    if (post.member) {
      const memberTag = document.createElement("span");
      memberTag.className = "member-tag";
      memberTag.textContent = post.member;
      meta.appendChild(memberTag);
    }

    const time = document.createElement("span");
    time.textContent = fmtDate(post.published_at);
    meta.appendChild(time);

    body.appendChild(meta);

    const content = document.createElement("p");
    content.className = "content";
    content.textContent = post.content || "";
    body.appendChild(content);

    const link = document.createElement("a");
    link.className = "link";
    link.href = post.url;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = "元の投稿を見る →";
    body.appendChild(link);

    li.appendChild(body);
    list.appendChild(li);
  }
}

function populateMemberSelect() {
  const select = document.getElementById("member-select");
  const members = [...new Set(allPosts.map((p) => p.member).filter(Boolean))].sort();
  for (const m of members) {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    select.appendChild(opt);
  }
}

async function init() {
  const res = await fetch("data.json", { cache: "no-store" });
  const payload = await res.json();
  allPosts = payload.posts || [];

  const updated = document.getElementById("updated");
  if (payload.generated_at) {
    updated.textContent = `最終更新: ${fmtDate(payload.generated_at)}`;
  }

  populateMemberSelect();
  render();

  document.getElementById("platform-nav").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-platform]");
    if (!btn) return;
    activePlatform = btn.dataset.platform;
    for (const b of document.querySelectorAll("#platform-nav button")) {
      b.classList.toggle("active", b === btn);
    }
    render();
  });

  document.getElementById("member-select").addEventListener("change", (e) => {
    activeMember = e.target.value;
    render();
  });
}

init().catch((err) => {
  document.getElementById("empty").hidden = false;
  document.getElementById("empty").textContent = "データの読み込みに失敗しました。";
  console.error(err);
});
