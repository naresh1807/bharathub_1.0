// ─── LIKE / REACTION ───────────────────────────
function toggleLike(id) {
  const btn = document.getElementById(id);
  const icon = document.getElementById(id + '-icon');
  const countEl = document.getElementById(id + '-count');
  const liked = btn.classList.toggle('liked');
  const count = parseInt(countEl.textContent.replace(',',''));
  icon.textContent = liked ? '👍' : '👍';
  countEl.textContent = (liked ? count + 1 : count - 1).toLocaleString();
  if (liked) {
    btn.style.color = '#e11d48';
  } else {
    btn.style.color = '';
  }
}

function setReaction(id, emoji) {
  const btn = document.getElementById(id);
  const icon = document.getElementById(id + '-icon');
  const countEl = document.getElementById(id + '-count');
  icon.textContent = emoji;
  btn.classList.add('liked');
  btn.style.color = '#e11d48';
  const count = parseInt(countEl.textContent.replace(',',''));
  countEl.textContent = (count + 1).toLocaleString();
}

// ─── COMMENTS TOGGLE ───────────────────────────
function toggleComments(id) {
  const el = document.getElementById(id);
  el.classList.toggle('open');
}

// ─── LIVE VIEWER COUNT SIMULATION ──────────────
let viewerBase = 1240;
setInterval(() => {
  viewerBase += Math.floor(Math.random() * 7) - 3;
  if (viewerBase < 1100) viewerBase = 1100;
  if (viewerBase > 1400) viewerBase = 1400;
  const el = document.getElementById('viewerCount');
  if (el) el.textContent = viewerBase.toLocaleString('en-IN');
}, 3000);

// ─── NUMBER TICKER ANIMATION ───────────────────
function animateCounter(el, target, suffix) {
  let current = 0;
  const increment = target / 60;
  const timer = setInterval(() => {
    current += increment;
    if (current >= target) {
      current = target;
      clearInterval(timer);
    }
    el.textContent = Math.floor(current).toLocaleString('en-IN') + suffix;
  }, 30);
}

// window.bharathubRealStats: DB నుండి వచ్చిన నిజమైన counts
// (bharathub_home.html లో <script> ట్యాగ్ లో injected అవుతుంది).
// అవి లేకపోతే (var define కాకపోతే) ఈ యానిమేషన్ నే స్కిప్ చేస్తాం --
// ముందు లాగా ఫేక్ టార్గెట్ నంబర్స్ కి fall back అవ్వం.
window.addEventListener('load', () => {
  const stats = window.bharathubRealStats;
  if (!stats) return;
  setTimeout(() => {
    animateCounter(document.getElementById('stat-companies'), stats.employers, '');
    animateCounter(document.getElementById('stat-seekers'), stats.employees, '');
    animateCounter(document.getElementById('stat-vendors'), stats.vendors, '');
  }, 500);
});

function showJobLoginPrompt(role, company, salary) {
  document.getElementById('lpJobRole').textContent = role;
  document.getElementById('lpJobCompany').textContent = company;
  document.getElementById('lpJobSalary').textContent = salary;
  document.getElementById('loginPromptOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeJobLoginPrompt() {
  document.getElementById('loginPromptOverlay').classList.remove('open');
  document.body.style.overflow = '';
}
// Close on backdrop click
document.getElementById('loginPromptOverlay').addEventListener('click', function(e) {
  if (e.target === this) closeJobLoginPrompt();
});
