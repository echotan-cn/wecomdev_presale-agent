"""Vercel Serverless Function: POST /api/save → 保存需求数据到售前agent需求收集台账"""
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

MCP_URL = "https://qyapi.weixin.qq.com/mcp/robot-doc?apikey=S0RW0Ke7TfR0_NcWgTXq2Ht_BColuWjRzRVM9LMO3jHoIdKwI3gEPiNPnNxgkiPqhNXtAtM1_86okTOj8R5R8Q"
# 固定的台账表格信息
LEDGER_DOCID = "dcddEWjGM7gAHnxMevX-ohm59TVVaM_W9_iY2ZxWb5PIefmobcWsemSYfGTO7C6B_8BonhNapw5feJe1WgvsM-qA"
LEDGER_SHEET_ID = "q979lj"


def call_mcp(tool_name, arguments):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool_name, "arguments": arguments}}).encode("utf-8")
    req = urllib.request.Request(MCP_URL, data=payload, headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ct = resp.headers.get("Content-Type", "")
        body = resp.read().decode("utf-8")
        if "text/event-stream" in ct:
            result = None
            for line in body.split("\n"):
                line = line.strip()
                if line.startswith("data: "):
                    try:
                        result = json.loads(line[6:])
                    except:
                        pass
            return result
        else:
            return json.loads(body)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except:
            self._respond(400, {"error": "无效 JSON"})
            return

        # 构建记录
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")

        values = {
            "公司名称": [{"type": "text", "text": data.get("company", "")}],
            "所属行业": [{"type": "text", "text": data.get("industry", "")}],
            "公司规模": [{"text": data.get("size", "")}],
            "业务模式": [{"type": "text", "text": data.get("business", "")}],
            "痛点/需求": [{"type": "text", "text": data.get("direction", "")}],
            "业务深挖（AI问答）": [{"type": "text", "text": data.get("stage1_summary", "")}],
            "细节确认（AI问答）": [{"type": "text", "text": data.get("stage2_summary", "")}],
            "预算范围": [{"text": data.get("budget", "")}],
            "期望上线时间": [{"text": data.get("timeline", "")}],
            "AI需求报告": [{"type": "text", "text": data.get("report", "")}],
            "提交时间": now,
        }

        # Demo表格链接（如果有）
        demo_url = data.get("demo_url", "")
        if demo_url:
            values["Demo表格链接"] = [{"type": "url", "text": "查看Demo", "link": demo_url}]

        try:
            call_mcp("smartsheet_add_records", {
                "docid": LEDGER_DOCID,
                "sheet_id": LEDGER_SHEET_ID,
                "records": [{"values": values}]
            })
            self._respond(200, {"success": True, "message": "需求已保存到台账"})
        except Exception as e:
            self._respond(500, {"success": False, "error": str(e)})

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
