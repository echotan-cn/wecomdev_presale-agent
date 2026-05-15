#!/usr/bin/env python3
"""
统一服务：静态页面 + 智能表格创建 API（同一个端口 8765）
"""
import json
import asyncio
import aiohttp
from aiohttp import web
from pathlib import Path

MCP_URL = "https://qyapi.weixin.qq.com/mcp/robot-doc?apikey=S0RW0Ke7TfR0_NcWgTXq2Ht_BColuWjRzRVM9LMO3jHoIdKwI3gEPiNPnNxgkiPqhNXtAtM1_86okTOj8R5R8Q"
PORT = 8765
STATIC_DIR = Path(__file__).parent.parent  # 指向项目根目录


async def call_mcp(session, tool_name, arguments):
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool_name, "arguments": arguments}}
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    async with session.post(MCP_URL, json=payload, headers=headers) as resp:
        ct = resp.headers.get("Content-Type", "")
        if "text/event-stream" in ct:
            result = None
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    try:
                        result = json.loads(line[6:])
                    except:
                        pass
            return result
        else:
            return await resp.json()


def extract_result(mcp_resp):
    if not mcp_resp:
        return None
    result = mcp_resp.get("result", mcp_resp)
    if isinstance(result, dict):
        content = result.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    try:
                        return json.loads(item["text"])
                    except:
                        return item.get("text")
        return result
    return result


async def create_smartsheet(request):
    try:
        schema = await request.json()
    except:
        return web.json_response({"error": "无效 JSON"}, status=400)

    doc_name = schema.get("doc_name", "Demo智能表格")
    sheets = schema.get("sheets", [])
    if not sheets:
        return web.json_response({"error": "sheets 为空"}, status=400)

    steps = []
    async with aiohttp.ClientSession() as session:
        # 1. 创建文档
        resp = await call_mcp(session, "create_doc", {"doc_type": 10, "doc_name": doc_name})
        r = extract_result(resp)
        if not r or (isinstance(r, dict) and r.get("errcode", 0) != 0):
            return web.json_response({"error": "创建文档失败", "detail": str(r)}, status=500)

        docid = r.get("docid") if isinstance(r, dict) else None
        doc_url = r.get("url") if isinstance(r, dict) else None
        if not docid:
            return web.json_response({"error": "未获取 docid", "detail": str(r)}, status=500)
        steps.append(f"文档已创建: {doc_url}")

        # 2. 获取默认子表
        resp = await call_mcp(session, "smartsheet_get_sheet", {"docid": docid})
        sr = extract_result(resp)
        default_sid = None
        if isinstance(sr, dict):
            sl = sr.get("sheet_list", sr.get("sheets", []))
            if isinstance(sl, list) and sl:
                default_sid = sl[0].get("sheet_id")

        created = []
        for idx, sdef in enumerate(sheets):
            sname = sdef.get("sheet_name", f"子表{idx+1}")
            fields = sdef.get("fields", [])
            records = sdef.get("sample_records", [])

            if idx == 0 and default_sid:
                sid = default_sid
                await call_mcp(session, "smartsheet_update_sheet", {"docid": docid, "sheet_id": sid, "title": sname})
            else:
                resp = await call_mcp(session, "smartsheet_add_sheet", {"docid": docid, "title": sname})
                sr2 = extract_result(resp)
                sid = None
                if isinstance(sr2, dict):
                    sid = sr2.get("sheet_id") or (sr2.get("properties", {}) or {}).get("sheet_id")
                if not sid:
                    steps.append(f"子表 {sname} 创建失败")
                    continue

            steps.append(f"子表「{sname}」就绪")

            # 3. 获取默认字段
            resp = await call_mcp(session, "smartsheet_get_fields", {"docid": docid, "sheet_id": sid})
            fr = extract_result(resp)
            dfid, dftype = None, "FIELD_TYPE_TEXT"
            if isinstance(fr, dict):
                fl = fr.get("fields", [])
                if fl:
                    dfid = fl[0].get("field_id")
                    dftype = fl[0].get("field_type", "FIELD_TYPE_TEXT")

            # 4. 重命名默认字段 + 添加剩余字段
            if fields and dfid:
                await call_mcp(session, "smartsheet_update_fields", {
                    "docid": docid, "sheet_id": sid,
                    "fields": [{"field_id": dfid, "field_title": fields[0]["field_title"], "field_type": dftype}]
                })
                if len(fields) > 1:
                    await call_mcp(session, "smartsheet_add_fields", {
                        "docid": docid, "sheet_id": sid,
                        "fields": [{"field_title": f["field_title"], "field_type": f["field_type"]} for f in fields[1:]]
                    })
                steps.append(f"  {len(fields)} 个字段已配置")

            # 5. 插入示例数据
            if records:
                resp = await call_mcp(session, "smartsheet_get_fields", {"docid": docid, "sheet_id": sid})
                cf = extract_result(resp)
                fmap = {}
                if isinstance(cf, dict):
                    for f in cf.get("fields", []):
                        fmap[f["field_title"]] = f

                fmtd = []
                for rec in records:
                    vals = {}
                    for k, v in rec.items():
                        if k not in fmap:
                            continue
                        ft = fmap[k].get("field_type", "FIELD_TYPE_TEXT")
                        if ft == "FIELD_TYPE_TEXT":
                            vals[k] = [{"type": "text", "text": str(v)}]
                        elif ft in ("FIELD_TYPE_NUMBER", "FIELD_TYPE_CURRENCY", "FIELD_TYPE_PERCENTAGE", "FIELD_TYPE_PROGRESS"):
                            try:
                                vals[k] = float(v)
                            except:
                                vals[k] = [{"type": "text", "text": str(v)}]
                        elif ft == "FIELD_TYPE_SINGLE_SELECT":
                            vals[k] = [{"text": str(v)}]
                        elif ft == "FIELD_TYPE_DATE_TIME":
                            vals[k] = str(v)
                        elif ft == "FIELD_TYPE_CHECKBOX":
                            vals[k] = bool(v)
                        elif ft in ("FIELD_TYPE_PHONE_NUMBER", "FIELD_TYPE_EMAIL", "FIELD_TYPE_BARCODE"):
                            vals[k] = str(v)
                        else:
                            vals[k] = [{"type": "text", "text": str(v)}]
                    fmtd.append({"values": vals})

                if fmtd:
                    await call_mcp(session, "smartsheet_add_records", {"docid": docid, "sheet_id": sid, "records": fmtd})
                    steps.append(f"  {len(fmtd)} 条示例数据已写入")

            created.append({"sheet_name": sname, "sheet_id": sid})

    return web.json_response({"success": True, "doc_name": doc_name, "docid": docid, "url": doc_url, "sheets": created, "steps": steps})


async def health(request):
    return web.json_response({"status": "ok"})


app = web.Application()
app.router.add_get("/api/health", health)
app.router.add_post("/api/create", create_smartsheet)
# 静态文件：服务项目根目录下的 HTML
app.router.add_static("/", STATIC_DIR, show_index=True)

if __name__ == "__main__":
    print(f"🚀 统一服务启动在 http://localhost:{PORT}")
    print(f"   网页：http://localhost:{PORT}/presale-agent-demo.html")
    print(f"   API：POST http://localhost:{PORT}/api/create")
    web.run_app(app, host="127.0.0.1", port=PORT)
