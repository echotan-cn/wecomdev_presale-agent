"""Vercel Serverless Function: POST /api/match -> 知识库匹配"""
import json
import re
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path


# 知识库路径（相对于 deploy 目录）
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


def load_industry_knowledge():
    """加载行业知识"""
    industries = {}
    ind_dir = KNOWLEDGE_DIR / "industries"
    if ind_dir.exists():
        for f in ind_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                industries[f.stem] = data
            except:
                pass
    return industries


def load_detailed_cases():
    """加载完整交付案例"""
    cases = []
    cases_dir = KNOWLEDGE_DIR / "cases"
    if cases_dir.exists():
        for f in cases_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                cases.append(data)
            except:
                pass
    return cases


def match_industry(industry, industry_knowledge):
    """匹配行业通用知识"""
    if not industry:
        return None
    industry_lower = industry.lower()
    for key, data in industry_knowledge.items():
        tags = [t.lower() for t in data.get("tags", [])]
        name = data.get("industry_name", "").lower()
        if industry_lower in name or any(industry_lower in t or t in industry_lower for t in tags):
            return data
    return None


def match_detailed_case(query, detailed_cases, top_k=2):
    """匹配完整交付案例"""
    if not query or not detailed_cases:
        return []

    query_lower = query.lower()
    scored = []
    for case in detailed_cases:
        score = 0
        meta = case.get("meta", {})
        case_industry = meta.get("industry", "").lower()
        case_scene = meta.get("scene", "").lower()

        if case_industry in query_lower or query_lower in case_industry:
            score += 5
        else:
            for word in re.split(r'[，,、。/\s]+', query_lower):
                if len(word) >= 2 and word in case_industry:
                    score += 4
                    break

        if case_scene in query_lower:
            score += 3

        summary = case.get("demand_summary", "").lower()
        for word in re.split(r'[，,、。\s]+', query_lower):
            if len(word) >= 2 and word in summary:
                score += 2

        if score > 0:
            scored.append((score, case))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def process_match(body):
    """处理匹配请求"""
    industry = body.get("industry", "")
    direction = body.get("direction", "")
    query = f"{industry} {direction}".strip()

    # 加载知识库
    industry_knowledge = load_industry_knowledge()
    detailed_cases = load_detailed_cases()

    # 匹配行业知识
    industry_data = match_industry(industry, industry_knowledge)
    industry_text = ""
    if industry_data:
        content = industry_data.get("content", "")
        industry_text = content[:2000] if len(content) > 2000 else content

    # 匹配案例
    matched_cases = match_detailed_case(query, detailed_cases, top_k=2)
    case_hints = ""
    for case in matched_cases:
        meta = case.get("meta", {})
        solution = case.get("solution", {})
        hint = f"【{meta.get('industry', '')} - {meta.get('scene', '')}】\n"
        hint += f"痛点：{'; '.join(case.get('pain_points', [])[:4])}\n"
        hint += f"方案架构：{solution.get('architecture', '')}\n"
        tables = solution.get("tables", [])
        if tables:
            table_names = [t.get("table_name", "") for t in tables[:6]]
            hint += f"子表：{', '.join(table_names)}\n"
        rules = solution.get("automation_rules", [])
        if rules:
            hint += f"自动化：{'; '.join(rules[:3])}\n"
        features = solution.get("key_features", [])
        if features:
            hint += f"亮点：{'; '.join(features[:3])}\n"
        case_hints += hint + "\n"

    return {
        "industry_knowledge": industry_text,
        "case_hints": case_hints.strip(),
        "matched": bool(industry_text or case_hints)
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except:
            self._respond(400, {"error": "无效 JSON", "matched": False})
            return
        result = process_match(data)
        self._respond(200, result)

    def do_OPTIONS(self):
        self._respond(200, {})

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
