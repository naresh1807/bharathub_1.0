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

// ── CHAT ─────────────────────────────────
function openChat(name, color, el) {
  // Mobile: hide sidebar, show chat area
  if (window.innerWidth <= 640) {
    const sidebar = document.getElementById('waSidebar');
    const main = document.getElementById('waMain');
    if (sidebar) sidebar.classList.add('wa-hide');
    if (main) main.classList.add('wa-show');
  }
  const nameEl = document.getElementById('chatName');
  const avatar = document.getElementById('chatAvatarImg');
  const statusEl = document.querySelector('.wa-chatheader__status');
  if (nameEl) nameEl.textContent = name;
  if (avatar) {
    avatar.style.background = color;
    avatar.textContent = name.split(' ').map(n => n[0]).join('').slice(0,3);
  }
  if (statusEl) {
    const members = el && el.getAttribute('data-members');
    statusEl.textContent = members ? members : 'online';
  }
  document.querySelectorAll('.wa-chatitem').forEach(i => i.classList.remove('active'));
  if (el) el.classList.add('active');
}

// ── NEW GROUP (WHATSAPP-STYLE) ────────────────
function openNewGroupModal() {
  document.getElementById('waGroupOverlay').classList.add('open');
}
function closeNewGroupModal() {
  document.getElementById('waGroupOverlay').classList.remove('open');
  document.querySelectorAll('.wa-group-checkbox').forEach(cb => cb.checked = false);
  document.getElementById('waGroupNameInput').value = '';
}
function createGroup() {
  const nameInput = document.getElementById('waGroupNameInput');
  const groupName = nameInput.value.trim();
  const checked = Array.from(document.querySelectorAll('.wa-group-checkbox:checked')).map(cb => cb.value);
  if (!groupName) { alert('⚠️ Please enter a group name!'); return; }
  if (checked.length < 1) { alert('⚠️ Please select at least 1 participant!'); return; }

  const initials = groupName.split(' ').map(w => w[0]).join('').toUpperCase().slice(0,2);
  const colors = ['#00a884','#0050b3','#4a148c','#1b5e20','#b71c1c'];
  const groupColor = colors[Math.floor(Math.random() * colors.length)];
  const membersText = checked.length + ' participants: ' + checked.join(', ');

  const list = document.getElementById('waChatList');
  const groupItem = document.createElement('div');
  groupItem.className = 'wa-chatitem';
  groupItem.setAttribute('data-contact', groupName);
  groupItem.setAttribute('data-members', membersText);
  groupItem.setAttribute('onclick', `openChat('${groupName.replace(/'/g,"\\'")}','${groupColor}',this)`);
  groupItem.innerHTML = `
    <div class="wa-avatar" style="background:${groupColor};">👥</div>
    <div class="wa-chatitem__body">
      <div class="wa-chatitem__row1">
        <div class="wa-chatitem__name">${groupName}</div>
        <div class="wa-chatitem__time">now</div>
      </div>
      <div class="wa-chatitem__row2">
        <div class="wa-chatitem__preview">Group created · ${checked.length} members</div>
      </div>
    </div>`;
  list.insertBefore(groupItem, list.firstChild);

  closeNewGroupModal();
  groupItem.click();
  alert('✅ Group "' + groupName + '" created!');
}
document.addEventListener('DOMContentLoaded', function() {
  const overlay = document.getElementById('waGroupOverlay');
  if (overlay) overlay.addEventListener('click', function(e) { if (e.target === overlay) closeNewGroupModal(); });
});

function sendMsg() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim(); if (!text) return;
  const msgs = document.getElementById('chatMessages');
  const time = new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});
  msgs.innerHTML += `
    <div class="wa-msgrow sent">
      <div class="wa-bubble sent">${text}<span class="wa-bubble__time">${time}<span class="wa-tick">✓✓</span></span></div>
    </div>`;
  input.value = '';
  msgs.scrollTop = msgs.scrollHeight;
}

// ── PROFILE EDIT ─────────────────────────
function toggleEditForm() {
  const card = document.getElementById('editFormCard');
  card.style.display = card.style.display === 'none' ? 'block' : 'none';
}

function saveProfile() {
  document.getElementById('otpOverlay').classList.add('open');
  document.querySelectorAll('.otp-digit').forEach(i => i.value = '');
  document.querySelectorAll('.otp-digit')[0].focus();
}

function moveProfileOtp(input, idx) {
  if (input.value && idx < 6) document.querySelectorAll('.otp-digit')[idx].focus();
}

function confirmProfileUpdate() {
  const otp = Array.from(document.querySelectorAll('.otp-digit')).map(i => i.value).join('');
  if (otp.length < 6) { alert('Please enter the complete 6-digit OTP!'); return; }
  document.getElementById('otpOverlay').classList.remove('open');
  document.getElementById('editFormCard').style.display = 'none';
  alert('✅ Profile successfully updated!');
}

// ── GMAIL-STYLE MAIL DATA ─────────────────────
// ── GMAIL-STYLE MAIL DATA (folder-based) ──────
const folderData = {
  inbox: [
    {
      sender: 'Wipro HR', avatarColor: '#4a148c', avatarLetter: 'W',
      subject: 'Offer Letter — Django Backend Engineer',
      preview: 'Dear Ravi, we are sending you the offer letter. Please review...',
      date: 'Today, 2:30 PM', unread: true, starred: false,
      content: `Dear Ravi,

We are pleased to send you the offer letter for the Django Backend Engineer position. Please review the attached document carefully and confirm your acceptance at your earliest convenience.

Looking forward to having you on our team.

Best regards,
Wipro HR Team`,
      attachment: 'OfferLetter.pdf', attachType: 'doc'
    },
    {
      sender: 'TCS Recruitment', avatarColor: '#0050b3', avatarLetter: 'T',
      subject: 'Interview Confirmation — Python Developer',
      preview: 'June 5th interview confirmed. Please bring original documents...',
      date: 'Yesterday, 4:15 PM', unread: true, starred: false,
      content: `Dear Ravi,

This is to confirm your interview for the Python Developer position scheduled on June 5th, 2026 at 10:00 AM at our Hyderabad office.

Please bring your original educational documents and a valid ID proof.

Regards,
TCS Recruitment Team`,
      attachment: null, attachType: null
    }
  ],
  sent: [
    {
      sender: 'To: Wipro HR', avatarColor: 'var(--accent)', avatarLetter: 'R',
      subject: 'Re: Offer Letter — Django Backend Engineer',
      preview: 'Thank you for the offer! I accept the position...',
      date: '2 days ago', unread: false, starred: false,
      content: `Dear Wipro HR,

Thank you for the offer letter. I am happy to accept the position and look forward to joining the team.

Best regards,
Ravi Kumar`,
      attachment: null, attachType: null
    }
  ],
  drafts: [],
  trash: [],
  starred: []
};
let currentFolder = 'inbox';
let currentOpenIdx = -1;

function updateFolderCounts() {
  const inboxUnread = folderData.inbox.filter(e => e.unread).length;
  const starredCount = folderData.inbox.filter(e => e.starred).length + folderData.sent.filter(e => e.starred).length;
  const trashCount = folderData.trash.length;
  const inboxBadge = document.getElementById('gmCountInbox');
  const starredBadge = document.getElementById('gmCountStarred');
  const trashBadge = document.getElementById('gmCountTrash');
  if (inboxBadge) inboxBadge.textContent = inboxUnread;
  if (starredBadge) starredBadge.textContent = starredCount;
  if (trashBadge) trashBadge.textContent = trashCount;
}

function getCurrentFolderData() {
  if (currentFolder === 'starred') {
    return [...folderData.inbox, ...folderData.sent].filter(e => e.starred);
  }
  return folderData[currentFolder] || [];
}

function switchFolder(folder, el) {
  currentFolder = folder;
  document.querySelectorAll('.gm-folder').forEach(f => f.classList.remove('active'));
  document.querySelectorAll(`.gm-folder`).forEach(f => {
    if (f.getAttribute('onclick') && f.getAttribute('onclick').includes(`'${folder}'`)) f.classList.add('active');
  });
  backToInbox();
  renderMailList();
  closeMailDrawer();
}

function renderMailList() {
  const list = document.getElementById('mailContent');
  if (!list) return;
  const data = getCurrentFolderData();
  if (data.length === 0) {
    list.innerHTML = `<div class="gm-empty-state"><div class="gm-empty-state__icon">📭</div><div>No emails in ${currentFolder}</div></div>`;
    return;
  }
  list.innerHTML = data.map((email, i) => `
    <div class="gm-row ${email.unread ? 'unread' : ''}" onclick="openEmailRow(this,${i})">
      <span class="gm-star ${email.starred ? 'starred' : ''}" onclick="toggleStar(event,this,${i})">${email.starred ? '★' : '☆'}</span>
      <div class="gm-row-avatar" style="background:${email.avatarColor};">${email.avatarLetter}</div>
      <div class="gm-row-body">
        <div class="gm-row-line1">
          <div class="gm-sender">${email.sender}</div>
          <div class="gm-time">${email.date}</div>
        </div>
        <div class="gm-subjectwrap"><span class="gm-subject">${email.subject}</span><span class="gm-preview">${email.preview}</span></div>
      </div>
      <span class="gm-row-delete" onclick="deleteEmailRow(event,${i})" title="Delete">🗑️</span>
    </div>`).join('');
  updateFolderCounts();
}

function toggleStar(event, el, idx) {
  event.stopPropagation();
  const data = getCurrentFolderData();
  const email = data[idx];
  if (email) email.starred = !email.starred;
  el.classList.toggle('starred');
  el.textContent = el.classList.contains('starred') ? '★' : '☆';
  updateFolderCounts();
}

function deleteEmailRow(event, idx) {
  event.stopPropagation();
  const data = getCurrentFolderData();
  const email = data[idx];
  if (!email) return;
  if (currentFolder === 'trash') {
    if (!confirm('Delete this email permanently?')) return;
    folderData.trash = folderData.trash.filter(e => e !== email);
  } else {
    // Move to trash
    const sourceArr = folderData[currentFolder === 'starred' ? (folderData.inbox.includes(email) ? 'inbox' : 'sent') : currentFolder];
    const srcIdx = sourceArr.indexOf(email);
    if (srcIdx > -1) sourceArr.splice(srcIdx, 1);
    email.unread = false;
    folderData.trash.unshift(email);
  }
  renderMailList();
}

function deleteCurrentReadingEmail() {
  if (currentOpenIdx === -1) return;
  const data = getCurrentFolderData();
  const email = data[currentOpenIdx];
  if (!email) return;
  if (currentFolder === 'trash') {
    if (!confirm('Delete this email permanently?')) return;
    folderData.trash = folderData.trash.filter(e => e !== email);
  } else {
    const sourceArr = folderData[currentFolder === 'starred' ? (folderData.inbox.includes(email) ? 'inbox' : 'sent') : currentFolder];
    const srcIdx = sourceArr.indexOf(email);
    if (srcIdx > -1) sourceArr.splice(srcIdx, 1);
    email.unread = false;
    folderData.trash.unshift(email);
  }
  backToInbox();
  renderMailList();
}

function openEmailRow(el, idx) {
  const data = getCurrentFolderData();
  const email = data[idx];
  if (!email) return;
  currentOpenIdx = idx;
  email.unread = false;
  el.classList.remove('unread');

  document.getElementById('gmSubject').textContent = email.subject;
  document.getElementById('gmFrom').textContent = email.sender;
  document.getElementById('gmDate').textContent = email.date;
  document.getElementById('gmContent').textContent = email.content;
  const avatar = document.getElementById('gmAvatar');
  avatar.style.background = email.avatarColor;
  avatar.textContent = email.avatarLetter;

  const attachArea = document.getElementById('gmAttachArea');
  if (email.attachment) {
    attachArea.style.display = 'flex';
    attachArea.innerHTML = `<div class="gm-reading__attach-chip" style="cursor:pointer;" onclick="previewAttachment('${email.attachment}','${email.attachType}')">📎 ${email.attachment}</div>`;
  } else {
    attachArea.style.display = 'none';
  }

  document.getElementById('gmReading').classList.add('active');
  updateFolderCounts();
}
function backToInbox() {
  document.getElementById('gmReading').classList.remove('active');
  currentOpenIdx = -1;
}

// ── MAIL COMPOSE ───────────────────────────────
let composeAttachedFiles = [];
function openComposeModal() {
  document.getElementById('gmComposeOverlay').classList.add('open');
}
function closeComposeModal() {
  document.getElementById('gmComposeOverlay').classList.remove('open');
  document.getElementById('composeTo').value = '';
  document.getElementById('composeSubject').value = '';
  document.getElementById('composeBody').value = '';
  composeAttachedFiles = [];
  renderComposeAttachments();
}
document.addEventListener('DOMContentLoaded', function() {
  const overlay = document.getElementById('gmComposeOverlay');
  if (overlay) overlay.addEventListener('click', function(e) { if (e.target === overlay) closeComposeModal(); });
  renderMailList();
});
function sendComposedMail() {
  const to = document.getElementById('composeTo').value.trim();
  if (!to) { alert('⚠️ Please enter a recipient!'); return; }
  alert('✅ Mail sent!');
  closeComposeModal();
}
function handleComposeFileSelect(input) {
  Array.from(input.files).forEach(f => composeAttachedFiles.push(f.name));
  renderComposeAttachments();
  input.value = '';
}
function removeComposeAttachment(idx) {
  composeAttachedFiles.splice(idx, 1);
  renderComposeAttachments();
}
function renderComposeAttachments() {
  const wrap = document.getElementById('composeAttachList');
  if (!wrap) return;
  wrap.innerHTML = composeAttachedFiles.map((name, i) =>
    `<div class="gm-attach-chip">📎 ${name}<button onclick="removeComposeAttachment(${i})">✕</button></div>`
  ).join('');
}

// ── ATTACHMENT PREVIEW ─────────────────────────
function previewAttachment(name, type) {
  document.getElementById('attachPreviewName').textContent = name;
  const icon = document.getElementById('attachPreviewIcon');
  const icons = { doc: '📄', image: '🖼️', video: '🎥' };
  icon.textContent = icons[type] || '📎';
  document.getElementById('attachPreviewOverlay').classList.add('open');
}
function closeAttachPreview() {
  document.getElementById('attachPreviewOverlay').classList.remove('open');
}

// ── MAIL DRAWER (mobile) ───────────────────────
function openMailDrawer() {
  document.getElementById('gmDrawerOverlay').classList.add('open');
  document.getElementById('gmDrawer').classList.add('open');
}
function closeMailDrawer() {
  document.getElementById('gmDrawerOverlay').classList.remove('open');
  document.getElementById('gmDrawer').classList.remove('open');
}

function showCompose() { openComposeModal(); }

function searchChats(val) {
  document.querySelectorAll('.wa-chatitem').forEach(item => {
    const name = item.querySelector('.wa-chatitem__name');
    const text = name ? name.textContent.toLowerCase() : '';
    item.style.display = text.includes(val.toLowerCase()) ? 'flex' : 'none';
  });
}

function searchMail(val) {
  document.querySelectorAll('.gm-row').forEach(row => {
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(val.toLowerCase()) ? 'flex' : 'none';
  });
}

function showInbox() {
  switchFolder('inbox');
  document.querySelectorAll('.gm-folder').forEach(f => f.classList.remove('active'));
  const inboxFolder = document.querySelector(`.gm-sidebar .gm-folder`);
  if (inboxFolder) inboxFolder.classList.add('active');
}

// ── WHATSAPP CHAT: HEADER 3-DOT MENU ──────────
function toggleHeaderMenu(event) {
  event.stopPropagation();
  document.getElementById('waHeaderDropdown').classList.toggle('open');
}
function clearChat() {
  if (!confirm('Clear all messages in this chat?')) return;
  document.getElementById('chatMessages').innerHTML = '';
  document.getElementById('waHeaderDropdown').classList.remove('open');
}
function deleteChatConversation() {
  if (!confirm('Delete this entire chat conversation?')) return;
  document.getElementById('chatMessages').innerHTML = '<div style="text-align:center;color:#667781;font-size:13px;padding:20px;">Conversation deleted</div>';
  document.getElementById('waHeaderDropdown').classList.remove('open');
}

// ── WHATSAPP CHAT: MESSAGE DELETE ─────────────
function toggleMsgMenu(event, btn) {
  event.stopPropagation();
  const dropdown = btn.parentElement.querySelector('.wa-msg-dropdown');
  const wasOpen = dropdown && dropdown.classList.contains('open');
  document.querySelectorAll('.wa-msg-dropdown.open').forEach(d => d.classList.remove('open'));
  if (dropdown && !wasOpen) dropdown.classList.add('open');
}
function deleteMessage(btn) {
  const row = btn.closest('.wa-msgrow');
  if (row) row.remove();
}

// Close all open dropdowns/menus when clicking elsewhere
document.addEventListener('click', function() {
  document.querySelectorAll('.wa-msg-dropdown.open, .wa-header-dropdown.open, .wa-attach-menu.open').forEach(d => d.classList.remove('open'));
});

// ── WHATSAPP CHAT: ATTACHMENT MENU ────────────
function triggerChatFile() {
  document.getElementById('chatFileInput').click();
}
function handleChatFileSelect(input) {
  const file = input.files[0];
  if (!file) return;
  const msgs = document.getElementById('chatMessages');
  const time = new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});
  let bubbleContent = '';
  if (file.type.startsWith('image/')) {
    const url = URL.createObjectURL(file);
    bubbleContent = `<img src="${url}" class="wa-image-msg"><span class="wa-bubble__time">${time}<span class="wa-tick">✓✓</span></span>`;
  } else if (file.type.startsWith('video/')) {
    bubbleContent = `<div class="wa-file-msg"><div class="wa-file-icon">🎥</div><div class="wa-file-info"><div class="wa-file-name">${file.name}</div><div class="wa-file-size">${(file.size/1024/1024).toFixed(1)} MB</div></div></div><span class="wa-bubble__time">${time}<span class="wa-tick">✓✓</span></span>`;
  } else {
    bubbleContent = `<div class="wa-file-msg"><div class="wa-file-icon">📄</div><div class="wa-file-info"><div class="wa-file-name">${file.name}</div><div class="wa-file-size">${(file.size/1024).toFixed(0)} KB</div></div></div><span class="wa-bubble__time">${time}<span class="wa-tick">✓✓</span></span>`;
  }
  const msgId = 'msg-' + Date.now();
  msgs.innerHTML += `
    <div class="wa-msgrow sent" id="${msgId}">
      <button class="wa-msg-menu-btn" onclick="toggleMsgMenu(event,this)">⋮</button>
      <div class="wa-bubble sent">${bubbleContent}</div>
      <div class="wa-msg-dropdown"><button onclick="deleteMessage(this)">🗑️ Delete message</button></div>
    </div>`;
  msgs.scrollTop = msgs.scrollHeight;
  input.value = '';
}

// ── MOBILE NAV ────────────────────────────────
function mobileNav(section, btn) {
  document.querySelectorAll('.mobile-nav-item').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  showSection(section);
}

// ── MOBILE WHATSAPP-STYLE CHAT NAV ────────────
function closeMobileChat() {
  const sidebar = document.getElementById('waSidebar');
  const main = document.getElementById('waMain');
  if (sidebar) sidebar.classList.remove('wa-hide');
  if (main) main.classList.remove('wa-show');
}
function initMobileChat() {
  if (window.innerWidth <= 640) {
    const sidebar = document.getElementById('waSidebar');
    const main = document.getElementById('waMain');
    if (sidebar) sidebar.classList.remove('wa-hide');
    if (main) main.classList.remove('wa-show');
  }
}

// logout() was removed -- it only did window.location.href to the login
// page without ever ending the Django session. The Logout button in
// candidate_dashboard.html is now a real POST <form> to accounts:logout,
// which calls django.contrib.auth.logout() server-side.
