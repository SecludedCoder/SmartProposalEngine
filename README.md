
**SmartProposal Engine** 旨在解决商业咨询、销售和项目管理中的核心痛点：将大量零散、非结构化的信息（如客户访谈录音、商务谈判纪要、内部会议记录）高效地转化为高质量、专业化的商业文档。借助大型语言模型（LLM）的强大能力，本工具实现了从信息输入到方案输出的全流程自动化。

## 目录

- [✨ 功能亮点](#-功能亮点)
- [🏗️ 系统架构](#️-系统架构)
- [🛠️ 技术栈](#️-技术栈)
- [⚙️ 安装与配置](#️-安装与配置)
- [▶️ 快速开始](#️-快速开始)
- [🚀 使用指南](#️-使用指南)
- [🧩 核心模块说明](#️-核心模块说明)
- [🔧 自定义与扩展](#️-自定义与扩展)
- [🗺️ 未来路线图](#️-未来路线图)
- [🤝 贡献指南](#️-贡献指南)
- [📜 许可证](#️-许可证)

## ✨ 功能亮点

*   **🎙️ 多模态输入处理**:
    *   **智能音频转录**: 支持多种主流音频格式 (`m4a`, `mp3`, `wav` 等)，利用 Gemini API 对长音频进行高精度转录，并能自动识别不同说话人。
    *   **文档内容提取**: 支持多种文档格式 (`docx`, `pdf`, `txt` 等)，自动提取核心文本内容。
    *   **AI 文本优化**: 可选的 AI 文本优化功能，提升转录稿的可读性和专业性。

*   **🧠 基于场景的深度分析**:
    *   内置多种专业分析模板，覆盖客户访谈、商务谈判、内部会议等核心商业场景。
    *   通过精心设计的 Prompt 链，从海量文本中提取关键商业洞察、决策要点和行动项。
    *   支持用户提供自定义分析模板，满足个性化需求。

*   **✍️ 定制化方案生成**:
    *   一键生成结构完整、逻辑清晰的商业文档，如项目建议书、商务报价方案、解决方案简报等。
    *   能够智能融合用户上传的“企业能力文档”（如公司介绍、成功案例），极大增强生成方案的针对性和说服力。
    *   支持客户信息注入，实现方案的个性化定制。

*   **⚡ 端到端自动化工作流**:
    *   提供“一键生成”模式，支持批量文件处理，实现从原始输入到最终方案的无人干预全流程自动化。
    *   清晰的进度跟踪和结果汇总，便于管理和复盘。
    *   模块化的服务设计，保证了系统的稳定性和可扩展性。

*   **🔌 多模型提供商支持**:
    *   采用可插拔的 Provider 架构，目前已支持 **Google Gemini** 和 **阿里云通义千问 (Qwen)**。
    *   用户可在应用启动时选择使用的模型提供商并配置 API Key。
    *   可在侧边栏为不同任务（转录、分析、生成）动态切换和选择最合适的模型。

## 🏗️ 系统架构

项目采用分层、面向服务的架构，确保了高度的模块化和可扩展性。

```
+-------------------------------------------------------------+
|                         UI Layer (Streamlit)                |
|  [ app.py | 1_...py | 2_...py | 3_...py | 4_...py ]          |
+-------------------------------------------------------------+
                              |
+-------------------------------------------------------------+
|                        Service Layer                        |
| [ Transcription | Analysis | Proposal | Document Service ]  |
+-------------------------------------------------------------+
                              |
+-------------------------------------------------------------+
|                          Core Layer                         |
| [ ModelInterface | PromptManager | SessionManager | ... ]   |
+-------------------------------------------------------------+
                              |
+-------------------------------------------------------------+
|                    LLM Provider Layer (Abstracted)          |
| [ BaseProvider | GeminiProvider | QwenProvider | ... ]      |
+-------------------------------------------------------------+
       |                         |                          |
    Google API                Qwen API                   ...
```

*   **UI Layer**: 使用 Streamlit 构建，负责用户交互和页面展示。
*   **Service Layer**: 封装核心业务逻辑，如转录、分析、方案生成等。每个服务都是一个独立的模块。
*   **Core Layer**: 提供核心支持组件，如统一模型接口 (`ModelInterface`)、提示词管理 (`PromptManager`) 和会话状态管理 (`SessionManager`)。
*   **LLM Provider Layer**: 抽象层，用于适配不同的 LLM 提供商。`ModelInterface` 通过调度此层的具体实现来调用不同的 AI 模型，使得添加新的模型提供商变得非常简单。

## 🛠️ 技术栈

*   **前端框架**: [Streamlit](https://streamlit.io/)
*   **AI 核心**: [Google Gemini API](https://ai.google.dev/), [阿里云通义千问 API](https://help.aliyun.com/document_detail/2582124.html)
*   **开发语言**: Python 3.8+
*   **文档处理**: `python-docx`, `PyPDF2`
*   **音频处理**: `pydub` (用于分割), Google Gemini API (用于转录)
*   **核心依赖**: `google-generativeai`, `dashscope`, `streamlit`

## ⚙️ 安装与配置

#### 1. 前置要求
*   Python 3.8 或更高版本
*   Git
*   [FFmpeg](https://ffmpeg.org/download.html) (用于音频处理，请确保已安装并添加到系统 PATH)

#### 2. 克隆项目仓库
```bash
git clone https://github.com/your-repo/SmartProposalEngine.git
cd SmartProposalEngine
```

#### 3. 创建并激活虚拟环境 (推荐)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

#### 4. 安装依赖
```bash
pip install -r requirements.txt
```

#### 5. 配置 API 密钥
应用启动后，会引导您在界面上输入所选模型提供商的 API Key。这是推荐的快速启动方式。

或者，您也可以通过配置文件 `app_config.ini` 使用存储在本地文件中的密钥（不推荐用于生产环境）：
1.  在 `app_config.ini` 中，设置：
    ```ini
    [API_SETTINGS]
    use_internal_api_key = true
    api_key_file = api_key.txt
    ```
2.  在项目根目录创建一个 `api_key.txt` 文件，并将您的 API Key 粘贴进去。

## ▶️ 快速开始

在项目根目录下，执行以下命令来启动应用：

```bash
python run_app.py
```

或者直接使用 Streamlit CLI:

```bash
streamlit run app.py
```

应用将在您的默认浏览器中打开，地址通常为 `http://localhost:8501`。

## 🚀 使用指南

应用启动后，您将看到一个初始化设置页面：

1.  **选择模型提供商**: 从下拉列表中选择您想使用的 AI 服务，如 `Gemini` 或 `Qwen`。
2.  **输入 API Key**: 在文本框中输入您选择的提供商对应的有效 API Key。
3.  **保存并开始**: 点击按钮，系统会验证 Key 并初始化模型。

初始化成功后，您将进入应用主界面。您可以从左侧的导航栏选择不同的功能模块：

*   **📄 内容输入处理**: 上传音频或文档文件，将其转化为纯文本。这是所有工作流的起点。
*   **🔍 深度分析**: 将上一步得到的文本进行深度分析，提取商业洞察。
*   **📋 方案生成**: 基于分析报告，结合企业能力文档，生成最终的商业方案。
*   **🚀 一键生成**: **(推荐)** 这是一个端到端的自动化流程。您只需上传原始文件和配置参数，系统会自动完成转录、分析和方案生成的所有步骤，并提供批量下载。

在应用的侧边栏，您可以随时调整用于不同任务（转录、分析、方案）的 AI 模型。

## 🧩 核心模块说明

*   `app.py`: 应用主入口，负责 UI 布局、页面导航和会话初始化。
*   `run_app.py`: 推荐的启动脚本，支持环境检查和端口管理。
*   `pages/`: 包含所有 Streamlit 子页面，每个文件对应一个功能模块。
*   `core/`: 存放项目核心抽象组件。
    *   `model_interface.py`: 核心的模型调度器，是与所有 LLM API 交互的统一入口。
    *   `prompt_manager.py`: 负责从 `prompts/` 目录加载和管理所有提示词模板。
    *   `session_manager.py`: 管理应用会话状态和跨页面数据传递。
*   `llm_providers/`: 存放不同 LLM 提供商的接口实现。
*   `services/`: 封装了各项具体的业务逻辑，如 `TranscriptionService`, `AnalysisService`。
*   `utils/`: 存放通用的工具函数，如文件处理、格式化等。
*   `prompts/`: **项目的“智慧大脑”**。这里存放了所有与 LLM 交互的提示词模板（Markdown 格式），您可以直接修改这些文件来调整 AI 的行为。
*   `app_config.ini`: 应用主配置文件，可配置模型提供商、默认模型、功能开关等。
*   `models.conf`: 模型定义文件，包含所有可用模型的 API 名称、显示名称和价格信息，用于成本估算。

## 🔧 自定义与扩展

本系统具有良好的可扩展性：

*   **添加新的分析/方案模板**:
    1.  在 `prompts/analysis` 或 `prompts/proposal` 目录下，创建一个新的 `.md` 文件。
    2.  参照现有模板的格式编写您的提示词，使用 `{variable}` 格式定义变量。
    3.  系统会自动加载新模板，并在 UI 的下拉菜单中显示。

*   **添加新的 LLM 提供商**:
    1.  在 `llm_providers/` 目录下创建一个新的 `your_provider.py` 文件。
    2.  创建一个继承自 `BaseProvider` 的新类。
    3.  实现 `BaseProvider` 中定义的所有抽象方法（如 `generate`, `count_tokens` 等）。
    4.  在 `core/model_interface.py` 的 `initialize_model` 方法中添加对新 Provider 的初始化逻辑。
    5.  在 `app_config.ini` 中将新的 Provider 名称添加到 `available_providers` 列表中。

## 🗺️ 未来路线图

-   [ ] **增强的 UI/UX**: 引入更丰富的交互元素和可视化图表。
-   [ ] **结果缓存**: 实现对已处理文件的结果缓存，减少重复计算和API调用。
-   [ ] **云存储集成**: 支持从 AWS S3, Google Cloud Storage 等直接读取和写入文件。
-   [ ] **团队协作功能**: 支持多用户项目和权限管理。
-   [ ] **更多模型支持**: 集成更多优秀的 LLM 提供商，如 Anthropic Claude、Mistral 等。
-   [ ] **Docker 化部署**: 提供 Dockerfile，简化部署流程。

## 🤝 贡献指南

我们欢迎任何形式的贡献，包括功能建议、Bug 报告和代码提交！

1.  Fork 本项目仓库。
2.  创建您的功能分支 (`git checkout -b feature/AmazingFeature`)。
3.  提交您的更改 (`git commit -m 'Add some AmazingFeature'`)。
4.  将您的分支推送到远程仓库 (`git push origin feature/AmazingFeature`)。
5.  创建一个 Pull Request。

## 📜 许可证

本项目采用 MIT 许可证。详情请参阅 `LICENSE` 文件。
