// ── SECTION NAVIGATION ────────────────────
// ── APPLIED STATUS TABLE FILTER ──────────────
function filterAppliedTable(status) {
  showSection('applied');
  const selectEl = document.getElementById('appliedStatusFilter');
  if (selectEl) selectEl.value = status;
  document.querySelectorAll('#section-applied .status-table tbody tr').forEach(row => {
    const rowStatus = row.dataset.status;
    row.style.display = (status === 'all' || rowStatus === status) ? '' : 'none';
  });
  setTimeout(() => {
    const table = document.querySelector('#section-applied .card');
    if (table) table.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 100);
}

function showSection(id, tabEl, sidebarEl) {
  document.querySelectorAll('.section-page').forEach(s => s.classList.remove('active'));
  const sec = document.getElementById('section-' + id);
  if (sec) sec.classList.add('active');

  if (tabEl) {
    document.querySelectorAll('.topnav__tab').forEach(t => t.classList.remove('active'));
    tabEl.classList.add('active');
  }
  if (sidebarEl) {
    document.querySelectorAll('.sidebar__nav-item').forEach(t => t.classList.remove('active'));
    sidebarEl.classList.add('active');
  }
  if (id === 'chat') setTimeout(initMobileChat, 50);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── HIRE STATUS ───────────────────────────
function toggleHireStatus() {
  const pill = document.getElementById('hirePill');
  const label = document.getElementById('hireLabel');
  pill.classList.toggle('on');
  if (pill.classList.contains('on')) {
    label.textContent = '🟢 For Hire'; label.style.color = 'var(--success)';
  } else {
    label.textContent = '🔴 Hired'; label.style.color = 'var(--error)';
  }
}

function setHireStatus(s) {
  const hBtn = document.getElementById('hireBtn');
  const dBtn = document.getElementById('hiredBtn');
  if (s === 'hire') {
    hBtn.className = 'btn-sm btn-sm--primary'; dBtn.className = 'btn-sm btn-sm--outline';
  } else {
    hBtn.className = 'btn-sm btn-sm--outline'; dBtn.className = 'btn-sm btn-sm--primary';
  }
}

// ── JOB DETAIL ────────────────────────────
// ── JOB DATA ─────────────────────────────
const jobData = {
  tcs: {
    key: 'tcs', company: 'TCS', logo: 'TCS', color: '#0050b3',
    role: 'Python Developer', salary: '₹8-12 LPA',
    location: 'Hyderabad', type: 'Full Time', exp: 'Freshers OK',
    deadline: 'June 30, 2026', openings: '5 Positions',
    desc: 'TCS Hyderabad campus is looking for talented developers to build enterprise-level Python/Django applications. You will work on large-scale projects.',
    skills: ['Python', 'Django', 'MySQL', 'REST API', 'Git'],
    requirements: [
      'B.Tech/MCA in Computer Science or related field',
      '0-2 years experience (Freshers welcome)',
      'Strong Python programming skills',
      'Knowledge of Django framework',
      'Good communication skills'
    ],
    benefits: ['Health Insurance', 'PF & ESI', 'Annual Bonus', 'WFH Option', 'Learning Budget']
  },
  wipro: {
    key: 'wipro', company: 'Wipro', logo: 'WPR', color: '#4a148c',
    role: 'Django Backend Engineer', salary: '₹10-14 LPA',
    location: 'Bangalore', type: 'Full Time', exp: '1-3 Years',
    deadline: 'July 15, 2026', openings: '3 Positions',
    desc: 'Wipro Bangalore is looking for experienced Django developers to build scalable backend systems. An exciting opportunity to work on microservices architecture.',
    skills: ['Django', 'REST API', 'Python', 'PostgreSQL', 'Docker'],
    requirements: [
      'B.Tech in CS/IT or equivalent',
      '1-3 years Django experience required',
      'REST API design experience',
      'PostgreSQL knowledge',
      'Docker basics preferred'
    ],
    benefits: ['Medical Insurance', 'Stock Options', 'Gym Allowance', 'Flexi Hours', '5-Day Week']
  },
  infosys: {
    key: 'infosys', company: 'Infosys', logo: 'INF', color: '#1b5e20',
    role: 'Full Stack Developer', salary: '₹7-11 LPA',
    location: 'Pune', type: 'Hybrid', exp: 'Freshers OK',
    deadline: 'July 5, 2026', openings: '8 Positions',
    desc: 'Full stack development with React frontend and Python backend at Infosys Pune. An exciting role building modern web applications for enterprise clients.',
    skills: ['React', 'Python', 'Node.js', 'MySQL', 'HTML/CSS'],
    requirements: [
      'B.Tech/BCA/MCA degree',
      'React.js knowledge required',
      'Python basics required',
      'Good problem solving skills',
      'Freshers with strong projects welcome'
    ],
    benefits: ['Health Cover', 'Training Programs', 'Annual Hike', 'Transport', 'Cafeteria']
  },
  hcl: {
    key: 'hcl', company: 'HCL Tech', logo: 'HCL', color: '#b71c1c',
    role: 'Cyber Security Analyst', salary: '₹12-18 LPA',
    location: 'Chennai', type: 'Full Time', exp: '2-4 Years',
    deadline: 'June 25, 2026', openings: '2 Positions',
    desc: 'HCL Tech Chennai is looking for experienced security professionals to implement enterprise security solutions. A role focused on penetration testing and vulnerability assessment.',
    skills: ['Security', 'Python', 'Linux', 'OWASP', 'SIEM'],
    requirements: [
      'B.Tech in CS/IT or Cybersecurity',
      '2+ years security experience',
      'CEH/CISSP certification preferred',
      'Linux administration skills',
      'Security tools knowledge'
    ],
    benefits: ['High Salary', 'Certifications Funded', 'Health Insurance', 'Relocation Bonus', 'Night Allowance']
  },
  cognizant: {
    key: 'cognizant', company: 'Cognizant', logo: 'COG', color: '#006064',
    role: 'Data Scientist', salary: '₹14-20 LPA',
    location: 'Mumbai', type: 'Full Time', exp: '1-3 Years',
    deadline: 'July 20, 2026', openings: '4 Positions',
    desc: 'Cognizant Mumbai is looking for talented data scientists to develop machine learning models and provide business insights.',
    skills: ['Python', 'ML', 'TensorFlow', 'Pandas', 'SQL'],
    requirements: [
      'M.Tech/M.Sc in Data Science or related',
      '1-3 years ML experience',
      'TensorFlow/PyTorch knowledge',
      'Statistical analysis skills',
      'Big data tools preferred'
    ],
    benefits: ['High CTC', 'Remote Work', 'Conference Budget', 'Research Opportunities', 'Health Cover']
  },
  tech: {
    key: 'tech', company: 'Tech Mahindra', logo: 'TCH', color: '#e65100',
    role: 'Java Backend Developer', salary: '₹9-13 LPA',
    location: 'Noida', type: 'Full Time', exp: '1-3 Years',
    deadline: 'July 10, 2026', openings: '6 Positions',
    desc: 'Tech Mahindra Noida is looking for experienced Java developers to develop Spring Boot microservices. An opportunity to work with large banking clients.',
    skills: ['Java', 'Spring Boot', 'MySQL', 'Docker', 'Kafka'],
    requirements: [
      'B.Tech in CS/IT',
      '1-3 years Java experience',
      'Spring Boot knowledge required',
      'Microservices architecture',
      'MySQL/PostgreSQL experience'
    ],
    benefits: ['Competitive Salary', 'PF & Gratuity', 'Health Insurance', 'Annual Bonus', 'Work From Home']
  }
};

// Applied jobs tracking
const appliedJobs = new Set();
let currentJobKey = null;

// ── OPEN JOB DETAIL ──────────────────────
function openJobDetail(key) {
  const d = jobData[key];
  if (!d) return;
  currentJobKey = key;

  // Header
  const logo = document.getElementById('jdLogo');
  if (logo) { logo.textContent = d.logo; logo.style.background = d.color; }
  const comp = document.getElementById('jdCompany');
  if (comp) comp.textContent = d.company;
  const role = document.getElementById('jdRole');
  if (role) role.textContent = d.role;
  const sal = document.getElementById('jdSalary');
  if (sal) sal.textContent = d.salary;
  const loc = document.getElementById('jdLocation');
  if (loc) loc.textContent = '📍 ' + d.location;
  const typ = document.getElementById('jdType');
  if (typ) typ.textContent = '💼 ' + d.type;
  const exp = document.getElementById('jdExp');
  if (exp) exp.textContent = '🎓 ' + d.exp;

  // Body
  const dead = document.getElementById('jdDeadline');
  if (dead) dead.textContent = d.deadline;
  const open = document.getElementById('jdOpenings');
  if (open) open.textContent = d.openings;
  const desc = document.getElementById('jdDesc');
  if (desc) desc.textContent = d.desc;
  const skills = document.getElementById('jdSkills');
  if (skills) skills.innerHTML = d.skills.map(s => `<span class="tag">${s}</span>`).join('');
  const reqs = document.getElementById('jdReqs');
  if (reqs) reqs.innerHTML = d.requirements.map(r => `<li style="font-size:13px;color:#374151;margin-bottom:4px;">${r}</li>`).join('');
  const ben = document.getElementById('jdBenefits');
  if (ben) ben.innerHTML = d.benefits.map(b => `<span style="background:rgba(22,163,74,0.1);color:var(--success);font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;">${b}</span>`).join('');

  // Check if already applied
  const applyBtn = document.getElementById('jdApplyBtn');
  const alreadyApplied = document.getElementById('jdAlreadyApplied');
  const applySection = document.getElementById('jdApplySection');
  if (appliedJobs.has(key)) {
    if (applySection) applySection.style.display = 'none';
    if (alreadyApplied) alreadyApplied.style.display = 'block';
  } else {
    if (applySection) applySection.style.display = 'block';
    if (alreadyApplied) alreadyApplied.style.display = 'none';
    if (applyBtn) applyBtn.disabled = false;
  }

  // Show info view
  showJobInfo();
  document.getElementById('jobDetailOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeJobDetail() {
  document.getElementById('jobDetailOverlay').classList.remove('open');
  document.body.style.overflow = '';
  currentJobKey = null;
}

// ── SHOW/HIDE VIEWS ──────────────────────
function showJobInfo() {
  const info = document.getElementById('jdInfoView');
  const form = document.getElementById('jdApplyView');
  if (info) info.style.display = 'block';
  if (form) form.style.display = 'none';
}

function showApplyForm() {
  const d = jobData[currentJobKey];
  if (!d) return;
  const info = document.getElementById('jdInfoView');
  const form = document.getElementById('jdApplyView');
  if (info) info.style.display = 'none';
  if (form) form.style.display = 'block';

  // Fill apply form
  const applyRole = document.getElementById('applyForRole');
  const applyComp = document.getElementById('applyForCompany');
  if (applyRole) applyRole.textContent = d.role;
  if (applyComp) applyComp.textContent = d.company + ' · ' + d.location;

  // Reset form
  const sal = document.getElementById('applySalary');
  const cover = document.getElementById('applyCover');
  const consent = document.getElementById('applyConsent');
  const resumeLabel = document.getElementById('resumeLabel');
  if (sal) sal.value = '';
  if (cover) cover.value = '';
  if (consent) consent.checked = false;
  if (resumeLabel) resumeLabel.textContent = 'PDF, DOC · Max 5MB · Click to upload';

  // Scroll to top of modal
  const body = document.getElementById('jdBody');
  if (body) body.scrollTop = 0;
}

// ── RESUME UPLOAD ─────────────────────────
function handleResumeUpload(input) {
  const label = document.getElementById('resumeLabel');
  if (input.files && input.files[0]) {
    const file = input.files[0];
    if (file.size > 5 * 1024 * 1024) {
      alert('⚠️ File size must be less than 5MB!');
      input.value = '';
      return;
    }
    if (label) label.textContent = '✅ ' + file.name + ' (' + (file.size / 1024).toFixed(0) + ' KB)';
  }
}

// ── SUBMIT APPLICATION ────────────────────
function submitApplication() {
  const d = jobData[currentJobKey];
  if (!d) return;

  const name = document.getElementById('applyName');
  const email = document.getElementById('applyEmail');
  const mobile = document.getElementById('applyMobile');
  const consent = document.getElementById('applyConsent');

  if (!name || !name.value.trim()) { alert('⚠️ Please enter your name!'); return; }
  if (!email || !email.value.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
    alert('⚠️ Please enter a valid email!'); return;
  }
  if (!mobile || !mobile.value.trim()) { alert('⚠️ Please enter your mobile number!'); return; }
  if (!consent || !consent.checked) { alert('⚠️ Please check the consent checkbox!'); return; }

  // Mark as applied
  appliedJobs.add(currentJobKey);

  // Add to applied status table
  addToAppliedTable(d);

  // Close modal
  closeJobDetail();

  // Show success
  showApplicationSuccess(d.role, d.company);

  // Update apply button on job card
  updateJobCardApplied(currentJobKey);
}

// ── ADD TO APPLIED TABLE ──────────────────
function addToAppliedTable(d) {
  const tbody = document.querySelector('#section-applied .status-table tbody');
  if (!tbody) return;
  const today = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  const row = document.createElement('tr');
  row.id = 'applied-' + d.key;
  row.innerHTML = `
    <td><strong>${d.company}</strong></td>
    <td>${d.role}</td>
    <td>${today}</td>
    <td><span class="status-badge status-badge--applied">📨 Applied</span></td>
    <td><button class="btn btn--sm btn--outline" onclick="showSection('chat')">Chat HR</button></td>`;
  tbody.insertBefore(row, tbody.firstChild);

  // Update stat counter
  const totalEl = document.querySelector('#section-applied .stat-card:first-child .stat-card__num');
  if (totalEl) {
    const current = parseInt(totalEl.textContent) || 0;
    totalEl.textContent = current + 1;
  }
}

// ── UPDATE JOB CARD ───────────────────────
function updateJobCardApplied(key) {
  const cards = document.querySelectorAll('.job-card');
  cards.forEach(card => {
    if (card.getAttribute('onclick') && card.getAttribute('onclick').includes(key)) {
      const btn = card.querySelector('.btn-apply');
      if (btn) {
        btn.textContent = '✅ Applied';
        btn.style.background = 'var(--success)';
        btn.disabled = true;
        btn.onclick = null;
      }
    }
  });
}

// ── SUCCESS TOAST ─────────────────────────
function showApplicationSuccess(role, company) {
  // Remove existing toast
  const existing = document.getElementById('appToast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.id = 'appToast';
  toast.style.cssText = `
    position:fixed;bottom:24px;right:24px;z-index:500;
    background:linear-gradient(135deg,var(--success),#15803d);
    color:white;border-radius:14px;padding:16px 20px;
    box-shadow:0 8px 30px rgba(22,163,74,0.4);
    max-width:340px;animation:slideInToast 0.4s ease;
  `;
  toast.innerHTML = `
    <div style="display:flex;align-items:flex-start;gap:12px;">
      <div style="font-size:28px;">🎉</div>
      <div>
        <div style="font-size:14px;font-weight:700;margin-bottom:4px;">Application Submitted!</div>
        <div style="font-size:12px;opacity:0.85;">${role} — ${company}</div>
        <div style="font-size:12px;opacity:0.75;margin-top:4px;">BH20261001 · Status: Under Review</div>
        <button onclick="showSection('applied');document.getElementById('appToast').remove();"
          style="margin-top:8px;background:rgba(255,255,255,0.2);border:1px solid rgba(255,255,255,0.3);color:white;border-radius:6px;padding:5px 12px;font-family:var(--font);font-size:12px;font-weight:600;cursor:pointer;">
          📊 View Application Status →
        </button>
      </div>
      <button onclick="this.closest('#appToast').remove()" style="background:none;border:none;color:rgba(255,255,255,0.7);font-size:18px;cursor:pointer;padding:0;margin-left:4px;">✕</button>
    </div>`;
  document.body.appendChild(toast);

  // Auto remove after 6 seconds
  setTimeout(() => { const t = document.getElementById('appToast'); if (t) t.remove(); }, 6000);
}

// ── LEGACY applyJob (from job cards direct button) ──
function applyJob(role) {
  // Find key from role
  const key = Object.keys(jobData).find(k => jobData[k].role === role);
  if (key) {
    openJobDetail(key);
    setTimeout(() => showApplyForm(), 100);
  }
}

// ── FILTER JOBS ──────────────────────────
function filterJobs(val) {
  const cards = document.querySelectorAll('.job-card');
  cards.forEach(c => {
    const text = (c.textContent + ' ' + (c.dataset.skills || '')).toLowerCase();
    c.style.display = text.includes(val.toLowerCase()) ? 'block' : 'none';
  });
}
function filterJobTag(tag) {
  const cards = document.querySelectorAll('.job-card');
  cards.forEach(c => {
    const skills = (c.dataset.skills || '').toLowerCase();
    const text = c.textContent.toLowerCase();
    c.style.display = (tag === 'all' || skills.includes(tag) || text.includes(tag)) ? 'block' : 'none';
  });
}

// ── MOBILE NAV ────────────────────────────────
function mobileNav(section, btn) {
  document.querySelectorAll('.mobile-nav-item').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  showSection(section);
}

// logout() was removed -- it only did window.location.href to the login
// page without ever ending the Django session. The Logout button in
// candidate_dashboard.html is now a real POST <form> to accounts:logout,
// which calls django.contrib.auth.logout() server-side.

// ── OPEN THE RIGHT TAB WHEN ARRIVING VIA ?section=... ─────────────
// candidates/_nav.html (used by candidate_messages.html, and any
// future candidate sub-page) links back to this dashboard with e.g.
// "?section=profile" for tabs that only exist as JS show/hide
// sections here (Home/Profile/Videos/Mail aren't separate URLs).
// Without this, landing back on the dashboard always showed "Home"
// regardless of which tab the person actually clicked.
document.addEventListener('DOMContentLoaded', () => {
  const section = new URLSearchParams(window.location.search).get('section');
  if (!section) return;
  showSection(section);
  // showSection(id) ఒక్కటే ఇచ్చినప్పుడు (tabEl/sidebarEl లేకుండా),
  // content మారుతుంది కానీ ఏ నావ్ బటన్ "active" గా highlight
  // అవ్వదు -- ఇక్కడ ఆ రెండు బటన్లనీ (topnav + sidebar) వెతికి
  // మాన్యువల్‌గా active క్లాస్ పెడతాం.
  document.querySelectorAll('.topnav__tab').forEach((el) => el.classList.remove('active'));
  document.querySelectorAll('.sidebar__nav-item').forEach((el) => el.classList.remove('active'));
  const escaped = section.replace(/'/g, "\\'");
  document.querySelector(`.topnav__tab[onclick*="showSection('${escaped}'"]`)?.classList.add('active');
  document.querySelector(`.sidebar__nav-item[onclick*="showSection('${escaped}'"]`)?.classList.add('active');
});
