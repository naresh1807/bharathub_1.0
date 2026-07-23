// ── PANEL SWITCH ─────────────────────────────
function showPanel(id) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── PASSWORD TOGGLE ──────────────────────────
function togglePwd(inputId, btn) {
  const input = document.getElementById(inputId);
  if (input.type === 'password') {
    input.type = 'text'; btn.textContent = '🙈';
  } else {
    input.type = 'password'; btn.textContent = '👁️';
  }
}

// ── CAPTCHA ──────────────────────────────────
// NOTE: లాగిన్ ఇప్పుడు నిజమైన Django <form method="post"> ద్వారా
// నేరుగా EmployeeLoginView.post() కి సబ్మిట్ అవుతుంది, కాబట్టి
// ఇంతకుముందు ఉన్న fake "2FA OTP" మోడల్ ఫంక్షన్లు (doLogin/
// openLoginOtpModal/verifyLoginOTP వంటివి) తీసివేశాం -- అవి ఇక ఏ
// బటన్ నుండి కూడా కాల్ కావు (dead code). CAPTCHA-చెక్‌బాక్స్ లాగిన్
// బటన్‌ని enable/disable చేసే లాజిక్ మాత్రమే (UX కోసం) ఉంచాం.
function onCaptchaChange() {
  const checked = document.getElementById('loginCaptcha').checked;
  document.getElementById('loginBtn').disabled = !checked;
}
document.getElementById('loginBtn').disabled = true;

// ── CSRF HELPER (Django needs this header on every fetch POST) ──
function getCookie(name) {
  const match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return match ? decodeURIComponent(match.pop()) : '';
}
const CSRF_TOKEN = getCookie('csrftoken');

// ── FORGOT: STEP 1 VERIFY ────────────────────
function verifyIdentity() {
  const email = document.getElementById('forgotEmail').value.trim();
  const mobile = document.getElementById('forgotMobile').value.trim();
  const dob = document.getElementById('forgotDOB').value;

  hideError('verifyError');

  if (!email || !mobile || !dob) {
    showError('verifyError', 'Please enter Email, Mobile, and Date of Birth — all fields!');
    return;
  }

  fetch('/accounts/password/forgot/verify/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
    body: JSON.stringify({ role: 'employee', email, mobile, dob }),
  })
    .then(r => r.json())
    .then(data => {
      if (!data.ok) { showError('verifyError', data.error || 'Details did not match. Please check.'); return; }
      showForgotStep(2);
      startOtpCountdown();
    })
    .catch(() => showError('verifyError', 'Network error. Please try again.'));
}

// ── OTP COUNTDOWN ────────────────────────────
let otpTimerInterval;
function startOtpCountdown() {
  clearInterval(otpTimerInterval);
  let secs = 600; // 10 minutes
  otpTimerInterval = setInterval(() => {
    const m = Math.floor(secs / 60), s = secs % 60;
    const el = document.getElementById('otpCountdown');
    if (el) el.textContent = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    if (--secs < 0) {
      clearInterval(otpTimerInterval);
      if (el) { el.textContent = 'Expired ⚠️'; el.style.color = '#dc2626'; }
    }
  }, 1000);
}

function moveForgotOtp(input, idx) {
  input.classList.add('filled');
  const inputs = document.querySelectorAll('#forgot-step2 .otp-input');
  if (input.value && idx < 6) inputs[idx].focus();
}

function verifyForgotOTP() {
  const otp = Array.from(document.querySelectorAll('#forgot-step2 .otp-input')).map(i => i.value).join('');
  hideError('otpError');
  if (otp.length < 6) { showError('otpError', 'Please enter the complete 6-digit OTP!'); return; }

  fetch('/accounts/password/forgot/otp/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
    body: JSON.stringify({ otp }),
  })
    .then(r => r.json())
    .then(data => {
      if (!data.ok) { showError('otpError', data.error || 'Incorrect OTP. Please try again.'); return; }
      clearInterval(otpTimerInterval);
      showForgotStep(3);
    })
    .catch(() => showError('otpError', 'Network error. Please try again.'));
}

function resendOTP() {
  document.querySelectorAll('#forgot-step2 .otp-input').forEach(i => { i.value = ''; i.classList.remove('filled'); });
  startOtpCountdown();
  alert('✅ New OTP has been sent!');
}

// ── NEW PASSWORD ─────────────────────────────
function checkNewPwdStrength(pwd) {
  const bar = document.getElementById('newPwdBar');
  const label = document.getElementById('newPwdLabel');
  let s = 0;
  if (pwd.length >= 8) s++;
  if (/[A-Z]/.test(pwd)) s++;
  if (/[0-9]/.test(pwd)) s++;
  if (/[^A-Za-z0-9]/.test(pwd)) s++;
  const pct = ['0%','25%','50%','75%','100%'][s];
  const colors = ['#e5e7eb','#dc2626','#f97316','#eab308','#16a34a'];
  const labels = ['','Weak 😟','Fair 🙂','Good 👍','Strong 💪'];
  bar.style.width = pct; bar.style.background = colors[s];
  label.textContent = labels[s]; label.style.color = colors[s];
}

function checkPwdMatch() {
  const p1 = document.getElementById('newPwd').value;
  const p2 = document.getElementById('confirmPwd').value;
  const msg = document.getElementById('pwdMatchMsg');
  if (!p2) { msg.textContent = ''; return; }
  if (p1 === p2) {
    msg.textContent = '✅ Passwords match!'; msg.style.color = '#16a34a';
  } else {
    msg.textContent = '❌ Passwords do not match'; msg.style.color = '#dc2626';
  }
}

function resetPassword() {
  const p1 = document.getElementById('newPwd').value;
  const p2 = document.getElementById('confirmPwd').value;
  if (!p1 || !p2) { alert('Please enter your password!'); return; }
  if (p1 !== p2) { alert('Passwords do not match!'); return; }
  if (p1.length < 8) { alert('Password must be at least 8 characters!'); return; }

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

// ── STEP NAVIGATION ─────────────────────────
function showForgotStep(n) {
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById('forgot-step' + i);
    if (el) el.style.display = i === n ? 'block' : 'none';
    const dot = document.getElementById('dot' + i);
    if (dot) {
      dot.classList.remove('active','done');
      if (i < n) dot.classList.add('done');
      if (i === n) dot.classList.add('active');
    }
  }
}

// ── HELPERS ─────────────────────────────────
function showError(id, msg) {
  const el = document.getElementById(id);
  if (el) {
    const span = el.querySelector('span');
    if (span) span.textContent = msg;
    el.classList.add('show');
  }
}
function hideError(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('show');
}
