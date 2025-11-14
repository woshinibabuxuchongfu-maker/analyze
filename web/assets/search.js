const sh = {
  query: document.getElementById('query'),
  modelId: document.getElementById('searchModelId'),
  temperature: document.getElementById('searchTemperature'),
  btn: document.getElementById('searchBtn'),
  result: document.getElementById('searchResult'),
  hits: document.getElementById('searchHits'),
};

function setPanel(el, content, json = false) {
  el.classList.remove('muted');
  el.textContent = json ? JSON.stringify(content, null, 2) : String(content);
}
function setMuted(el, msg) {
  el.classList.add('muted');
  el.textContent = msg;
}

function renderHits(hits) {
  if (!hits || hits.length === 0) {
    return setMuted(sh.hits, '暂无搜索结果');
  }
  const html = hits.map(h => `• ${h.title} \n  ${h.url}\n  ${h.snippet}\n`).join('\n');
  sh.hits.classList.remove('muted');
  sh.hits.textContent = html;
}

async function handleSearch() {
  try {
    sh.btn.disabled = true;
    setMuted(sh.result, api.useMock ? '模拟搜索与分析中...' : '搜索与分析中...');
    setMuted(sh.hits, '检索中...');

    const payload = {
      query: sh.query.value.trim(),
      modelId: sh.modelId.value.trim(),
      temperature: Number(sh.temperature.value) || 0.2,
    };
    if (!payload.query) { alert('请输入关键词或链接'); sh.btn.disabled = false; return; }

    const res = await api.searchAnalyze(payload);
    try {
      const obj = JSON.parse(res.summary);
      const lines = [];
      if (obj.summary) lines.push(`摘要：${obj.summary}`);
      if (Array.isArray(obj.bullets)) {
        lines.push('要点：');
        obj.bullets.forEach((b,i)=>lines.push(`- ${b}`));
      }
      if (Array.isArray(obj.risks) && obj.risks.length>0) {
        lines.push('风险：');
        obj.risks.forEach((r)=>lines.push(`- ${r}`));
      }
      setPanel(sh.result, lines.join('\n'));
    } catch {
      setPanel(sh.result, res, true);
    }
    renderHits(res.hits || []);
  } catch (err) {
    setPanel(sh.result, `搜索或分析失败：${err.message||err}`);
  } finally {
    sh.btn.disabled = false;
  }
}

function init() {
  document.getElementById('searchBtn').addEventListener('click', handleSearch);
  // 模式徽章
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