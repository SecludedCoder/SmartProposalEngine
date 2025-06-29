<div align="center">
  <img src="assets/images/logo.png" alt="SmartProposal Engine Logo" width="150"/>
  <h1>SmartProposal Engine</h1>
  <p><strong>一个由 AI 驱动的智能商业方案生成引擎，能将原始会议录音、访谈纪要等信息，一键转化为结构清晰、内容专业的商业提案。</strong></p>
  
  <p>
    <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
    <img src="https://img.shields.io/badge/Streamlit-1.35+-orange.svg" alt="Streamlit Version">
    <img src="https://img.shields.io/badge/AI_Engine-Google_Gemini-purple.svg" alt="AI Engine">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
    <img src="https://img.shields.io/badge/Project_Status-MVP-informational.svg" alt="Project Status">
  </p>
</div>

---

**SmartProposal Engine** 旨在解决商业咨询、销售和项目管理中的核心痛点：将大量零散、非结构化的信息（如客户访谈、商务谈判录音、内部会议纪要）高效地转化为高质量、专业化的商业文档。借助 Google Gemini 强大的多模态和长文本理解能力，本工具实现了从信息输入到方案输出的全流程自动化。

### 目录
- [✨ 功能亮点](#-功能亮点)
- [🚀 效果演示](#-效果演示)
- [🛠️ 技术栈](#️-技术栈)
- [🏗️ 系统架构](#️-系统架构)
- [⚙️ 安装与配置](#️-安装与配置)
- [▶️ 快速开始](#️-快速开始)
- [🔧 核心配置](#️-核心配置)
- [🗺️ 未来路线图](#️-未来路线图)
- [🤝 贡献指南](#️-贡献指南)
- [📜 许可证](#️-许可证)

### ✨ 功能亮点

* **🎙️ 智能音频/文档处理**:
    * 支持多种主流音频格式 (`m4a`, `mp3`, `wav` 等) 和文档格式 (`docx`, `pdf`, `txt` 等)。
    * 利用 Gemini API 对长音频进行高精度转录，并自动识别不同说话人。
    * 可选的 AI 文本优化功能，提升转录稿的可读性和专业性。

* **🧠 基于场景的深度分析**:
    * 内置多种专业分析模板，覆盖客户访-谈、商务谈判、内部会议等核心商业场景。
    * 通过精心设计的 Prompts，从海量文本中提取关键商业洞察、决策要点和行动项。
    * 支持用户提供自定义分析模板，满足个性化需求。

* **✍️ 定制化方案生成**:
    * 一键生成结构完整、逻辑清晰的商业文档，如项目建议书、商务报价方案、解决方案简报等。
    * 能够智能融合用户上传的“企业能力文档”（如公司介绍、成功案例），极大增强生成方案的针对性和说服力。
    * 支持客户信息注入，实现方案的个性化定制。

* **⚡ 端到端自动化工作流**:
    * 提供“一键生成”模式，支持批量文件处理，实现从原始输入到最终方案的无人干预全流程自动化。
    * 清晰的进度跟踪和结果汇总，便于管理和复盘。
    * 模块化的服务设计，保证了系统的稳定性和可扩展性。

### 🚀 效果演示

**(建议您在此处替换为应用的实际截图)**

**1. 一键处理页面 - 配置工作流**
*（此处可以放 `4_??_One_Click_Generation.py` 页面的截图）*
![One Click Generation Screenshot](https://via.placeholder.com/800x450.png?text=Screenshot+of+One-Click+Generation+Page)

**2. 深度分析结果展示**
*（此处可以放 `2_??_Deep_Analysis.py` 页面生成结果的截图）*
![Analysis Result Screenshot](https://via.placeholder.com/800x450.png?text=Screenshot+of+Deep+Analysis+Result)

**3. 最终生成的项目建议书**
*（此处可以放 `3_??_Proposal_Generation.py` 页面生成方案的截图）*
![Proposal Result Screenshot](https://via.placeholder.com/800x450.png?text=Screenshot+of+Generated+Proposal)


### 🛠️ 技术栈

* **前端框架**: [Streamlit](https://streamlit.io/)
* **AI 核心**: [Google Gemini API (2.5-Pro, 2.5-Flash)](https://ai.google.dev/)
* **开发语言**: Python 3.8+
* **文档处理**: `python-docx`, `PyPDF2`
* **音频处理**: `pydub` (用于分割), Google AI Platform (用于转录)
* **核心依赖**: `google-generativeai`, `streamlit`

### 🏗️ 系统架构

项目采用了清晰的、面向服务的架构，将不同职责进行了解耦。