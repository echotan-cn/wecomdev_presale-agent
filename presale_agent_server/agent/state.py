#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话状态管理
每个用户会话独立维护一个状态机
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
import time


class Stage(Enum):
    """对话阶段"""
    STAGE_0_ICE_BREAK = 0  # 破冰定向
    STAGE_1_OVERVIEW = 1    # 业务全景
    STAGE_2_DEEP_DIVE = 2   # 细节深挖
    STAGE_3_REPORT = 3      # 生成报告


@dataclass
class DialogueData:
    """收集到的需求数据"""
    # 第0轮
    industry: str = ""           # 行业
    company_size: str = ""        # 企业规模
    problem_direction: str = ""  # 问题方向

    # 第1轮
    workflow: str = ""           # 业务流程
    pain_points: str = ""         # 痛点
    modules: str = ""             # 期望模块

    # 第2轮
    data_scale: str = ""         # 数据规模
    key_nodes: str = ""          # 关键节点
    roles: str = ""              # 使用角色
    business_detail: str = ""    # 业务模式细节
    data_source: str = ""        # 数据来源
    granularity: str = ""       # 管理颗粒度
    analysis_dimensions: str = "" # 经营分析维度

    # 元数据
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class SessionState:
    """单用户会话状态"""
    session_id: str
    user_id: str = ""

    stage: Stage = Stage.STAGE_0_ICE_BREAK
    turn_in_stage: int = 0  # 当前阶段内的轮次

    data: DialogueData = field(default_factory=DialogueData)

    history: list = field(default_factory=list)  # 对话历史

    def advance_stage(self):
        """推进到下一阶段"""
        if self.stage.value < Stage.STAGE_3_REPORT.value:
            self.stage = Stage(self.stage.value + 1)
            self.turn_in_stage = 0
            self.data.updated_at = time.time()

    def add_turn(self):
        """当前阶段增加一轮"""
        self.turn_in_stage += 1
        self.data.updated_at = time.time()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "stage": self.stage.name,
            "turn_in_stage": self.turn_in_stage,
            "data": asdict(self.data),
            "history": self.history,
        }


class SessionManager:
    """会话管理器（内存存储，生产环境建议换 Redis）"""

    def __init__(self):
        self._sessions: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

    def remove(self, session_id: str):
        self._sessions.pop(session_id, None)

    def cleanup_old(self, max_age_seconds: int = 3600):
        """清理超过 max_age 秒的会话"""
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if now - s.data.updated_at > max_age_seconds]
        for sid in expired:
            self.remove(sid)
        if expired:
            print(f"[SessionManager] 清理了 {len(expired)} 个过期会话")

    def count(self) -> int:
        return len(self._sessions)


# 全局会话管理器（单例）
session_manager = SessionManager()
