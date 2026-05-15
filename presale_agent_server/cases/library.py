#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案例知识库
简单的关键词匹配 RAG（后续可升级为向量检索）
"""

import json
import re
from pathlib import Path
from typing import Optional


CASE_LIBRARY = [
    {
        "customer": "兄弟装饰",
        "industry": "建筑业/房地产",
        "scale": "1001-5000人",
        "project_type": "CRM改造+ERP对接",
        "pain_points": "已用智能表格CRM模板，需要改造+对接自有ERP系统",
        "modules": ["智能表格CRM改造", "ERP数据对接", "业务数据同步"],
        "highlight": "CRM与ERP数据双向打通",
        "effect": "提升客户管理效率，减少人工数据维护",
        "delivery": "智能表格+API开发",
        "price_range": "¥30,000+",
        "tags": ["CRM", "ERP对接", "建筑", "房地产", "客户管理", "系统集成"],
    },
    {
        "customer": "正时家居",
        "industry": "制造业",
        "scale": "1-100人",
        "project_type": "客户管理+项目管理",
        "pain_points": "30多人，需要做跟客户的跟进记录和项目管理",
        "modules": ["客户档案", "跟进记录", "项目管理", "销售漏斗"],
        "highlight": "轻量级CRM+项目跟踪一体化",
        "effect": "客户跟进有记录，项目进度可视化",
        "delivery": "纯智能表格搭建",
        "price_range": "¥4,000~¥8,000",
        "tags": ["制造业", "CRM", "项目管理", "客户管理", "轻量级"],
    },
    {
        "customer": "盛隆国际",
        "industry": "建筑业/房地产",
        "scale": "小规模",
        "project_type": "房地产案场管理",
        "pain_points": "客户录入、房源销控信息管理",
        "modules": ["客户录入", "房源管理", "销控信息", "跟进记录"],
        "highlight": "案场客户与房源联动管理",
        "effect": "案场管理数字化，房源状态实时透明",
        "delivery": "纯智能表格搭建",
        "price_range": "¥4,980",
        "tags": ["房地产", "案场管理", "房源销控", "客户录入"],
    },
    {
        "customer": "贵州新粤黔海",
        "industry": "交通/运输/物流",
        "scale": "1-100人",
        "project_type": "物流撮合交易平台",
        "pain_points": "客户下单→匹配供应商→报价→收款的全链路",
        "modules": ["客户下单", "供应商匹配", "在线报价", "微信支付收款", "数据看板"],
        "highlight": "小程序+企微智能表格，打通获客→匹配→支付闭环",
        "effect": "物流撮合全流程线上化",
        "delivery": "应用定制（小程序）+智能表格",
        "price_range": "¥30,000",
        "tags": ["物流", "撮合平台", "支付", "小程序", "供应商管理"],
    },
    {
        "customer": "领航文化",
        "industry": "教育",
        "scale": "1-100人",
        "project_type": "托管班家校互通系统",
        "pain_points": "家长作业提交、老师考勤、错题讲解、周报生成、家长查询",
        "modules": [
            "作业提交双向收发",
            "考勤登记推送",
            "错题标注+视频生成",
            "周报自动生成推送",
            "家长自主查询",
            "三端权限隔离",
        ],
        "highlight": "家长/老师/管理员三端信息隔离，家长可自主查询",
        "effect": "家校互通自动化，减少老师80%行政工作量",
        "delivery": "纯定开（系统集成等）",
        "price_range": "需评估",
        "tags": ["教育", "家校互通", "托管班", "错题本", "周报", "自动化"],
    },
    {
        "customer": "明心数智",
        "industry": "服务业/本地生活",
        "scale": "1-100人",
        "project_type": "接待任务自动派发系统",
        "pain_points": "申请-分配链条断裂，状态不可视，评价缺失，数据无沉淀",
        "modules": [
            "接待申请",
            "自动分配（规则引擎）",
            "状态可查",
            "服务评价",
            "数据可视化",
        ],
        "highlight": "接待任务闭环管理，自动分配+满意度评价",
        "effect": "分配效率提升，接待数据可视化",
        "delivery": "纯智能表格搭建",
        "price_range": "¥6,980",
        "tags": ["接待管理", "任务分配", "自动化", "服务评价", "数据看板"],
    },
    {
        "customer": "合骥基金",
        "industry": "金融",
        "scale": "1-100人",
        "project_type": "财务报销+人事招聘系统",
        "pain_points": "财务报销、发票查重、人事招聘审批流程",
        "modules": ["报销申请", "发票查重", "招聘审批", "财务统计报表"],
        "highlight": "财务+人事一体化管理",
        "effect": "财务合规性提升，招聘流程透明",
        "delivery": "纯智能表格搭建",
        "price_range": "¥9,800",
        "tags": ["金融", "财务报销", "发票查重", "招聘", "审批"],
    },
    {
        "customer": "小隐餐饮",
        "industry": "餐饮",
        "scale": "小规模",
        "project_type": "OKR考核+HR自动化",
        "pain_points": "OKR考核设计困难，HR工作效率低，在职证明需人工处理",
        "modules": [
            "OKR目标制定",
            "在线审批流程",
            "在职证明自动生成",
            "绩效关联工资核算",
        ],
        "highlight": "OKR+绩效+工资联动自动化",
        "effect": "减少HR 60%重复工作",
        "delivery": "智能表格+API开发",
        "price_range": "需评估",
        "tags": ["餐饮", "OKR", "绩效考核", "HR", "自动化"],
    },
    {
        "customer": "Time Ceramics",
        "industry": "批发零售",
        "scale": "1-100人",
        "project_type": "海外人事管理系统",
        "pain_points": "海外员工签证管理、进出厂工时统计、证件到期提醒",
        "modules": [
            "员工档案（证件管理）",
            "进出厂工时统计",
            "签证到期提醒",
            "请假管理",
        ],
        "highlight": "工时精确统计，证件到期自动提醒",
        "effect": "人事管理合规，在场天数一键统计",
        "delivery": "智能表格",
        "price_range": "¥15,800（含套件）",
        "tags": ["海外人事", "工时统计", "签证管理", "证件提醒", "批发零售"],
    },
    {
        "customer": "远明建设",
        "industry": "建筑业",
        "scale": "1-100人",
        "project_type": "建筑联营挂靠项目管理系统",
        "pain_points": "房建/市政/装修/绿化联营挂靠项目管理，1%管理费核算",
        "modules": [
            "联营项目总台账",
            "立项审批表",
            "合同管理台账",
            "资金&管理费管理表",
            "印章证照使用登记",
            "签证变更风险跟踪",
            "项目进度安全巡检",
            "项目结案质保台账",
        ],
        "highlight": "8张关联表，1%管理费自动核算，联营挂靠全流程",
        "effect": "联营项目管理规范化，1%管理费自动计算",
        "delivery": "纯智能表格搭建（8个子表）",
        "price_range": "需评估",
        "tags": ["建筑业", "项目管理", "联营挂靠", "多表联动", "工程"],
    },
    {
        "customer": "酷睿达Credx",
        "industry": "制造业",
        "scale": "1-100人",
        "project_type": "全链路数字化管理",
        "pain_points": "CRM→OA审批→PMC排产→采购→入库→生产→质检→发货全链路",
        "modules": [
            "CRM订单导入",
            "OA审批流",
            "PMC排产",
            "采购管理",
            "入库出库",
            "生产执行",
            "质检",
            "包装发货",
            "ERP数据联动",
        ],
        "highlight": "从订单到发货全链路打通，用企微智能表格替代轻量ERP",
        "effect": "全流程数据流转，效率优先",
        "delivery": "应用定制+智能表格",
        "price_range": "需评估",
        "tags": ["制造业", "全链路", "PMC", "生产管理", "ERP替代"],
    },
    {
        "customer": "美港国际",
        "industry": "物流/货代",
        "scale": "1-100人",
        "project_type": "工单系统+会话同步",
        "pain_points": "客服处理100-200个群，工单手动录入，状态不透明",
        "modules": [
            "工单窗口（客户自助填写）",
            "系统自动生成工单号",
            "案件类型下拉",
            "状态追踪（待处理→已完成）",
            "满意度评分",
        ],
        "highlight": "工单窗口客户自助填写，自动同步到企微群",
        "effect": "工单处理效率提升，减少客服80%录入工作量",
        "delivery": "应用定制+智能表格",
        "price_range": "需评估",
        "tags": ["物流", "货代", "工单系统", "客服效率", "满意度评价"],
    },
    {
        "customer": "成都恒新源暖通",
        "industry": "服务业/维保",
        "scale": "1-100人",
        "project_type": "售后师傅工单管理+积分结算",
        "pain_points": "人工派工、积分计算、师傅工单照片人工存档",
        "modules": [
            "工单派发",
            "现场作业记录",
            "防伪溯源（照片留底）",
            "积分自动核算",
            "商机分发",
        ],
        "highlight": "替代手工Excel+企微收集表，师傅积分日清月结",
        "effect": "彻底替代手工，工作量减少70%",
        "delivery": "纯智能表格搭建",
        "price_range": "¥4,800",
        "tags": ["维保", "工单", "积分管理", "防伪溯源", "服务商"],
    },
    {
        "customer": "百鸣食品",
        "industry": "制造业",
        "scale": "小规模",
        "project_type": "类似金蝶的进销存系统",
        "pain_points": "需要进销存管理，与ERP系统对接",
        "modules": ["采购管理", "销售管理", "库存管理", "报表统计"],
        "highlight": "用企微智能表格替代传统ERP，轻量易用",
        "effect": "进销存管理数字化",
        "delivery": "应用定制+智能表格",
        "price_range": "需评估",
        "tags": ["制造业", "进销存", "ERP替代", "轻量化"],
    },
    {
        "customer": "烨嘉光电",
        "industry": "制造业",
        "scale": "501-1000人",
        "project_type": "数据中台+多系统拉通",
        "pain_points": "多个系统数据孤岛，需要统一入口、流程拉通、数据汇总",
        "modules": [
            "多系统数据中台",
            "流程拉通",
            "数据汇总",
            "审批统一入口",
            "智能表格实现CRM",
        ],
        "highlight": "企微作为数据中台，拉通其他系统统一入口",
        "effect": "打破数据孤岛，管理层一屏看全局",
        "delivery": "应用定制+智能表格",
        "price_range": "需评估（大型项目）",
        "tags": ["制造业", "数据中台", "系统集成", "多系统拉通", "数字化转型"],
    },
    {
        "customer": "璞谷科技",
        "industry": "制造业",
        "scale": "1-100人",
        "project_type": "销售客户管理+审批流程",
        "pain_points": "客户跟进管理、合同管理、报价审批流程",
        "modules": [
            "客户管理",
            "跟进记录",
            "合同管理",
            "报价审批",
            "权限控制",
        ],
        "highlight": "9张关联业务表，从客户需求到财务闭环",
        "effect": "销售全流程数字化",
        "delivery": "智能表格多子表",
        "price_range": "¥9,800",
        "tags": ["制造业", "CRM", "合同管理", "报价审批", "多表联动"],
    },
    {
        "customer": "志亿锌业（越南）",
        "industry": "制造业",
        "scale": "1-100人",
        "project_type": "任务分配+进度跟踪",
        "pain_points": "任务分配给员工，跟踪工作进度，截止日期提醒",
        "modules": ["任务分配", "进度跟踪", "截止日期提醒", "完成状态"],
        "highlight": "简单任务管理系统，适合生产型团队",
        "effect": "任务分配有记录，进度一目了然",
        "delivery": "纯智能表格搭建",
        "price_range": "¥4,600",
        "tags": ["制造业", "任务管理", "进度跟踪", "提醒", "轻量级"],
    },
    {
        "customer": "盘锦丰源蛋业",
        "industry": "农林牧渔",
        "scale": "1-100人",
        "project_type": "任务派发系统",
        "pain_points": "给员工下任务，员工执行后上报，查看完成情况",
        "modules": ["任务下达", "执行上报", "完成追踪", "统计汇总"],
        "highlight": "任务闭环管理，员工执行有记录",
        "effect": "任务执行透明化",
        "delivery": "纯智能表格搭建",
        "price_range": "需评估",
        "tags": ["农业", "任务管理", "执行追踪", "上下级协作"],
    },
    {
        "customer": "华遥食品",
        "industry": "食品工厂",
        "scale": "中等",
        "project_type": "销售全链路SOP+CRM+仪表盘+ERP打通",
        "pain_points": "搭建整套销售SOP，包含CRM、表单、仪表盘、ERP打通",
        "modules": [
            "销售SOP流程",
            "CRM客户管理",
            "数据仪表盘",
            "ERP数据打通",
            "日报周报",
            "AI辅助",
        ],
        "highlight": "食品工厂销售全链路数字化，含ERP打通",
        "effect": "销售数据可视化，ERP数据实时同步",
        "delivery": "应用定制+智能表格+API开发",
        "price_range": "需评估（大型项目）",
        "tags": ["食品", "销售SOP", "CRM", "ERP打通", "仪表盘", "AI辅助"],
    },
    {
        "customer": "南昌泰昂科技",
        "industry": "科技",
        "scale": "小规模",
        "project_type": "智能表格内部联动+进销存",
        "pain_points": "智能表格内部联动需求，类似飞书AI制作智能表格",
        "modules": ["多表联动", "数据汇总", "进销存管理"],
        "highlight": "用企微智能表格实现内部数据联动",
        "effect": "数据自动汇总，减少重复录入",
        "delivery": "智能表格+API开发",
        "price_range": "需评估",
        "tags": ["科技", "多表联动", "进销存", "自动化"],
    },
    {
        "customer": "某律所（通用模板）",
        "industry": "法律服务",
        "scale": "10-50人",
        "project_type": "全流程案件管理系统",
        "pain_points": "客户跟进混乱、案件进度不透明、手工对账容易出错、年度目标难追踪",
        "modules": [
            "线索管理（来源追踪）",
            "案件管理（6类案件×5级状态）",
            "收付款管理（单案利润自动核算）",
            "目标达成 & 预算执行（自动生成报表）",
            "内容营销（10+渠道曝光追踪）",
        ],
        "highlight": "单案利润自动核算 + 年度经营报表自动生成",
        "effect": "全流程数字化，年度目标达成情况一键生成",
        "delivery": "企微智能表格多子表 + 自动化规则 + 多视图",
        "price_range": "需评估",
        "tags": ["律所", "案件管理", "利润核算", "目标达成", "客户管理"],
    },
    {
        "customer": "安图特",
        "industry": "IT/系统集成",
        "scale": "中大型",
        "project_type": "采购竞价系统",
        "pain_points": "供应商管理混乱、比价效率低、合同管理不规范",
        "modules": ["供应商管理", "采购竞价流程", "合同管理", "报表统计"],
        "highlight": "竞价流程自动化，多供应商比价一目了然",
        "effect": "采购效率提升50%，合规率100%",
        "delivery": "企微智能表格 + 自动化规则",
        "price_range": "需评估",
        "tags": ["采购", "竞价", "供应商管理", "合同管理"],
    },
    {
        "customer": "广东中健",
        "industry": "制造业",
        "scale": "中大型",
        "project_type": "移动报工系统",
        "pain_points": "车间报工依赖纸笔，数据滞后，统计困难",
        "modules": ["工单管理", "移动报工", "产能统计", "计件薪资"],
        "highlight": "扫码移动报工，实时产能看板",
        "effect": "报工效率提升60%，数据实时准确",
        "delivery": "企微智能表格 + 移动端适配",
        "price_range": "需评估",
        "tags": ["制造业", "报工", "移动端", "产能统计"],
    },
    {
        "customer": "和气桃桃",
        "industry": "餐饮连锁",
        "scale": "连锁品牌",
        "project_type": "金蝶云星空集成第三方支付",
        "pain_points": "订单数据分散，财务对账困难，资金流水不清晰",
        "modules": ["订单管理", "支付集成", "财务对账", "经营报表"],
        "highlight": "金蝶 ERP + 微信/支付宝收单，自动对账",
        "effect": "财务对账时间从3天缩短到1小时",
        "delivery": "企微智能表格 + ERP 集成",
        "price_range": "需评估",
        "tags": ["餐饮", "ERP集成", "支付", "财务对账"],
    },
    {
        "customer": "云南淳定",
        "industry": "政务/企业服务",
        "scale": "中大型",
        "project_type": "企微智能表格项目管理",
        "pain_points": "项目进度不透明，跨部门协作困难，交付物管理混乱",
        "modules": ["项目管理", "任务分配", "进度跟踪", "交付物管理"],
        "highlight": "多视图项目看板，跨部门协作无缝",
        "effect": "项目交付准时率提升40%",
        "delivery": "企微智能表格多子表 + 自动化规则",
        "price_range": "需评估",
        "tags": ["项目管理", "跨部门协作", "进度管理"],
    },
    {
        "customer": "桂桂茶",
        "industry": "餐饮连锁",
        "scale": "连锁品牌",
        "project_type": "金蝶云星空食神经销商订货集成第三方支付收单",
        "pain_points": "经销商订货流程繁琐，订单确认慢，付款核对困难",
        "modules": ["订货管理", "支付收单", "经销商管理", "经营分析"],
        "highlight": "食神经销商订货 + 支付收单一体化",
        "effect": "订货确认周期从2天缩短到2小时",
        "delivery": "企微智能表格 + 金蝶集成 + 支付集成",
        "price_range": "需评估",
        "tags": ["餐饮", "订货", "经销商", "支付", "金蝶"],
    },
    # ========== 新增案例：制造业-改善提报 ==========
    {
        "customer": "福鸿",
        "industry": "制造业",
        "scale": "中等",
        "project_type": "员工改善提报+积分奖励系统",
        "pain_points": "改善建议提报流程不规范，积分计算靠人工，奖品库存管理混乱",
        "modules": ["改善提报", "积分自动计算", "奖品库存管理", "采购入库", "奖品兑换"],
        "highlight": "6表联动，提报→积分→兑换全流程自动化，积分实时计算",
        "effect": "提报流程规范化，积分零人工干预，奖品库存实时可见",
        "delivery": "纯智能表格搭建（6个子表联动）",
        "price_range": "需评估",
        "tags": ["制造业", "改善提报", "积分管理", "奖品兑换", "自动化", "6表联动"],
    },
    # ========== 新增案例：B2B工业品-销售CRM ==========
    {
        "customer": "长谊新材料",
        "industry": "B2B工业品/造纸",
        "scale": "1-100人",
        "project_type": "销售线索CRM+ERP对接",
        "pain_points": "线索收集靠Excel、分配靠微信群、老板看不到转化率、业务员日报重复填写",
        "modules": ["线索收集", "线索分配", "跟进管理", "项目立项", "销售日报", "ERP数据同步", "仪表盘"],
        "highlight": "24表4模块，线索→跟进→成交全链路可视化，自动生成日报",
        "effect": "线索转化率可视化，业务员减少50%日报工作量",
        "delivery": "企微智能表格（24张子表）+ ERP数据同步",
        "price_range": "需评估",
        "tags": ["B2B", "CRM", "销售管理", "线索跟进", "转化率", "ERP对接", "造纸", "工业品"],
    },
]


class CaseLibrary:
    """
    案例知识库
    支持：关键词匹配检索 + 行业知识库 + 需求池
    后续可升级：向量嵌入 + 余弦相似度检索
    """

    def __init__(self, cases_dir: Optional[str] = None):
        self.cases = list(CASE_LIBRARY)
        self.industry_knowledge = {}  # 行业通用知识
        self.detailed_cases = []  # 完整交付案例
        self.demand_pool = []  # 需求池数据

        # 如果有额外案例文件，加载进来
        if cases_dir:
            extra_cases = self._load_from_dir(cases_dir)
            self.cases.extend(extra_cases)

        # 加载知识库目录
        knowledge_dir = Path(__file__).parent.parent / "knowledge"
        if knowledge_dir.exists():
            self._load_knowledge(knowledge_dir)

    def count(self) -> int:
        return len(self.cases)

    def match(self, query: str, top_k: int = 3) -> list[dict]:
        """
        根据查询文本匹配最相关的案例
        多维度加权匹配：标签、行业、项目类型、痛点关键词
        """
        if not query:
            return self.cases[:top_k]

        query_lower = query.lower()
        scored = []
        for case in self.cases:
            score = 0

            # 精确词匹配计分
            for tag in case.get("tags", []):
                if tag.lower() in query_lower or query_lower in tag.lower():
                    score += 5
            if case.get("industry", "").lower() in query_lower:
                score += 3
            if case.get("project_type", "").lower() in query_lower:
                score += 2

            # 痛点关键词匹配
            pain = case.get("pain_points", "").lower()
            query_words = [w for w in re.split(r'[，,、。\s]+', query_lower) if len(w) >= 2]
            for word in query_words:
                if word in pain:
                    score += 3
                # 模块名匹配
                for mod in case.get("modules", []):
                    if isinstance(mod, str) and word in mod.lower():
                        score += 2

            if score > 0:
                scored.append((score, case))

        # 按分数排序，取 top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    def match_industry(self, industry: str) -> Optional[dict]:
        """匹配行业通用知识"""
        if not industry:
            return None
        industry_lower = industry.lower()
        for key, data in self.industry_knowledge.items():
            tags = [t.lower() for t in data.get("tags", [])]
            name = data.get("industry_name", "").lower()
            if industry_lower in name or any(industry_lower in t or t in industry_lower for t in tags):
                return data
        return None

    def match_detailed_case(self, query: str, top_k: int = 2) -> list[dict]:
        """匹配完整交付案例（含字段定义等详细信息）"""
        if not query or not self.detailed_cases:
            return []

        query_lower = query.lower()
        scored = []
        for case in self.detailed_cases:
            score = 0
            meta = case.get("meta", {})
            if meta.get("industry", "").lower() in query_lower:
                score += 5
            if meta.get("scene", "").lower() in query_lower:
                score += 3
            summary = case.get("demand_summary", "").lower()
            for word in re.split(r'[，,、。\s]+', query_lower):
                if len(word) >= 2 and word in summary:
                    score += 2
            if score > 0:
                scored.append((score, case))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    def get_all(self) -> list[dict]:
        return list(self.cases)

    def _load_knowledge(self, knowledge_dir: Path):
        """加载知识库目录"""
        # 行业知识
        industries_dir = knowledge_dir / "industries"
        if industries_dir.exists():
            for f in industries_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    self.industry_knowledge[f.stem] = data
                except Exception:
                    pass

        # 完整交付案例
        cases_dir = knowledge_dir / "cases"
        if cases_dir.exists():
            for f in cases_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    self.detailed_cases.append(data)
                except Exception:
                    pass

        # 需求池
        pool_dir = knowledge_dir / "demand_pool"
        if pool_dir.exists():
            for f in pool_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if "demands" in data:
                        self.demand_pool.extend(data["demands"])
                    elif "deals" in data:
                        self.demand_pool.extend(data["deals"])
                except Exception:
                    pass

    def _load_from_dir(self, cases_dir: str) -> list[dict]:
        """从目录加载额外的案例 JSON 文件"""
        extra = []
        dir_path = Path(cases_dir)
        if not dir_path.exists():
            return extra

        for f in dir_path.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    extra.extend(data)
            except Exception:
                pass
        return extra
