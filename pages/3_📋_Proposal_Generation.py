#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/pages/3_🎯_Proposal_Generation.py
功能说明: 方案生成页面，基于分析结果生成各类商业文档
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

import os
import sys
import streamlit as st
from pathlib import Path
from datetime import datetime
import time
import json
from typing import List, Optional, Dict, Any

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.proposal_service import ProposalService
from services.document_service import DocumentService
from core.session_manager import SessionManager
from utils.file_utils import (
    save_uploaded_file,
    get_file_metadata,
    format_file_size,
    create_unique_filename,
    ensure_directory_exists
)
from utils.format_utils import (
    format_metadata_display,
    truncate_text,
    format_table_text,
    markdown_to_text
)
from utils.validation_utils import validate_text_input, validate_file_type

# 页面配置
st.set_page_config(
    page_title="方案生成 - SmartProposal Engine",
    page_icon="🎯",
    layout="wide"
)


def initialize_page_state():
    """初始化页面状态"""
    if 'proposal_generation' not in st.session_state:
        st.session_state.proposal_generation = {
            'proposal_result': None,
            'generation_history': [],
            'current_template': 'project_proposal',
            'capability_docs': [],
            'custom_prompt': '',
            'client_info': {},
            'processing': False,
            'current_progress': 0  # 添加进度跟踪
        }

    # 确保SessionManager存在
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = SessionManager()

    # 创建或获取当前会话
    if not st.session_state.session_manager.current_session_id:
        st.session_state.session_manager.create_session('proposal_generation')


def load_analysis_result():
    """加载分析结果"""
    session_manager = st.session_state.session_manager

    # 尝试获取分析结果
    analysis_result = session_manager.get_result('analysis')
    if analysis_result:
        return analysis_result

    return None


def show_analysis_source_section():
    """显示分析报告源选择部分"""
    st.markdown("### 📊 选择分析报告")

    # 检查是否有上一步的结果
    previous_result = load_analysis_result()

    col1, col2 = st.columns(2)

    with col1:
        use_previous = st.checkbox(
            "使用深度分析结果",
            value=bool(previous_result),
            disabled=not bool(previous_result),
            help="使用深度分析页面的分析结果" if previous_result else "没有找到分析结果"
        )

    if use_previous and previous_result:
        with col2:
            st.success("✅ 已加载分析结果")

            # 显示分析信息
            analysis_template = previous_result.metadata.get('analysis_scenario', '未知')
            st.caption(f"分析类型: {analysis_template}")

        # 显示内容预览
        with st.expander("查看分析报告预览", expanded=False):
            # 显示执行摘要（如果有）
            if 'executive_summary' in previous_result.metadata:
                st.markdown("**执行摘要:**")
                st.info(previous_result.metadata['executive_summary'])
                st.markdown("---")

            # 显示部分内容
            st.text_area(
                "报告内容预览",
                value=truncate_text(previous_result.content, 1500),
                height=300,
                disabled=True
            )

        return previous_result.content, previous_result.metadata

    else:
        # 文件上传
        st.markdown("#### 📤 上传分析报告")

        uploaded_file = st.file_uploader(
            "上传分析报告文件",
            type=['txt', 'md', 'json'],
            help="支持文本、Markdown或JSON格式的分析报告"
        )

        if uploaded_file:
            # 保存上传的文件
            save_dir = Path("temp") / datetime.now().strftime("%Y%m%d_%H%M%S")
            success, file_path, message = save_uploaded_file(uploaded_file, save_dir)

            if success:
                st.success(message)

                # 读取文件内容
                if uploaded_file.type == 'application/json':
                    # JSON文件特殊处理
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        content = data.get('content', '')
                        metadata = data.get('metadata', {})
                else:
                    # 其他文件作为纯文本处理
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    metadata = get_file_metadata(file_path)

                # 验证内容
                is_valid, msg = validate_text_input(content, min_length=200)
                if is_valid:
                    return content, metadata
                else:
                    st.error(f"分析报告内容不符合要求: {msg}")
                    return None, None
            else:
                st.error(message)
                return None, None

    return None, None


def show_capability_docs_section():
    """显示企业能力文档上传部分"""
    st.markdown("### 🏢 企业能力文档（可选）")

    st.info("""
    上传企业介绍、案例展示、资质证明等文档，系统将在生成方案时参考这些信息，
    增强方案的针对性和说服力。
    """)

    # 文件上传
    uploaded_files = st.file_uploader(
        "选择能力文档",
        type=['docx', 'pdf', 'txt', 'md'],
        accept_multiple_files=True,
        help="可以上传多个文档，支持DOCX、PDF、TXT、Markdown格式"
    )

    capability_doc_paths = []

    if uploaded_files:
        # 显示已上传的文件
        st.markdown("#### 已上传的文档:")

        for i, uploaded_file in enumerate(uploaded_files):
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.text(f"📄 {uploaded_file.name}")

            with col2:
                st.caption(format_file_size(uploaded_file.size))

            with col3:
                # 保存文件
                save_dir = Path("temp") / "capability_docs" / datetime.now().strftime("%Y%m%d_%H%M%S")
                success, file_path, _ = save_uploaded_file(uploaded_file, save_dir)

                if success:
                    capability_doc_paths.append(file_path)
                    st.success("✓")
                else:
                    st.error("✗")

        # 保存到session state
        st.session_state.proposal_generation['capability_docs'] = capability_doc_paths

        # 显示文档预览选项
        if st.checkbox("预览文档内容", value=False):
            document_service = DocumentService()

            for doc_path in capability_doc_paths[:3]:  # 最多预览3个
                with st.expander(f"预览: {Path(doc_path).name}", expanded=False):
                    result = document_service.process(doc_path)
                    if result.is_success:
                        st.text_area(
                            "内容预览",
                            value=truncate_text(result.content, 1000),
                            height=200,
                            disabled=True
                        )
                    else:
                        st.error("无法读取文档内容")

    return capability_doc_paths


def show_proposal_configuration():
    """显示方案生成配置部分"""
    st.markdown("### ⚙️ 方案配置")

    # 初始化方案服务以获取可用模板
    proposal_service = ProposalService()

    # 基本配置
    col1, col2 = st.columns([2, 1])

    with col1:
        # 方案类型选择
        proposal_types = proposal_service.PROPOSAL_TYPES
        template_options = list(proposal_types.keys())
        template_names = [proposal_types[key]['name'] for key in template_options]

        selected_index = st.selectbox(
            "选择方案类型",
            range(len(template_options)),
            format_func=lambda x: template_names[x],
            index=template_options.index(st.session_state.proposal_generation['current_template']),
            help="选择要生成的方案类型"
        )

        selected_template = template_options[selected_index]
        st.session_state.proposal_generation['current_template'] = selected_template

        # 显示方案说明
        proposal_info = proposal_types[selected_template]
        st.info(f"**方案说明**: {proposal_info['description']}")

        # 显示方案章节
        st.markdown("**包含章节:**")
        sections_text = " → ".join(proposal_info['sections'])
        st.caption(sections_text)

    with col2:
        # 方案选项
        st.markdown("**生成选项**")

        include_pricing = st.checkbox(
            "包含报价信息",
            value=selected_template == 'quotation_proposal',
            help="在方案中包含价格和报价信息"
        )

        include_timeline = st.checkbox(
            "包含时间计划",
            value=True,
            help="在方案中包含项目时间线"
        )

        language = st.selectbox(
            "语言",
            options=['zh', 'en'],
            format_func=lambda x: {'zh': '中文', 'en': 'English'}.get(x, x),
            help="方案的输出语言"
        )

    # 客户信息部分
    with st.expander("👤 客户信息（可选）", expanded=False):
        st.markdown("提供客户信息可以让方案更加个性化")

        col1, col2 = st.columns(2)

        with col1:
            client_name = st.text_input(
                "客户名称",
                placeholder="XX科技有限公司",
                help="将在方案中使用的客户公司名称"
            )

            project_name = st.text_input(
                "项目名称",
                placeholder="智能化升级项目",
                help="项目的正式名称"
            )

            industry = st.text_input(
                "所属行业",
                placeholder="互联网/制造业/金融等",
                help="客户所在的行业"
            )

        with col2:
            contact_person = st.text_input(
                "联系人",
                placeholder="张总",
                help="主要联系人姓名或职位"
            )

            budget_range = st.text_input(
                "预算范围",
                placeholder="50-100万",
                help="项目的预算范围（如果知道）"
            )

            timeline = st.text_input(
                "时间要求",
                placeholder="3个月内完成",
                help="项目的时间要求"
            )

        # 保存客户信息
        client_info = {
            'client_name': client_name,
            'project_name': project_name,
            'industry': industry,
            'contact_person': contact_person,
            'budget_range': budget_range,
            'timeline': timeline
        }

        # 过滤掉空值
        client_info = {k: v for k, v in client_info.items() if v}
        st.session_state.proposal_generation['client_info'] = client_info

    # 自定义模板部分
    with st.expander("🛠️ 自定义方案模板（高级）", expanded=False):
        st.markdown("""
        您可以提供自定义的方案生成模板。模板中可使用以下变量：
        - `{analysis_report}`: 分析报告内容
        - `{capability_docs}`: 企业能力文档内容
        - `{client_info}`: 客户信息
        """)

        custom_prompt = st.text_area(
            "自定义方案模板",
            value=st.session_state.proposal_generation.get('custom_prompt', ''),
            height=400,
            placeholder="输入您的自定义方案生成模板...",
            help="留空则使用选定的预设模板"
        )

        if custom_prompt:
            st.session_state.proposal_generation['custom_prompt'] = custom_prompt

        # 模板示例
        if st.button("查看模板示例"):
            st.code("""
# 项目建议书

## 一、项目背景
基于分析报告：{analysis_report}

## 二、解决方案
[详细方案设计]

## 三、我们的优势
{capability_docs}

## 四、项目计划
[实施计划和时间表]

## 五、投资与收益
[商务条款和ROI分析]
""", language='markdown')

    # 返回配置选项
    options = {
        'template': selected_template,
        'include_pricing': include_pricing,
        'include_timeline': include_timeline,
        'language': language,
        'client_info': client_info,
        'custom_prompt': custom_prompt if custom_prompt else None
    }

    return options


def perform_proposal_generation(analysis_report: str,
                                analysis_metadata: dict,
                                capability_docs: List[str],
                                options: dict):
    """执行方案生成"""
    session_manager = st.session_state.session_manager

    # 创建进度容器
    progress_container = st.container()

    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 初始化进度跟踪
        st.session_state.proposal_generation['current_progress'] = 0

        try:
            # 初始化方案服务
            status_text.text("正在初始化方案生成服务...")
            progress_bar.progress(10)
            st.session_state.proposal_generation['current_progress'] = 10

            proposal_service = ProposalService()

            # 定义进度回调
            def progress_callback(msg):
                status_text.text(msg)
                # 从 session state 获取当前进度
                current = st.session_state.proposal_generation['current_progress']
                if current < 90:
                    new_progress = min(current + 15, 90)
                    progress_bar.progress(new_progress)
                    st.session_state.proposal_generation['current_progress'] = new_progress

            options['progress_callback'] = progress_callback

            # 添加能力文档到选项
            if capability_docs:
                options['capability_docs'] = capability_docs

            # 准备输入数据
            input_data = {
                'analysis_report': analysis_report,
                'metadata': analysis_metadata
            }

            # 执行方案生成
            status_text.text("正在生成方案...")
            progress_bar.progress(30)
            st.session_state.proposal_generation['current_progress'] = 30

            start_time = time.time()
            result = proposal_service.process(
                input_data,
                template=options['template'],
                options=options
            )

            progress_bar.progress(100)
            st.session_state.proposal_generation['current_progress'] = 100

            if result.is_success:
                status_text.text("✅ 方案生成完成！")

                # 应用客户信息定制化
                if options.get('client_info'):
                    result.content = proposal_service.customize_proposal(
                        result.content,
                        options['client_info']
                    )

                # 保存结果到会话
                session_manager.save_result('proposal', result)
                st.session_state.proposal_generation['proposal_result'] = result

                # 添加到历史记录
                st.session_state.proposal_generation['generation_history'].append({
                    'timestamp': datetime.now(),
                    'template': options['template'],
                    'processing_time': result.processing_time,
                    'has_capability_docs': bool(capability_docs),
                    'result': result
                })

                # 获取方案大纲
                outline = proposal_service.get_proposal_outline(options['template'])
                result.metadata['outline'] = outline

                st.success(f"""
                方案生成成功！
                - 生成时间: {result.processing_time:.1f} 秒
                - 使用模型: {result.model_used}
                - Token使用: {result.total_tokens:,}
                - 预估费用: ${result.metadata.get('estimated_cost', 0):.4f}
                """)

                # 自动刷新页面以显示结果
                time.sleep(1)
                st.rerun()

            else:
                status_text.text("❌ 方案生成失败")
                st.error(f"生成失败: {result.error}")

        except Exception as e:
            status_text.text("❌ 发生错误")
            st.error(f"生成过程中发生错误: {str(e)}")

        finally:
            # 清理进度显示
            time.sleep(2)
            progress_container.empty()
            # 重置进度
            st.session_state.proposal_generation['current_progress'] = 0


def show_proposal_result():
    """显示方案生成结果"""
    result = st.session_state.proposal_generation.get('proposal_result')

    if not result:
        return

    st.markdown("---")
    st.markdown("### 📄 生成的方案")

    # 显示方案信息
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("方案类型", result.metadata.get('proposal_name', '未知'))

    with col2:
        st.metric("生成用时", f"{result.processing_time:.1f} 秒")

    with col3:
        st.metric("字数", f"{result.metadata.get('word_count', 0):,}")

    with col4:
        reading_time = result.metadata.get('estimated_reading_time_minutes', 0)
        st.metric("预计阅读", f"{reading_time} 分钟")

    # 方案大纲（如果有）
    if 'outline' in result.metadata and result.metadata['outline']:
        with st.expander("📑 方案大纲", expanded=True):
            outline = result.metadata['outline']
            for item in outline:
                level = item.get('level', 1)
                indent = "  " * (level - 1)
                st.write(f"{indent}{item['number']}. {item['title']}")
                if 'description' in item:
                    st.caption(f"{indent}   {item['description']}")

    # 方案内容显示
    st.markdown("#### 📝 方案内容")

    # 显示选项
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        display_mode = st.radio(
            "显示模式",
            options=['formatted', 'plain'],
            format_func=lambda x: {'formatted': '格式化显示', 'plain': '纯文本'}.get(x, x),
            horizontal=True
        )

    with col2:
        if st.button("📋 复制全文"):
            st.write(result.content)  # Streamlit会自动添加复制功能
            st.success("已复制到剪贴板！")

    with col3:
        # 打印预览
        if st.button("🖨️ 打印预览"):
            # 在新标签页中打开打印友好的版本
            st.markdown(f'<a href="data:text/html,{result.content}" target="_blank">在新窗口打开</a>',
                        unsafe_allow_html=True)

    # 显示方案内容
    if display_mode == 'formatted':
        # 使用容器显示格式化的Markdown内容
        content_container = st.container()
        with content_container:
            # 添加一些样式以改善显示效果
            st.markdown("""
            <style>
            .proposal-content {
                line-height: 1.6;
                font-size: 16px;
            }
            .proposal-content h1 { color: #1f77b4; margin-top: 2em; }
            .proposal-content h2 { color: #2c5aa0; margin-top: 1.5em; }
            .proposal-content h3 { color: #3d6db5; margin-top: 1.2em; }
            .proposal-content ul, .proposal-content ol { margin-left: 2em; }
            .proposal-content blockquote { 
                border-left: 4px solid #ddd; 
                padding-left: 1em; 
                color: #666; 
            }
            </style>
            """, unsafe_allow_html=True)

            st.markdown(f'<div class="proposal-content">{result.content}</div>',
                        unsafe_allow_html=True)
    else:
        # 纯文本显示
        st.text_area(
            "方案内容",
            value=result.content,
            height=600,
            disabled=True
        )

    # 操作按钮
    st.markdown("#### 💾 导出和保存")

    col1, col2, col3, col4 = st.columns(4)

    # 准备文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    proposal_type = result.metadata.get('proposal_type', 'proposal')
    client_name = st.session_state.proposal_generation.get('client_info', {}).get('client_name', '')

    if client_name:
        base_filename = f"{client_name}_{proposal_type}_{timestamp}"
    else:
        base_filename = f"{proposal_type}_{timestamp}"

    with col1:
        # 下载Markdown格式
        filename_md = f"{base_filename}.md"

        st.download_button(
            label="📥 下载(Markdown)",
            data=result.content,
            file_name=filename_md,
            mime="text/markdown",
            use_container_width=True
        )

    with col2:
        # 下载纯文本格式
        plain_text = markdown_to_text(result.content)
        filename_txt = f"{base_filename}.txt"

        st.download_button(
            label="📥 下载(TXT)",
            data=plain_text,
            file_name=filename_txt,
            mime="text/plain",
            use_container_width=True
        )

    with col3:
        # 下载完整数据（JSON）
        export_data = {
            'proposal': result.content,
            'metadata': result.metadata,
            'client_info': st.session_state.proposal_generation.get('client_info', {}),
            'generation_info': {
                'processing_time': result.processing_time,
                'model_used': result.model_used,
                'tokens_consumed': result.tokens_consumed,
                'timestamp': datetime.now().isoformat()
            }
        }

        filename_json = f"{base_filename}_complete.json"
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)

        st.download_button(
            label="📥 下载(完整数据)",
            data=json_str,
            file_name=filename_json,
            mime="application/json",
            use_container_width=True
        )

    with col4:
        # 重新生成
        if st.button("🔄 重新生成", use_container_width=True):
            st.session_state.proposal_generation['proposal_result'] = None
            st.rerun()


def show_generation_history():
    """显示生成历史"""
    history = st.session_state.proposal_generation.get('generation_history', [])

    if not history:
        return

    st.markdown("---")
    st.markdown("### 📚 生成历史")

    # 按时间倒序显示最近的生成记录
    for item in reversed(history[-5:]):  # 只显示最近5条
        template_name = ProposalService.PROPOSAL_TYPES.get(
            item['template'], {}
        ).get('name', item['template'])

        extra_info = []
        if item.get('has_capability_docs'):
            extra_info.append("含能力文档")

        title = f"{template_name} - {item['timestamp'].strftime('%H:%M:%S')}"
        if extra_info:
            title += f" ({', '.join(extra_info)})"

        with st.expander(title, expanded=False):
            st.text(f"生成时间: {item['processing_time']:.1f} 秒")
            st.text(f"方案长度: {len(item['result'].content):,} 字符")

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"使用此方案", key=f"use_{item['timestamp']}"):
                    st.session_state.proposal_generation['proposal_result'] = item['result']
                    st.rerun()

            with col2:
                if st.button(f"查看详情", key=f"view_{item['timestamp']}"):
                    with st.container():
                        st.markdown("**方案预览:**")
                        st.text_area(
                            "内容",
                            value=truncate_text(item['result'].content, 1000),
                            height=300,
                            disabled=True,
                            key=f"preview_{item['timestamp']}"
                        )


def main():
    """主函数"""
    # 初始化页面状态
    initialize_page_state()

    # 页面标题
    st.title("🎯 方案生成")
    st.markdown("基于分析结果生成专业的商业方案和项目建议书")

    # 显示生成结果（如果有）
    if st.session_state.proposal_generation.get('proposal_result'):
        show_proposal_result()
        show_generation_history()
    else:
        # 获取分析报告
        analysis_report, analysis_metadata = show_analysis_source_section()

        if analysis_report:
            st.markdown("---")

            # 企业能力文档
            capability_docs = show_capability_docs_section()

            st.markdown("---")

            # 方案配置
            options = show_proposal_configuration()

            st.markdown("---")

            # 生成方案按钮
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                button_text = "🚀 生成方案"
                if capability_docs:
                    button_text += f" ({len(capability_docs)}份参考)"

                if st.button(
                        button_text,
                        type="primary",
                        use_container_width=True,
                        disabled=st.session_state.proposal_generation.get('processing', False)
                ):
                    st.session_state.proposal_generation['processing'] = True
                    perform_proposal_generation(
                        analysis_report,
                        analysis_metadata,
                        capability_docs,
                        options
                    )
                    st.session_state.proposal_generation['processing'] = False

        # 显示历史记录
        show_generation_history()

    # 侧边栏信息
    with st.sidebar:
        st.markdown("### 💡 使用提示")
        st.info("""
**方案类型选择**：
- 项目建议书：完整的项目方案
- 商务报价：重点在价格和服务
- 解决方案简报：精简版方案

**企业能力文档**：
- 上传公司介绍、案例等
- 系统会自动引用相关内容
- 增强方案的说服力

**客户信息**：
- 填写客户信息个性化方案
- 自动替换客户名称等信息

**导出格式**：
- Markdown：保留格式
- TXT：纯文本，便于编辑
- JSON：包含完整数据
""")

        # 方案模板说明
        if st.button("📖 查看方案结构"):
            proposal_type = st.session_state.proposal_generation.get('current_template', 'project_proposal')
            proposal_info = ProposalService.PROPOSAL_TYPES.get(proposal_type, {})

            st.markdown(f"### {proposal_info.get('name', '方案')}结构")

            sections = proposal_info.get('sections', [])
            for i, section in enumerate(sections, 1):
                st.write(f"{i}. {section}")


if __name__ == "__main__":
    main()