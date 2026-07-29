// ============================================================================
// videos/static/videos/js/video_feed.js
// ఈ ఫైల్ Home page, Employer Dashboard, Candidate Dashboard -- మూడు చోట్లా
// {% include "videos/_feed.html" %} వాడిన ప్రతిచోటా లోడ్ అవుతుంది. ఫంక్షన్
// పేర్లన్నీ `vf` ప్రిఫిక్స్ తో ఉన్నాయి, ఎందుకంటే candidate_dashboard.js /
// employer_dashboard.js / bharathub_home.js లో ఇప్పటికే వేరే విషయాలకి
// ఇలాంటి పేర్లు (toggleLike, showSection) వాడుతున్నారు -- collision రాకుండా.
// ============================================================================

const VF_REACTION_EMOJI = { like: "👍", love: "❤️", clap: "👏", support: "🤝", celebrate: "🎉" };

// messaging/static/messaging/js/chat.js లో వాడిన అదే cookie-read పద్ధతి --
// CSRF_COOKIE_HTTPONLY = False గా settings.py లో సెట్ చేసి ఉంది కాబట్టి ఇది
// పనిచేస్తుంది.
function vfGetCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

// అనామక (login అవ్వని) యూజర్ Like/Comment నొక్కితే -- Home పేజీలో already
// ఉన్న "Login to Apply" మోడల్ (showJobLoginPrompt) ఉంటే దాన్నే తిరిగి
// వాడతాం; లేకపోతే (dashboard పేజీల్లో ఈ కేస్ రాదు, ఎందుకంటే dashboard
// చూడాలంటే ఇప్పటికే లాగిన్ అయి ఉండాలి) నేరుగా లాగిన్ పేజీ కి పంపుతాం.
function vfRequireLogin() {
  if (typeof showJobLoginPrompt === "function") {
    showJobLoginPrompt("Login Required", "Login to like, comment & watch more videos", "");
  } else {
    window.location.href = "/employee_login.html";
  }
}

function vfToggleComments(btn) {
  const card = btn.closest(".vf-card");
  const panel = card.querySelector(".vf-comments");
  panel.classList.toggle("vf-open");
}

function vfToggleLike(el, reaction) {
  const wrap = el.closest(".vf-like-wrap");
  const btn = wrap.querySelector(".vf-action-btn");
  const videoId = btn.dataset.videoId;
  const authed = btn.dataset.authenticated === "1";

  if (!authed) {
    vfRequireLogin();
    return;
  }

  fetch(`/videos/${videoId}/like/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": vfGetCsrfToken(),
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Requested-With": "XMLHttpRequest",
    },
    body: `reaction=${encodeURIComponent(reaction || "like")}`,
  })
    .then((r) => r.json())
    .then((data) => {
      const iconEl = btn.querySelector(".vf-reaction-icon");
      const countEl = btn.querySelector(".vf-like-count");
      countEl.textContent = data.like_count;
      if (data.liked) {
        btn.classList.add("vf-liked");
        iconEl.textContent = data.reaction_emoji || VF_REACTION_EMOJI[data.reaction] || "👍";
      } else {
        btn.classList.remove("vf-liked");
        iconEl.textContent = "👍";
      }
    })
    .catch(() => alert("Something went wrong, please try again."));
}

function vfSubmitComment(event, form) {
  event.preventDefault();
  const panel = form.closest(".vf-comments");
  const videoId = panel.dataset.videoId;
  const input = form.querySelector("input[name=text]");
  const text = input.value.trim();
  if (!text) return false;

  fetch(`/videos/${videoId}/comment/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": vfGetCsrfToken(),
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Requested-With": "XMLHttpRequest",
    },
    body: `text=${encodeURIComponent(text)}`,
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        alert(data.error);
        return;
      }
      const div = document.createElement("div");
      div.className = "vf-comment";
      const safeText = data.text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
      div.innerHTML =
        `<div class="vf-comment__avatar">${data.initials}</div>` +
        `<div class="vf-comment__bubble"><div class="vf-comment__name">${data.name}</div>${safeText}</div>`;
      form.parentNode.insertBefore(div, form);
      input.value = "";

      const card = panel.closest(".vf-card");
      const countEl = card.querySelector(".vf-comment-count");
      if (countEl) countEl.textContent = data.comment_count;
    })
    .catch(() => alert("Comment could not be posted, please try again."));

  return false;
}

// ── UPLOAD DROPZONE (Employer dashboard "Videos" panel మాత్రమే) ─────────
function vfHandleFileSelect(input) {
  const form = document.getElementById("vfUploadForm");
  if (!input.files || !input.files.length || !form) return;
  form.style.display = "block";
  const nameEl = document.getElementById("vfSelectedFileName");
  if (nameEl) nameEl.textContent = "📁 " + input.files[0].name;
}
