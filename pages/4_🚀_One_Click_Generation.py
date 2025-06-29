#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/pages/4_🚀_One_Click_Generation.py
功能说明: 一键生成页面，实现从输入到方案的端到端处理
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
import zipfile
from typing import List, Dict, Optional, Any, Tuple
import shutil

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_processor import DocumentProcessor
from core.session_manager import SessionManager
from services.analysis_service import DeepAnalysisService
from services.proposal_service import ProposalService
from services.document_service import DocumentService
from utils.file_utils import (
    save_uploaded_file,
    get_file_metadata,
    format_file_size,
    create_unique_filename,
    ensure_directory_exists,
    validate_file_size,
    validate_file_format,
    create_temp_directory,
    cleanup_directory
)
from utils.format_utils import (
    format_duration,
    format_timestamp,
    format_percentage,
    format_table_text
)
from utils.validation_utils import validate_batch_files
from utils.ui_utils import check_api_key_setup # 引入检查函数

# 页面配置
st.set_page_config(
    page_title="一键生成 - SmartProposal Engine",
    page_icon="🚀",
    layout="wide"
)


def initialize_page_state():
    """初始化页面状态"""
    if 'one_click_generation' not in st.session_state:
        st.session_state.one_click_generation = {
            'input_files': [],
            'capability_docs': [],
            'processing_status': 'idle',  # idle, processing, completed, error
            'current_step': None,
            'processing_results': {},
            'workflow_config': {
                'analysis_template': 'customer_interview',
                'proposal_template': 'project_proposal',
                'enable_text_optimization': False,
                'include_capability_docs': True
            },
            'batch_id': None,
            'start_time': None,
            'end_time': None,
            'current_progress': 0,  # 添加全局进度跟踪
            'file_progress': {}  # 添加每个文件的进度跟踪
        }

    # 确保SessionManager存在
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = SessionManager()

    # 创建批次会话
    if not st.session_state.one_click_generation.get('batch_id'):
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        st.session_state.one_click_generation['batch_id'] = batch_id
        st.session_state.session_manager.create_session(f'batch_{batch_id}')


def show_upload_section():
    """显示文件上传部分"""
    st.markdown("### 📁 上传文件")

    # 创建两个标签页
    tab1, tab2 = st.tabs(["📥 待处理文件", "🏢 企业能力文档"])

    with tab1:
        st.info("""
        上传需要处理的原始文件，支持：
        - **音频文件**：客户访谈录音、会议录音等（m4a, mp3, wav等）
        - **文档文件**：需求文档、会议记录等（docx, pdf, txt等）
        """)

        uploaded_input_files = st.file_uploader(
            "选择要处理的文件",
            type=['m4a', 'mp3', 'wav', 'aac', 'ogg', 'flac', 'mp4',
                  'docx', 'pdf', 'txt', 'doc', 'rtf'],
            accept_multiple_files=True,
            key="input_files_uploader",
            help="可以同时上传多个文件进行批量处理"
        )

        if uploaded_input_files:
            # 验证文件
            file_paths = []
            total_size = 0

            st.markdown("#### 已上传的待处理文件:")

            # 创建表格显示文件信息
            file_info_data = []

            for file in uploaded_input_files:
                # 验证单个文件大小
                is_valid_size, size_msg = validate_file_size(file.size / (1024 * 1024), 200)

                if is_valid_size:
                    file_info_data.append({
                        "文件名": file.name,
                        "类型": file.type,
                        "大小": format_file_size(file.size),
                        "状态": "✅ 有效"
                    })
                    total_size += file.size
                else:
                    file_info_data.append({
                        "文件名": file.name,
                        "类型": file.type,
                        "大小": format_file_size(file.size),
                        "状态": f"❌ {size_msg}"
                    })

            # 显示文件列表
            for info in file_info_data:
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                with col1:
                    st.text(info["文件名"])
                with col2:
                    st.caption(info["类型"])
                with col3:
                    st.caption(info["大小"])
                with col4:
                    st.caption(info["状态"])

            # 显示汇总信息
            st.caption(f"总计: {len(uploaded_input_files)} 个文件, {format_file_size(total_size)}")

            # 保存有效文件
            valid_files = [f for f, info in zip(uploaded_input_files, file_info_data)
                           if "✅" in info["状态"]]
            st.session_state.one_click_generation['input_files'] = valid_files

    with tab2:
        st.info("""
        上传企业介绍、成功案例、资质证明等文档，系统将在生成方案时智能引用，
        增强方案的专业性和说服力。（可选）
        """)

        uploaded_capability_docs = st.file_uploader(
            "选择企业能力文档",
            type=['docx', 'pdf', 'txt', 'md'],
            accept_multiple_files=True,
            key="capability_docs_uploader",
            help="这些文档将作为生成方案的参考资料"
        )

        if uploaded_capability_docs:
            st.markdown("#### 已上传的能力文档:")

            doc_info_data = []
            for doc in uploaded_capability_docs:
                doc_info_data.append({
                    "文件名": doc.name,
                    "大小": format_file_size(doc.size)
                })

            # 显示文档列表
            for info in doc_info_data:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.text(f"📄 {info['文件名']}")
                with col2:
                    st.caption(info['大小'])

            st.session_state.one_click_generation['capability_docs'] = uploaded_capability_docs

    # 返回文件统计
    input_files = st.session_state.one_click_generation.get('input_files', [])
    capability_docs = st.session_state.one_click_generation.get('capability_docs', [])

    return input_files, capability_docs


def show_workflow_configuration():
    """显示工作流配置部分"""
    st.markdown("### ⚙️ 处理配置")

    config = st.session_state.one_click_generation['workflow_config']

    col1, col2 = st.columns(2)

    with col1:
        # 分析配置
        st.markdown("#### 🔍 分析设置")

        # 分析模板选择
        analysis_service = DeepAnalysisService()
        scenarios = analysis_service.ANALYSIS_SCENARIOS
        template_options = list(scenarios.keys())
        template_names = [scenarios[key]['name'] for key in template_options]

        selected_analysis_index = st.selectbox(
            "分析场景",
            range(len(template_options)),
            format_func=lambda x: template_names[x],
            index=template_options.index(config['analysis_template']),
            key="analysis_template_select",
            help="选择适合的分析场景"
        )

        config['analysis_template'] = template_options[selected_analysis_index]

        # 文本优化选项（仅对音频文件有效）
        config['enable_text_optimization'] = st.checkbox(
            "启用转录文本优化",
            value=config['enable_text_optimization'],
            help="使用AI优化音频转录的文本质量（会增加处理时间）"
        )

        # 说话人识别选项
        config['enable_speaker_diarization'] = st.checkbox(
            "启用说话人识别",
            value=True,
            help="识别并区分不同的说话人（适用于多人对话）"
        )

    with col2:
        # 方案生成配置
        st.markdown("#### 📝 方案设置")

        # 方案模板选择
        proposal_service = ProposalService()
        proposal_types = proposal_service.PROPOSAL_TYPES
        proposal_options = list(proposal_types.keys())
        proposal_names = [proposal_types[key]['name'] for key in proposal_options]

        selected_proposal_index = st.selectbox(
            "方案类型",
            range(len(proposal_options)),
            format_func=lambda x: proposal_names[x],
            index=proposal_options.index(config['proposal_template']),
            key="proposal_template_select",
            help="选择要生成的方案类型"
        )

        config['proposal_template'] = proposal_options[selected_proposal_index]

        # 是否使用能力文档
        has_capability_docs = len(st.session_state.one_click_generation.get('capability_docs', [])) > 0
        config['include_capability_docs'] = st.checkbox(
            f"引用企业能力文档 ({len(st.session_state.one_click_generation.get('capability_docs', []))}份)",
            value=config['include_capability_docs'] and has_capability_docs,
            disabled=not has_capability_docs,
            help="在方案中引用上传的企业能力文档"
        )

        # 输出语言
        config['output_language'] = st.selectbox(
            "输出语言",
            options=['zh', 'en'],
            format_func=lambda x: {'zh': '中文', 'en': 'English'}.get(x, x),
            help="方案的输出语言"
        )

    # 高级设置
    with st.expander("🔧 高级设置", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            config['max_workers'] = st.number_input(
                "并发处理数",
                min_value=1,
                max_value=5,
                value=1,
                help="同时处理的文件数量（建议保持为1以避免API限制）"
            )

        with col2:
            config['save_intermediate_results'] = st.checkbox(
                "保存中间结果",
                value=True,
                help="保存每个处理步骤的结果"
            )

        with col3:
            config['auto_cleanup'] = st.checkbox(
                "自动清理临时文件",
                value=True,
                help="处理完成后自动清理临时文件"
            )

    # 客户信息（可选）
    st.markdown("#### 👤 客户信息（可选）")
    col1, col2, col3 = st.columns(3)

    with col1:
        config['client_name'] = st.text_input(
            "客户名称",
            placeholder="XX科技有限公司",
            help="将在方案中使用的客户名称"
        )

    with col2:
        config['project_name'] = st.text_input(
            "项目名称",
            placeholder="智能化升级项目",
            help="项目的正式名称"
        )

    with col3:
        config['contact_person'] = st.text_input(
            "联系人",
            placeholder="张总",
            help="主要联系人"
        )

    # 更新配置
    st.session_state.one_click_generation['workflow_config'] = config

    return config


def process_single_file(file, file_index: int, total_files: int,
                        config: dict, progress_callback) -> Dict[str, Any]:
    """处理单个文件的完整流程"""
    results = {
        'file_name': file.name,
        'file_index': file_index,
        'steps': {},
        'success': False,
        'error': None
    }

    temp_dir = None

    # 初始化该文件的进度跟踪
    file_key = f"file_{file_index}"
    st.session_state.one_click_generation['file_progress'][file_key] = 0

    try:
        # 步骤1: 保存文件
        progress_callback(f"[{file_index + 1}/{total_files}] 正在保存文件: {file.name}")

        batch_id = st.session_state.one_click_generation['batch_id']
        temp_dir = Path("temp") / batch_id / f"file_{file_index}"
        ensure_directory_exists(temp_dir)

        success, file_path, message = save_uploaded_file(file, temp_dir)
        if not success:
            raise Exception(f"文件保存失败: {message}")

        # 步骤2: 文档处理（转录或提取文本）
        progress_callback(f"[{file_index + 1}/{total_files}] 正在处理文件内容...")

        processor = DocumentProcessor()

        # 创建文件特定的进度回调
        def file_progress_callback(msg):
            progress_callback(f"[{file_index + 1}/{total_files}] {msg}")
            # 更新文件进度
            current = st.session_state.one_click_generation['file_progress'][file_key]
            if current < 90:
                new_progress = min(current + 10, 90)
                st.session_state.one_click_generation['file_progress'][file_key] = new_progress

        process_options = {
            'enable_speaker_diarization': config.get('enable_speaker_diarization', True),
            'enable_text_optimization': config.get('enable_text_optimization', False),
            'max_segment_duration_minutes': 20,
            'extract_metadata': True,
            'progress_callback': file_progress_callback
        }

        process_result = processor.process_file(file_path, process_options)

        if not process_result.is_success:
            raise Exception(f"文件处理失败: {process_result.error}")

        results['steps']['processing'] = {
            'success': True,
            'content_length': len(process_result.content),
            'processing_time': process_result.processing_time,
            'file_type': process_result.source_type
        }

        # 步骤3: 深度分析
        progress_callback(f"[{file_index + 1}/{total_files}] 正在进行深度分析...")

        analysis_service = DeepAnalysisService()
        analysis_options = {
            'template': config['analysis_template'],
            'include_recommendations': True,
            'output_format': 'markdown',
            'progress_callback': file_progress_callback
        }

        analysis_result = analysis_service.process(
            process_result.content,
            template=config['analysis_template'],
            options=analysis_options
        )

        if not analysis_result.is_success:
            raise Exception(f"分析失败: {analysis_result.error}")

        results['steps']['analysis'] = {
            'success': True,
            'template_used': config['analysis_template'],
            'processing_time': analysis_result.processing_time,
            'tokens_used': analysis_result.total_tokens
        }

        # 步骤4: 方案生成
        progress_callback(f"[{file_index + 1}/{total_files}] 正在生成方案...")

        proposal_service = ProposalService()
        proposal_options = {
            'template': config['proposal_template'],
            'language': config.get('output_language', 'zh'),
            'progress_callback': file_progress_callback
        }

        # 添加客户信息
        client_info = {}
        if config.get('client_name'):
            client_info['client_name'] = config['client_name']
        if config.get('project_name'):
            client_info['project_name'] = config['project_name']
        if config.get('contact_person'):
            client_info['contact_person'] = config['contact_person']

        if client_info:
            proposal_options['client_info'] = client_info

        # 添加能力文档
        if config.get('include_capability_docs') and st.session_state.one_click_generation.get('capability_docs'):
            # 处理能力文档
            capability_paths = []
            for doc in st.session_state.one_click_generation['capability_docs']:
                doc_path = temp_dir / f"capability_{doc.name}"
                with open(doc_path, 'wb') as f:
                    f.write(doc.getbuffer())
                capability_paths.append(str(doc_path))

            proposal_options['capability_docs'] = capability_paths

        proposal_result = proposal_service.process(
            analysis_result.content,
            template=config['proposal_template'],
            options=proposal_options
        )

        if not proposal_result.is_success:
            raise Exception(f"方案生成失败: {proposal_result.error}")

        results['steps']['proposal'] = {
            'success': True,
            'template_used': config['proposal_template'],
            'processing_time': proposal_result.processing_time,
            'tokens_used': proposal_result.total_tokens,
            'word_count': proposal_result.metadata.get('word_count', 0)
        }

        # 保存所有结果
        results['success'] = True
        results['final_results'] = {
            'original_content': process_result.content,
            'analysis_report': analysis_result.content,
            'proposal': proposal_result.content,
            'metadata': {
                'file_metadata': process_result.metadata,
                'analysis_metadata': analysis_result.metadata,
                'proposal_metadata': proposal_result.metadata
            }
        }

        # 计算总处理时间和成本
        total_time = (process_result.processing_time +
                      analysis_result.processing_time +
                      proposal_result.processing_time)

        total_tokens = (process_result.total_tokens +
                        analysis_result.total_tokens +
                        proposal_result.total_tokens)

        total_cost = (process_result.metadata.get('estimated_cost', 0) +
                      analysis_result.metadata.get('estimated_cost', 0) +
                      proposal_result.metadata.get('estimated_cost', 0))

        results['summary'] = {
            'total_processing_time': total_time,
            'total_tokens': total_tokens,
            'total_cost': total_cost
        }

        # 标记文件处理完成
        st.session_state.one_click_generation['file_progress'][file_key] = 100

    except Exception as e:
        results['success'] = False
        results['error'] = str(e)
        progress_callback(f"[{file_index + 1}/{total_files}] ❌ 处理失败: {str(e)}")

    finally:
        # 清理临时文件（如果配置了自动清理）
        if config.get('auto_cleanup', True) and temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

    return results


def process_all_files(input_files: List, config: dict):
    """处理所有文件的主函数"""
    st.session_state.one_click_generation['processing_status'] = 'processing'
    st.session_state.one_click_generation['start_time'] = datetime.now()
    st.session_state.one_click_generation['current_progress'] = 0
    st.session_state.one_click_generation['file_progress'] = {}

    # 创建进度显示区域
    progress_container = st.container()

    with progress_container:
        # 总体进度条
        overall_progress = st.progress(0)
        status_text = st.empty()

        # 详细进度信息
        detail_container = st.container()

        # 处理每个文件
        all_results = []
        total_files = len(input_files)

        for i, file in enumerate(input_files):
            # 更新总体进度
            overall_progress_value = i / total_files
            overall_progress.progress(overall_progress_value)
            st.session_state.one_click_generation['current_progress'] = int(overall_progress_value * 100)

            # 定义进度回调
            def progress_callback(msg):
                status_text.text(msg)

            # 显示当前文件信息
            with detail_container:
                st.markdown(f"### 正在处理: {file.name}")
                file_progress = st.progress(0)

                # 创建步骤指示器
                steps_cols = st.columns(4)
                step_indicators = []

                with steps_cols[0]:
                    step_indicators.append(st.empty())
                    step_indicators[0].info("📥 文件处理")

                with steps_cols[1]:
                    step_indicators.append(st.empty())
                    step_indicators[1].info("🔍 深度分析")

                with steps_cols[2]:
                    step_indicators.append(st.empty())
                    step_indicators[2].info("📝 方案生成")

                with steps_cols[3]:
                    step_indicators.append(st.empty())
                    step_indicators[3].info("💾 保存结果")

                # 创建文件进度更新器
                def update_file_progress():
                    file_key = f"file_{i}"
                    if file_key in st.session_state.one_click_generation['file_progress']:
                        progress_val = st.session_state.one_click_generation['file_progress'][file_key]
                        file_progress.progress(progress_val / 100.0)

            # 处理文件
            result = process_single_file(file, i, total_files, config, progress_callback)

            # 更新步骤指示器
            if result['success']:
                for indicator in step_indicators:
                    indicator.success("✅ 完成")
            else:
                # 根据失败的步骤更新指示器
                if 'processing' in result['steps'] and result['steps']['processing']['success']:
                    step_indicators[0].success("✅ 完成")
                else:
                    step_indicators[0].error("❌ 失败")

                if 'analysis' in result['steps'] and result['steps']['analysis']['success']:
                    step_indicators[1].success("✅ 完成")
                elif 'analysis' in result['steps']:
                    step_indicators[1].error("❌ 失败")

                if 'proposal' in result['steps'] and result['steps']['proposal']['success']:
                    step_indicators[2].success("✅ 完成")
                elif 'proposal' in result['steps']:
                    step_indicators[2].error("❌ 失败")

            all_results.append(result)

            # 清理详细进度显示
            detail_container.empty()

            # 添加延迟避免API限制
            if i < total_files - 1:
                time.sleep(2)

        # 更新最终状态
        overall_progress.progress(1.0)
        st.session_state.one_click_generation['current_progress'] = 100
        status_text.text("✅ 所有文件处理完成！")

    # 保存结果
    st.session_state.one_click_generation['processing_results'] = all_results
    st.session_state.one_click_generation['processing_status'] = 'completed'
    st.session_state.one_click_generation['end_time'] = datetime.now()

    # 显示处理摘要
    show_processing_summary(all_results)


def show_processing_summary(results: List[Dict]):
    """显示处理摘要"""
    st.markdown("---")
    st.markdown("### 📊 处理摘要")

    # 计算统计数据
    total_files = len(results)
    successful_files = sum(1 for r in results if r['success'])
    failed_files = total_files - successful_files

    # 计算总时间
    start_time = st.session_state.one_click_generation.get('start_time')
    end_time = st.session_state.one_click_generation.get('end_time')

    if start_time and end_time:
        total_duration = (end_time - start_time).total_seconds()
    else:
        total_duration = 0

    # 显示关键指标
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "处理文件数",
            f"{successful_files}/{total_files}",
            delta=f"{format_percentage(successful_files / total_files if total_files > 0 else 0)} 成功率"
        )

    with col2:
        st.metric(
            "总处理时间",
            format_duration(total_duration),
            delta=f"平均 {format_duration(total_duration / total_files if total_files > 0 else 0)}/文件"
        )

    with col3:
        total_tokens = sum(r.get('summary', {}).get('total_tokens', 0) for r in results if r['success'])
        st.metric(
            "Token使用",
            f"{total_tokens:,}",
            delta="总计"
        )

    with col4:
        total_cost = sum(r.get('summary', {}).get('total_cost', 0) for r in results if r['success'])
        st.metric(
            "预估费用",
            f"${total_cost:.2f}",
            delta="USD"
        )

    # 显示详细结果
    if failed_files > 0:
        st.warning(f"有 {failed_files} 个文件处理失败")

        # 显示失败文件列表
        with st.expander("查看失败文件详情", expanded=True):
            for result in results:
                if not result['success']:
                    st.error(f"**{result['file_name']}**: {result.get('error', '未知错误')}")

    # 显示成功文件的结果
    if successful_files > 0:
        st.success(f"成功处理 {successful_files} 个文件")

        # 准备下载
        show_download_section(results)


def show_download_section(results: List[Dict]):
    """显示下载部分"""
    st.markdown("### 💾 下载结果")

    # 创建输出目录
    batch_id = st.session_state.one_click_generation['batch_id']
    output_dir = Path("output") / batch_id
    ensure_directory_exists(output_dir)

    # 准备下载选项
    col1, col2, col3 = st.columns(3)

    with col1:
        download_format = st.selectbox(
            "选择下载格式",
            options=['all', 'proposals_only', 'complete_package'],
            format_func=lambda x: {
                'all': '所有文件（分别下载）',
                'proposals_only': '仅方案文档',
                'complete_package': '完整数据包（ZIP）'
            }.get(x, x)
        )

    with col2:
        include_intermediate = st.checkbox(
            "包含中间结果",
            value=False,
            help="包含转录文本和分析报告"
        )

    with col3:
        organize_by_client = st.checkbox(
            "按客户组织",
            value=bool(st.session_state.one_click_generation['workflow_config'].get('client_name')),
            help="使用客户名称组织文件"
        )

    # 生成下载文件
    if st.button("📦 生成下载文件", type="primary", use_container_width=True):
        with st.spinner("正在准备下载文件..."):
            download_files = prepare_download_files(
                results,
                output_dir,
                download_format,
                include_intermediate,
                organize_by_client
            )

            if download_files:
                st.success(f"已生成 {len(download_files)} 个文件")

                # 显示下载按钮
                for file_info in download_files:
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        with open(file_info['path'], 'rb') as f:
                            st.download_button(
                                label=f"📥 {file_info['display_name']}",
                                data=f.read(),
                                file_name=file_info['filename'],
                                mime=file_info['mime_type'],
                                use_container_width=True
                            )

                    with col2:
                        st.caption(file_info['size'])


def prepare_download_files(results: List[Dict],
                           output_dir: Path,
                           format_type: str,
                           include_intermediate: bool,
                           organize_by_client: bool) -> List[Dict]:
    """准备下载文件"""
    download_files = []

    # 获取客户名称
    client_name = st.session_state.one_click_generation['workflow_config'].get('client_name', '')
    if organize_by_client and client_name:
        base_dir = output_dir / client_name.replace(' ', '_')
    else:
        base_dir = output_dir

    ensure_directory_exists(base_dir)

    if format_type == 'complete_package':
        # 创建ZIP包
        zip_filename = f"SmartProposal_Package_{st.session_state.one_click_generation['batch_id']}.zip"
        zip_path = output_dir / zip_filename

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for result in results:
                if result['success'] and 'final_results' in result:
                    file_base = Path(result['file_name']).stem

                    # 添加方案
                    proposal_content = result['final_results']['proposal']
                    proposal_name = f"{file_base}_proposal.md"
                    zipf.writestr(f"proposals/{proposal_name}", proposal_content)

                    if include_intermediate:
                        # 添加转录文本
                        transcript_content = result['final_results']['original_content']
                        transcript_name = f"{file_base}_transcript.txt"
                        zipf.writestr(f"transcripts/{transcript_name}", transcript_content)

                        # 添加分析报告
                        analysis_content = result['final_results']['analysis_report']
                        analysis_name = f"{file_base}_analysis.md"
                        zipf.writestr(f"analysis/{analysis_name}", analysis_content)

                    # 添加元数据
                    metadata = {
                        'file_name': result['file_name'],
                        'processing_summary': result.get('summary', {}),
                        'metadata': result['final_results']['metadata']
                    }
                    metadata_name = f"{file_base}_metadata.json"
                    zipf.writestr(f"metadata/{metadata_name}",
                                  json.dumps(metadata, ensure_ascii=False, indent=2))

            # 添加汇总报告
            summary_report = generate_summary_report(results)
            zipf.writestr("SUMMARY_REPORT.md", summary_report)

        download_files.append({
            'path': str(zip_path),
            'filename': zip_filename,
            'display_name': f"完整数据包 ({len([r for r in results if r['success']])} 个文件)",
            'size': format_file_size(zip_path.stat().st_size),
            'mime_type': 'application/zip'
        })

    else:
        # 分别保存文件
        for result in results:
            if result['success'] and 'final_results' in result:
                file_base = Path(result['file_name']).stem

                if format_type == 'all' or format_type == 'proposals_only':
                    # 保存方案
                    proposal_content = result['final_results']['proposal']
                    proposal_filename = f"{file_base}_proposal.md"
                    proposal_path = base_dir / proposal_filename

                    with open(proposal_path, 'w', encoding='utf-8') as f:
                        f.write(proposal_content)

                    download_files.append({
                        'path': str(proposal_path),
                        'filename': proposal_filename,
                        'display_name': f"方案 - {file_base}",
                        'size': format_file_size(proposal_path.stat().st_size),
                        'mime_type': 'text/markdown'
                    })

                if format_type == 'all' and include_intermediate:
                    # 保存转录文本
                    transcript_content = result['final_results']['original_content']
                    transcript_filename = f"{file_base}_transcript.txt"
                    transcript_path = base_dir / transcript_filename

                    with open(transcript_path, 'w', encoding='utf-8') as f:
                        f.write(transcript_content)

                    download_files.append({
                        'path': str(transcript_path),
                        'filename': transcript_filename,
                        'display_name': f"转录 - {file_base}",
                        'size': format_file_size(transcript_path.stat().st_size),
                        'mime_type': 'text/plain'
                    })

                    # 保存分析报告
                    analysis_content = result['final_results']['analysis_report']
                    analysis_filename = f"{file_base}_analysis.md"
                    analysis_path = base_dir / analysis_filename

                    with open(analysis_path, 'w', encoding='utf-8') as f:
                        f.write(analysis_content)

                    download_files.append({
                        'path': str(analysis_path),
                        'filename': analysis_filename,
                        'display_name': f"分析 - {file_base}",
                        'size': format_file_size(analysis_path.stat().st_size),
                        'mime_type': 'text/markdown'
                    })

    return download_files


def generate_summary_report(results: List[Dict]) -> str:
    """生成汇总报告"""
    report = f"""# SmartProposal Engine 批处理报告

**批次ID**: {st.session_state.one_click_generation['batch_id']}  
**处理时间**: {st.session_state.one_click_generation['start_time'].strftime('%Y-%m-%d %H:%M:%S')} - {st.session_state.one_click_generation['end_time'].strftime('%Y-%m-%d %H:%M:%S')}  
**处理配置**:
- 分析模板: {st.session_state.one_click_generation['workflow_config']['analysis_template']}
- 方案模板: {st.session_state.one_click_generation['workflow_config']['proposal_template']}
- 客户名称: {st.session_state.one_click_generation['workflow_config'].get('client_name', '未指定')}

## 处理结果摘要

| 文件名 | 状态 | 处理时间 | Token使用 | 费用 |
|--------|------|----------|-----------|------|
"""

    for result in results:
        status = "✅ 成功" if result['success'] else "❌ 失败"

        if result['success']:
            summary = result.get('summary', {})
            time_str = f"{summary.get('total_processing_time', 0):.1f}秒"
            tokens_str = f"{summary.get('total_tokens', 0):,}"
            cost_str = f"${summary.get('total_cost', 0):.4f}"
        else:
            time_str = "-"
            tokens_str = "-"
            cost_str = "-"

        report += f"| {result['file_name']} | {status} | {time_str} | {tokens_str} | {cost_str} |\n"

    # 添加统计信息
    total_success = sum(1 for r in results if r['success'])
    total_time = sum(r.get('summary', {}).get('total_processing_time', 0) for r in results if r['success'])
    total_tokens = sum(r.get('summary', {}).get('total_tokens', 0) for r in results if r['success'])
    total_cost = sum(r.get('summary', {}).get('total_cost', 0) for r in results if r['success'])

    report += f"""
## 统计汇总

- **成功处理**: {total_success}/{len(results)} 个文件
- **总处理时间**: {format_duration(total_time)}
- **总Token使用**: {total_tokens:,}
- **总费用**: ${total_cost:.2f}

---
*Generated by SmartProposal Engine*
"""

    return report


def main():
    """主函数"""
    # 初始化页面状态
    initialize_page_state()

    # 页面标题
    st.title("🚀 一键生成")
    st.markdown("从原始文件到专业方案的端到端自动化处理")

    # 根据处理状态显示不同内容
    status = st.session_state.one_click_generation['processing_status']

    if status == 'completed':
        # 显示处理结果
        results = st.session_state.one_click_generation.get('processing_results', [])
        show_processing_summary(results)

        # 重新开始按钮
        if st.button("🔄 开始新的批处理", use_container_width=True):
            # 重置状态
            st.session_state.one_click_generation = {
                'input_files': [],
                'capability_docs': [],
                'processing_status': 'idle',
                'current_step': None,
                'processing_results': {},
                'workflow_config': st.session_state.one_click_generation['workflow_config'],
                'batch_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'start_time': None,
                'end_time': None,
                'current_progress': 0,
                'file_progress': {}
            }
            st.rerun()

    elif status == 'processing':
        # 正在处理中
        st.info("正在处理中，请稍候...")
        st.spinner("处理可能需要几分钟时间，请勿关闭页面")

    else:  # idle
        # 文件上传部分
        input_files, capability_docs = show_upload_section()

        if input_files:
            st.markdown("---")

            # 工作流配置
            config = show_workflow_configuration()

            st.markdown("---")

            # 处理预览
            st.markdown("### 📋 处理预览")

            # 显示将要处理的信息
            col1, col2 = st.columns(2)

            with col1:
                st.info(f"""
                **待处理文件**: {len(input_files)} 个  
                **能力文档**: {len(capability_docs)} 个  
                **分析场景**: {DeepAnalysisService.ANALYSIS_SCENARIOS.get(config['analysis_template'], {}).get('name', config['analysis_template'])}  
                **方案类型**: {ProposalService.PROPOSAL_TYPES.get(config['proposal_template'], {}).get('name', config['proposal_template'])}
                """)

            with col2:
                # 预估处理时间
                estimated_time_per_file = 60  # 每个文件约60秒
                estimated_total_time = len(input_files) * estimated_time_per_file

                st.info(f"""
                **预计处理时间**: {format_duration(estimated_total_time)}  
                **文本优化**: {'启用' if config.get('enable_text_optimization') else '禁用'}  
                **输出语言**: {'中文' if config.get('output_language', 'zh') == 'zh' else 'English'}  
                **客户**: {config.get('client_name', '未指定')}
                """)

            # 开始处理按钮
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button(
                        "🚀 开始批量处理",
                        type="primary",
                        use_container_width=True,
                        help="开始处理所有上传的文件"
                ):
                    # 开始处理
                    process_all_files(input_files, config)
                    st.rerun()

    # 侧边栏信息
    with st.sidebar:
        st.markdown("### 💡 使用提示")
        st.info("""
**批量处理流程**：
1. 上传原始文件（音频/文档）
2. 上传企业能力文档（可选）
3. 配置处理参数
4. 点击开始批量处理
5. 等待处理完成
6. 下载生成的方案

**处理步骤**：
- 文件处理：转录音频或提取文本
- 深度分析：提取商业洞察
- 方案生成：生成专业文档

**注意事项**：
- 每个文件独立处理
- 支持多种文件格式
- 自动保存中间结果
- 可打包下载所有结果
""")

        # 显示当前批次信息
        if st.session_state.one_click_generation.get('batch_id'):
            st.markdown("---")
            st.markdown("### 📊 当前批次")
            st.text(f"ID: {st.session_state.one_click_generation['batch_id']}")

            if status == 'completed':
                results = st.session_state.one_click_generation.get('processing_results', [])
                success_count = sum(1 for r in results if r['success'])
                st.metric("成功率", f"{success_count}/{len(results)}")


if __name__ == "__main__":
    main()