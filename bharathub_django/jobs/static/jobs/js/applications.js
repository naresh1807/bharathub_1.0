/* ═══════════════════════════════════════════════════════════════════
   jobs/applications.js
   Behaviour for the "Applications" page (jobs app).

   Status changes (Shortlist / Interview / Reject) are now real
   server-side POST forms in jobs/_applications_body.html (see
   ApplicationStatusUpdateView in jobs/views.py) -- so the old
   updateStatus()/scheduleInterview() JS-only mock functions (which
   only repainted a badge client-side and never saved anything) have
   been removed. Only pure UI helpers remain here.
   ═══════════════════════════════════════════════════════════════════ */

function scrollToCandidates() {
  const grid = document.querySelector('.candidate-card');
  if (grid) grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function switchView(view) {
  document.getElementById('gridView').style.display = view === 'grid' ? 'grid' : 'none';
  document.getElementById('tableView').style.display = view === 'table' ? 'block' : 'none';
}

function logout() {
  window.location.href = '/employer_login.html';
}
