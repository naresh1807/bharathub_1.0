// ── STEP NAVIGATION ────────────────────────
function goStep(n) {
  // Validate before moving forward
  if (n === 2 && !validateEmpStep1()) return;
  if (n === 3 && !validateEmpStep2()) return;
  if (n === 4 && !validateEmpStep3()) return;

  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById('step' + i);
    if (el) el.style.display = i === n ? 'block' : 'none';
    const ind = document.getElementById('si' + i);
    if (ind) {
      ind.classList.remove('active','done');
      if (i < n) ind.classList.add('done');
      if (i === n) ind.classList.add('active');
    }
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── EMPLOYER STEP VALIDATIONS ──────────────────────
function validateEmpStep1() {
  const name = document.getElementById('companyName') ? document.getElementById('companyName').value.trim() : '';
  const sector = document.getElementById('industrySector') ? document.getElementById('industrySector').value : '';
  const type = document.querySelector('.type-chip.selected');
  if (!name) { alert('⚠️ Please enter the Company Legal Name!'); return false; }
  if (!type) { alert('⚠️ Please select the Company Type!'); return false; }
  if (!sector) { alert('⚠️ Please select the Industry Sector!'); return false; }
  return true;
}
function validateEmpStep2() {
  const state = document.getElementById('hqState') ? document.getElementById('hqState').value : '';
  const city = document.querySelector('#step2 input[placeholder="City name"]');
  if (!state) { alert('⚠️ Please select the Headquarters State!'); return false; }
  if (!city || !city.value.trim()) { alert('⚠️ Please enter the City!'); return false; }
  return true;
}
function validateEmpStep3() {
  const email = document.getElementById('corpEmail') ? document.getElementById('corpEmail').value.trim() : '';
  if (!email) { alert('⚠️ Official Corporate Enter an email!'); return false; }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { alert('⚠️ Please enter a valid email format!'); return false; }
  const blocked = ['gmail','yahoo','hotmail','outlook','rediffmail'];
  const domain = email.split('@')[1] ? email.split('@')[1].split('.')[0].toLowerCase() : '';
  if (blocked.includes(domain)) { alert('⚠️ Personal email is not allowed! Use a company domain email.'); return false; }
  return true;
}
function selectType(el) {
  document.querySelectorAll('.type-chip').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
}

// ── BRANCH TABLE ────────────────────────────
let branchCount = 1;
function addBranch() {
  branchCount++;
  const tbody = document.getElementById('branchTableBody');
  const row = document.createElement('tr');
  row.id = 'branch-' + branchCount;
  row.innerHTML = `
    <td style="font-weight:700;color:var(--primary);">${branchCount}</td>
    <td><input type="text" placeholder="City name"></td>
    <td><select><option>Telangana</option><option>AP</option><option>Karnataka</option><option>Tamil Nadu</option><option>Maharashtra</option><option>Delhi</option><option>Gujarat</option></select></td>
    <td><input type="text" placeholder="Branch address"></td>
    <td><input type="text" placeholder="PIN" maxlength="6"></td>
    <td><button class="btn-remove-branch" onclick="removeBranch(${branchCount})">❌</button></td>
  `;
  tbody.appendChild(row);
}
function removeBranch(id) {
  const row = document.getElementById('branch-' + id);
  if (row) row.remove();
}

// ── VALIDATE PIN ─────────────────────────────
function validatePin(input) {
  input.value = input.value.replace(/\D/g,'');
  if (input.value.length === 6) {
    input.classList.add('valid'); input.classList.remove('invalid');
  } else {
    input.classList.remove('valid');
  }
}

// ── VALIDATE CIN ─────────────────────────────
function validateCIN(input) {
  input.value = input.value.toUpperCase();
  const check = document.getElementById('cinCheck');
  const hint = document.getElementById('cinHint');
  if (input.value.length === 21) {
    input.classList.add('valid'); input.classList.remove('invalid');
    check.classList.add('show');
    hint.textContent = '✅ Valid CIN format'; hint.className = 'form__hint success';
  } else {
    input.classList.remove('valid');
    check.classList.remove('show');
    hint.textContent = `${input.value.length}/21 characters`; hint.className = 'form__hint';
  }
}

// ── VALIDATE GST ─────────────────────────────
function validateGST(input) {
  input.value = input.value.toUpperCase();
  const check = document.getElementById('gstCheck');
  const hint = document.getElementById('gstHint');
  if (input.value.length === 15) {
    input.classList.add('valid'); input.classList.remove('invalid');
    check.classList.add('show');
    hint.textContent = '✅ Valid GSTIN format'; hint.className = 'form__hint success';
  } else {
    input.classList.remove('valid');
    check.classList.remove('show');
    hint.textContent = `${input.value.length}/15 characters`; hint.className = 'form__hint';
  }
}

// ── VALIDATE PAN ─────────────────────────────
function validatePAN(input) {
  input.value = input.value.toUpperCase();
  const check = document.getElementById('panCheck');
  const hint = document.getElementById('panHint');
  const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
  if (panRegex.test(input.value)) {
    input.classList.add('valid'); input.classList.remove('invalid');
    check.classList.add('show');
    hint.textContent = '✅ Valid PAN format'; hint.className = 'form__hint success';
  } else {
    input.classList.remove('valid');
    check.classList.remove('show');
    hint.textContent = 'Format: AAAAA0000A'; hint.className = 'form__hint';
  }
}

// ── CORPORATE EMAIL VALIDATE ─────────────────
const blockedDomains = ['gmail','yahoo','hotmail','outlook','rediffmail','yopmail','tempmail'];
function validateCorpEmail(input) {
  const val = input.value.toLowerCase();
  const check = document.getElementById('emailDomainCheck');
  if (!val.includes('@')) { check.className = 'email-domain-check'; check.querySelector('span').textContent = 'Enter an email'; return; }
  const domain = val.split('@')[1];
  if (!domain) return;
  const domainName = domain.split('.')[0];
  if (blockedDomains.includes(domainName)) {
    input.classList.add('invalid'); input.classList.remove('valid');
    check.className = 'email-domain-check invalid';
    check.querySelector('span').textContent = `❌ ${domain} not allowed! Use a company email.`;
  } else if (domain.includes('.') && domain.length > 3) {
    input.classList.add('valid'); input.classList.remove('invalid');
    check.className = 'email-domain-check valid';
    check.querySelector('span').textContent = `✅ Valid corporate domain: @${domain}`;
  }
}

// ── PASSWORD STRENGTH ────────────────────────
function checkPwdStrength(pwd) {
  const bar = document.getElementById('pwdBar');
  const lbl = document.getElementById('pwdLbl');
  let s = 0;
  if (pwd.length >= 8) s++;
  if (/[A-Z]/.test(pwd)) s++;
  if (/[0-9]/.test(pwd)) s++;
  if (/[^A-Za-z0-9]/.test(pwd)) s++;
  const pct = ['0%','25%','50%','75%','100%'][s];
  const colors = ['#e5e7eb','#dc2626','#f97316','#eab308','#16a34a'];
  const labels = ['','Weak 😟','Fair 🙂','Good 👍','Strong 💪'];
  bar.style.width = pct; bar.style.background = colors[s];
  lbl.textContent = labels[s]; lbl.style.color = colors[s];
}

function checkPwdMatch() {
  const p1 = document.getElementById('empPwd1').value;
  const p2 = document.getElementById('empPwd2').value;
  const hint = document.getElementById('pwdMatchHint');
  if (!p2) { hint.textContent = ''; return; }
  if (p1 === p2) { hint.textContent = '✅ Passwords match!'; hint.className = 'form__hint success'; }
  else { hint.textContent = '❌ Does not match'; hint.className = 'form__hint error'; }
}

function togglePwd(id, btn) {
  const el = document.getElementById(id);
  el.type = el.type === 'password' ? 'text' : 'password';
  btn.textContent = el.type === 'password' ? '👁️' : '🙈';
}

// ── CAPTCHA ──────────────────────────────────
function onCaptchaChange() {
  const ok = document.getElementById('empCaptcha').checked;
  document.getElementById('captchaOk').style.display = ok ? 'block' : 'none';
}

// ── OTP ──────────────────────────────────────
// ── FINAL SUBMIT (client-side pre-check only) ─
// NOTE: కంపెనీ రిజిస్ట్రేషన్ ఇప్పుడు నిజమైన Django <form method="post">
// ద్వారా సర్వర్ కి డైరెక్ట్ గా సబ్మిట్ అవుతుంది (accounts/views.py లోని
// EmployerRegistrationView.post()). ఇంతకుముందు ఇక్కడ ఉన్న fake
// Corporate-OTP-verify ఫంక్షన్లు (sendCorporateOTP/verifyOTP/
// finalizeRegistration వంటివి) తీసివేశాం -- నిజమైన SMS/Email సర్వీస్
// లేకుండా అవి కేవలం UI నటనే తప్ప నిజంగా దేన్నీ verify చేయలేదు, పైగా
// ఇప్పుడు ఏ బటన్ నుండి కూడా కాల్ కావు (dead code). పాస్‌వర్డ్/రీక్యాప్చా/
// టర్మ్స్ చెక్ మాత్రం ఇక్కడ validateEmployerForm() లో నిజంగానే
// (UX కోసం) ఉంచాం -- ఇది <form onsubmit="return validateEmployerForm()">
// నుండి కాల్ అవుతుంది.
function validateEmployerForm() {
  const captcha = document.getElementById('empCaptcha').checked;
  const terms = document.getElementById('empTerms').checked;
  const p1 = document.getElementById('empPwd1').value;
  const p2 = document.getElementById('empPwd2').value;

  if (!p1 || p1.length < 8) { alert('⚠️ Please set a strong password (8+ characters)!'); return false; }
  if (p1 !== p2) { alert('⚠️ Passwords do not match!'); return false; }
  if (!captcha) { alert('⚠️ Please verify the reCAPTCHA!'); return false; }
  if (!terms) { alert('⚠️ Please accept the Terms & Conditions!'); return false; }
  return true;
}

// ── TERMS & PRIVACY MODAL SYSTEM ──────────────
let termsRead = false;
let privacyRead = false;
let currentCheckbox = null;

function openTermsModal(checkboxId) {
  currentCheckbox = checkboxId || null;
  // Reset read state for this open
  const body = document.getElementById('termsBody');
  const fill = document.getElementById('termsFill');
  const btn = document.getElementById('termsAcceptBtn');
  const text = document.getElementById('termsProgressText');
  if (!termsRead) {
    if (fill) fill.style.width = '0%';
    if (btn) btn.disabled = true;
    if (text) text.textContent = 'Scroll down to read all terms before accepting';
    if (body) body.scrollTop = 0;
  } else {
    if (fill) fill.style.width = '100%';
    if (btn) btn.disabled = false;
    if (text) text.textContent = '✅ You have read the Terms of Service';
  }
  document.getElementById('termsOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function openPrivacyModal(checkboxId) {
  currentCheckbox = checkboxId || null;
  const body = document.getElementById('privacyBody');
  const fill = document.getElementById('privacyFill');
  const btn = document.getElementById('privacyAcceptBtn');
  const text = document.getElementById('privacyProgressText');
  if (!privacyRead) {
    if (fill) fill.style.width = '0%';
    if (btn) btn.disabled = true;
    if (text) text.textContent = 'Scroll down to read all privacy policy before accepting';
    if (body) body.scrollTop = 0;
  } else {
    if (fill) fill.style.width = '100%';
    if (btn) btn.disabled = false;
    if (text) text.textContent = '✅ You have read the Privacy Policy';
  }
  document.getElementById('privacyOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeTermsModal() {
  document.getElementById('termsOverlay').classList.remove('open');
  document.body.style.overflow = '';
}

function closePrivacyModal() {
  document.getElementById('privacyOverlay').classList.remove('open');
  document.body.style.overflow = '';
}

function trackReadProgress(type) {
  const bodyId = type === 'terms' ? 'termsBody' : 'privacyBody';
  const fillId = type === 'terms' ? 'termsFill' : 'privacyFill';
  const btnId = type === 'terms' ? 'termsAcceptBtn' : 'privacyAcceptBtn';
  const textId = type === 'terms' ? 'termsProgressText' : 'privacyProgressText';
  const body = document.getElementById(bodyId);
  if (!body) return;
  const scrolled = body.scrollTop;
  const total = body.scrollHeight - body.clientHeight;
  const pct = total > 0 ? Math.min(100, Math.round((scrolled / total) * 100)) : 100;
  const fill = document.getElementById(fillId);
  const btn = document.getElementById(btnId);
  const text = document.getElementById(textId);
  if (fill) fill.style.width = pct + '%';
  if (pct >= 90) {
    if (type === 'terms') termsRead = true;
    else privacyRead = true;
    if (btn) btn.disabled = false;
    if (text) text.textContent = '✅ You have read the ' + (type === 'terms' ? 'Terms of Service' : 'Privacy Policy');
  } else {
    if (text) text.textContent = pct + '% read — please scroll to the bottom to accept';
  }
}

function acceptTerms(type) {
  const targetCb = currentCheckbox ? document.getElementById(currentCheckbox) : null;
  if (type === 'terms') {
    termsRead = true;
    closeTermsModal();
    // If privacy not yet read, prompt it next
    if (!privacyRead) {
      setTimeout(() => openPrivacyModal(currentCheckbox), 300);
      return;
    }
  } else {
    privacyRead = true;
    closePrivacyModal();
  }
  // Both read — tick the checkbox
  if (termsRead && privacyRead && targetCb) {
    targetCb.checked = true;
  }
}

// Intercept checkbox click — open modal first
function handleTermsCheckbox(event, checkboxId) {
  const cb = event.target;
  if (cb.checked) {
    if (termsRead && privacyRead) {
      cb.checked = true; // both already read — allow
      return;
    }
    cb.checked = false; // prevent check until both read
    if (!termsRead) {
      openTermsModal(checkboxId);
    } else if (!privacyRead) {
      openPrivacyModal(checkboxId);
    }
  }
}
