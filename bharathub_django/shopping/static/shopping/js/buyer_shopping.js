/* ═══════════════════════════════════════════════════════════════════
   shopping/buyer_shopping.js
   Cart + checkout behaviour for the employer/buyer side of the B2B
   marketplace. Extracted from employers/static/employers/js/
   employer_dashboard.js -- this used to be the "shopping" and
   "myorders" JS tabs inside the giant single-page employer
   dashboard. They are now two separate real pages:
     /shop/shop.html        (browse + add to cart + checkout)
     /shop/my_orders.html   (track placed orders)
   This ONE file is loaded on BOTH pages so every function below is
   available on either.

   ✅ CHECKOUT IS NOW REAL (previously it was not):
   The cart itself still only lives in the browser's memory while the
   Shop page is open (adding to cart doesn't touch the server) --
   that part is unchanged and is fine, exactly like any normal
   e-commerce site's client-side cart. What used to be fake is
   "Proceed to Checkout": it used to fabricate a random order ID and
   push it into an in-memory `allOrders` array that lived only on
   that one page -- no Order/OrderItem was ever saved, and navigating
   to My Orders (a real page load) reset that array to empty, so the
   order you "just placed" would vanish.
   Now proceedCheckout() submits the cart (product_id + qty pairs) as
   a real POST to shopping:place_order (see shopping/views.py
   PlaceOrderView), which creates real Order/OrderItem rows, adjusts
   stock, and redirects to My Orders -- which now server-renders the
   actual DB records (see shopping/_my_orders_body.html). The old
   client-only order tracker (allOrders/renderOrdersList/
   updateOrderBadge/markDelivered/cancelOrder/reorderItems) has been
   removed since it's no longer needed.
   ═══════════════════════════════════════════════════════════════════ */

// ── BUY NOW (direct instant checkout) ─────────
function buyNow(btn, productId, name, price, icon) {
  const card = btn.closest('.product-card');
  const qtyInp = card ? card.querySelector('.qty-input') : null;
  const qty = qtyInp ? (parseInt(qtyInp.value) || 1) : 1;

  cartItems[productId] = { productId, name, price, qty, icon };
  updateCartBadge();

  // Open cart modal directly at checkout state
  openCartModal();
}

// ── NOTIFY RESTOCK ─────────────────────────────
function notifyRestock(name) {
  alert('🔔 You will be notified when "' + name + '" is back in stock!\n\nWe will send an email to your registered corporate email.');
}

// ── SHOPPING FUNCTIONS ─────────────────────────
let cartItems = {}; // { productId: { productId, name, price, qty, icon } }
// చెక్‌అవుట్ మోడల్ లో యూజర్ టైప్ చేసిన/ఎడిట్ చేసిన డెలివరీ అడ్రస్ --
// cartChangeQty() లాంటివి మోడల్ ని re-render చేసినా విలువ పోకుండా
// ఇక్కడ ఉంచుతాం. మొదటిసారి employer.address తో ప్రీఫిల్ అవుతుంది
// (shop.html: window.BHARATHUB_EMPLOYER_ADDRESS).
let deliveryAddressValue = window.BHARATHUB_EMPLOYER_ADDRESS || '';

function changeQty(btn, delta) {
  const inp = btn.closest('div').querySelector('.qty-input');
  if (!inp) return;
  const max = parseInt(inp.getAttribute('max')) || 99;
  let val = parseInt(inp.value) || 1;
  val = Math.max(1, Math.min(max, val + delta));
  inp.value = val;
}

function addToCart(btn, productId, name, price, icon) {
  const card = btn.closest('.product-card');
  const qtyInp = card ? card.querySelector('.qty-input') : null;
  const qty = qtyInp ? (parseInt(qtyInp.value) || 1) : 1;

  if (cartItems[productId]) {
    cartItems[productId].qty += qty;
  } else {
    cartItems[productId] = { productId, name, price, qty, icon };
  }

  updateCartBadge();

  // Button feedback
  const orig = btn.textContent;
  btn.textContent = '✅ Added!';
  btn.style.background = 'var(--success)';
  btn.disabled = true;
  setTimeout(() => {
    btn.textContent = '🛒 Add to Cart';
    btn.style.background = '';
    btn.disabled = false;
  }, 1500);

  showCartToast(name, qty, price);
}

function updateCartBadge() {
  const total = Object.values(cartItems).reduce((s, i) => s + i.qty, 0);
  const el = document.getElementById('cartNum');
  if (el) el.textContent = total;
}

function showCartToast(name, qty, price) {
  const old = document.getElementById('cartToast');
  if (old) old.remove();
  const t = document.createElement('div');
  t.id = 'cartToast';
  t.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:600;background:linear-gradient(135deg,var(--primary),#2a4a7f);color:white;border-radius:12px;padding:14px 18px;box-shadow:0 8px 28px rgba(26,54,93,0.35);max-width:320px;animation:slideInToast 0.35s ease;display:flex;align-items:center;gap:12px;';
  t.innerHTML = `
    <span style="font-size:28px;">🛒</span>
    <div style="flex:1;">
      <div style="font-size:13px;font-weight:700;">Added to Cart!</div>
      <div style="font-size:12px;opacity:0.8;margin-top:2px;">${name} × ${qty} — ₹${(price*qty).toLocaleString('en-IN')}</div>
    </div>
    <button onclick="openCartModal()" style="background:var(--accent);border:none;color:white;border-radius:8px;padding:6px 12px;font-family:var(--font);font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap;">View Cart</button>
    <button onclick="this.closest('#cartToast').remove()" style="background:none;border:none;color:rgba(255,255,255,0.7);font-size:18px;cursor:pointer;padding:0;">✕</button>`;
  document.body.appendChild(t);
  setTimeout(() => { const x = document.getElementById('cartToast'); if (x) x.remove(); }, 4000);
}

function openCartModal() {
  let modal = document.getElementById('cartModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'cartModal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);backdrop-filter:blur(4px);z-index:500;display:flex;align-items:center;justify-content:center;padding:20px;';
    modal.onclick = (e) => { if (e.target === modal) closeCartModal(); };
    document.body.appendChild(modal);
  }
  renderCartModal(modal);
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
}

function renderCartModal(modal) {
  const items = Object.values(cartItems);
  const total = items.reduce((s, i) => s + i.price * i.qty, 0);
  const totalItems = items.reduce((s, i) => s + i.qty, 0);

  modal.innerHTML = `
    <div style="background:white;border-radius:18px;max-width:560px;width:100%;max-height:85vh;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 24px 64px rgba(0,0,0,0.2);animation:popIn 0.3s ease;">
      <!-- Header -->
      <div style="background:linear-gradient(135deg,var(--primary),#2a4a7f);padding:18px 24px;display:flex;align-items:center;justify-content:space-between;">
        <div>
          <div style="font-size:18px;font-weight:800;color:white;">🛒 Shopping Cart</div>
          <div style="font-size:12px;color:rgba(255,255,255,0.65);margin-top:2px;">${totalItems} items</div>
        </div>
        <button onclick="closeCartModal()" style="background:rgba(255,255,255,0.15);border:none;color:white;width:32px;height:32px;border-radius:50%;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;">✕</button>
      </div>

      <!-- Cart Items -->
      <div style="flex:1;overflow-y:auto;padding:16px;">
        ${items.length === 0 ? `
          <div style="text-align:center;padding:40px 20px;">
            <div style="font-size:56px;margin-bottom:12px;">🛒</div>
            <div style="font-size:16px;font-weight:700;color:var(--primary);">Cart is Empty!</div>
            <div style="font-size:13px;color:var(--muted);margin-top:6px;">Add products</div>
            <button onclick="closeCartModal()" style="margin-top:16px;background:var(--accent);color:white;border:none;border-radius:8px;padding:10px 22px;font-family:var(--font);font-size:13px;font-weight:600;cursor:pointer;">🛍️ Continue Shopping</button>
          </div>` : items.map(item => `
          <div style="display:flex;align-items:center;gap:14px;padding:14px;border-radius:12px;border:1px solid rgba(26,54,93,0.1);margin-bottom:10px;background:rgba(244,247,246,0.5);" id="cart-item-${item.productId}">
            <div style="width:52px;height:52px;border-radius:12px;background:rgba(26,54,93,0.07);display:flex;align-items:center;justify-content:center;font-size:26px;flex-shrink:0;">${item.icon}</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:13px;font-weight:700;color:var(--primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${item.name}</div>
              <div style="font-size:12px;color:var(--success);font-weight:600;margin-top:2px;">₹${item.price.toLocaleString('en-IN')} × ${item.qty} = ₹${(item.price*item.qty).toLocaleString('en-IN')}</div>
            </div>
            <div style="display:flex;align-items:center;border:1.5px solid rgba(26,54,93,0.15);border-radius:8px;overflow:hidden;flex-shrink:0;">
              <button onclick="cartChangeQty(${item.productId},-1)" style="width:30px;height:30px;border:none;background:var(--light-bg);cursor:pointer;font-size:16px;font-weight:700;color:var(--primary);">−</button>
              <span style="width:34px;text-align:center;font-size:13px;font-weight:700;color:var(--primary);">${item.qty}</span>
              <button onclick="cartChangeQty(${item.productId},1)" style="width:30px;height:30px;border:none;background:var(--light-bg);cursor:pointer;font-size:16px;font-weight:700;color:var(--primary);">+</button>
            </div>
            <button onclick="removeFromCart(${item.productId})" style="background:rgba(220,38,38,0.1);border:1px solid rgba(220,38,38,0.2);color:var(--error);border-radius:8px;width:32px;height:32px;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;flex-shrink:0;" title="Remove">🗑️</button>
          </div>`).join('')}
      </div>

      ${items.length > 0 ? `
      <!-- Footer -->
      <div style="border-top:1px solid rgba(26,54,93,0.1);padding:16px 20px;">
        <div style="margin-bottom:14px;">
          <label style="font-size:12px;font-weight:700;color:var(--primary);display:block;margin-bottom:6px;">📍 Delivery Address</label>
          <textarea id="deliveryAddressInput" oninput="deliveryAddressValue = this.value;" placeholder="Enter the full address this order should be delivered to..." style="width:100%;min-height:56px;border:1.5px solid rgba(26,54,93,0.15);border-radius:8px;padding:8px 10px;font-family:var(--font);font-size:12.5px;resize:vertical;">${deliveryAddressValue}</textarea>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <span style="font-size:13px;color:var(--muted);">Items (${totalItems})</span>
          <span style="font-size:13px;font-weight:600;">₹${total.toLocaleString('en-IN')}</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
          <span style="font-size:15px;font-weight:700;color:var(--primary);">Total Amount</span>
          <span style="font-size:20px;font-weight:800;color:var(--success);">₹${total.toLocaleString('en-IN')}</span>
        </div>
        <div style="display:flex;gap:10px;">
          <button onclick="closeCartModal()" style="flex:1;background:none;border:1.5px solid rgba(26,54,93,0.2);border-radius:10px;padding:12px;font-family:var(--font);font-size:14px;font-weight:600;color:var(--muted);cursor:pointer;">← Continue Shopping</button>
          <button onclick="proceedCheckout()" style="flex:2;background:linear-gradient(135deg,var(--accent),#ff8c00);color:white;border:none;border-radius:10px;padding:12px;font-family:var(--font);font-size:15px;font-weight:700;cursor:pointer;box-shadow:0 4px 14px rgba(255,153,0,0.35);">🚀 Proceed to Checkout</button>
        </div>
      </div>` : ''}
    </div>`;
}

function cartChangeQty(productId, delta) {
  if (!cartItems[productId]) return;
  cartItems[productId].qty = Math.max(1, cartItems[productId].qty + delta);
  updateCartBadge();
  const modal = document.getElementById('cartModal');
  if (modal) renderCartModal(modal);
}

function removeFromCart(productId) {
  delete cartItems[productId];
  updateCartBadge();
  const modal = document.getElementById('cartModal');
  if (modal) renderCartModal(modal);
}

function closeCartModal() {
  const modal = document.getElementById('cartModal');
  if (modal) modal.style.display = 'none';
  document.body.style.overflow = '';
}

// ── CHECKOUT (submits a real POST to shopping:place_order) ────────
function proceedCheckout() {
  const items = Object.values(cartItems);
  if (items.length === 0) { alert('⚠️ Cart is empty! Add products.'); return; }

  const addressInput = document.getElementById('deliveryAddressInput');
  const address = (addressInput ? addressInput.value : deliveryAddressValue).trim();
  if (!address) { alert('⚠️ Please enter a delivery address before placing the order.'); return; }
  deliveryAddressValue = address;

  const form = document.getElementById('checkoutForm');
  if (!form) { alert('⚠️ Checkout form not found, please refresh the page and try again.'); return; }

  // ఇంతకుముందు ఇక్కడ ఒక ఫేక్ ఆర్డర్ ఐడి తయారుచేసి in-memory array లో
  // పెట్టేవాళ్ళం -- ఇప్పుడు కార్ట్ లోని ప్రతి ఐటమ్ కీ ఒక product_id +
  // qty హిడెన్ ఇన్‌పుట్ జతని జోడించి, checkoutForm ని నిజంగా submit()
  // చేస్తాం. ఇది shopping:place_order కి POST అవుతుంది (real Order/
  // OrderItem create + stock decrement), తర్వాత My Orders పేజీ కి
  // రీడైరెక్ట్ అవుతుంది.
  form.querySelectorAll('input[name="product_id"], input[name="qty"], input[name="delivery_address"]').forEach(el => el.remove());

  const addressField = document.createElement('input');
  addressField.type = 'hidden';
  addressField.name = 'delivery_address';
  addressField.value = address;
  form.appendChild(addressField);

  items.forEach(item => {
    const pidInput = document.createElement('input');
    pidInput.type = 'hidden';
    pidInput.name = 'product_id';
    pidInput.value = item.productId;
    form.appendChild(pidInput);

    const qtyInput = document.createElement('input');
    qtyInput.type = 'hidden';
    qtyInput.name = 'qty';
    qtyInput.value = item.qty;
    form.appendChild(qtyInput);
  });

  form.submit();
}

function filterProducts(val) {
  document.querySelectorAll('.product-card').forEach(card => {
    const name = (card.dataset.name || '').toLowerCase();
    const text = card.textContent.toLowerCase();
    card.style.display = (!val || name.includes(val.toLowerCase()) || text.includes(val.toLowerCase())) ? 'block' : 'none';
  });
}

function filterCategory(cat, chip) {
  document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  document.querySelectorAll('.product-card').forEach(card => {
    card.style.display = (cat === 'all' || card.dataset.category === cat) ? 'block' : 'none';
  });
}

// ── SHARED PAGE HELPERS (needed on both shop.html and my_orders.html) ──

/* ── scrollToOrders() ──────────────────────────────────────────────
   Used on the My Orders page: scrolls to whichever of #ordersList /
   #ordersEmpty is currently visible (both are now server-rendered by
   Django -- see shopping/_my_orders_body.html). */
function scrollToOrders() {
  const list = document.getElementById('ordersList');
  const empty = document.getElementById('ordersEmpty');
  const target = list || empty;
  if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
