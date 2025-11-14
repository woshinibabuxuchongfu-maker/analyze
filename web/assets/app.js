/* 全局逻辑：绑定表单交互，调用 API，并渲染结果与历史 */

const el = {
  sport: document.getElementById('sport'),
  dataText: document.getElementById('dataText'),
  modelId: document.getElementById('modelId'),
  temperature: document.getElementById('temperature'),
  analyzeBtn: document.getElementById('analyzeBtn'),
  resultPanel: document.getElementById('resultPanel'),
  refreshHistoryBtn: document.getElementById('refreshHistoryBtn'),
  filterBySport: document.getElementById('filterBySport'),
  historyTbody: document.getElementById('historyTbody'),
  textInputWrap: document.getElementById('textInputWrap'),
};

function setResult(content, type = 'text') {
  el.resultPanel.classList.remove('muted');
  if (type === 'json') {
    el.resultPanel.textContent = JSON.stringify(content, null, 2);
  } else {
    el.resultPanel.textContent = String(content);
  }
}

function setLoading(msg = '分析中...') {
  el.resultPanel.classList.add('muted');
  el.resultPanel.textContent = `${msg}`;
}

// 仅保留文本输入

async function handleAnalyze() {
  try {
    el.analyzeBtn.disabled = true;
    setLoading(api.useMock ? '模拟分析中...' : '分析中...');

    const dataText = el.dataText.value.trim();
    if (!dataText) {
      alert('请输入数据文本');
      return;
    }

    const payload = {
      sport: el.sport.value,
      modelId: el.modelId.value.trim(),
      temperature: Number(el.temperature.value) || 0.3,
      dataText,
    };

    const res = await api.analyze(payload);
    setResult(res, 'json');
    await renderHistory();
  } catch (err) {
    console.error(err);
    setResult(`分析失败：${err.message || err}`);
  } finally {
    el.analyzeBtn.disabled = false;
  }
}

function fmtTime(iso) {
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

async function renderHistory() {
  const onlyCurrentSport = el.filterBySport.checked;
  const list = await api.listResults({ sport: onlyCurrentSport ? el.sport.value : undefined });
  if (!list || list.length === 0) {
    el.historyTbody.innerHTML = '<tr><td colspan="4" class="muted">暂无记录</td></tr>';
    return;
  }
  el.historyTbody.innerHTML = list.map(item => `
    <tr data-id="${item.id}">
      <td><code>${item.id}</code></td>
      <td>${item.sport}</td>
      <td>${item.summary ? item.summary.replace(/</g,'&lt;') : ''}</td>
      <td class="muted">${fmtTime(item.createdAt)}</td>
    </tr>
  `).join('');
}

function bindEvents() {
  el.analyzeBtn.addEventListener('click', handleAnalyze);
  el.refreshHistoryBtn.addEventListener('click', renderHistory);
  el.sport.addEventListener('change', renderHistory);

  // 点击历史行查看详情
  el.historyTbody.addEventListener('click', async (e) => {
    const tr = e.target.closest('tr[data-id]');
    if (!tr) return;
    const id = tr.getAttribute('data-id');
    try {
      setLoading('加载详情中...');
      const detail = await api.getResult(id);
      if (!detail) {
        setResult('未找到该结果');
        return;
      }
      setResult(detail, 'json');
    } catch (err) {
      setResult(`获取详情失败：${err.message || err}`);
    }
  });
}

function init() {
  bindEvents();
  renderHistory();
  // 顶部模式徽章
  try {
    const header = document.querySelector('.app-header');
    if (header) {
      const badge = document.createElement('span');
      badge.className = 'badge' + (api.useMock ? ' ok' : '');
      badge.style.marginLeft = '8px';
      badge.textContent = api.useMock ? 'API: 模拟' : 'API: 后端';
      header.appendChild(badge);
    }
  } catch {}
}

init();