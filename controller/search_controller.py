import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from controller.llm_client import VolcClient  # type: ignore
except Exception:
    import importlib.util
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(ROOT, 'controller', 'llm_client.py')
    spec = importlib.util.spec_from_file_location('local_llm_for_search', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Cannot load controller/llm_client.py')
    _llm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_llm)  # type: ignore
    VolcClient = _llm.VolcClient


def _is_url(text: str) -> bool:
    s = (text or '').strip().lower()
    return s.startswith('http://') or s.startswith('https://')


def _http_get(url: str, timeout: int = 20) -> Optional[str]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    try:
        import requests  # type: ignore
        r = requests.get(url, timeout=timeout, headers=headers)
        r.raise_for_status()
        return r.content.decode('utf-8', errors='ignore')
    except Exception:
        try:
            import urllib.request
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
                return resp.read().decode('utf-8', errors='ignore')
        except Exception:
            return None


def web_search(query: str, limit: int = 10) -> List[Dict[str, str]]:
    q = (query or '').strip()
    if not q:
        return []
    hits: List[Dict[str, str]] = []

    if _is_url(q):
        html = _http_get(q)
        title = ''
        snippet = ''
        if html:
            import re
            m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            if m:
                title = re.sub(r'\s+', ' ', m.group(1)).strip()
            m2 = re.search(r'<meta[^>]*name=["\"]description["\"][^>]*content=["\"]([^"\"]+)["\"]', html, re.IGNORECASE)
            if m2:
                snippet = re.sub(r'\s+', ' ', m2.group(1)).strip()
            if not snippet:
                text = re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>', ' ', html, flags=re.IGNORECASE)
                snippet = re.sub(r'\s+', ' ', text).strip()[:200]
        hits.append({'title': title or q, 'url': q, 'snippet': snippet})
        return hits

    ddg_url = f'https://html.duckduckgo.com/html/?q={q}'
    ddg_html = _http_get(ddg_url)
    def _parse_ddg(html: str) -> List[Dict[str, str]]:
        res: List[Dict[str, str]] = []
        import re
        for m in re.finditer(r'<a[^>]*class=["\"]result__a["\"][^>]*href=["\"]([^"\"]+)["\"][^>]*>([\s\S]*?)</a>', html, re.IGNORECASE):
            url = m.group(1)
            title = re.sub(r'<[^>]+>', '', m.group(2))
            title = re.sub(r'\s+', ' ', title).strip()
            snip = ''
            tail = html[m.end():m.end()+500]
            ms = re.search(r'<a[^>]*class=["\"]result__snippet["\"][^>]*>([\s\S]*?)</a>|<div[^>]*class=["\"]result__snippet["\"][^>]*>([\s\S]*?)</div>', tail, re.IGNORECASE)
            if ms:
                snip = re.sub(r'<[^>]+>', '', (ms.group(1) or ms.group(2) or ''))
                snip = re.sub(r'\s+', ' ', snip).strip()
            res.append({'title': title, 'url': url, 'snippet': snip})
        return res
    if ddg_html:
        hits.extend(_parse_ddg(ddg_html))

    if len(hits) < limit:
        bing_url = f'https://www.bing.com/search?q={q}'
        bing_html = _http_get(bing_url)
        if bing_html:
            import re
            for m in re.finditer(r'<li[^>]*class=["\"]b_algo["\"][^>]*>[\s\S]*?<h2>\s*<a[^>]*href=["\"]([^"\"]+)["\"][^>]*>([\s\S]*?)</a>[\s\S]*?</h2>([\s\S]*?)</li>', bing_html, re.IGNORECASE):
                url = m.group(1)
                title = re.sub(r'<[^>]+>', '', m.group(2))
                title = re.sub(r'\s+', ' ', title).strip()
                snippet = re.sub(r'<[^>]+>', '', m.group(3))
                snippet = re.sub(r'\s+', ' ', snippet).strip()
                hits.append({'title': title, 'url': url, 'snippet': snippet})
        if len(hits) < limit:
            cn_bing = f'https://cn.bing.com/search?q={q}'
            cn_html = _http_get(cn_bing)
            if cn_html:
                import re
                for m in re.finditer(r'<li[^>]*class=["\"]b_algo["\"][^>]*>[\s\S]*?<h2>\s*<a[^>]*href=["\"]([^"\"]+)["\"][^>]*>([\s\S]*?)</a>[\s\S]*?</h2>([\s\S]*?)</li>', cn_html, re.IGNORECASE):
                    url = m.group(1)
                    title = re.sub(r'<[^>]+>', '', m.group(2))
                    title = re.sub(r'\s+', ' ', title).strip()
                    snippet = re.sub(r'<[^>]+>', '', m.group(3))
                    snippet = re.sub(r'\s+', ' ', snippet).strip()
                    hits.append({'title': title, 'url': url, 'snippet': snippet})

    seen = set()
    uniq: List[Dict[str, str]] = []
    for h in hits:
        key = (h.get('title','').strip(), h.get('url','').strip())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
        if len(uniq) >= limit:
            break
    return uniq


def search_and_analyze(query: str, temperature: Optional[float]) -> Dict[str, Any]:
    hits = web_search(query, limit=10)
    sys_prompt = (
        "你是一位专业的比赛信息整合者。基于给定的网页标题/摘要/正文片段，"
        "提炼与这场比赛相关的‘预测结果’或‘关键信息’，强调来源一致性与不确定性。"
        "输出 JSON："
        "- summary: 200字以内中文摘要（覆盖主流观点与分歧）。"
        "- bullets: 数组，列出3-8条关键信息或预测（含来源索引）。"
        "- risks: 数组，给出风险或反例（含来源索引）。"
        "只输出 JSON。"
    )

    def _extract_text(url: str) -> str:
        html = _http_get(url) or ''
        if not html:
            return ''
        import re
        text = re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>', ' ', html, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:600]

    lines: List[str] = []
    for i, h in enumerate(hits[:10], start=1):
        t = (h.get('title') or '').strip()
        u = (h.get('url') or '').strip()
        s = (h.get('snippet') or '').strip()
        body = _extract_text(u) if u and i <= 5 else ''
        part = f"[{i}] {t}\n{u}\n{s}"
        if body:
            part += f"\n{body}"
        lines.append(part)
    joined = "\n\n".join(lines) or "(无命中)"

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f"比赛问题：{query}\n\n相关网页（最多10条）：\n{joined}"},
    ]

    summary: str
    try:
        client = VolcClient()
        summary = client.chat(messages, temperature=temperature)
    except Exception:
        bullets = []
        for i, h in enumerate(hits[:8], start=1):
            t = (h.get('title') or '').strip()
            if t:
                bullets.append(f"[{i}] {t}")
        summary = json.dumps({
            "summary": "模型暂不可用，以下为直接聚合的网页标题摘要。",
            "bullets": bullets,
            "risks": ["网络检索或模型不可用，建议人工核验来源信息。"],
        }, ensure_ascii=False)

    created_at = datetime.utcnow().isoformat()
    return {
        "ok": True,
        "query": query,
        "createdAt": created_at,
        "summary": summary,
        "hits": hits,
    }