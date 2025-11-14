const acc = {
  refreshBtn: document.getElementById('refreshBtn'),
  footballPanel: document.getElementById('footballPanel'),
  basketballPanel: document.getElementById('basketballPanel'),
};

function setPanel(el, text) {
  el.classList.remove('muted');
  el.textContent = text;
}
function setMuted(el, text) {
  el.classList.add('muted');
  el.textContent = text;
}

function extractFields(item) {
  const sport = item.sport;
  const r = item.result || {};
  const preds = r.predictions || {};
  const score = typeof preds.score === 'string' ? preds.score : (preds.score || '');
  const corners = typeof preds.corners === 'string' ? preds.corners : (preds.corners || '');
  const advice = typeof r.betting_advice === 'string' ? r.betting_advice : '';
  const qt = item.queryText || '';
  let ou = '';
  let spread = '';
  const textPool = [score, corners, advice].join(' ');
  if (/大分|小分|大球|小球|总分/.test(textPool)) {
    const m = textPool.match(/(大分|小分|大球|小球)/);
    ou = m ? m[1] : '';
  }
  if (/让分|让球|受让|让-?\d+/.test(textPool)) {
    const m2 = textPool.match(/(让分|让球|受让|让-?\d+)/);
    spread = m2 ? m2[1] : '';
  }
  const match = qt || (typeof r.summary === 'string' ? r.summary.slice(0, 40) : '');
  return { sport, match, score, ou, spread };
}

async function fetchSport(sport) {
  const list = await api.listResults({ sport });
  const ids = (list || []).slice(0, 20).map(i => i.id);
  const rows = [];
  for (const id of ids) {
    const detail = await api.getResult(id);
    if (detail && detail.result) {
      const f = extractFields(detail);
      const line = `${f.match} | 比分预测：${f.score || '-'} | 大小球：${f.ou || '-'} | 让分：${f.spread || '-'}`;
      rows.push(line);
    }
  }
  return rows;
}

async function refresh() {
  try {
    acc.refreshBtn.disabled = true;
    setMuted(acc.footballPanel, '加载中...');
    setMuted(acc.basketballPanel, '加载中...');
    const [fRows, bRows] = await Promise.all([fetchSport('football'), fetchSport('basketball')]);
    setPanel(acc.footballPanel, (fRows.length ? '• ' + fRows.join('\n• ') : '暂无数据'));
    setPanel(acc.basketballPanel, (bRows.length ? '• ' + bRows.join('\n• ') : '暂无数据'));
  } catch (e) {
    setPanel(acc.footballPanel, `加载失败：${e && e.message ? e.message : e}`);
    setPanel(acc.basketballPanel, `加载失败：${e && e.message ? e.message : e}`);
  } finally {
    acc.refreshBtn.disabled = false;
  }
}

function init() {
  acc.refreshBtn.addEventListener('click', refresh);
}

init();