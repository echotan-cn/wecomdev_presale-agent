# 企业微信定制开发需求助手

> AI 驱动的售前需求洞察系统，基于 DeepSeek V4-Flash + 企微智能表格 MCP

## 在线体验

🔗 **https://deploy-ok11.vercel.app**

## 功能

1. **智能需求收集**：5步结构化问答，AI 根据用户回答动态生成追问
2. **需求洞察报告**：AI 自动生成包含业务分析、方案建议、报价区间的完整报告
3. **一键生成 Demo**：根据需求自动创建企微智能表格（含子表+字段+示例数据）
4. **数据自动归档**：所有需求数据自动保存到「售前agent需求收集台账」

## 技术栈

- **前端**：纯 HTML + CSS + JS（单文件，无框架依赖）
- **AI**：DeepSeek V4-Flash API（动态生成问题和报告）
- **后端**：Vercel Python Serverless Functions
- **数据**：企微智能表格 MCP（创建表格 + 保存台账）
- **部署**：Vercel

## 项目结构

```
├── deploy/                    # Vercel 部署目录
│   ├── index.html             # 前端页面
│   ├── vercel.json            # Vercel 配置
│   └── api/
│       ├── create.py          # Serverless: 创建智能表格
│       └── save.py            # Serverless: 保存需求到台账
├── presale_agent_server/      # 本地服务 + 知识库
│   ├── unified_server.py      # 本地统一服务（开发用）
│   ├── smartsheet_creator.py  # 本地表格创建服务
│   ├── cases/
│   │   ├── knowledge_base.md  # 售前知识库（200+真实案例）
│   │   └── library.py         # 案例库（结构化数据）
│   ├── agent/
│   │   ├── dialogue.py        # 对话逻辑
│   │   └── state.py           # 状态管理
│   └── main.py                # 企微长连接机器人（实验性）
├── presale-agent-demo.html    # 开发用源文件
└── README.md
```

## 部署

### Vercel 部署（推荐）

```bash
cd deploy
vercel --yes --prod
```

### 本地开发

```bash
cd presale_agent_server
python3 unified_server.py
# 访问 http://localhost:8765/presale-agent-demo.html
```

## 提问框架

| 步骤 | 内容 | 类型 |
|------|------|------|
| 第1步 基础信息 | 公司名、行业、规模、业务模式、痛点 | 5题固定 |
| 第2步 业务深挖 | 痛点拆解、业务流转、涉及角色 | 3题AI动态 |
| 第3步 细节确认 | 数据量/来源、仪表盘、权限 + 预算/时间 | 3题AI动态+2题固定 |
| 第4步 报告 | 完整需求洞察报告 | AI生成 |
| 第5步 Demo | 智能表格 Demo（真实创建） | AI+MCP |
