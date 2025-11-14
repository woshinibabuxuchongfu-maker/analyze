import json
import os
from typing import List, Dict, Any, Optional

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # type: ignore


def _load_env() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_env = os.path.join(root, ".env")
    if os.path.exists(root_env):
        if load_dotenv is not None:
            load_dotenv(dotenv_path=root_env, override=False)
        else:
            try:
                with open(root_env, 'r', encoding='utf-8') as f:
                    for line in f:
                        s = line.strip()
                        if not s or s.startswith('#'):
                            continue
                        if '=' not in s:
                            continue
                        k, v = s.split('=', 1)
                        k = k.strip()
                        v = v.strip()
                        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                            v = v[1:-1]
                        if os.getenv(k) is None:
                            os.environ[k] = v
            except Exception:
                pass
    if load_dotenv is not None:
        load_dotenv(override=False)


def _http_post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    try:
        import requests  # type: ignore
        # 明确期望 UTF-8 JSON，避免响应头错误导致乱码
        req_headers = {**headers, 'Accept': 'application/json'}
        r = requests.post(url, headers=req_headers, json=payload, timeout=60)
        r.raise_for_status()
        return json.loads(r.content.decode('utf-8'))
    except Exception:
        import urllib.request
        req = urllib.request.Request(url, method='POST')
        for k, v in headers.items():
            req.add_header(k, v)
        data = json.dumps(payload).encode('utf-8')
        with urllib.request.urlopen(req, data=data, timeout=60) as resp:  # nosec B310
            text = resp.read().decode('utf-8')
            return json.loads(text)


class VolcClient:
    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None):
        _load_env()
        self.api_key = api_key or os.getenv('VOLC_API_KEY') or os.getenv('ARK_API_KEY')
        if not self.api_key:
            raise RuntimeError('Missing VOLC_API_KEY (or ARK_API_KEY) in environment')
        self.base_url = (base_url or os.getenv('VOLC_API_BASE') or os.getenv('ARK_API_BASE')
                         or 'https://ark.cn-beijing.volces.com/api/v3')
        self.model = model or os.getenv('VOLC_MODEL') or os.getenv('ARK_MODEL') or 'ep-xxxx'
        self.temperature = temperature if temperature is not None else float(os.getenv('VOLC_TEMPERATURE', '0.2'))
        self.max_tokens = max_tokens if max_tokens is not None else int(os.getenv('VOLC_MAX_TOKENS', '512'))

    def chat(self, messages: List[Dict[str, str]], temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> str:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': self.temperature if temperature is None else temperature,
            'max_tokens': self.max_tokens if max_tokens is None else max_tokens,
        }

        # 优先尝试 v3 路径，失败时回退到 openai/v1（不同部署网关可能只开放其一）
        base = self.base_url.rstrip('/')
        url_v3 = base + '/chat/completions'

        def _extract_text(resp: dict) -> str:
            return resp['choices'][0]['message']['content']

        last_err: Optional[Exception] = None
        for url in (url_v3, None):
            try:
                if url is None:
                    # 构造 openai/v1 路径：去掉末尾的 /api/v3（若存在），再拼接 openai/v1
                    root = base[:-7] if base.endswith('/api/v3') else base
                    url = root + '/openai/v1/chat/completions'
                data = _http_post_json(url, payload, headers)
                try:
                    return _extract_text(data)
                except Exception as e:
                    last_err = e
                    # 尝试下一种路径
                    continue
            except Exception as e:
                last_err = e
                continue

        raise RuntimeError(f'Unexpected response from Volcengine: {str(last_err)}')


def build_empathy_system_prompt() -> str:
    return (
        "你是一位资深球迷兼情绪陪伴者，专注安慰因足球（英超/西甲/德甲/意甲/法甲）或篮球（NBA）比赛预测失败而沮丧的玩家。\n"
        "\n"
        "【足球场景】当用户提到五大联赛球队（如曼联、皇马、拜仁等）：\n"
        "- 用真实背景共情：‘又让利物浦最后10分钟绝杀了？这剧本太熟悉了…’\n"
        "- 可提及近期赛况、历史恩怨或战术痛点（如‘克洛普的高位逼抢今天被打穿了’），但不长篇分析；\n"
        "- 安慰要结合球队特质：对传统豪门说‘底蕴在，反弹快’，对小球队说‘能拼到这已经值得骄傲’。\n"
        "\n"
        "【篮球场景】当用户提到NBA球队（如湖人、勇士、凯尔特人等）：\n"
        "- 用联盟语境共鸣：‘G6汤又隐身了？这轮系列赛看得人血压飙升！’\n"
        "- 可轻点现实因素：负荷管理、伤病、裁判尺度（如‘最后那个犯规不吹确实离谱’），但不引战；\n"
        "- 安慰贴合球队处境：争冠队说‘还有抢七机会’，重建队说‘年轻核心拼到最后一秒已超预期’。\n"
        "\n"
        "【通用原则】\n"
        "- 先骂/叹/共情（‘这球能输？真他妈傻逼！绝对有剧本！’）；\’），再给1个微小行动（‘去投10个三分冷静下’‘喝口冰啤酒压压惊’）；\n"
        "- 绝不说‘看开点’‘输赢正常’这类空话，也绝不诊断心理或法律问题；\n"
        "- 语气像一起熬夜看球的朋友：热血、真实、带点江湖气，60–150字，口语化，禁用术语堆砌。\n"
    )