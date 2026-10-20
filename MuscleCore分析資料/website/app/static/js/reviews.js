(() => {
  'use strict';
  const channel = typeof BroadcastChannel === 'function' ? new BroadcastChannel('vibecart-ratings') : null;
  function updateRating(data) {
    document.querySelectorAll('[data-product-rating]').forEach(node => {
      if (node.dataset.productRating === data.product_id) node.textContent = `★ ${Number(data.rating).toFixed(1)}`;
    });
    document.querySelectorAll('[data-rating-count]').forEach(node => {
      if (node.dataset.ratingCount === data.product_id) node.textContent = `（${data.rating_count}筆評價）`;
    });
    document.querySelectorAll('[data-rating-default]').forEach(node => {
      if (node.dataset.ratingDefault === data.product_id) node.remove();
    });
  }
  let refreshing = false;
  async function refreshRecommendations() {
    const blocks = document.getElementById('recommendation-blocks');
    if (!blocks || refreshing) return;
    refreshing = true;
    try {
      const response = await fetch(blocks.dataset.refreshUrl, {cache: 'no-store'});
      if (response.ok && response.headers.get('Content-Type')?.includes('text/html')) blocks.innerHTML = await response.text();
    } catch (_) { /* Keep the last confirmed recommendations on network failure. */ }
    finally { refreshing = false; }
  }
  if (channel) channel.onmessage = event => { updateRating(event.data); refreshRecommendations(); };
  window.addEventListener('focus', refreshRecommendations);
  window.addEventListener('pageshow', event => { if (event.persisted) window.location.reload(); });
  document.querySelectorAll('[data-review-form]').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      if (button.disabled) return;
      button.disabled = true;
      const status = form.querySelector('[data-review-status]');
      status.textContent = '正在送出評價…';
      const values = new FormData(form);
      try {
        const response = await fetch(form.action, {method: 'POST', headers: {
          'Content-Type': 'application/json', 'X-CSRF-Token': values.get('csrf_token')
        }, body: JSON.stringify({rating: Number(values.get('rating')), title: values.get('title'), content: values.get('content')})});
        if (response.redirected || !response.headers.get('Content-Type')?.includes('application/json')) {
          throw new Error('登入或表單已失效，請重新載入頁面。');
        }
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || '評價未送出，請稍後重試。');
        updateRating(data);
        channel?.postMessage(data);
        refreshRecommendations();
        form.querySelectorAll('input, select, textarea').forEach(node => { node.disabled = true; });
        status.textContent = '評價已送出，商品星等已更新。';
      } catch (error) {
        status.textContent = error.message || '連線中斷，請保留相同星等與內容重試。';
        button.disabled = false;
      }
    });
  });
})();
