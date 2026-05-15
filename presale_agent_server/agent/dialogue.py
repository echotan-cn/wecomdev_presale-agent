#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
需求洞察 Agent — 核心对话逻辑
将 HTML Demo 的 agentLogic 迁移到这里
"""

import re
from typing import Optional

from .state import SessionState, SessionManager, Stage, DialogueData
from cases.library import CaseLibrary


WELCOME_MSG = """你好！我是**企业微信定制开发需求助手** 👋

在给你推荐方案之前，我想先花几分钟了解一下你的实际情况，这样才能帮你规划出真正好用的系统。

先问两个简单的：
1️⃣ 你们是什么行业的？公司大概多少人在用？
2️⃣ 这次想用智能表格解决什么方面的问题？（比如客户管理、项目跟踪、数据报表……一句话说个大方向就行）"""

PROMPT_STAGE_0 = """请先简单描述一下你的情况：
1️⃣ 你们是什么行业的？
2️⃣ 这次想用智能表格解决什么方面的问题？"""


class DemandInsightAgent:
    """
    需求洞察对话 Agent

    对话流程：
    - Stage 0（破冰定向）：获取行业 + 问题方向
    - Stage 1（业务全景）：获取流程 + 痛点 + 模块
    - Stage 2（细节深挖）：数据规模/关键节点/角色 等 6 个维度
    - Stage 3（报告）：输出结构化需求洞察报告
    """

    # 每阶段的快速回复建议（企微没有快速回复按钮，但可作为 Agent 提示词）
    QUICK_REPLIES: dict[int, list[str]] = {
        0: ["我们是律所，想管案件和客户", "制造业，想做采购管理", "我们是做电商的"],
        1: ["客户跟进混乱，订单容易漏", "各部门数据分散，对账麻烦", "项目多，进度不好把控"],
        2: ["大概几百个客户", "审批节点多，经常逾期", "需要区分销售和财务的权限"],
    }

    def __init__(self, case_lib: CaseLibrary):
        self.case_lib = case_lib
        self.session_mgr = SessionManager()

    # ----------------------------------------------------------
    # 对话入口
    # ----------------------------------------------------------

    async def process(self, session_id: str, user_input: str) -> tuple[str, bool]:
        """
        处理用户输入，返回 (回复内容, 是否结束当前报告)
        回复内容可能是普通文本，也可能是一个流式 dict
        """
        state = self.session_mgr.get(session_id)

        # 记录历史
        state.history.append({"role": "user", "content": user_input})

        # 分阶段处理
        if state.stage == Stage.STAGE_0_ICE_BREAK:
            reply = self._handle_stage_0(state, user_input)
        elif state.stage == Stage.STAGE_1_OVERVIEW:
            reply = self._handle_stage_1(state, user_input)
        elif state.stage == Stage.STAGE_2_DEEP_DIVE:
            reply = self._handle_stage_2(state, user_input)
        else:
            reply = "感谢你的信息！需求洞察已完成。如需重新开始，请说「重新开始」。"

        # 记录 Agent 回复
        state.history.append({"role": "agent", "content": reply if isinstance(reply, str) else str(reply)})

        return reply, state.stage == Stage.STAGE_3_REPORT

    def get_welcome_message(self) -> str:
        return WELCOME_MSG

    # ----------------------------------------------------------
    # 各阶段处理逻辑
    # ----------------------------------------------------------

    def _handle_stage_0(self, state: SessionState, user_input: str) -> str:
        """第0轮：破冰定向"""
        # 简单解析：提取行业关键词
        industry, direction = self._parse_industry(user_input)
        state.data.industry = industry or user_input
        state.data.problem_direction = direction or user_input

        state.advance_stage()

        return self._render_stream(
            f"好的，了解了！接下来帮你捋一下业务全貌 ——\n\n"
            f"请你描述一下：\n"
            f"1️⃣ 你们现在这块业务的**流程**大概是怎样的？\n"
            f"   （从头到尾走一遍，比如：接单→生产→发货→回款）\n"
            f"2️⃣ 现在**最头疼的问题**是什么？\n"
            f"   （出错最多的、最花时间的、最让你烦的）\n"
            f"3️⃣ 如果做一个管理系统，你希望它**包含哪些板块**？\n"
            f"   （比如：客户管理、订单管理、报表统计……）"
        )

    def _handle_stage_1(self, state: SessionState, user_input: str) -> str:
        """第1轮：业务全景"""
        state.data.workflow = user_input
        state.data.pain_points = user_input
        state.data.modules = user_input

        # 生成理解确认 + 案例匹配
        summary = self._generate_summary(state)
        cases = self.case_lib.match(state.data.industry, top_k=2)
        case_suggestion = self._format_cases_suggestion(cases)

        state.advance_stage()

        return self._render_stream(
            f"{summary}\n\n"
            f"确认无误的话，我再深入问几个细节，帮你把需求锁死 👇\n\n"
            f"1️⃣ **数据规模**：你们大概有多少核心业务数据？（比如多少客户/产品/订单）\n"
            f"2️⃣ **关键节点**：哪些环节需要自动提醒或通知？（比如逾期、审批、到期）\n"
            f"3️⃣ **使用角色**：谁来用这个系统？不同人看到的内容需要区分吗？"
            f"{case_suggestion}"
        )

    def _handle_stage_2(self, state: SessionState, user_input: str) -> str:
        """第2轮：细节深挖（2轮子对话）"""
        state.add_turn()

        if state.turn_in_stage == 1:
            state.data.data_scale = user_input
            state.data.key_nodes = user_input
            state.data.roles = user_input

            return self._render_stream(
                "明白了，记下来了 ✍️ 再问最后几个：\n\n"
                "4️⃣ **数据来源**：你们现在的数据在哪里？（Excel？其他系统？纸质记录？）需要迁移过来吗？\n"
                "5️⃣ **经营分析**：老板/管理层想看什么报表？按什么维度统计？（按月/按人/按区域…）\n"
                "6️⃣ **管理颗粒度**：数据要管到多细？\n"
                "   （比如库存到 SKU 还是批次？客户到公司还是联系人级别？）"
            )

        if state.turn_in_stage >= 2:
            state.data.data_source = user_input
            state.data.analysis_dimensions = user_input
            state.data.granularity = user_input

            # 生成最终报告
            state.advance_stage()
            report = self._generate_report(state)
            return report

        return "感谢补充！让我整理一下..."

    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------

    def _parse_industry(self, text: str) -> tuple[str, str]:
        """简单从文本中提取行业和方向关键词"""
        industry_keywords = {
            "律所": "法律服务", "律师": "法律服务",
            "制造": "制造业", "工厂": "制造业",
            "电商": "电商", "零售": "零售",
            "外贸": "外贸", "物流": "物流",
            "餐饮": "餐饮", "医疗": "医疗",
            "教育": "教育培训", "建筑": "建筑",
        }
        direction_keywords = {
            "客户": "客户管理", "案件": "案件管理", "项目": "项目管理",
            "订单": "订单管理", "采购": "采购管理", "库存": "库存管理",
            "财务": "财务管理", "审批": "流程审批", "报表": "报表统计",
        }

        industry = ""
        direction = ""
        for kw, ind in industry_keywords.items():
            if kw in text:
                industry = ind
                break
        for kw, d in direction_keywords.items():
            if kw in text:
                direction = d
                break

        return industry, direction

    def _generate_summary(self, state: SessionState) -> str:
        industry = state.data.industry or "你的行业"
        return (
            f"📝 **我目前的理解是：**\n\n"
            f"> 你们是「{industry}」行业，想基于企业微信智能表格搭建一套管理系统，\n"
            f"> 核心目标是解决手工管理带来的效率和准确性问题。\n\n"
            f"根据你刚才的描述，系统大概需要覆盖以下板块：\n"
            f"- 核心业务流程的在线化管理\n"
            f"- 关键数据的统一记录和查询\n"
            f"- 经营分析和报表自动生成\n\n"
            f"**对吗？有没有需要补充或纠正的？**"
        )

    def _format_cases_suggestion(self, cases: list[dict]) -> str:
        if not cases:
            return ""
        lines = ["\n\n---\n\n📌 **推荐参考案例**"]
        for case in cases:
            lines.append(f"- **{case['customer']}**：{case['project_type']}")
            if case.get("highlight"):
                lines.append(f"  亮点：{case['highlight']}")
        lines.append("\n_（案例仅供参考，你的需求可能不同，我们会根据你的情况定制）_")
        return "\n".join(lines)

    def _generate_report(self, state: SessionState) -> str:
        """生成最终需求洞察报告"""
        data = state.data

        def g(field: str) -> str:
            val = getattr(data, field, "") or "待确认"
            return val if val else "待确认"

        report_lines = [
            "✅ **需求收集完成！** 整理如下：",
            "",
            "━━━━━━━━━━━━━━━━━━━",
            "📋 **需求洞察报告**",
            "━━━━━━━━━━━━━━━━━━━",
            "",
            "**【客户信息】**",
            f"• 行业：{g('industry')}",
            f"• 规模：{g('company_size') or '待确认'}",
            "",
            "**【需求概览】**",
            f"• 一句话描述：基于企微智能表格搭建{g('industry') or '业务'}全流程管理系统",
            f"• 原始痛点：{g('pain_points')}",
            "",
            "**【系统框架】**",
            f"• 核心模块：{g('modules')}",
            "",
            "**【细节规格】**",
            f"• 数据规模：{g('data_scale')}",
            f"• 关键节点：{g('key_nodes')}",
            f"• 管理颗粒度：{g('granularity')}",
            f"• 数据来源：{g('data_source')}",
            f"• 分析维度：{g('analysis_dimensions')}",
            f"• 使用角色：{g('roles')}",
            "",
            "━━━━━━━━━━━━━━━━━━━",
            "",
            "这份报告我会同步给方案团队，后续会有专人跟你确认技术细节并出具正式方案。",
            "",
            "还有什么需要补充的吗？",
        ]
        return "\n".join(report_lines)

    def _render_stream(self, content: str, chunk_size: int = 50) -> dict:
        """
        将文本转为流式消息格式
        返回 dict，main.py 会按 chunks 逐段发送
        """
        chunks = [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]
        return {"type": "stream", "chunks": chunks}
