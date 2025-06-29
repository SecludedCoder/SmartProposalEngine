#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/pages/2_🔍_Deep_Analysis.py
功能说明: 深度分析页面，对转录文本进行商业洞察分析
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-29
版本: 1.1.0
"""

import os
import sys
import streamlit as st
from pathlib import Path
from datetime import datetime
import time
import json

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analysis_service import DeepAnalysisService
from core.session_manager import SessionManager
from core.prompt_manager import PromptManager
from utils.file_utils import (
    save_uploaded_file,
    get_file_metadata,
    format_file_size,
    prepare_download_file
)
from utils.format_utils import (
    format_metadata_display,
    format_duration,
    truncate_text,
    markdown_to_text
)
from utils.validation_utils import validate_text_input
from utils.ui_utils import check_api_key_setup  # 引入检查函数

# 页面配置
st.set_page_config(
    page_title="深度分析 - SmartProposal Engine",
    page_icon="🔍",
    layout="wide"
)


def initialize_page_state():
    """初始化页面状态"""
    if 'deep_analysis' not in st.session_state:
        st.session_state.deep_analysis = {
            'analysis_result': None,
            'analysis_history': [],
            'current_template': 'customer_interview',
            'custom_prompt': '',
            'processing': False,
            'current_progress': 0  # 添加进度跟踪
        }

    # 确保SessionManager存在
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = SessionManager()

    # 创建或获取当前会话
    if not st.session_state.session_manager.current_session_id:
        st.session_state.session_manager.create_session('deep_analysis')


def load_previous_result():
    """加载上一步的结果"""
    session_manager = st.session_state.session_manager

    # 尝试获取转录结果
    transcription_result = session_manager.get_result('transcription')
    if transcription_result:
        return transcription_result

    # 尝试获取输入处理结果
    input_result = session_manager.get_result('input_processing')
    if input_result:
        return input_result

    return None


def show_data_source_section():
    """显示数据源选择部分"""
    st.markdown("### 📊 选择数据源")

    # 检查是否有上一步的结果
    previous_result = load_previous_result()

    col1, col2 = st.columns(2)

    with col1:
        use_previous = st.checkbox(
            "使用上一步处理结果",
            value=bool(previous_result),
            disabled=not bool(previous_result),
            help="使用内容输入页面的处理结果" if previous_result else "没有找到上一步的处理结果"
        )

    if use_previous and previous_result:
        with col2:
            st.success(f"✅ 已加载上一步结果")
            st.caption(f"内容长度: {len(previous_result.content):,} 字符")

        # 显示内容预览
        with st.expander("查看内容预览", expanded=False):
            st.text_area(
                "内容预览",
                value=truncate_text(previous_result.content, 1000),
                height=200,
                disabled=True
            )

        return previous_result.content, previous_result.metadata

    else:
        # 文件上传或文本输入
        tab1, tab2 = st.tabs(["📤 上传文件", "✍️ 文本输入"])

        with tab1:
            uploaded_file = st.file_uploader(
                "上传转录文本或文档",
                type=['txt', 'docx', 'pdf', 'json'],
                help="支持TXT、DOCX、PDF或之前导出的JSON文件"
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

                    return content, metadata
                else:
                    st.error(message)
                    return None, None

        with tab2:
            text_input = st.text_area(
                "粘贴或输入文本内容",
                height=300,
                placeholder="在此输入需要分析的文本内容...",
                help="建议文本长度在100-50000字符之间"
            )

            if text_input:
                # 显示字数统计
                char_count = len(text_input)
                word_count = len(text_input.split())
                st.caption(f"字符数: {char_count:,} | 词数: {word_count:,}")

                # 验证输入
                is_valid, message = validate_text_input(
                    text_input,
                    min_length=100,
                    max_length=100000
                )

                if is_valid:
                    metadata = {
                        'source': 'text_input',
                        'char_count': char_count,
                        'word_count': word_count,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    return text_input, metadata
                else:
                    st.warning(message)
                    return None, None

    return None, None


def show_analysis_configuration():
    """显示分析配置部分"""
    st.markdown("### ⚙️ 分析配置")

    # 初始化分析服务以获取可用模板
    analysis_service = DeepAnalysisService()

    col1, col2 = st.columns([2, 1])

    with col1:
        # 分析场景选择
        scenarios = analysis_service.ANALYSIS_SCENARIOS
        template_options = list(scenarios.keys())
        template_names = [scenarios[key]['name'] for key in template_options]

        selected_index = st.selectbox(
            "选择分析场景",
            range(len(template_options)),
            format_func=lambda x: template_names[x],
            index=template_options.index(st.session_state.deep_analysis['current_template']),
            help="选择适合您业务场景的分析模板"
        )

        selected_template = template_options[selected_index]
        st.session_state.deep_analysis['current_template'] = selected_template

        # 显示场景说明
        scenario_info = scenarios[selected_template]
        st.info(f"**场景说明**: {scenario_info['description']}")

        # 显示重点分析领域
        st.markdown("**重点分析领域:**")
        focus_areas_text = " | ".join(scenario_info['focus_areas'])
        st.caption(focus_areas_text)

    with col2:
        # 高级选项
        st.markdown("**高级选项**")

        include_recommendations = st.checkbox(
            "包含行动建议",
            value=True,
            help="在分析报告中包含具体的行动建议"
        )

        extract_action_items = st.checkbox(
            "提取行动项",
            value=True,
            help="自动提取并列出需要执行的行动项"
        )

        output_format = st.selectbox(
            "输出格式",
            options=['markdown', 'text'],
            format_func=lambda x: {'markdown': 'Markdown格式', 'text': '纯文本'}.get(x, x),
            help="选择分析报告的输出格式"
        )

    # 自定义Prompt部分
    with st.expander("🛠️ 自定义分析模板（高级）", expanded=False):
        st.markdown("""
        您可以提供自定义的分析模板来替代预设模板。模板中可使用以下变量：
        - `{transcript}`: 待分析的文本内容
        - `{additional_context}`: 额外的上下文信息
        """)

        custom_prompt = st.text_area(
            "自定义分析模板",
            value=st.session_state.deep_analysis.get('custom_prompt', ''),
            height=300,
            placeholder="输入您的自定义分析模板...",
            help="留空则使用选定的预设模板"
        )

        if custom_prompt:
            st.session_state.deep_analysis['custom_prompt'] = custom_prompt

        # 额外上下文
        additional_context = st.text_area(
            "额外上下文信息（可选）",
            height=100,
            placeholder="提供额外的背景信息或特殊要求...",
            help="这些信息将帮助AI更好地理解分析需求"
        )

    # 返回配置选项
    options = {
        'template': selected_template,
        'include_recommendations': include_recommendations,
        'extract_action_items': extract_action_items,
        'output_format': output_format,
        'custom_prompt': custom_prompt if custom_prompt else None,
        'additional_context': additional_context if additional_context else None
    }

    return options


def perform_analysis(content: str, metadata: dict, options: dict):
    """执行深度分析"""
    session_manager = st.session_state.session_manager

    # 创建进度容器
    progress_container = st.container()

    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 初始化进度跟踪
        st.session_state.deep_analysis['current_progress'] = 0

        try:
            # 初始化分析服务
            status_text.text("正在初始化分析服务...")
            progress_bar.progress(10)
            st.session_state.deep_analysis['current_progress'] = 10

            analysis_service = DeepAnalysisService()

            # 定义进度回调
            def progress_callback(msg):
                status_text.text(msg)
                current = st.session_state.deep_analysis['current_progress']
                if current < 90:
                    new_progress = min(current + 20, 90)
                    progress_bar.progress(new_progress)
                    st.session_state.deep_analysis['current_progress'] = new_progress

            options['progress_callback'] = progress_callback

            # 准备输入数据
            input_data = {
                'transcript': content,
                'metadata': metadata
            }

            # 执行分析
            status_text.text("正在进行深度分析...")
            progress_bar.progress(30)
            st.session_state.deep_analysis['current_progress'] = 30

            start_time = time.time()
            result = analysis_service.process(
                input_data,
                template=options['template'],
                options=options
            )

            progress_bar.progress(100)
            st.session_state.deep_analysis['current_progress'] = 100

            if result.is_success:
                status_text.text("✅ 分析完成！")

                # 保存结果到会话
                session_manager.save_result('analysis', result)
                st.session_state.deep_analysis['analysis_result'] = result

                # 添加到历史记录
                st.session_state.deep_analysis['analysis_history'].append({
                    'timestamp': datetime.now(),
                    'template': options['template'],
                    'processing_time': result.processing_time,
                    'result': result
                })

                # 如果需要提取行动项
                if options.get('extract_action_items'):
                    action_items = analysis_service.extract_action_items(result)
                    result.metadata['action_items'] = action_items

                # 生成执行摘要
                executive_summary = analysis_service.generate_executive_summary(result)
                result.metadata['executive_summary'] = executive_summary

                st.success(f"""
                深度分析成功完成！
                - 处理时间: {result.processing_time:.1f} 秒
                - 使用模型: {result.model_used}
                - Token使用: {result.total_tokens:,}
                """)

                # 自动刷新页面以显示结果
                time.sleep(1)
                st.rerun()

            else:
                status_text.text("❌ 分析失败")
                st.error(f"分析失败: {result.error}")

        except Exception as e:
            status_text.text("❌ 发生错误")
            st.error(f"分析过程中发生错误: {str(e)}")

        finally:
            # 清理进度显示
            time.sleep(2)
            progress_container.empty()
            # 重置进度
            st.session_state.deep_analysis['current_progress'] = 0


def show_analysis_result():
    """显示分析结果"""
    result = st.session_state.deep_analysis.get('analysis_result')

    if not result:
        return

    st.markdown("---")
    st.markdown("### 📊 分析结果")

    # 显示执行摘要
    if 'executive_summary' in result.metadata:
        st.markdown("#### 📄 执行摘要")
        st.info(result.metadata['executive_summary'])

    # 显示关键指标
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("分析用时", f"{result.processing_time:.1f} 秒")

    with col2:
        st.metric("Token使用", f"{result.total_tokens:,}")

    with col3:
        if 'estimated_cost' in result.metadata:
            st.metric("预估费用", f"${result.metadata['estimated_cost']:.4f}")

    with col4:
        st.metric("分析模板", result.metadata.get('analysis_scenario', '未知'))

    # 显示完整分析报告
    st.markdown("#### 📑 完整分析报告")

    # 报告显示选项
    col1, col2 = st.columns([3, 1])
    with col1:
        show_full_report = st.checkbox("显示完整报告", value=True)
    with col2:
        if st.button("📋 复制到剪贴板"):
            st.write(result.content)  # Streamlit会自动添加复制功能
            st.success("已复制到剪贴板！")

    # 显示报告内容
    if show_full_report:
        # 使用容器显示格式化的Markdown内容
        report_container = st.container()
        with report_container:
            st.markdown(result.content)
    else:
        # 显示摘要
        preview_length = 2000
        preview_text = truncate_text(result.content, preview_length)
        st.text_area(
            "报告预览",
            value=preview_text,
            height=400,
            disabled=True
        )

    # 显示行动项（如果有）
    if 'action_items' in result.metadata and result.metadata['action_items']:
        st.markdown("#### 🎯 提取的行动项")

        action_items = result.metadata['action_items']
        for i, item in enumerate(action_items, 1):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"{i}. {item['description']}")
            with col2:
                st.caption(f"优先级: {item.get('priority', '中')}")

    # 操作按钮
    st.markdown("#### ⏯️ 保存和下一步")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # 下载Markdown格式
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_md = f"analysis_report_{timestamp}.md"

        st.download_button(
            label="💾 下载报告(MD)",
            data=result.content,
            file_name=filename_md,
            mime="text/markdown",
            use_container_width=True
        )

    with col2:
        # 下载JSON格式（包含完整数据）
        export_data = {
            'content': result.content,
            'metadata': result.metadata,
            'processing_info': {
                'processing_time': result.processing_time,
                'model_used': result.model_used,
                'tokens_consumed': result.tokens_consumed,
                'timestamp': datetime.now().isoformat()
            }
        }

        filename_json = f"analysis_report_{timestamp}.json"
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)

        st.download_button(
            label="💾 下载报告(JSON)",
            data=json_str,
            file_name=filename_json,
            mime="application/json",
            use_container_width=True
        )

    with col3:
        # 发送到方案生成
        if st.button("➡️ 发送到方案生成", type="primary", use_container_width=True):
            session_manager = st.session_state.session_manager
            session_manager.save_result('analysis', result)
            st.success("已保存！请前往 **方案生成** 页面继续")
            time.sleep(2)
            st.rerun()

    with col4:
        # 重新分析
        if st.button("🔄 重新分析", use_container_width=True):
            st.session_state.deep_analysis['analysis_result'] = None
            st.rerun()


def show_analysis_history():
    """显示分析历史"""
    history = st.session_state.deep_analysis.get('analysis_history', [])

    if not history:
        return

    st.markdown("---")
    st.markdown("### 📜 分析历史")

    # 按时间倒序显示最近的分析
    for item in reversed(history[-5:]):  # 只显示最近5条
        template_name = DeepAnalysisService.ANALYSIS_SCENARIOS.get(
            item['template'], {}
        ).get('name', item['template'])

        with st.expander(
                f"{template_name} - {item['timestamp'].strftime('%H:%M:%S')}",
                expanded=False
        ):
            st.text(f"处理时间: {item['processing_time']:.1f} 秒")
            st.text(f"内容长度: {len(item['result'].content):,} 字符")

            if st.button(f"使用此结果", key=f"use_{item['timestamp']}"):
                st.session_state.deep_analysis['analysis_result'] = item['result']
                st.rerun()


def main():
    """主函数"""
    # 在页面顶部检查API Key设置
    check_api_key_setup()

    # 初始化页面状态
    initialize_page_state()

    # 页面标题
    st.title("🔍 深度分析")
    st.markdown("对转录文本进行商业洞察分析，提取关键信息和行动建议")

    # 显示分析结果（如果有）
    if st.session_state.deep_analysis.get('analysis_result'):
        show_analysis_result()
        show_analysis_history()
    else:
        # 获取数据源
        content, metadata = show_data_source_section()

        if content:
            st.markdown("---")

            # 显示分析配置
            options = show_analysis_configuration()

            st.markdown("---")

            # 执行分析按钮
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button(
                        "▶️ 开始分析",
                        type="primary",
                        use_container_width=True,
                        disabled=st.session_state.deep_analysis.get('processing', False)
                ):
                    st.session_state.deep_analysis['processing'] = True
                    perform_analysis(content, metadata, options)
                    st.session_state.deep_analysis['processing'] = False

        # 显示历史记录
        show_analysis_history()

    # 侧边栏信息
    with st.sidebar:
        st.markdown("### 💡 使用提示")
        st.info("""
**分析场景选择**：
- 客户访谈：适合需求挖掘
- 商务谈判：适合条款分析
- 内部会议：适合决策提取

**自定义模板**：
- 支持完全自定义分析逻辑
- 使用 {transcript} 引用文本

**下一步**：
- 分析完成后可生成方案
- 支持多次分析对比
""")

        # 模板帮助
        if st.button("📖 查看模板示例"):
            st.markdown("""
**自定义模板示例**：
```
请分析以下对话内容，重点关注：
1. 客户的核心需求
2. 预算范围
3. 决策时间线

对话内容：
{transcript}

请提供结构化的分析报告。
```
""")


if __name__ == "__main__":
    main()