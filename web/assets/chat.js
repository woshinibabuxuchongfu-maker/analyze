const CHAT_KEY = 'chat_history_v1';
const SESSION_KEY = 'chat_session_id';

function nowIso() { return new Date().toISOString(); }

function loadChat() {
  try { return JSON.parse(localStorage.getItem(CHAT_KEY) || '[]'); } catch { return []; }
}
function saveChat(list) { localStorage.setItem(CHAT_KEY, JSON.stringify(list)); }

function getSessionId() {
  let sid = localStorage.getItem(SESSION_KEY);
  if (!sid) {
    // 简易生成：时间戳 + 随机串
    sid = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

const els = {
  log: document.getElementById('chatLog'),
  input: document.getElementById('chatInput'),
  send: document.getElementById('chatSend'),
  clear: document.getElementById('chatClear'),
};

function addMsg(role, content, createdAt = nowIso()) {
  const div = document.createElement('div');
  div.className = `msg ${role === 'user' ? 'user' : 'bot'}`;
  div.innerHTML = `
    <div class="bubble">${String(content).replace(/</g,'&lt;')}</div>
    <div class="meta">${role === 'user' ? '我' : '助手'} · ${new Date(createdAt).toLocaleString()}</div>
  `;
  els.log.appendChild(div);
  els.log.scrollTop = els.log.scrollHeight;
}

async function handleSend() {
  const text = els.input.value.trim();
  if (!text) return;
  els.input.value = '';
  els.send.disabled = true;

  // 显示并保存用户消息
  const history = loadChat();
  const userMsg = { role: 'user', content: text, createdAt: nowIso() };
  history.push(userMsg);
  saveChat(history);
  addMsg('user', userMsg.content, userMsg.createdAt);

  // 调用聊天 API（后端或模拟）
  try {
    const res = await api.chat({ text, history, sessionId: getSessionId() });
    const botMsg = { role: 'assistant', content: res.reply || '（无回复）', createdAt: res.createdAt || nowIso() };
    const next = loadChat();
    next.push(botMsg);
    saveChat(next);
    addMsg('bot', botMsg.content, botMsg.createdAt);
  } catch (err) {
    addMsg('bot', `发送失败：${err.message || err}`);
  } finally {
    els.send.disabled = false;
    els.input.focus();
  }
}

function handleClear() {
  saveChat([]);
  els.log.innerHTML = `
    <div class="msg bot">
      <div class="bubble">嗨，我在这儿倾听。最近有什么让你抓狂的事吗？</div>
      <div class="meta">系统 · 已清空历史</div>
    </div>`;
}

function init() {
  // 徽章提示当前模式
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

  // 渲染历史
  const history = loadChat();
  for (const m of history) addMsg(m.role, m.content, m.createdAt);

  // 确保 sessionId 初始化
  getSessionId();

  // 绑定事件
  els.send.addEventListener('click', handleSend);
  els.clear.addEventListener('click', handleClear);
  els.input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  });
}

init();