// ── SECTION NAVIGATION ────────────────────────
// ── STAT CARD CLICK HELPERS ───────────────────
// (filterApplicationsByStatus() and scrollToCandidates() moved to
//  jobs/static/jobs/js/applications.js; scrollToOrders(), buyNow(),
//  addToCart() and the rest of the cart/checkout functions moved to
//  shopping/static/shopping/js/buyer_shopping.js -- Applications,
//  Shopping and My Orders are now their own pages instead of tabs
//  inside this dashboard.)
function showSection(id, tabEl, sidebarEl) {
  document.querySelectorAll('.section-page').forEach(s => s.classList.remove('active'));
  const target = id === 'postjob' ? 'postjob' : id;
  const el = document.getElementById('section-' + target);
  if (el) el.classList.add('active');

  if (tabEl) {
    document.querySelectorAll('.topnav__tab').forEach(t => t.classList.remove('active'));
    tabEl.classList.add('active');
  }
  if (sidebarEl) {
    document.querySelectorAll('.sidebar__item').forEach(t => t.classList.remove('active'));
    sidebarEl.classList.add('active');
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── JOB POST ─────────────────────────────────
// ఇంతకుముందు ఇక్కడ postJob() అనే ఫంక్షన్ ఉండేది -- అది కేవలం
// alert() చూపించి, ఏ డేటానీ ఎక్కడికీ పంపేది కాదు (పూర్తిగా JS మాక్).
// ఇప్పుడు "Post Job Now" / "Save as Draft" రెండూ నిజమైన
// <button type="submit" name="action" value="..."> బటన్లు (చూడండి
// employer_dashboard.html) -- నొక్కగానే బ్రౌజర్ ఫారమ్ ని నేరుగా
// employers/views.py కి POST చేస్తుంది, JS ఇక్కడ ఏమీ చేయనవసరం లేదు.
// సర్వర్ (Django) validate చేసి, DB లో save చేసి, success/error
// మెసేజ్ తో తిరిగి ఇదే పేజీ కి redirect చేస్తుంది.

// ── SKILL TAGS ───────────────────────────────
// ఎందుకు ఇలా మార్చాం: ముందు ఈ చిప్స్ UI కేవలం విజువల్ మాత్రమే --
// దేనికీ కనెక్ట్ కాలేదు, ఫారమ్ సబ్మిట్ అయినప్పుడు స్కిల్స్ డేటా
// ఎక్కడికీ వెళ్ళేది కాదు. ఇప్పుడు employers/forms.py లోని
// skills_required అనే దాచిన (hidden, style="display:none") ఫీల్డ్
// ఉంది -- ప్రతిసారి ఒక చిప్ యాడ్/రిమూవ్ అయినప్పుడు, ఆ దాచిన ఫీల్డ్
// value ని syncSkillsField() తాజాగా ఉంచుతుంది. ఫారమ్ సబ్మిట్ అయ్యేది
// ఈ దాచిన ఫీల్డ్ లో ఉన్న కామా-సెపరేటెడ్ టెక్స్ట్ నే.
function syncSkillsField() {
  const tags = document.querySelectorAll('#skillTagsInput .skill-tag');
  const skills = Array.from(tags).map(t => t.firstChild.textContent.trim());
  const hidden = document.getElementById('skillsRequiredField');
  if (hidden) hidden.value = skills.join(', ');
}

function addSkillTag(e) {
  if (e.key === 'Enter') {
    // Enter నొక్కినప్పుడు ఫారమ్ ఆటోమేటిక్‌గా సబ్మిట్ అవ్వకుండా ఆపడం --
    // లేకపోతే యూజర్ ఒక స్కిల్ టైప్ చేసి Enter నొక్కగానే మొత్తం జాబ్
    // ఫారమ్ (ఇంకా పూర్తిగా నింపకుండానే) సబ్మిట్ అయిపోతుంది.
    e.preventDefault();
    const input = document.getElementById('skillTagInput');
    const val = input.value.trim();
    if (!val) return;
    const tag = document.createElement('span');
    tag.className = 'skill-tag';
    tag.innerHTML = `${val} <button type="button" onclick="removeSkillTag(this)">✕</button>`;
    input.parentNode.insertBefore(tag, input);
    input.value = '';
    syncSkillsField();
  }
}
function removeSkillTag(btn) {
  btn.parentNode.remove();
  syncSkillsField();
}
// పేజీ లోడ్ అయినప్పుడు (ఉదా: వాలిడేషన్ ఎర్రర్ తర్వాత ఫారమ్ మళ్ళీ
// స్కిల్ చిప్స్‌తో redisplay అయినప్పుడు), హిడెన్ ఫీల్డ్ ని సర్వర్
// రెండర్ చేసిన చిప్స్ తో ఒకసారి sync చేసుకుంటాం.
document.addEventListener('DOMContentLoaded', syncSkillsField);

// ── VIDEO UPLOAD ──────────────────────────────
// (real dropzone handling now lives in videos/static/videos/js/video_feed.js
//  -- vfHandleFileSelect() -- since the "Videos" tab is a proper DB-backed
//  feature now, not a mock preview.)

// (updateStatus(), scheduleInterview() and switchView() moved to
//  jobs/static/jobs/js/applications.js along with the Applications page.
//  Every Chat/Mail function -- openChat(), sendMsg(), the mail
//  compose/folder functions, group-chat modal, etc. -- moved to
//  messaging/static/messaging/js/employer_messages.js along with
//  the Chat+Mail page.)

// ── MOBILE NAV ────────────────────────────────
function mobileNav(section, btn) {
  document.querySelectorAll('.mobile-nav-item').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  showSection(section);
}
// (initMobileChat() and closeMobileChat() moved to
//  messaging/static/messaging/js/employer_messages.js along with
//  the rest of the Chat UI.)

// logout() was removed -- it only did window.location.href to the login
// page without ever ending the Django session. The Logout button in
// employers/_nav.html is now a real POST <form> to accounts:logout,
// which calls django.contrib.auth.logout() server-side.
