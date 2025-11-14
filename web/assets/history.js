const elH = {
  sportFilter: document.getElementById('sportFilter'),
  refreshBtn: document.getElementById('refreshHistoryBtn'),
  tableBody: document.getElementById('historyTbody'),
  detailPanel: document.getElementById('detailPanel'),
};

function setDetail(content, type = 'json') {
  elH.detailPanel.classList.remove('muted');
  if (type === 'json') {
    elH.detailPanel.textContent = JSON.stringify(content, null, 2);
  } else {
    elH.detailPanel.textContent = String(content);
  }
}

function setDetailLoading(msg = '加载详情...') {
  elH.detailPanel.classList.add('muted');
  elH.detailPanel.textContent = msg;
}

function fmtTime(iso) {
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

async function renderHistory() {
  const v = elH.sportFilter.value;
  const sport = v === 'all' ? undefined : v;
  const list = await api.listResults({ sport });
  if (!list || list.length === 0) {
    elH.tableBody.innerHTML = '<tr><td colspan="4" class="muted">暂无记录</td></tr>';
    return;
  }
  elH.tableBody.innerHTML = list.map(i => `
    <tr data-id="${i.id}">
      <td><code>${i.id}</code></td>
      <td>${i.sport}</td>
      <td>${(i.summary||'').replace(/</g,'&lt;')}</td>
      <td class="muted">${fmtTime(i.createdAt)}</td>
    </tr>
  `).join('');
}

function bindEvents() {
  elH.refreshBtn.addEventListener('click', renderHistory);
  elH.sportFilter.addEventListener('change', renderHistory);
  elH.tableBody.addEventListener('click', async (e) => {
    const tr = e.target.closest('tr[data-id]');
    if (!tr) return;
    const id = tr.getAttribute('data-id');
    try {
      setDetailLoading();
      const detail = await api.getResult(id);
      if (!detail) return setDetail('未找到记录', 'text');
      setDetail(detail, 'json');
    } catch (err) {
      setDetail(`获取详情失败：${err.message||err}`, 'text');
    }
  });
}

function init() {
  bindEvents();
  renderHistory();
}

init();