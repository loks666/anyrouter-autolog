const dishGrid = document.querySelector('#order-dishes');
const adminList = document.querySelector('#admin-dishes');
const totalEl = document.querySelector('#order-total');
const orderMessage = document.querySelector('#order-message');
const submitOrderBtn = document.querySelector('#submit-order');
const customerNameInput = document.querySelector('#customer-name');

const dishForm = document.querySelector('#dish-form');
const dishIdInput = document.querySelector('#dish-id');
const dishNameInput = document.querySelector('#dish-name');
const dishDescriptionInput = document.querySelector('#dish-description');
const dishPriceInput = document.querySelector('#dish-price');
const dishImageInput = document.querySelector('#dish-image');
const dishAvailableInput = document.querySelector('#dish-available');
const resetDishBtn = document.querySelector('#reset-dish');

const logList = document.querySelector('#log-list');
const refreshLogsBtn = document.querySelector('#refresh-logs');

let dishes = [];

const formatPrice = (price) => `¥${Number(price).toFixed(2)}`;

const fetchDishes = async () => {
  const response = await fetch('/api/dishes');
  dishes = await response.json();
  renderDishes();
  renderAdminList();
};

const renderDishes = () => {
  dishGrid.innerHTML = '';
  dishes.forEach((dish) => {
    const card = document.createElement('div');
    card.className = 'dish-card';
    const imageUrl = dish.image_url || '/static/images/placeholder.svg';
    card.innerHTML = `
      <img src="${imageUrl}" alt="${dish.name}" />
      <h3>${dish.name}</h3>
      <p>${dish.description || '暂无描述'}</p>
      <div class="price">${formatPrice(dish.price)}</div>
      <div class="quantity">
        <label>数量</label>
        <input type="number" min="0" value="0" data-id="${dish.id}" ${
          dish.available ? '' : 'disabled'
        } />
      </div>
    `;
    if (!dish.available) {
      card.classList.add('disabled');
      const badge = document.createElement('span');
      badge.textContent = '已下架';
      badge.className = 'tag';
      card.appendChild(badge);
    }
    dishGrid.appendChild(card);
  });
  dishGrid.querySelectorAll('input[type="number"]').forEach((input) => {
    input.addEventListener('input', updateTotal);
  });
  updateTotal();
};

const updateTotal = () => {
  let total = 0;
  dishGrid.querySelectorAll('input[type="number"]').forEach((input) => {
    const quantity = Number(input.value || 0);
    if (!quantity) return;
    const dish = dishes.find((item) => item.id === Number(input.dataset.id));
    if (!dish) return;
    total += dish.price * quantity;
  });
  totalEl.textContent = formatPrice(total);
};

const submitOrder = async () => {
  orderMessage.textContent = '';
  const customerName = customerNameInput.value.trim();
  if (!customerName) {
    orderMessage.textContent = '请输入客户姓名。';
    return;
  }
  const items = [];
  dishGrid.querySelectorAll('input[type="number"]').forEach((input) => {
    const quantity = Number(input.value || 0);
    if (quantity <= 0) return;
    items.push({ dish_id: Number(input.dataset.id), quantity });
  });
  if (!items.length) {
    orderMessage.textContent = '请选择至少一道菜品。';
    return;
  }
  submitOrderBtn.disabled = true;
  try {
    const response = await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_name: customerName, items }),
    });
    if (!response.ok) {
      const error = await response.json();
      orderMessage.textContent = error.detail || '提交失败';
      return;
    }
    const data = await response.json();
    orderMessage.textContent = `订单已创建，总计 ${formatPrice(data.total)}`;
    dishGrid.querySelectorAll('input[type="number"]').forEach((input) => {
      input.value = 0;
    });
    updateTotal();
    await refreshLogs();
  } finally {
    submitOrderBtn.disabled = false;
  }
};

const renderAdminList = () => {
  adminList.innerHTML = '';
  dishes.forEach((dish) => {
    const row = document.createElement('div');
    row.className = 'admin-item';
    row.innerHTML = `
      <div>
        <strong>${dish.name}</strong>
        <div><span>${formatPrice(dish.price)}</span> · <span>${
          dish.available ? '上架中' : '已下架'
        }</span></div>
      </div>
      <div class="admin-actions">
        <button data-action="edit" data-id="${dish.id}">编辑</button>
        <button data-action="delete" data-id="${dish.id}">删除</button>
      </div>
    `;
    adminList.appendChild(row);
  });

  adminList.querySelectorAll('button').forEach((button) => {
    button.addEventListener('click', handleAdminAction);
  });
};

const handleAdminAction = async (event) => {
  const action = event.target.dataset.action;
  const dishId = Number(event.target.dataset.id);
  const dish = dishes.find((item) => item.id === dishId);
  if (!dish) return;
  if (action === 'edit') {
    dishIdInput.value = dish.id;
    dishNameInput.value = dish.name;
    dishDescriptionInput.value = dish.description || '';
    dishPriceInput.value = dish.price;
    dishImageInput.value = dish.image_url || '';
    dishAvailableInput.checked = dish.available;
  }
  if (action === 'delete') {
    const confirmDelete = window.confirm(`确定删除 ${dish.name} 吗？`);
    if (!confirmDelete) return;
    await fetch(`/api/dishes/${dish.id}`, { method: 'DELETE' });
    await fetchDishes();
    await refreshLogs();
  }
};

const resetDishForm = () => {
  dishForm.reset();
  dishIdInput.value = '';
  dishAvailableInput.checked = true;
};

const submitDishForm = async (event) => {
  event.preventDefault();
  const payload = {
    name: dishNameInput.value.trim(),
    description: dishDescriptionInput.value.trim() || null,
    price: Number(dishPriceInput.value || 0),
    image_url: dishImageInput.value.trim() || null,
    available: dishAvailableInput.checked,
  };
  const dishId = dishIdInput.value;
  const endpoint = dishId ? `/api/dishes/${dishId}` : '/api/dishes';
  const method = dishId ? 'PUT' : 'POST';
  const response = await fetch(endpoint, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json();
    alert(error.detail || '保存失败');
    return;
  }
  resetDishForm();
  await fetchDishes();
  await refreshLogs();
};

const refreshLogs = async () => {
  const response = await fetch('/api/logs?limit=20');
  const logs = await response.json();
  logList.innerHTML = '';
  logs.forEach((log) => {
    const item = document.createElement('li');
    item.innerHTML = `<strong>${log.action}</strong> · ${log.detail} <div>${
      log.created_at
    }</div>`;
    logList.appendChild(item);
  });
};

submitOrderBtn.addEventListener('click', submitOrder);
dishForm.addEventListener('submit', submitDishForm);
resetDishBtn.addEventListener('click', resetDishForm);
refreshLogsBtn.addEventListener('click', refreshLogs);

fetchDishes();
refreshLogs();
