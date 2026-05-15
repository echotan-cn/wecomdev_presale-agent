#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信定制开发需求助手 - 服务端
长连接 WebSocket + 需求洞察 Agent

依赖安装：
  pip install websockets aiohttp

运行：
  python main.py --bot-id YOUR_BOT_ID --secret YOUR_SECRET
"""

import argparse
import asyncio
import json
import logging
import sys
import time
import uuid
from pathlib import Path

import websockets

from agent.dialogue import DemandInsightAgent
from agent.state import SessionState
from cases.library import CaseLibrary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("wecom-bot")


# ============================================================
# 企业微信长连接 WebSocket 客户端
# ============================================================

class WeComWebSocketClient:
    """企业微信智能机器人长连接客户端"""

    WSS_URL = "wss://openws.work.weixin.qq.com"
    HEARTBEAT_INTERVAL = 30  # 秒

    def __init__(self, bot_id: str, secret: str, agent: DemandInsightAgent):
        self.bot_id = bot_id
        self.secret = secret
        self.agent = agent
        self.ws = None
        self._running = False

    async def connect(self):
        """建立长连接并订阅"""
        logger.info(f"正在连接到 {self.WSS_URL} ...")
        self.ws = await websockets.connect(self.WSS_URL, ping_interval=None)
        logger.info("WebSocket 连接成功，发送订阅请求...")

        # 订阅命令
        subscribe_cmd = {
            "cmd": "aibot_subscribe",
            "headers": {"req_id": self._req_id()},
            "body": {
                "bot_id": self.bot_id,
                "secret": self.secret,
            },
        }
        await self.ws.send(json.dumps(subscribe_cmd))

        resp = await self.ws.recv()
        resp_data = json.loads(resp)
        if resp_data.get("errcode") != 0:
            logger.error(f"订阅失败: {resp_data}")
            raise Exception(f"订阅失败: {resp_data.get('errmsg')}")

        logger.info("订阅成功，长连接已建立！")
        self._running = True

    async def run(self):
        """主循环：处理消息+心跳"""
        await self.connect()
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        try:
            while self._running:
                try:
                    raw = await asyncio.wait_for(self.ws.recv(), timeout=60)
                    msg = json.loads(raw)
                    await self._handle_message(msg)
                except asyncio.TimeoutError:
                    # 正常的超时，继续循环
                    continue
                except websockets.ConnectionClosed as e:
                    logger.warning(f"连接断开: {e}")
                    break
        finally:
            heartbeat_task.cancel()
            await self._reconnect()

    async def _handle_message(self, msg: dict):
        """处理各类回调消息"""
        cmd = msg.get("cmd", "")
        body = msg.get("body", {})
        headers = msg.get("headers", {})

        logger.info(f"收到命令: {cmd} | msgid={body.get('msgid', 'N/A')}")

        if cmd == "aibot_msg_callback":
            # 用户发来的消息
            user_text = body.get("text", {}).get("content", "")
            chatid = body.get("chatid", "")
            from_user = body.get("from", {}).get("userid", "")
            msgid = body.get("msgid", "")

            await self._handle_user_message(user_text, chatid, from_user, msgid)

        elif cmd == "aibot_event_callback":
            event_type = body.get("event", {}).get("eventtype", "")
            if event_type == "enter_chat":
                # 用户进入会话，发送欢迎语
                await self._send_welcome_msg(body)
            elif event_type == "disconnected_event":
                logger.warning("收到断开事件，可能是新连接替代了本连接")

        elif cmd == "ping":
            # 服务端心跳
            await self._send_pong(headers.get("req_id", ""))

    async def _handle_user_message(self, user_text: str, chatid: str, from_user: str, msgid: str):
        """处理用户消息，运行 Agent 对话逻辑"""
        session_id = f"{chatid}_{from_user}"

        # 调用 Agent 获取回复
        reply_content, is_final = await self.agent.process(session_id, user_text)

        # 流式回复
        if isinstance(reply_content, str):
            # 单条消息，一次性发送
            await self._send_text_message(chatid, reply_content)
        elif isinstance(reply_content, dict) and reply_content.get("type") == "stream":
            # 流式消息
            stream_id = f"stream_{msgid}"
            content_chunks = reply_content.get("chunks", [])
            for i, chunk in enumerate(content_chunks):
                is_last = (i == len(content_chunks) - 1)
                await self._send_stream_chunk(
                    chatid, stream_id, chunk,
                    finish=is_last,
                    feedback_id=reply_content.get("feedback_id")
                )

    async def _send_text_message(self, chatid: str, content: str, markdown: bool = False):
        """发送文本/markdown 回复（用 aibot_respond_msg）"""
        body = {
            "msgtype": "markdown" if markdown else "text",
        }
        if markdown:
            body["markdown"] = {"content": content}
        else:
            body["text"] = {"content": content}

        msg = {"cmd": "aibot_respond_msg", "headers": {"req_id": self._req_id()}, "body": body}
        await self.ws.send(json.dumps(msg, ensure_ascii=False))

    async def _send_stream_chunk(self, chatid: str, stream_id: str, content: str, finish: bool, feedback_id: str = None):
        """发送流式消息片段"""
        body = {
            "chatid": chatid,
            "chat_type": 1,
            "msgtype": "stream",
            "stream": {
                "id": stream_id,
                "finish": finish,
                "content": content,
            },
        }
        if feedback_id:
            body["stream"]["feedback"] = {"id": feedback_id}

        msg = {"cmd": "aibot_respond_msg", "headers": {"req_id": self._req_id()}, "body": body}
        await self.ws.send(json.dumps(msg, ensure_ascii=False))

    async def _send_welcome_msg(self, body: dict):
        """发送欢迎语"""
        from_user = body.get("from", {}).get("userid", "")
        msgid = body.get("msgid", "")

        welcome = self.agent.get_welcome_message()

        msg = {
            "cmd": "aibot_respond_welcome_msg",
            "headers": {"req_id": self._req_id()},
            "body": {
                "msgtype": "text",
                "text": {"content": welcome},
            },
        }
        await self.ws.send(json.dumps(msg, ensure_ascii=False))

    async def _send_pong(self, req_id: str):
        """响应心跳"""
        msg = {"cmd": "pong", "headers": {"req_id": req_id}}
        await self.ws.send(json.dumps(msg))

    async def _heartbeat_loop(self):
        """心跳保活循环"""
        while self._running:
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)
            if self._running and self.ws:
                try:
                    await self.ws.send(json.dumps({"cmd": "ping", "headers": {"req_id": self._req_id()}}))
                except Exception as e:
                    logger.warning(f"心跳发送失败: {e}")
                    break

    async def _reconnect(self):
        """断线重连（指数退避）"""
        delay = 5
        while True:
            logger.info(f"{delay}秒后尝试重连...")
            await asyncio.sleep(delay)
            try:
                await self.connect()
                await self.run()
                break
            except Exception as e:
                logger.error(f"重连失败: {e}")
                delay = min(delay * 2, 120)

    @staticmethod
    def _req_id() -> str:
        return f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


# ============================================================
# 入口
# ============================================================

async def main():
    parser = argparse.ArgumentParser(description="企业微信定制开发需求助手 - 服务端")
    parser.add_argument("--bot-id", required=True, help="智能机器人的 BotID")
    parser.add_argument("--secret", required=True, help="长连接专用 Secret")
    parser.add_argument("--cases-dir", default=str(Path(__file__).parent / "cases"), help="案例文件夹路径")
    args = parser.parse_args()

    # 加载案例库
    case_lib = CaseLibrary(args.cases_dir)
    logger.info(f"案例库加载完成，共 {case_lib.count()} 个案例")

    # 初始化 Agent
    agent = DemandInsightAgent(case_lib)

    # 启动长连接
    client = WeComWebSocketClient(args.bot_id, args.secret, agent)
    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("服务已停止")
