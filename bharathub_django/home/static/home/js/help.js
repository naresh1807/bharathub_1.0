function toggleFAQ(el) {
  const answer = el.nextElementSibling;
  const arrow = el.querySelector('.faq-arrow');
  answer.classList.toggle('open');
  arrow.classList.toggle('open');
}

function filterCat(cat, card) {
  document.querySelectorAll('.cat-card').forEach(c => c.classList.remove('active'));
  card.classList.add('active');
  document.querySelectorAll('.faq-section').forEach(s => {
    s.style.display = cat === 'all' || (s.dataset.cat && s.dataset.cat.includes(cat)) ? 'block' : 'none';
  });
}

function searchHelp(val) {
  const q = val.toLowerCase().trim();
  document.querySelectorAll('.faq-item').forEach(item => {
    const text = item.textContent.toLowerCase();
    item.style.display = !q || text.includes(q) ? 'block' : 'none';
  });
}
