(() => {
  'use strict';
  document.querySelectorAll('[data-major-filter]').forEach(select => {
    select.addEventListener('change', () => { select.form.elements.category.value = ''; });
  });
  document.querySelectorAll('[data-quantity-control]').forEach(control => {
    const input = control.querySelector('input');
    control.querySelectorAll('[data-step]').forEach(button => button.addEventListener('click', () => {
      input.value = String(Math.max(Number(input.min), Math.min(Number(input.max), (Number(input.value) || 1) + Number(button.dataset.step))));
      input.dispatchEvent(new Event('input', {bubbles: true}));
    }));
  });
  document.querySelectorAll('[data-sku-form]').forEach(form => {
    const select = form.querySelector('[data-sku-select]');
    const quantity = form.elements.quantity;
    const button = form.querySelector('button[type="submit"]');
    const section = form.closest('.detail');
    const initialPrice = section.querySelector('[data-sku-price]').textContent;
    const initialStock = section.querySelector('[data-sku-stock]').textContent;
    function update() {
      const option = select.selectedOptions[0];
      const stock = Number(option?.dataset.stock || 0);
      const selected = Boolean(option?.value);
      const available = selected && stock > 0 && !option.disabled;
      quantity.max = String(Math.min(99, stock));
      if (available) quantity.value = String(Math.max(1, Math.min(Number(quantity.value) || 1, Number(quantity.max))));
      quantity.disabled = !available;
      form.querySelectorAll('[data-step]').forEach(node => { node.disabled = !available; });
      button.disabled = !available;
      button.textContent = available ? '加入購物車' : select.disabled || selected ? '已售完，補貨中' : '請先選擇規格';
      section.querySelector('[data-sku-price]').textContent = selected ? `NT$ ${Number(option.dataset.price).toLocaleString('zh-TW', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : initialPrice;
      section.querySelector('[data-sku-stock]').textContent = selected ? `現有庫存：${stock}` : initialStock;
      form.querySelector('[data-sku-status]').textContent = available ? `本次最多可選 ${quantity.max} 件；結帳時會再次確認價格與庫存。` : select.disabled ? '商品已售完，補貨中。' : '請選擇規格。';
    }
    const sellable = Array.from(select.options).filter(option => option.value && !option.disabled);
    if (sellable.length === 1) select.value = sellable[0].value;
    select.addEventListener('change', update);
    update();
  });
})();
