// ─── MOBILE NAV DRAWER ──────────────────────────
// ఇంతకుముందు మొబైల్ లో ఏ నావిగేషన్ మెనూ లేదు -- ఈ మూడు ఫంక్షన్లు
// హెడర్ లోని ☰ బటన్ (#mobileMenuToggle) తో drawer (#mobileNavDrawer)
// ని తెరవడం/మూయడం చేస్తాయి.
function toggleMobileNav() {
  const drawer = document.getElementById('mobileNavDrawer');
  if (drawer.classList.contains('open')) {
    closeMobileNav();
  } else {
    openMobileNav();
  }
}

function openMobileNav() {
  const drawer = document.getElementById('mobileNavDrawer');
  const overlay = document.getElementById('mobileNavOverlay');
  const toggle = document.getElementById('mobileMenuToggle');
  drawer.classList.add('open');
  overlay.classList.add('open');
  drawer.setAttribute('aria-hidden', 'false');
  toggle.setAttribute('aria-expanded', 'true');
  document.body.style.overflow = 'hidden';
}

function closeMobileNav() {
  const drawer = document.getElementById('mobileNavDrawer');
  const overlay = document.getElementById('mobileNavOverlay');
  const toggle = document.getElementById('mobileMenuToggle');
  drawer.classList.remove('open');
  overlay.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
  toggle.setAttribute('aria-expanded', 'false');
  document.body.style.overflow = '';
}

// Escape కీ తో మూయడం, మరియు స్క్రీన్ ని డెస్క్‌టాప్ సైజ్ కి రీసైజ్
// చేస్తే (ఉదా: ఫోన్ rotate చేసినా, లేదా బ్రౌజర్ విండో పెద్దది
// చేసినా) drawer ఆటోమేటిక్‌గా మూసుకుపోవాలి -- లేకపోతే డెస్క్‌టాప్
// వ్యూ లో కూడా అది తెరిచే ఉండిపోతుంది.
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeMobileNav();
});
window.addEventListener('resize', () => {
  if (window.innerWidth > 768) closeMobileNav();
});

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
