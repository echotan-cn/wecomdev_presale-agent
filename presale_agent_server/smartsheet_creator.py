#!/usr/bin/env python3
"""
企微智能表格创建中转服务
接收前端 JSON → 调用企微 MCP 创建智能表格 → 返回链接
"""

import json
import asyncio
import aiohttp
from aiohttp import web

MCP_URL = "https://qyapi.weixin.qq.com/mcp/robot-doc?apikey=S0RW0Ke7TfR0_NcWgTXq2Ht_BColuWjRzRVM9LMO3jHoIdKwI3gEPiNPnNxgkiPqhNXtAtM1_86okTOj8R5R8Q"
PORT = 8766


async def call_mcp(session, tool_name, arguments):
    """调用企微 MCP 工具"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    
    async with session.post(MCP_URL, json=payload, headers=headers) as resp:
        # MCP streamable-http 可能返回 SSE 或 JSON
        content_type = resp.headers.get("Content-Type", "")
        
        if "text/event-stream" in content_type:
            # SSE 模式：读取所有事件，取最后一个有 data 的
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


def extract_result_text(mcp_response):
    """从 MCP 响应中提取文本内容"""
    if not mcp_response:
        return None
    # jsonrpc 格式
    result = mcp_response.get("result", mcp_response)
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
    """
    POST /create
    Body: {"doc_name": "...", "sheets": [{"sheet_name": "...", "fields": [...], "sample_records": [...]}]}
    """
    try:
        schema = await request.json()
    except:
        return web.json_response({"error": "无效的 JSON"}, status=400)

    doc_name = schema.get("doc_name", "Demo智能表格")
    sheets = schema.get("sheets", [])
    
    if not sheets:
        return web.json_response({"error": "sheets 不能为空"}, status=400)

    steps = []
    
    async with aiohttp.ClientSession() as session:
        # Step 1: 创建智能表格文档
        steps.append("正在创建智能表格...")
        resp = await call_mcp(session, "create_doc", {
            "doc_type": 10,
            "doc_name": doc_name
        })
        result = extract_result_text(resp)
        
        if not result or (isinstance(result, dict) and result.get("errcode", 0) != 0):
            return web.json_response({"error": "创建文档失败", "detail": str(result)}, status=500)
        
        # 提取 docid 和 url
        docid = None
        doc_url = None
        if isinstance(result, dict):
            docid = result.get("docid")
            doc_url = result.get("url")
        
        if not docid:
            return web.json_response({"error": "未获取到 docid", "detail": str(result)}, status=500)
        
        steps.append(f"文档已创建: {doc_url}")

        # Step 2: 获取默认子表
        resp = await call_mcp(session, "smartsheet_get_sheet", {"docid": docid})
        sheet_result = extract_result_text(resp)
        
        # 提取默认 sheet_id
        default_sheet_id = None
        if isinstance(sheet_result, dict):
            sheet_list = sheet_result.get("sheet_list", sheet_result.get("sheets", []))
            if isinstance(sheet_list, list) and len(sheet_list) > 0:
                default_sheet_id = sheet_list[0].get("sheet_id")
        
        created_sheets = []
        
        for idx, sheet_def in enumerate(sheets):
            sheet_name = sheet_def.get("sheet_name", f"子表{idx+1}")
            fields = sheet_def.get("fields", [])
            records = sheet_def.get("sample_records", [])
            
            # 第一个子表用默认的，后面的新建
            if idx == 0 and default_sheet_id:
                sheet_id = default_sheet_id
                # 重命名子表
                await call_mcp(session, "smartsheet_update_sheet", {
                    "docid": docid,
                    "sheet_id": sheet_id,
                    "title": sheet_name
                })
            else:
                # 新建子表
                resp = await call_mcp(session, "smartsheet_add_sheet", {
                    "docid": docid,
                    "title": sheet_name
                })
                sr = extract_result_text(resp)
                if isinstance(sr, dict):
                    sheet_id = sr.get("sheet_id")
                else:
                    steps.append(f"子表 {sheet_name} 创建失败")
                    continue
            
            if not sheet_id:
                steps.append(f"子表 {sheet_name} 无 sheet_id")
                continue
            
            steps.append(f"子表「{sheet_name}」已创建")

            # Step 3: 获取默认字段
            resp = await call_mcp(session, "smartsheet_get_fields", {
                "docid": docid,
                "sheet_id": sheet_id
            })
            fields_result = extract_result_text(resp)
            
            default_field_id = None
            default_field_type = "FIELD_TYPE_TEXT"
            if isinstance(fields_result, dict):
                field_list = fields_result.get("fields", [])
                if isinstance(field_list, list) and len(field_list) > 0:
                    default_field_id = field_list[0].get("field_id")
                    default_field_type = field_list[0].get("field_type", "FIELD_TYPE_TEXT")

            # Step 4: 重命名默认字段为第一个字段
            if fields and default_field_id:
                first_field = fields[0]
                await call_mcp(session, "smartsheet_update_fields", {
                    "docid": docid,
                    "sheet_id": sheet_id,
                    "fields": [{
                        "field_id": default_field_id,
                        "field_title": first_field["field_title"],
                        "field_type": default_field_type
                    }]
                })
                steps.append(f"  字段「{first_field['field_title']}」已设置")
                
                # Step 5: 添加剩余字段
                remaining_fields = fields[1:]
                if remaining_fields:
                    await call_mcp(session, "smartsheet_add_fields", {
                        "docid": docid,
                        "sheet_id": sheet_id,
                        "fields": [{"field_title": f["field_title"], "field_type": f["field_type"]} for f in remaining_fields]
                    })
                    steps.append(f"  已添加 {len(remaining_fields)} 个字段")

            # Step 6: 插入示例数据
            if records:
                # 重新获取字段信息（确保字段已创建完毕）
                resp = await call_mcp(session, "smartsheet_get_fields", {
                    "docid": docid,
                    "sheet_id": sheet_id
                })
                current_fields = extract_result_text(resp)
                field_map = {}
                if isinstance(current_fields, dict):
                    for f in current_fields.get("fields", []):
                        field_map[f["field_title"]] = f
                
                # 构建 records
                formatted_records = []
                for record in records:
                    values = {}
                    for key, val in record.items():
                        if key not in field_map:
                            continue
                        ft = field_map[key].get("field_type", "FIELD_TYPE_TEXT")
                        
                        if ft == "FIELD_TYPE_TEXT":
                            values[key] = [{"type": "text", "text": str(val)}]
                        elif ft in ("FIELD_TYPE_NUMBER", "FIELD_TYPE_CURRENCY", "FIELD_TYPE_PERCENTAGE", "FIELD_TYPE_PROGRESS"):
                            try:
                                values[key] = float(val) if val else 0
                            except:
                                values[key] = [{"type": "text", "text": str(val)}]
                        elif ft == "FIELD_TYPE_SINGLE_SELECT":
                            values[key] = [{"text": str(val)}]
                        elif ft == "FIELD_TYPE_DATE_TIME":
                            values[key] = str(val)
                        elif ft == "FIELD_TYPE_CHECKBOX":
                            values[key] = bool(val)
                        elif ft in ("FIELD_TYPE_PHONE_NUMBER", "FIELD_TYPE_EMAIL", "FIELD_TYPE_BARCODE"):
                            values[key] = str(val)
                        elif ft == "FIELD_TYPE_URL":
                            values[key] = [{"type": "url", "text": str(val), "link": str(val)}]
                        else:
                            values[key] = [{"type": "text", "text": str(val)}]
                    
                    formatted_records.append({"values": values})
                
                if formatted_records:
                    await call_mcp(session, "smartsheet_add_records", {
                        "docid": docid,
                        "sheet_id": sheet_id,
                        "records": formatted_records
                    })
                    steps.append(f"  已插入 {len(formatted_records)} 条示例数据")
            
            created_sheets.append({"sheet_name": sheet_name, "sheet_id": sheet_id})

    return web.json_response({
        "success": True,
        "doc_name": doc_name,
        "docid": docid,
        "url": doc_url,
        "sheets": created_sheets,
        "steps": steps
    })


async def health(request):
    return web.json_response({"status": "ok"})


# CORS 中间件
@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        resp = web.Response()
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


app = web.Application(middlewares=[cors_middleware])
app.router.add_get("/health", health)
app.router.add_post("/create", create_smartsheet)
app.router.add_options("/create", health)  # CORS preflight

if __name__ == "__main__":
    print(f"🚀 智能表格创建服务启动在 http://localhost:{PORT}")
    print(f"   POST /create  - 创建智能表格")
    print(f"   GET  /health  - 健康检查")
    web.run_app(app, host="127.0.0.1", port=PORT)
