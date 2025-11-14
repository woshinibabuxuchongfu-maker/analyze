import os
import json
from typing import Optional, Dict, Any, List, Type
from datetime import datetime

from sqlalchemy.orm import Session

# import models and volc client（保持运行环境健壮）
try:
    from server.models import FootballAnalysis, BasketballAnalysis  # type: ignore
    from controller.llm_client import VolcClient  # type: ignore
except Exception:
    import importlib.util
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _load(abs_rel: str, name: str):
        path = os.path.join(ROOT, abs_rel)
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f'Cannot load {abs_rel}')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        return mod

    _models = _load(os.path.join('server', 'models.py'), 'local_models')
    _llm = _load(os.path.join('controller', 'llm_client.py'), 'local_llm')
    FootballAnalysis = _models.FootballAnalysis
    BasketballAnalysis = _models.BasketballAnalysis
    VolcClient = _llm.VolcClient


def _read_text_file(path: str) -> Optional[str]:
    try:
        if path and os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception:
        pass
    return None


def _build_analysis_system_prompt(sport: str) -> str:
    key = 'FOOTBALL' if sport == 'football' else 'BASKETBALL'
    file_env = os.getenv(f'ANALYSIS_PROMPT_{key}_FILE')
    text_env = os.getenv(f'ANALYSIS_PROMPT_{key}_TEXT')

    override = None
    if file_env:
        override = _read_text_file(file_env)
    if not override and text_env:
        override = text_env
    if override and override.strip():
        return override

    if sport == 'football':
        return (
            "你是一位资深足球比赛分析师，基于提供的资料进行专业判断，并严格以 JSON 输出。\n"
            "分析维度：\n"
            "1) 赛程与战意/体能：赛程密度、轮换深度、是否关键战、是否为后续赛事留力。\n"
            "2) 技战术与阵型：攻守平衡、边路/中路推进、压迫/反击、定位球强弱与对位。\n"
            "3) 人员与伤停：核心球员状态、伤停名单、首发可用性、替补厚度。\n"
            "4) 裁判尺度：历史判罚倾向、越位/手球尺度、是否易出现点球或大量黄牌。\n"
            "5) 庄家思路与市场：盘赔变化、冷热度、可能的认知陷阱与大众情绪利用。\n"
            "6) 投注量结构：单边投注比例、临场波动，给出逆向或规避思路。\n\n"
            "JSON 字段：\n"
            "- summary: 精炼摘要。\n"
            "- angles: { schedule_motivation, tactics_style, referee, bookmaker_psychology, betting_volume }。\n"
            "- deep_analysis: 逻辑链条清晰的深度分析文本，含不确定性。\n"
            "- predictions: { score: 比分预测（如 '2-1'），corners: 角球相关预测/趋势 }。\n"
            "- betting_advice: 投注建议（方案/止损/风险点，兼顾保守与激进）。\n"
            "- probability: 0-1 之间小数。\n"
            "- disclaimers: 风险与边界提示（不构成投资建议）。\n"
            "只输出 JSON。"
        )
    else:
        return (
            "你是一位资深篮球比赛分析师，基于提供的资料进行专业判断，并严格以 JSON 输出。\n"
            "分析维度：\n"
            "1) 赛程与体能：背靠背/三连战、旅途与时差、轮换人数、负荷管理。\n"
            "2) 战术与节奏：进攻/防守效率（ORtg/DRtg 简述）、节奏 Pace、挡拆/单打/外线投射结构。\n"
            "3) 人员与匹配：主力可用性、对位身高与对抗、替补火力、犯规与罚球。\n"
            "4) 裁判尺度：吹罚严格度、三分/突破的受益程度、技术犯规倾向。\n"
            "5) 庄家思路与市场：让分/总分变化、公众倾向、可能的陷阱。\n"
            "6) 投注量结构：单边比例与临场波动，给出顺势或逆向思路。\n\n"
            "JSON 字段：\n"
            "- summary: 精炼摘要。\n"
            "- angles: { schedule_motivation, tactics_style, referee, bookmaker_psychology, betting_volume }。\n"
            "- deep_analysis: 逻辑链条清晰的深度分析文本，含不确定性。\n"
            "- predictions: { score: 总分趋势+分差判断（如 '大分/小分+分差范围'），corners: 节奏/篮板/失误相关趋势 }。\n"
            "- betting_advice: 投注建议（方案/止损/风险点，兼顾保守与激进）。\n"
            "- probability: 0-1 之间小数。\n"
            "- disclaimers: 风险与边界提示（不构成投资建议）。\n"
            "只输出 JSON。"
        )


def _call_model_for_analysis(text: str, sport: str, model_id: Optional[str], temperature: Optional[float]) -> Dict[str, Any]:
    system = _build_analysis_system_prompt(sport)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"比赛资料：\n{text}"},
    ]

    try:
        client = VolcClient()
        raw = client.chat(messages, temperature=temperature)
    except Exception as e:
        # 兜底结构化结果（让前端不再看到 500）
        msg = str(e)
        return {
            "summary": "模型暂不可用，已返回兜底分析要点。",
            "angles": {
                "schedule_motivation": "依据文本做粗略判断，注意不确定性。",
                "tactics_style": "从描述中提炼攻守与对位线索，仅供参考。",
                "referee": "未获取裁判信息，建议赛前复核。",
                "bookmaker_psychology": "警惕盘赔变化与大众情绪陷阱。",
                "betting_volume": "控制仓位，避免情绪化追单。",
            },
            "deep_analysis": f"模型调用失败（{msg}）。以下为基于输入文本的通用分析框架与风险提示：\n{text[:1000]}",
            "predictions": {"score": "N/A", "corners": "N/A"},
            "betting_advice": "建议观望或小仓位试探，严格止损。",
            "probability": 0.5,
            "disclaimers": "AI 生成内容仅供参考，不构成投资建议。",
        }

    # 解析模型输出 JSON；失败则尽力修复
    data: Dict[str, Any]
    try:
        data = json.loads(raw)
    except Exception:
        try:
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1 and end > start:
                data = json.loads(raw[start:end + 1])
            else:
                raise ValueError('No JSON object found')
        except Exception:
            data = {
                "summary": raw.strip()[:2000],
                "angles": {},
                "deep_analysis": raw.strip(),
                "predictions": {"score": "N/A", "corners": "N/A"},
                "betting_advice": "请谨慎，模型未返回结构化结果。",
                "probability": 0.5,
                "disclaimers": "AI 生成内容仅供参考，不构成投资建议。",
            }

    # 规范化字段
    data.setdefault("summary", "")
    data.setdefault("angles", {})
    data.setdefault("deep_analysis", "")
    preds = data.get("predictions") or {}
    if not isinstance(preds, dict):
        preds = {"score": str(preds), "corners": ""}
    preds.setdefault("score", "")
    preds.setdefault("corners", "")
    data["predictions"] = preds
    try:
        p = float(data.get("probability", 0.5))
        data["probability"] = max(0.0, min(1.0, p))
    except Exception:
        data["probability"] = 0.5
    data.setdefault("betting_advice", "")
    data.setdefault("disclaimers", "AI 生成内容仅供参考，不构成投资建议。")
    return data


def _persist_analysis_record(db: Session, sport: str, query_text: str, result: Dict[str, Any]):
    """根据运动类型选择目标表保存，便于后续替换为统一表或其他存储。"""
    model_map: Dict[str, Type] = {
        'football': FootballAnalysis,
        'basketball': BasketballAnalysis,
    }
    record_cls = model_map.get(sport)
    if record_cls is None:
        raise ValueError("invalid sport for persist")
    rec = record_cls(query_text=query_text, result_json=json.dumps(result, ensure_ascii=False))
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def analyze_game(db: Session, sport: str, data_text: str, model_id: Optional[str], temperature: Optional[float]) -> Dict[str, Any]:
    sport = (sport or '').lower()
    if sport not in ("football", "basketball"):
        raise ValueError("sport must be 'football' or 'basketball'")

    result = _call_model_for_analysis(data_text, sport, model_id, temperature)
    created_at = datetime.utcnow().isoformat()

    # 持久化容错：写库失败时回滚并继续返回分析结果，避免前端看到 500
    rec_id: Optional[int] = None
    try:
        rec = _persist_analysis_record(db, sport, data_text, result)
        rec_id = rec.id
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        # 记录到标准输出，便于部署环境查看
        print(f"[analyze] persist failed: {e}")

    return {
        "id": rec_id,
        "sport": sport,
        "createdAt": created_at,
        "ok": True,
        "result": result,
        "summary": result.get("summary", ""),
        "persisted": rec_id is not None,
    }


def list_results(db: Session, sport: Optional[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if sport is None:
        fa = db.query(FootballAnalysis).order_by(FootballAnalysis.created_at.desc()).limit(100).all()
        ba = db.query(BasketballAnalysis).order_by(BasketballAnalysis.created_at.desc()).limit(100).all()
        for r in fa:
            try:
                summary = json.loads(r.result_json).get('summary', '')
            except Exception:
                summary = ''
            items.append({"id": r.id, "sport": "football", "summary": summary, "createdAt": r.created_at.isoformat()})
        for r in ba:
            try:
                summary = json.loads(r.result_json).get('summary', '')
            except Exception:
                summary = ''
            items.append({"id": r.id, "sport": "basketball", "summary": summary, "createdAt": r.created_at.isoformat()})
        items.sort(key=lambda x: x["createdAt"], reverse=True)
        return items

    sport = sport.lower()
    if sport == 'football':
        rows = db.query(FootballAnalysis).order_by(FootballAnalysis.created_at.desc()).limit(200).all()
        for r in rows:
            try:
                summary = json.loads(r.result_json).get('summary', '')
            except Exception:
                summary = ''
            items.append({"id": r.id, "sport": "football", "summary": summary, "createdAt": r.created_at.isoformat()})
        return items
    if sport == 'basketball':
        rows = db.query(BasketballAnalysis).order_by(BasketballAnalysis.created_at.desc()).limit(200).all()
        for r in rows:
            try:
                summary = json.loads(r.result_json).get('summary', '')
            except Exception:
                summary = ''
            items.append({"id": r.id, "sport": "basketball", "summary": summary, "createdAt": r.created_at.isoformat()})
        return items
    raise ValueError("invalid sport for list")


def get_result(db: Session, id: int) -> Optional[Dict[str, Any]]:
    r = db.query(FootballAnalysis).filter(FootballAnalysis.id == id).first()
    if r is not None:
        try:
            data = json.loads(r.result_json)
        except Exception:
            data = {"raw": r.result_json}
        return {
            "id": r.id,
            "sport": "football",
            "createdAt": r.created_at.isoformat(),
            "queryText": r.query_text,
            "result": data,
        }
    r2 = db.query(BasketballAnalysis).filter(BasketballAnalysis.id == id).first()
    if r2 is not None:
        try:
            data = json.loads(r2.result_json)
        except Exception:
            data = {"raw": r2.result_json}
        return {
            "id": r2.id,
            "sport": "basketball",
            "createdAt": r2.created_at.isoformat(),
            "queryText": r2.query_text,
            "result": data,
        }
    return None