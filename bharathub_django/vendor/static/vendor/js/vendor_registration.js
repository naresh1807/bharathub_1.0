// ── STEP NAVIGATION ────────────────────────
function goStep(n) {
  // Validate before moving forward
  if (n === 2 && !validateVndStep1()) return;
  if (n === 3 && !validateVndStep2()) return;
  if (n === 4 && !validateVndStep3()) return;

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

// ── VENDOR STEP VALIDATIONS ────────────────────────
function validateVndStep1() {
  const biz = document.querySelector('#step1 input[placeholder="Your shop/business name"]');
  const owner = document.querySelector('#step1 input[placeholder="Owner full name"]');
  const cat = document.querySelector('.cat-chip.selected');
  const gst = document.getElementById('gstInput') ? document.getElementById('gstInput').value.trim() : '';
  const pan = document.getElementById('panInput') ? document.getElementById('panInput').value.trim() : '';
  if (!biz || !biz.value.trim()) { alert('⚠️ Please enter the Business/Shop Name!'); return false; }
  if (!owner || !owner.value.trim()) { alert('⚠️ Please enter the Owner Name!'); return false; }
  if (!cat) { alert('⚠️ Please select the Vendor Category!'); return false; }
  if (!gst && !pan) { alert('⚠️ Please enter a GST Number or PAN Number!'); return false; }
  return true;
}
function validateVndStep2() {
  const state = document.querySelector('#step2 select');
  const city = document.querySelector('#step2 input[placeholder="City name"]');
  const pin = document.querySelector('#step2 input[placeholder="500001"]');
  const photos = document.getElementById('shopPhotoInput');
  if (!state || !state.value) { alert('⚠️ Please select the State!'); return false; }
  if (!city || !city.value.trim()) { alert('⚠️ Please enter the City!'); return false; }
  if (!pin || !pin.value.trim() || pin.value.length < 6) { alert('⚠️ Please enter a valid 6-digit PIN code!'); return false; }
  if (!photos || !photos.files || photos.files.length === 0) { alert('⚠️ Please upload the Shop Front Photo! (Mandatory)'); return false; }
  return true;
}
function validateVndStep3() { return true; }
function selectCat(el) {
  document.querySelectorAll('.cat-chip').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
}

// ── GST VALIDATE ─────────────────────────────
function validateGST(input) {
  input.value = input.value.toUpperCase();
  const v = document.getElementById('gstVerify');
  if (input.value.length === 15) {
    input.classList.add('valid'); input.classList.remove('invalid');
    v.className = 'verify-row valid';
    v.querySelector('span').textContent = '✅ Valid GSTIN format';
  } else {
    input.classList.remove('valid');
    v.className = 'verify-row';
    v.querySelector('span').textContent = `${input.value.length}/15 characters`;
  }
}

// ── PAN VALIDATE ──────────────────────────────
function validatePAN(input) {
  input.value = input.value.toUpperCase();
  const v = document.getElementById('panVerify');
  const regex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
  if (regex.test(input.value)) {
    input.classList.add('valid'); input.classList.remove('invalid');
    v.className = 'verify-row valid';
    v.querySelector('span').textContent = '✅ Valid PAN format';
  } else {
    input.classList.remove('valid');
    v.className = 'verify-row';
    v.querySelector('span').textContent = 'Format: AAAAA0000A';
  }
}

// ── PHOTO PREVIEW ────────────────────────────
function previewShopPhotos(input) {
  const grid = document.getElementById('photoPreviewGrid');
  grid.innerHTML = '';
  if (input.files) {
    Array.from(input.files).forEach(file => {
      const reader = new FileReader();
      reader.onload = e => {
        const img = document.createElement('img');
        img.src = e.target.result;
        img.className = 'photo-preview-item';
        img.title = file.name;
        grid.appendChild(img);
      };
      reader.readAsDataURL(file);
    });
    document.getElementById('shopPhotoZone').style.borderColor = 'var(--success)';
  }
}

// ── CATALOG TABLE ────────────────────────────
let catCount = 1;
function addCatalogItem() {
  catCount++;
  const tbody = document.getElementById('catalogBody');
  const row = document.createElement('tr');
  row.id = 'cat-' + catCount;
  row.innerHTML = `
    <td style="font-weight:700;color:var(--primary);">${catCount}</td>
    <td><input type="text" placeholder="Product/Service name"></td>
    <td><select><option>Software</option><option>Hardware</option><option>Service</option><option>Supply</option><option>Training</option><option>Catering</option></select></td>
    <td><input type="number" placeholder="1500"></td>
    <td><select><option>Per Unit</option><option>Per Hour</option><option>Per Day</option><option>Per Month</option><option>Per Year</option><option>Fixed</option></select></td>
    <td><input type="text" placeholder="Brief description"></td>
    <td><button class="btn-remove" onclick="removeCatalogItem(${catCount})">❌</button></td>
  `;
  tbody.appendChild(row);
}
function removeCatalogItem(id) {
  const row = document.getElementById('cat-' + id);
  if (row) row.remove();
}

// ── PASSWORD ──────────────────────────────────
function togglePwd(id, btn) {
  const el = document.getElementById(id);
  el.type = el.type === 'password' ? 'text' : 'password';
  btn.textContent = el.type === 'password' ? '👁️' : '🙈';
}
function checkPwdStrength(pwd) {
  const bar = document.getElementById('pwdBar');
  const lbl = document.getElementById('pwdLbl');
  let s = 0;
  if (pwd.length >= 8) s++;
  if (/[A-Z]/.test(pwd)) s++;
  if (/[0-9]/.test(pwd)) s++;
  if (/[^A-Za-z0-9]/.test(pwd)) s++;
  const pcts = ['0%','25%','50%','75%','100%'];
  const colors = ['#e5e7eb','#dc2626','#f97316','#eab308','#16a34a'];
  const labels = ['','Weak 😟','Fair 🙂','Good 👍','Strong 💪'];
  bar.style.width = pcts[s]; bar.style.background = colors[s];
  lbl.textContent = labels[s]; lbl.style.color = colors[s];
}
function checkPwdMatch() {
  const p1 = document.getElementById('vndPwd1').value;
  const p2 = document.getElementById('vndPwd2').value;
  const hint = document.getElementById('pwdMatchHint');
  if (!p2) { hint.textContent = ''; return; }
  if (p1 === p2) { hint.textContent = '✅ Passwords match!'; hint.style.color = 'var(--success)'; }
  else { hint.textContent = '❌ Does not match'; hint.style.color = 'var(--error)'; }
}

// ── FINAL SUBMIT (client-side pre-check only) ─
// NOTE: వెండర్ రిజిస్ట్రేషన్ ఇప్పుడు నిజమైన Django <form method="post">
// ద్వారా సర్వర్ కి డైరెక్ట్ గా సబ్మిట్ అవుతుంది (vendor/views.py లోని
// VendorRegistrationView.post()). ఇంతకుముందు ఇక్కడ ఉన్న fake
// Dual-OTP-verify ఫంక్షన్లు (sendDualOTP/verifyOTP/finalizeRegistration
// వంటివి) తీసివేశాం -- నిజమైన SMS/Email సర్వీస్ లేకుండా అవి కేవలం UI
// నటనే తప్ప నిజంగా దేన్నీ verify చేయలేదు, పైగా ఇప్పుడు ఏ బటన్ నుండి
// కూడా కాల్ కావు (dead code). పాస్‌వర్డ్/ఇమెయిల్-మొబైల్/రీక్యాప్చా/
// టర్మ్స్ చెక్ మాత్రం ఇక్కడ validateVendorForm() లో నిజంగానే (UX కోసం)
// ఉంచాం -- ఇది <form onsubmit="return validateVendorForm()"> నుండి
// కాల్ అవుతుంది.
function validateVendorForm() {
  const p1 = document.getElementById('vndPwd1').value;
  const p2 = document.getElementById('vndPwd2').value;
  const captcha = document.getElementById('vndCaptcha').checked;
  const terms = document.getElementById('vndTerms').checked;
  const email = document.getElementById('vendorEmail').value.trim();
  const mobile = document.getElementById('vendorMobile').value.trim();

  if (!email || !mobile) { alert('⚠️ Business Email and Mobile number are required!'); return false; }
  if (!p1 || p1.length < 8) { alert('⚠️ Password must be at least 8 characters!'); return false; }
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
