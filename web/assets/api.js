// 简易 API 客户端，默认调用后端接口；当 URL 参数含 mock=1 时走本地模拟
(() => {
  const params = new URLSearchParams(location.search);
  // 默认优先走后端接口；如需本地模拟可加 ?mock=1 覆盖
  const defaultDevMock = false;
  const useMock = params.has('mock') ? (params.get('mock') === '1') : defaultDevMock;

  const API_BASE = '';

  async function httpJson(path, options = {}) {
    const url = API_BASE + path;
    const maxRetries = 2;
    let lastErr;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const res = await fetch(url, {
          headers: { 'Content-Type': 'application/json' },
          ...options,
        });
        if (!res.ok) {
          const text = await res.text().catch(() => '');
          throw new Error(`HTTP ${res.status}: ${text}`);
        }
        return res.json();
      } catch (e) {
        lastErr = e;
        if (attempt < maxRetries) {
          await new Promise(r => setTimeout(r, 300));
          continue;
        }
        throw e;
      }
    }
    throw lastErr;
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function getLocalHistory() {
    const raw = localStorage.getItem('analysis_history_v1') || '[]';
    try { return JSON.parse(raw); } catch { return []; }
  }
  function setLocalHistory(items) {
    localStorage.setItem('analysis_history_v1', JSON.stringify(items));
  }

  function summarize(text) {
    if (!text) return '';
    const s = String(text).replace(/\s+/g, ' ').trim();
    return s.length > 80 ? s.slice(0, 77) + '...' : s;
  }

  const api = {
    useMock,

    // 分析接口：后端建议提供 POST /api/analyze
    // 请求体：{ sport, modelId, temperature, dataText }
    async analyze(payload) {
      if (!useMock) {
        return httpJson('/api/analyze', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      }
      // 本地模拟（用于无后端情况下跑通流程）
      const id = Math.random().toString(36).slice(2, 10);
      const createdAt = nowIso();
      const mock = {
        id,
        sport: payload.sport,
        modelId: payload.modelId,
        createdAt,
        ok: true,
        result: {
          summary: `模拟${payload.sport}分析：${summarize(payload.dataText)}`,
          insights: [
            '样例洞察：关键球员影响较大',
            '样例洞察：节奏控制决定上半场走势',
          ],
          meta: { temperature: payload.temperature ?? 0.3 },
        },
      };
      const items = getLocalHistory();
      items.unshift(mock);
      setLocalHistory(items.slice(0, 200));
      return mock;
    },

    // 历史列表：后端建议提供 GET /api/results?sport=football|basketball
    async listResults({ sport } = {}) {
      if (!useMock) {
        const q = sport ? `?sport=${encodeURIComponent(sport)}` : '';
        return httpJson(`/api/results${q}`);
      }
      const items = getLocalHistory();
      const filtered = sport ? items.filter(i => i.sport === sport) : items;
      return filtered.map(i => ({
        id: i.id,
        sport: i.sport,
        summary: i.result?.summary || '',
        createdAt: i.createdAt,
      }));
    },

    // 详情：后端建议提供 GET /api/results/:id
    async getResult(id) {
      if (!useMock) {
        return httpJson(`/api/results/${encodeURIComponent(id)}`);
      }
      const items = getLocalHistory();
      return items.find(i => i.id === id) || null;
    },

    // 搜索并分析：后端使用 POST /api/search
    async searchAnalyze(payload) {
      if (!useMock) {
        const body = { query: payload.query || '', temperature: payload.temperature ?? 0.2 };
        return httpJson('/api/search', {
          method: 'POST',
          body: JSON.stringify(body),
        });
      }
      const hits = [
        { title: '示例新闻：球队伤病报告', url: 'https://example.com/news/injury', snippet: '主力前锋可能缺席下一场比赛。' },
        { title: '示例数据：近期战绩', url: 'https://example.com/stats/form', snippet: '近5场3胜1平1负，进攻效率提升。' },
      ];
      return {
        ok: true,
        query: payload.query,
        modelId: payload.modelId,
        createdAt: nowIso(),
        summary: `模拟分析摘要：基于 ${hits.length} 条网络结果进行归纳。`,
        hits,
      };
    },

    // 吐槽聊天：后端建议 POST /api/chat  { text, history? }
    async chat(payload) {
      if (!useMock) {
        return httpJson('/api/chat', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      }
      const templates = [
        (t) => `我懂，这种事真的让人上火。先深呼吸一下。关于“${t}”，咱们可以换个角度看看：哪些是你能掌控的？`,
        (t) => `辛苦了。听起来“${t}”确实憋屈。或许短暂休息下，再把注意力放在下一步可执行的小目标上。`,
        (t) => `抱抱你。这种经历“${t}”很常见，但你的坚持很难得。不妨记录三个小改进点，逐个击破。`,
      ];
      const pick = templates[Math.floor(Math.random() * templates.length)];
      return { reply: pick(payload.text || ''), createdAt: nowIso() };
    },

    // 对话时间线（可选 sessionId）
    async getConversations({ sessionId, page = 1, pageSize = 20, order = 'desc' } = {}) {
      if (!useMock) {
        const q = new URLSearchParams({ page, pageSize, order });
        if (sessionId != null) q.set('sessionId', sessionId);
        return httpJson(`/api/conversations?${q.toString()}`);
      }
      // mock 模式：从本地聊天记录构造
      const raw = localStorage.getItem('chat_history_v1') || '[]';
      let items = [];
      try { items = JSON.parse(raw).map((m, i) => ({ id: i + 1, role: m.role, content: m.content, createdAt: m.createdAt, sessionId: localStorage.getItem('chat_session_id') || null })); } catch {}
      items.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
      const total = items.length;
      const start = (page - 1) * pageSize;
      const pageItems = items.slice(start, start + pageSize);
      return { items: pageItems, page, pageSize, total };
    },

    // 会话分组摘要
    async getConversationSessions({ page = 1, pageSize = 20 } = {}) {
      if (!useMock) {
        const q = new URLSearchParams({ page, pageSize });
        return httpJson(`/api/conversation-sessions?${q.toString()}`);
      }
      const sid = localStorage.getItem('chat_session_id') || null;
      const raw = localStorage.getItem('chat_history_v1') || '[]';
      let count = 0; try { count = JSON.parse(raw).length; } catch {}
      return { items: [{ sessionId: sid, firstAt: nowIso(), lastAt: nowIso(), count }], page, pageSize, total: 1 };
    },
  };

  window.api = api;
})();