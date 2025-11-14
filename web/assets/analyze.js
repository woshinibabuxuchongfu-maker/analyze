// 分析页脚本：仅保留“文本”数据输入
const sport = document.body.getAttribute('data-sport') || 'football';

const el = {
  dataText: document.getElementById('dataText'),
  temperature: document.getElementById('temperature'),
  analyzeBtn: document.getElementById('analyzeBtn'),
  resultPanel: document.getElementById('resultPanel'),
};

function setResult(content, type = 'text') {
  el.resultPanel.classList.remove('muted');
  el.resultPanel.textContent = type === 'json' ? JSON.stringify(content, null, 2) : String(content);
}

function setLoading(msg = '分析中...') {
  el.resultPanel.classList.add('muted');
  el.resultPanel.textContent = `${msg}`;
}

async function handleAnalyze() {
  try {
    el.analyzeBtn.disabled = true;
    setLoading(api.useMock ? '模拟分析中...' : '分析中...');

    const dataText = (el.dataText && typeof el.dataText.value === 'string') ? el.dataText.value.trim() : '';
    if (!dataText) { alert('请输入数据文本'); return; }

    const payload = {
      sport,
      temperature: (el.temperature && typeof el.temperature.value !== 'undefined')
        ? (Number(el.temperature.value) || 0.3)
        : 0.3,
      dataText,
    };

    const res = await api.analyze(payload);
    setResult(res, 'json');
  } catch (err) {
    console.error(err);
    setResult(`分析失败：${err.message || err}`);
  } finally {
    el.analyzeBtn.disabled = false;
  }
}

function bindEvents() {
  el.analyzeBtn.addEventListener('click', handleAnalyze);
}

function init() {
  bindEvents();
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