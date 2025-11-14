(() => {
  if (window.ChatHistory) return;

  const state = {
    tlPage: 1, tlPageSize: 20, tlTotal: 0,
    ssPage: 1, ssPageSize: 20, ssTotal: 0,
  };

  function esc(s) { return String(s || '').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  async function renderTimeline() {
    const res = await window.api.getConversations({ page: state.tlPage, pageSize: state.tlPageSize });
    state.tlTotal = res.total;
    const pages = Math.max(1, Math.ceil(res.total / res.pageSize));
    const list = document.getElementById('timeline-list');
    const info = document.getElementById('tl-page-info');
    info.textContent = `第 ${res.page} / ${pages} 页（共 ${res.total} 条）`;
    if (!res.items?.length) {
      list.innerHTML = '<div class="muted">暂无对话</div>';
      return;
    }
    list.innerHTML = res.items.map(i => `
      <div class="list-item">
        <div class="meta">
          <span class="role ${i.role}">${i.role}</span>
          <span class="time">${new Date(i.createdAt).toLocaleString()}</span>
          ${i.sessionId ? `<span class="sid" title="session">${esc(i.sessionId)}</span>` : ''}
        </div>
        <div class="content">${esc(i.content)}</div>
      </div>
    `).join('');
  }

  async function renderSessions() {
    const res = await window.api.getConversationSessions({ page: state.ssPage, pageSize: state.ssPageSize });
    state.ssTotal = res.total;
    const pages = Math.max(1, Math.ceil(res.total / res.pageSize));
    const list = document.getElementById('session-list');
    const info = document.getElementById('ss-page-info');
    info.textContent = `第 ${res.page} / ${pages} 页（共 ${res.total} 组）`;
    if (!res.items?.length) {
      list.innerHTML = '<div class="muted">暂无会话</div>';
      return;
    }
    list.innerHTML = res.items.map(i => `
      <div class="list-item">
        <div class="meta">
          <span class="sid">${esc(i.sessionId ?? '(无 session)')}</span>
          <span class="time">${new Date(i.firstAt).toLocaleString()} → ${new Date(i.lastAt).toLocaleString()}</span>
          <span class="count">${i.count} 条</span>
        </div>
      </div>
    `).join('');
  }

  function bindEvents() {
    const root = document.getElementById('chat-history');
    if (!root) return;
    root.querySelector('#tl-prev').addEventListener('click', () => { if (state.tlPage > 1) { state.tlPage--; renderTimeline(); } });
    root.querySelector('#tl-next').addEventListener('click', () => {
      const pages = Math.max(1, Math.ceil(state.tlTotal / state.tlPageSize));
      if (state.tlPage < pages) { state.tlPage++; renderTimeline(); }
    });
    root.querySelector('#ss-prev').addEventListener('click', () => { if (state.ssPage > 1) { state.ssPage--; renderSessions(); } });
    root.querySelector('#ss-next').addEventListener('click', () => {
      const pages = Math.max(1, Math.ceil(state.ssTotal / state.ssPageSize));
      if (state.ssPage < pages) { state.ssPage++; renderSessions(); }
    });
    root.querySelector('#history-refresh').addEventListener('click', () => { renderTimeline(); renderSessions(); });

    root.querySelectorAll('.tabs .tab').forEach(btn => {
      btn.addEventListener('click', () => {
        root.querySelectorAll('.tabs .tab').forEach(b => b.classList.remove('active'));
        root.querySelectorAll('.tab-panels .panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        root.querySelector(`#panel-${tab}`).classList.add('active');
      });
    });
  }

  function init() {
    const root = document.getElementById('chat-history');
    if (!root) return;
    bindEvents();
    renderTimeline();
    renderSessions();
    window.ChatHistory = { refresh: () => { renderTimeline(); renderSessions(); } };
  }

  document.addEventListener('DOMContentLoaded', init);
})();