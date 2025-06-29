# SmartProposal Engine 📋

SmartProposal Engine是一个基于AI的智能商业方案生成系统，能够自动将原始信息（音频录音、文档等）转化为专业的商业提案和项目建议书。

## 🌟 核心功能

### 1. **智能转录** 🎙️
- 支持多种音频格式（m4a, mp3, wav等）
- 自动识别多说话人对话
- 支持超长音频自动分割处理
- 可选的AI文本优化功能

### 2. **深度分析** 🔍
- 多种预设分析模板（客户访谈、商务谈判、内部会议等）
- 智能提取关键信息和商业洞察
- 自动生成执行摘要和行动建议
- 支持自定义分析模板

### 3. **方案生成** 📋
- 自动生成专业的项目建议书
- 支持多种方案类型（项目建议书、商务报价、解决方案简报等）
- 整合企业能力文档，增强方案说服力
- 客户信息个性化定制

### 4. **一键处理** 🚀
- 端到端的自动化处理流程
- 批量文件处理能力
- 实时进度跟踪
- 结果批量导出

## 🛠️ 技术架构

### 核心技术栈
- **前端框架**: Streamlit
- **AI引擎**: Google Gemini API (支持2.5-pro和2.5-flash)
- **文档处理**: python-docx, PyPDF2
- **音频处理**: pydub, Google Speech-to-Text
- **开发语言**: Python 3.8+

### 项目结构
```
smart_proposal_engine/
├── app.py                    # 主应用入口
├── pages/                    # Streamlit页面
│   ├── 1_📄_Input_Processing.py
│   ├── 2_🔍_Deep_Analysis.py
│   ├── 3_📋_Proposal_Generation.py
│   └── 4_🚀_One_Click_Generation.py
├── services/                 # 业务服务层
│   ├── transcription_service.py
│   ├── analysis_service.py
│   └── proposal_service.py
├── core/                     # 核心组件
│   ├── prompt_manager.py
│   ├── model_interface.py
│   └── session_manager.py
├── prompts/                  # AI提示词模板
├── utils/                    # 工具函数
└── requirements.txt          # 项目依赖
```

## 📦 安装指南

### 前置要求
- Python 3.8 或更高版本
- Google Gemini API密钥
- FFmpeg（用于音频处理）

### 安装步骤

1. **克隆项目仓库**
```bash
git clone https://github.com/smartproposal/engine.git
cd smart_proposal_engine
```

2. **创建虚拟环境**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **安装FFmpeg**
- Windows: 从 [FFmpeg官网](https://ffmpeg.org/download.html) 下载并添加到PATH
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt-get install ffmpeg`

5. **配置API密钥**

创建 `.env` 文件：
```bash
cp .env.example .env
```

编辑 `.env` 文件，添加您的Google API密钥：
```
GOOGLE_API_KEY=your_api_key_here
```

或者，您可以在 `app_config.ini` 中配置使用内部密钥文件：
```ini
[API_SETTINGS]
use_internal_api_key = true
api_key_file = api_key.txt
```

## 🚀 使用指南

### 启动应用
```bash
streamlit run app.py
```

应用将在默认浏览器中打开，通常地址为 `http://localhost:8501`

### 功能使用流程

#### 1. 内容输入处理
- 上传音频文件或文档
- 选择处理选项（说话人识别、文本优化等）
- 获取转录或提取的文本内容

#### 2. 深度分析
- 选择或上传分析内容
- 选择合适的分析模板
- 获取结构化的分析报告

#### 3. 方案生成
- 上传分析报告
- 上传企业能力文档（可选）
- 配置方案参数和客户信息
- 生成专业的商业方案

#### 4. 一键生成（推荐）
- 批量上传所有文件
- 一次性配置所有参数
- 自动完成全流程处理
- 批量下载所有结果

### 配置说明

主要配置文件 `app_config.ini`：

```ini
[MODEL_SETTINGS]
# 不同任务使用的模型
transcription_model = models/gemini-2.5-flash
analysis_model = models/gemini-2.5-pro
proposal_model = models/gemini-2.5-pro

[FILE_SETTINGS]
# 文件大小和格式限制
max_file_size_mb = 200
allowed_audio_formats = m4a,mp3,wav,aac,ogg,flac
allowed_document_formats = docx,pdf,txt

[FEATURE_SETTINGS]
# 功能开关
enable_deep_analysis = true
enable_proposal_generation = true
enable_custom_prompts = true
```

## 📊 使用场景

### 1. 客户需求分析
- 上传客户访谈录音
- 自动提取需求点和痛点
- 生成针对性的项目建议书

### 2. 商务谈判支持
- 处理谈判录音或记录
- 分析各方立场和条款
- 生成谈判策略和报价方案

### 3. 内部会议整理
- 转录会议录音
- 提取决策要点和行动项
- 生成会议纪要和执行计划

### 4. 批量方案制作
- 批量处理多个客户资料
- 统一生成定制化方案
- 大幅提升工作效率

## 🔧 高级功能

### 自定义提示词模板
1. 在 `prompts/` 目录下创建新的模板文件
2. 使用Markdown格式编写模板
3. 在模板中使用变量占位符（如 `{transcript}`）

### 批处理API
```python
from services.document_service import DocumentService
from services.analysis_service import DeepAnalysisService

# 批量处理文档
doc_service = DocumentService()
results = doc_service.batch_process_documents(file_paths)

# 批量分析
analysis_service = DeepAnalysisService()
analyses = analysis_service.batch_analyze(documents, template='customer_interview')
```

### 扩展开发
系统采用模块化设计，便于扩展：
- 新增服务：继承 `BaseService` 类
- 新增模板：在相应目录添加模板文件
- 新增页面：在 `pages/` 目录创建新页面

## 📈 性能优化建议

1. **API调用优化**
   - 使用批量处理减少API调用次数
   - 合理设置并发数避免限流
   - 启用结果缓存减少重复处理

2. **文件处理优化**
   - 大文件自动分片处理
   - 使用流式处理减少内存占用
   - 定期清理临时文件

3. **模型选择优化**
   - 转录任务使用Flash模型节省成本
   - 复杂分析使用Pro模型保证质量
   - 根据任务特点选择合适的模型

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- Google Gemini团队提供的强大AI能力
- Streamlit社区的优秀框架
- 所有贡献者和用户的支持

## 📞 联系方式

- 项目主页: [https://github.com/smartproposal/engine](https://github.com/smartproposal/engine)
- 问题反馈: [Issues](https://github.com/smartproposal/engine/issues)
- 邮箱: support@smartproposal.ai

---

**SmartProposal Engine** - 让商业方案制作更智能、更高效！ 🚀
