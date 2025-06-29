#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/pages/1_📄_Input_Processing.py
功能说明: 内容输入处理页面
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

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_processor import DocumentProcessor
from core.session_manager import SessionManager
from utils.file_utils import (
    save_uploaded_file,
    get_file_metadata,
    format_file_size,
    prepare_download_file
)
from utils.format_utils import (
    format_metadata_display,
    format_duration,
    truncate_text
)
from utils.validation_utils import validate_text_input
from utils.ui_utils import check_api_key_setup  # 引入检查函数

# 页面配置
st.set_page_config(
    page_title="内容输入处理 - SmartProposal Engine",
    page_icon="📄",
    layout="wide"
)


def initialize_page_state():
    """初始化页面状态"""
    if 'input_processing' not in st.session_state:
        st.session_state.input_processing = {
            'current_tab': 'file_upload',
            'processing_result': None,
            'processing_history': [],
            'temp_file_path': None,
            'current_progress': 0  # 添加进度跟踪
        }

    # 确保SessionManager存在
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = SessionManager()

    # 创建或获取当前会话
    if not st.session_state.session_manager.current_session_id:
        st.session_state.session_manager.create_session('input_processing')


def show_file_upload_tab():
    """显示文件上传标签页"""
    st.markdown("### 📁 文件上传")

    # 支持的格式说明
    col1, col2 = st.columns(2)

    with col1:
        st.info("""
        **支持的音频格式：**
        - M4A, MP3, WAV, AAC, OGG, FLAC
        - 最大文件大小：200 MB
        - 支持超长音频自动分割
        """)

    with col2:
        st.info("""
        **支持的文档格式：**
        - DOCX, PDF, TXT, DOC, RTF
        - 最大文件大小：50 MB
        - 自动提取文档内容和元数据
        """)

    # 文件上传组件
    uploaded_file = st.file_uploader(
        "选择要处理的文件",
        type=['m4a', 'mp3', 'wav', 'aac', 'ogg', 'flac', 'mp4',
              'docx', 'pdf', 'txt', 'doc', 'rtf', 'odt'],
        help="拖拽文件到此处或点击浏览"
    )

    if uploaded_file is not None:
        # 显示文件信息
        file_details = {
            "文件名": uploaded_file.name,
            "文件类型": uploaded_file.type,
            "文件大小": format_file_size(uploaded_file.size)
        }

        st.markdown("#### ℹ️ 文件信息")
        for key, value in file_details.items():
            st.text(f"{key}: {value}")

        # 处理选项
        st.markdown("#### ⚙️ 处理选项")

        # 根据文件类型显示不同选项
        file_ext = Path(uploaded_file.name).suffix.lower()

        options = {}

        if file_ext in ['.m4a', '.mp3', '.wav', '.aac', '.ogg', '.flac', '.mp4']:
            # 音频文件选项
            col1, col2 = st.columns(2)

            with col1:
                options['enable_speaker_diarization'] = st.checkbox(
                    "启用说话人识别",
                    value=True,
                    key="file_upload_speaker_diarization",
                    help="识别并区分不同的说话人"
                )

                if options['enable_speaker_diarization']:
                    options['maintain_speaker_consistency'] = st.checkbox(
                        "保持说话人一致性",
                        value=True,
                        key="file_upload_speaker_consistency",
                        help="在长音频中保持说话人标识的一致性"
                    )

            with col2:
                options['enable_text_optimization'] = st.checkbox(
                    "启用文本优化",
                    value=False,
                    key="file_upload_text_optimization",
                    help="使用AI优化转录文本质量"
                )

                options['max_segment_duration_minutes'] = st.slider(
                    "最大片段时长（分钟）",
                    min_value=10,
                    max_value=30,
                    value=20,
                    key="file_upload_segment_duration",
                    help="超长音频将被分割成多个片段"
                )

        else:
            # 文档文件选项
            col1, col2 = st.columns(2)

            with col1:
                options['extract_metadata'] = st.checkbox(
                    "提取元数据",
                    value=True,
                    key="file_upload_extract_metadata",
                    help="提取文档的作者、创建时间等信息"
                )

            with col2:
                options['clean_output'] = st.checkbox(
                    "清理输出文本",
                    value=True,
                    key="file_upload_clean_output",
                    help="移除多余的空格和空行"
                )

        # 处理按钮
        if st.button("▶️ 开始处理", type="primary", use_container_width=True, key="file_upload_process"):
            process_uploaded_file(uploaded_file, options)


def show_text_input_tab():
    """显示文本输入标签页"""
    st.markdown("### ✍️ 文本输入")

    st.info("""
    直接粘贴或输入文本内容，适用于：
    - 已有的转录文本
    - 会议记录
    - 其他文本内容
    """)

    # 文本输入区域
    text_input = st.text_area(
        "请输入文本内容",
        height=400,
        placeholder="在此粘贴或输入文本内容...",
        key="text_input_area",
        help="支持中英文，建议长度在50-50000字符之间"
    )

    # 显示字数统计
    if text_input:
        char_count = len(text_input)
        word_count = len(text_input.split())
        st.caption(f"字符数: {char_count:,} | 词数: {word_count:,}")

    # 输入选项
    st.markdown("#### ⚙️ 处理选项")

    col1, col2 = st.columns(2)

    with col1:
        input_type = st.selectbox(
            "文本类型",
            options=['transcript', 'document', 'general'],
            format_func=lambda x: {
                'transcript': '转录文本',
                'document': '文档内容',
                'general': '通用文本'
            }.get(x, x),
            key="text_input_type",
            help="选择文本的类型以获得最佳处理效果"
        )

    with col2:
        if input_type == 'transcript':
            enable_optimization = st.checkbox(
                "启用文本优化",
                value=False,
                key="text_input_optimization",
                help="使用AI优化转录文本质量"
            )
        else:
            enable_optimization = False

    # 处理按钮
    if st.button("▶️ 处理文本", type="primary", use_container_width=True, key="text_input_process"):
        if text_input.strip():
            # 验证文本
            is_valid, message = validate_text_input(
                text_input,
                min_length=50,
                max_length=100000
            )

            if is_valid:
                process_text_input(text_input, input_type, enable_optimization)
            else:
                st.error(message)
        else:
            st.warning("请输入文本内容")


def process_uploaded_file(uploaded_file, options):
    """处理上传的文件"""
    session_manager = st.session_state.session_manager

    # 创建进度容器
    progress_container = st.container()

    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 初始化进度跟踪
        st.session_state.input_processing['current_progress'] = 0

        try:
            # 保存上传的文件
            status_text.text("正在保存文件...")
            progress_bar.progress(10)
            st.session_state.input_processing['current_progress'] = 10

            save_dir = Path("temp") / datetime.now().strftime("%Y%m%d_%H%M%S")
            success, file_path, message = save_uploaded_file(
                uploaded_file,
                save_dir
            )

            if not success:
                st.error(f"文件保存失败: {message}")
                return

            st.session_state.input_processing['temp_file_path'] = file_path

            # 初始化处理器
            status_text.text("正在初始化处理器...")
            progress_bar.progress(20)
            st.session_state.input_processing['current_progress'] = 20

            processor = DocumentProcessor()

            # 定义进度回调
            def progress_callback(msg):
                status_text.text(msg)
                # 动态更新进度条
                current = st.session_state.input_processing['current_progress']
                if current < 90:
                    new_progress = min(current + 10, 90)
                    progress_bar.progress(new_progress)
                    st.session_state.input_processing['current_progress'] = new_progress

            options['progress_callback'] = progress_callback

            # 处理文件
            status_text.text("正在处理文件...")
            progress_bar.progress(30)
            st.session_state.input_processing['current_progress'] = 30

            start_time = time.time()
            result = processor.process_file(file_path, options)
            processing_time = time.time() - start_time

            progress_bar.progress(100)
            st.session_state.input_processing['current_progress'] = 100

            if result.is_success:
                status_text.text("✅ 处理完成！")

                # 保存结果到会话
                session_manager.save_result('input_processing', result)
                st.session_state.input_processing['processing_result'] = result

                # 添加到历史记录
                st.session_state.input_processing['processing_history'].append({
                    'filename': uploaded_file.name,
                    'timestamp': datetime.now(),
                    'processing_time': processing_time,
                    'result': result
                })

                # 显示成功消息
                st.success(f"""
                文件处理成功！
                - 处理时间: {processing_time:.1f} 秒
                - 内容长度: {len(result.content):,} 字符
                """)

                # 自动展示结果
                time.sleep(1)
                st.rerun()

            else:
                status_text.text("❌ 处理失败")
                st.error(f"处理失败: {result.error}")

        except Exception as e:
            status_text.text("❌ 发生错误")
            st.error(f"处理过程中发生错误: {str(e)}")

        finally:
            # 清理进度显示
            time.sleep(2)
            progress_container.empty()
            # 重置进度
            st.session_state.input_processing['current_progress'] = 0


def process_text_input(text_input, input_type, enable_optimization):
    """处理文本输入"""
    session_manager = st.session_state.session_manager

    with st.spinner("正在处理文本..."):
        try:
            processor = DocumentProcessor()

            options = {
                'enable_text_optimization': enable_optimization
            }

            start_time = time.time()
            result = processor.process_text_input(
                text_input,
                input_type,
                options
            )
            processing_time = time.time() - start_time

            if result.is_success:
                # 保存结果
                session_manager.save_result('input_processing', result)
                st.session_state.input_processing['processing_result'] = result

                # 添加到历史记录
                st.session_state.input_processing['processing_history'].append({
                    'filename': f"文本输入_{datetime.now().strftime('%H%M%S')}",
                    'timestamp': datetime.now(),
                    'processing_time': processing_time,
                    'result': result
                })

                st.success(f"文本处理成功！处理时间: {processing_time:.1f} 秒")

                # 自动展示结果
                time.sleep(1)
                st.rerun()

            else:
                st.error(f"处理失败: {result.error}")

        except Exception as e:
            st.error(f"处理过程中发生错误: {str(e)}")


def show_processing_result():
    """显示处理结果"""
    result = st.session_state.input_processing.get('processing_result')

    if not result:
        return

    st.markdown("---")
    st.markdown("### 📊 处理结果")

    # 结果摘要
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("内容长度", f"{len(result.content):,} 字符")

    with col2:
        st.metric("处理时间", f"{result.processing_time:.1f} 秒")

    with col3:
        if result.tokens_consumed:
            st.metric("Token使用", f"{result.total_tokens:,}")

    # 元数据显示
    if result.metadata:
        with st.expander("ℹ️ 详细信息", expanded=False):
            # 格式化显示元数据
            for key, value in result.metadata.items():
                if key not in ['error', 'original_text']:
                    st.text(f"{key}: {value}")

    # 内容预览
    st.markdown("#### 📋 内容预览")

    # 预览选项
    col1, col2 = st.columns([3, 1])
    with col1:
        preview_length = st.slider(
            "预览长度",
            min_value=500,
            max_value=5000,
            value=1500,
            step=500,
            key="result_preview_length"
        )

    with col2:
        show_full = st.checkbox("显示全文", value=False, key="result_show_full")

    # 显示内容
    if show_full:
        st.text_area(
            "处理后的内容",
            value=result.content,
            height=600,
            disabled=True,
            key="result_full_content"
        )
    else:
        preview_text = truncate_text(result.content, preview_length)
        st.text_area(
            "处理后的内容（预览）",
            value=preview_text,
            height=400,
            disabled=True,
            key="result_preview_content"
        )

    # 操作按钮
    st.markdown("#### ⏯️ 保存和下一步")

    col1, col2, col3 = st.columns(3)

    with col1:
        # 下载按钮
        download_content = result.content
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"processed_content_{timestamp}.txt"

        st.download_button(
            label="💾 下载结果",
            data=download_content,
            file_name=filename,
            mime="text/plain",
            use_container_width=True,
            key="result_download"
        )

    with col2:
        # 发送到分析
        if st.button("➡️ 发送到深度分析", type="primary", use_container_width=True, key="send_to_analysis"):
            # 保存到会话供下一步使用
            session_manager = st.session_state.session_manager
            session_manager.save_result('transcription', result)
            st.success("已保存！请前往 **深度分析** 页面继续")
            # 可以在这里加一个短暂的延迟然后刷新页面，让用户看到消息
            time.sleep(2)
            st.rerun()

    with col3:
        # 清除结果
        if st.button("🗑️ 清除结果", use_container_width=True, key="clear_result"):
            st.session_state.input_processing['processing_result'] = None
            st.rerun()


def show_processing_history():
    """显示处理历史"""
    history = st.session_state.input_processing.get('processing_history', [])

    if not history:
        return

    st.markdown("---")
    st.markdown("### 📜 处理历史")

    # 按时间倒序显示
    for idx, item in enumerate(reversed(history[-5:])):  # 只显示最近5条
        with st.expander(
                f"{item['filename']} - {item['timestamp'].strftime('%H:%M:%S')}",
                expanded=False
        ):
            st.text(f"处理时间: {item['processing_time']:.1f} 秒")
            st.text(f"内容长度: {len(item['result'].content):,} 字符")

            if st.button(f"使用此结果", key=f"use_history_{idx}_{item['timestamp']}"):
                st.session_state.input_processing['processing_result'] = item['result']
                st.rerun()


def main():
    """主函数"""
    # 在页面顶部检查API Key设置
    check_api_key_setup()

    # 初始化页面状态
    initialize_page_state()

    # 页面标题
    st.title("📄 内容输入处理")
    st.markdown("上传音频或文档文件，或直接输入文本内容进行处理")

    # 选择输入方式
    tab1, tab2 = st.tabs(["📁 文件上传", "✍️ 文本输入"])

    with tab1:
        show_file_upload_tab()

    with tab2:
        show_text_input_tab()

    # 显示处理结果
    if st.session_state.input_processing.get('processing_result'):
        show_processing_result()

    # 显示处理历史
    show_processing_history()

    # 侧边栏信息
    with st.sidebar:
        st.markdown("### 💡 使用提示")
        st.info("""
**文件上传**：
- 支持音频和文档文件
- 音频会自动转录为文本
- 文档会提取文本内容

**文本输入**：
- 可直接粘贴已有文本
- 支持优化转录文本

**下一步**：
- 处理完成后可发送到深度分析
- 或下载结果保存
""")

        # 清理临时文件
        if st.button("🗑️ 清理临时文件", key="sidebar_cleanup"):
            session_manager = st.session_state.session_manager
            if session_manager.cleanup_all_temp_files():
                st.success("临时文件已清理")
            else:
                st.error("清理失败")


if __name__ == "__main__":
    main()