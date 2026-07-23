// ── PANEL SWITCH ─────────────────────────────
function showPanel(id) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── PASSWORD TOGGLE ──────────────────────────
function togglePwd(id, btn) {
  const el = document.getElementById(id);
  el.type = el.type === 'password' ? 'text' : 'password';
  btn.textContent = el.type === 'password' ? '👁️' : '🙈';
}

// ── CAPTCHA ──────────────────────────────────
function onCaptcha() {
  document.getElementById('loginBtn').disabled = !document.getElementById('loginCaptcha').checked;
}

// NOTE: లాగిన్ ఇప్పుడు నిజమైన Django <form method="post"> ద్వారా
// నేరుగా VendorLoginView.post() కి సబ్మిట్ అవుతుంది, కాబట్టి
// ఇంతకుముందు ఉన్న fake "2FA OTP" మోడల్ ఫంక్షన్లు (doLogin/
// openVndOtpModal/verifyLoginOTP వంటివి) తీసివేశాం -- అవి ఇక ఏ
// బటన్ నుండి కూడా కాల్ కావు (dead code).

// ── CSRF HELPER (Django needs this header on every fetch POST) ──
function getCookie(name) {
  const match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return match ? decodeURIComponent(match.pop()) : '';
}
const CSRF_TOKEN = getCookie('csrftoken');

// ── FORGOT: STEP 1 ───────────────────────────
function verifyIdentity() {
  const email = document.getElementById('fEmail').value.trim();
  const mobile = document.getElementById('fMobile').value.trim();
  const vndId = document.getElementById('fVndId').value.trim();
  hideAlert('verifyAlert');

  if (!email || !mobile || !vndId) {
    showAlert('verifyAlert', 'Please enter Email, Mobile, and Vendor ID — all fields!');
    return;
  }

  fetch('/accounts/password/forgot/verify/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
    body: JSON.stringify({ role: 'vendor', email, mobile, vendor_id: vndId }),
  })
    .then(r => r.json())
    .then(data => {
      if (!data.ok) { showAlert('verifyAlert', data.error || 'Details did not match. Please check.'); return; }
      showForgotStep(2);
      startForgotTimer();
    })
    .catch(() => showAlert('verifyAlert', 'Network error. Please try again.'));
}

// ── FORGOT OTP TIMER ─────────────────────────
let forgotTimerInterval;
function startForgotTimer() {
  clearInterval(forgotTimerInterval);
  let secs = 600;
  forgotTimerInterval = setInterval(() => {
    const m = Math.floor(secs/60), s = secs % 60;
    const el = document.getElementById('fOtpTimer');
    if (el) el.textContent = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    if (--secs < 0) {
      clearInterval(forgotTimerInterval);
      if (el) { el.textContent = 'Expired ⚠️'; el.style.color = 'var(--error)'; }
    }
  }, 1000);
}

function moveFOtp(input, idx) {
  input.classList.add('filled');
  if (input.value && idx < 6) document.querySelectorAll('#forgotOtpRow .otp-digit')[idx].focus();
}

function verifyForgotOTP() {
  const otp = Array.from(document.querySelectorAll('#forgotOtpRow .otp-digit')).map(i => i.value).join('');
  hideAlert('otpAlert');
  if (otp.length < 6) { showAlert('otpAlert', 'Please enter the complete 6-digit OTP!'); return; }

  fetch('/accounts/password/forgot/otp/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
    body: JSON.stringify({ otp }),
  })
    .then(r => r.json())
    .then(data => {
      if (!data.ok) { showAlert('otpAlert', data.error || 'Incorrect OTP. Please try again.'); return; }
      clearInterval(forgotTimerInterval);
      showForgotStep(3);
    })
    .catch(() => showAlert('otpAlert', 'Network error. Please try again.'));
}

function resendForgotOTP() {
  document.querySelectorAll('#forgotOtpRow .otp-digit').forEach(i => { i.value = ''; i.classList.remove('filled'); });
  startForgotTimer();
  alert('✅ New OTP has been sent!');
}

// ── STEP 3: NEW PASSWORD ─────────────────────
function checkPwdStr(pwd) {
  const bar = document.getElementById('newPwdBar');
  const lbl = document.getElementById('newPwdLbl');
  let s = 0;
  if (pwd.length >= 8) s++;
  if (/[A-Z]/.test(pwd)) s++;
  if (/[0-9]/.test(pwd)) s++;
  if (/[^A-Za-z0-9]/.test(pwd)) s++;
  const colors = ['#e5e7eb','#dc2626','#f97316','#eab308','#16a34a'];
  const labels = ['','Weak 😟','Fair 🙂','Good 👍','Strong 💪'];
  const pcts = ['0%','25%','50%','75%','100%'];
  bar.style.width = pcts[s]; bar.style.background = colors[s];
  lbl.textContent = labels[s]; lbl.style.color = colors[s];
}

function checkPwdMatch() {
  const p1 = document.getElementById('newPwd').value;
  const p2 = document.getElementById('confPwd').value;
  const msg = document.getElementById('pwdMatchMsg');
  if (!p2) { msg.textContent = ''; return; }
  if (p1 === p2) { msg.textContent = '✅ Passwords match!'; msg.style.color = 'var(--success)'; }
  else { msg.textContent = '❌ Does not match'; msg.style.color = 'var(--error)'; }
}

function resetPassword() {
  const p1 = document.getElementById('newPwd').value;
  const p2 = document.getElementById('confPwd').value;
  if (!p1 || p1.length < 8) { alert('Password must be at least 8 characters!'); return; }
  if (p1 !== p2) { alert('Passwords do not match!'); return; }

  fetch('/accounts/password/forgot/set/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
    body: JSON.stringify({ password: p1, confirm_password: p2 }),
  })
    .then(r => r.json())
    .then(data => {
      if (!data.ok) { alert(data.error || 'Password could not be reset. Please try again.'); return; }
      showForgotStep(4);
    })
    .catch(() => alert('Network error. Please try again.'));
}

// ── STEP NAVIGATION ──────────────────────────
function showForgotStep(n) {
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById('fstep' + i);
    if (el) el.style.display = i === n ? 'block' : 'none';
    const dot = document.getElementById('fd' + i);
    if (dot) {
      dot.classList.remove('active','done');
      if (i < n) dot.classList.add('done');
      if (i === n) dot.classList.add('active');
    }
  }
}

// ── HELPERS ──────────────────────────────────
function showAlert(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  const span = el.querySelector('span');
  if (span) span.textContent = msg;
  el.classList.add('show');
}
function hideAlert(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('show');
}
