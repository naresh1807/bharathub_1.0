let expCount=1, isFresher=true;

// ── STEP NAV ──
function go(n){
  if(n===2&&!v1())return;
  if(n===3&&!v2())return;
  if(n===4&&!v3())return;
  for(let i=1;i<=4;i++){
    const el=document.getElementById('s'+i);
    if(el)el.style.display=i===n?'block':'none';
    const ind=document.getElementById('si'+i);
    if(ind){ind.classList.remove('active','done');if(i<n)ind.classList.add('done');if(i===n)ind.classList.add('active');}
  }
  window.scrollTo({top:0,behavior:'smooth'});
}

// ── VALIDATIONS ──
function v1(){
  const name=document.getElementById('f_name').value.trim();
  const mob=document.getElementById('f_mobile').value.replace(/\D/g,'');
  const email=document.getElementById('f_email').value.trim();
  const dob=document.getElementById('f_dob').value;
  const gender=document.getElementById('f_gender').value;
  if(!name)return err(1,'Please enter your full name!');
  if(name.length<2)return err(1,'Please enter a valid name!');
  if(!mob||mob.length!==10||!/^[6-9]/.test(mob))return err(1,'Please enter a valid 10-digit mobile number!');
  if(!email)return err(1,'Please enter your email address!');
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))return err(1,'Please enter a valid email format!');
  if(!dob)return err(1,'Please select your Date of Birth!');
  if(!gender)return err(1,'Please select your Gender!');
  hideErr(1);return true;
}
function v2(){
  if(!document.getElementById('f_qual').value)return err(2,'Please select your Qualification!');
  hideErr(2);return true;
}
function v3(){return true;}
function v4(){
  const p1=document.getElementById('f_p1').value;
  const p2=document.getElementById('f_p2').value;
  if(!p1||p1.length<8){alert('⚠️ Password must be at least 8 characters!');return false;}
  if(p1!==p2){alert('⚠️ Passwords do not match!');return false;}
  if(!document.getElementById('captcha').checked){alert('⚠️ Please verify the CAPTCHA!');return false;}
  if(!document.getElementById('terms').checked){alert('⚠️ Please accept the Terms & Conditions!');return false;}
  return true;
}
function err(n,m){const a=document.getElementById('a'+n);const am=document.getElementById('a'+n+'m');if(a&&am){am.textContent=m;a.classList.add('show');}return false;}
function hideErr(n){const a=document.getElementById('a'+n);if(a)a.classList.remove('show');}

// ── MARITAL ──
// ఇంతకుముందు ఇది married/unmarried ని బట్టి Father's Name / Spouse's
// Name ఫీల్డ్స్ ని టోగుల్ చేసేది -- ఇప్పుడు Father's Name ఎప్పుడూ
// ఒకే ఫీల్డ్ గా (మారిటల్ స్టేటస్ తో సంబంధం లేకుండా) కనిపిస్తుంది
// కాబట్టి, ఇది కేవలం ఎంచుకున్న ఆప్షన్ కి "sel" (హైలైట్) క్లాస్ మాత్రమే
// జోడిస్తుంది.
function selMarital(t,el){
  document.querySelectorAll('.mopt').forEach(o=>o.classList.remove('sel'));
  el.classList.add('sel');
}

// ── PHOTO ──
function prevPhoto(inp){
  if(inp.files&&inp.files[0]){
    if(inp.files[0].size>2*1024*1024){alert('⚠️ Photo size must be less than 2MB!');return;}
    const r=new FileReader();
    r.onload=e=>{const p=document.getElementById('photoPrev');p.innerHTML=`<img src="${e.target.result}" alt="Photo">`;};
    r.readAsDataURL(inp.files[0]);
  }
}

// ── QUALIFICATION ──
function showQual(v){
  const tabs=document.getElementById('qtabs');
  tabs.style.display=v?'flex':'none';
  document.querySelectorAll('.qsec').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.qtab').forEach(t=>t.classList.remove('active'));
  if(v==='ssc')swQual('ssc');
  else if(v==='inter')swQual('inter');
  else if(v==='degree'||v==='pg')swQual('degree');
}
function swQual(t){
  document.querySelectorAll('.qsec').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.qtab').forEach(t2=>t2.classList.remove('active'));
  const s=document.getElementById('qs-'+t);
  const b=document.getElementById('qt-'+t);
  if(s)s.classList.add('active');
  if(b)b.classList.add('active');
}

// ── FRESHER TOGGLE ──
function togFresher(){
  const tog=document.getElementById('ftog');
  tog.classList.toggle('on');
  isFresher=tog.classList.contains('on');
  document.getElementById('expSec').classList.toggle('vis',!isFresher);
  document.getElementById('flbl').textContent=isFresher?'I am a Fresher 🎓':'I have Work Experience 💼';
  document.getElementById('fsub').textContent=isFresher?'No work experience — proceed directly to security verification':'Add your work experience details';
}

// ── EXPERIENCE ──
function calcDur(inp){
  const entry=inp.closest('.exp-entry');if(!entry)return;
  const from=entry.querySelector('.efrom').value;
  const to=entry.querySelector('.eto').value;
  const id=entry.id.split('-')[1];
  if(from&&to){
    const s=new Date(from),e=new Date(to);
    if(e<s){alert('⚠️ Relieving date cannot be before joining date!');inp.value='';return;}
    let m=(e.getFullYear()-s.getFullYear())*12+(e.getMonth()-s.getMonth());
    if(m<0)m=0;
    const y=Math.floor(m/12),rm=m%12;
    const b=document.getElementById('dur-'+id);
    const t=document.getElementById('dt-'+id);
    if(b)b.style.display='inline-flex';
    if(t)t.textContent=`${y} Years, ${rm} Months`;
  }
}
function addExp(){
  expCount++;
  const d=document.createElement('div');
  d.className='exp-entry';d.id='ex-'+expCount;
  d.innerHTML=`<div class="exp-hdr"><span class="exp-title">🏢 Company #${expCount}</span><button class="exp-rm" onclick="rmExp(${expCount})">❌ Remove</button></div>
    <div class="row"><div class="fg"><label class="lbl">Company Name</label><input type="text" class="inp" placeholder="Company name"></div><div class="fg"><label class="lbl">Position / Role</label><input type="text" class="inp" placeholder="Software Engineer"></div></div>
    <div class="row"><div class="fg"><label class="lbl">Joining Date</label><input type="date" class="inp efrom" oninput="calcDur(this)"></div><div class="fg"><label class="lbl">Relieving Date</label><input type="date" class="inp eto" oninput="calcDur(this)"></div></div>
    <div class="dur-badge" id="dur-${expCount}" style="display:none;">🕐 Total Duration: <span id="dt-${expCount}"></span></div>
    <div class="fg" style="margin-top:14px;"><label class="lbl">Core Skills Used</label><input type="text" class="inp" placeholder="Java, Python, React..."></div>`;
  document.getElementById('expList').appendChild(d);
}
function rmExp(id){const e=document.getElementById('ex-'+id);if(e)e.remove();}

// ── PASSWORD ──
function chkPwd(p){
  let s=0;
  if(p.length>=8)s++;if(/[A-Z]/.test(p))s++;if(/[0-9]/.test(p))s++;if(/[^A-Za-z0-9]/.test(p))s++;
  const c=['#e5e7eb','#dc2626','#f97316','#eab308','#16a34a'];
  const l=['','Weak 😟','Fair 🙂','Good 👍','Strong 💪'];
  const pc=['0%','25%','50%','75%','100%'];
  const bar=document.getElementById('pbar');const lbl=document.getElementById('plbl');
  if(bar){bar.style.width=pc[s];bar.style.background=c[s];}
  if(lbl){lbl.textContent=l[s];lbl.style.color=c[s];}
}
function chkMatch(){
  const p1=document.getElementById('f_p1').value;
  const p2=document.getElementById('f_p2').value;
  const h=document.getElementById('pmatch');
  if(!p2){h.textContent='';return;}
  if(p1===p2){h.textContent='✅ Passwords match!';h.className='hint hint-ok';}
  else{h.textContent='❌ Does not match';h.className='hint hint-err';}
}
function togPwd(id,btn){
  const e=document.getElementById(id);if(!e)return;
  e.type=e.type==='password'?'text':'password';
  btn.textContent=e.type==='password'?'👁️':'🙈';
}

// ── CAPTCHA ──
function onCaptcha(){
  document.getElementById('captchaOk').style.display=document.getElementById('captcha').checked?'block':'none';
}

// ── OTP గమనిక ──
// NOTE: రిజిస్ట్రేషన్ ఇప్పుడు నిజమైన Django <form method="post"> ద్వారా
// నేరుగా సర్వర్ కి సబ్మిట్ అవుతుంది (accounts/views.py లోని
// EmployeeRegistrationView.post()), కాబట్టి ఇక్కడ ఇంతకుముందు ఉన్న
// fake-OTP-verify JS ఫంక్షన్లు (sendOTP/vrfOtp/finalize వంటివి) ఇక
// అవసరం లేక తొలగించాం -- అవి ఇప్పుడు ఏ బటన్ నుండి కూడా కాల్ కావు
// (dead code).

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
