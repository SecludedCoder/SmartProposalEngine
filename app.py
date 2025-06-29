#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/app.py
功能说明: SmartProposal Engine主应用入口
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-29
版本: 1.1.0
"""

import os
import sys
import time
import streamlit as st
from pathlib import Path
import configparser
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.session_manager import SessionManager
from core.model_interface import ModelInterface
from utils.file_utils import ensure_directory_exists

# 页面配置
st.set_page_config(
    page_title="SmartProposal Engine",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/smartproposal/engine',
        'Report a bug': 'https://github.com/smartproposal/engine/issues',
        'About': """
        # SmartProposal Engine

        智能商业方案生成系统

        版本: 1.1.0
        """
    }
)


def load_custom_css():
    """加载自定义CSS样式"""
    css_file = Path(__file__).parent / "assets" / "styles" / "custom.css"
    if css_file.exists():
        #【修改】明确指定UTF-8编码读取CSS文件
        with open(css_file, 'r', encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        # 默认样式
        st.markdown("""
        <style>
        /* 主标题样式 */
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 1rem;
            padding: 1rem 0;
            border-bottom: 3px solid #e0e0e0;
        }

        /* 功能卡片样式 */
        .feature-card {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border: 1px solid #e0e0e0;
            transition: all 0.3s ease;
        }

        .feature-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }

        /* 统计信息样式 */
        .stat-card {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            border: 1px solid #e0e0e0;
        }

        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #1f77b4;
        }

        .stat-label {
            font-size: 0.9rem;
            color: #666;
            margin-top: 0.5rem;
        }

        /* 侧边栏样式 */
        .css-1d391kg {
            background-color: #f8f9fa;
        }

        /* 按钮样式增强 */
        .stButton > button {
            background-color: #1f77b4;
            color: white;
            border: none;
            padding: 0.5rem 2rem;
            border-radius: 5px;
            font-weight: bold;
            transition: all 0.3s ease;
        }

        .stButton > button:hover {
            background-color: #145a8b;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        /* 成功消息样式 */
        .success-message {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
        }

        /* 错误消息样式 */
        .error-message {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
        }
        </style>
        """, unsafe_allow_html=True)


def initialize_session_state():
    """初始化会话状态"""
    # 初始化SessionManager
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = SessionManager()

    # 初始化其他会话变量
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.api_key_configured = False  # 新增：标记API Key是否已配置
        st.session_state.model_provider = None  # 新增：存储选择的模型提供商
        st.session_state.processing_history = []
        st.session_state.current_workflow = None
        st.session_state.last_activity = datetime.now()

    # 初始化模型接口（不立即进行API Key配置）
    if 'model_interface' not in st.session_state:
        try:
            st.session_state.model_interface = ModelInterface()
            # 如果使用内部key，它在__init__中已经初始化了
            if st.session_state.model_interface.is_initialized:
                st.session_state.api_key_configured = True
                st.session_state.model_provider = st.session_state.model_interface.provider
        except Exception as e:
            st.session_state.api_key_configured = False
            st.session_state.model_error = str(e)


def create_directories():
    """创建必要的目录"""
    directories = [
        'temp',
        'output',
        'prompts/analysis',
        'prompts/proposal',
        'prompts/transcription'
    ]

    for directory in directories:
        ensure_directory_exists(directory)


def load_config():
    """加载应用配置"""
    config_path = Path(__file__).parent / "app_config.ini"
    config = configparser.ConfigParser()

    if config_path.exists():
        # 【修改】明确指定UTF-8编码读取配置文件
        config.read(config_path, encoding='utf-8')
        st.session_state.config = config
    else:
        st.warning("配置文件未找到，使用默认配置")
        st.session_state.config = None


def show_initialization_page():
    """显示API Key和模型提供商设置页面"""
    st.title("🚀 欢迎使用 SmartProposal Engine")
    st.header("请先完成系统设置")

    st.info("为了使用本系统的AI功能，您需要提供一个有效的API Key。")

    config = st.session_state.config
    providers_str = config.get('MODEL_PROVIDERS', 'available_providers', fallback='Gemini')
    providers = [p.strip() for p in providers_str.split(',')]
    default_provider = config.get('MODEL_PROVIDERS', 'default_provider', fallback='Gemini')

    col1, col2 = st.columns(2)
    with col1:
        selected_provider = st.selectbox(
            "1. 选择模型提供商",
            options=providers,
            index=providers.index(default_provider) if default_provider in providers else 0
        )

    with col2:
        api_key = st.text_input(
            "2. 输入您的API Key",
            type="password",
            help=f"请输入 {selected_provider} 的 API Key"
        )

    if st.button("保存并开始使用", type="primary", use_container_width=True):
        if not api_key:
            st.error("API Key 不能为空！")
        else:
            with st.spinner("正在验证和初始化模型..."):
                try:
                    # 获取模型接口实例并进行初始化
                    model_interface = st.session_state.model_interface
                    model_interface.initialize_model(api_key, selected_provider)

                    # 更新会话状态
                    st.session_state.api_key_configured = True
                    st.session_state.model_provider = selected_provider

                    # 设置默认模型
                    for task in ['transcription', 'analysis', 'proposal']:
                        default_model_key = f'{task}_model'
                        if config.has_option('MODEL_SETTINGS', default_model_key):
                            default_model = config.get('MODEL_SETTINGS', default_model_key)
                            model_interface.set_model(task, default_model)

                    st.success("初始化成功！系统已准备就绪。")
                    time.sleep(1)
                    st.rerun()

                except Exception as e:
                    st.error(f"初始化失败: {e}")
                    st.error("请检查您的API Key和网络连接后重试。")


def show_sidebar():
    """显示侧边栏"""
    with st.sidebar:
        st.markdown("## 🚀 SmartProposal Engine")
        st.markdown("---")

        # 显示当前状态
        if st.session_state.get('api_key_configured'):
            st.success(f"✅ 系统已就绪 ({st.session_state.get('model_provider')})")
        else:
            st.error("⚠️ 系统未配置")

        st.markdown("---")

        # 新增：模型配置部分
        st.markdown("### ⚙️ 模型配置")
        model_interface = st.session_state.get('model_interface')
        provider = st.session_state.get('model_provider')

        if model_interface and provider:
            available_models = model_interface.get_available_models(provider)
            model_options = [m['api_name'] for m in available_models]

            def format_func(name):
                model_conf = model_interface.all_models.get(name)
                if model_conf:
                    return f"{model_conf.display_name} ({name.split('/')[-1]})"
                return name

            # 转录模型
            current_trans_model = model_interface.get_model_name('transcription')
            trans_index = model_options.index(current_trans_model) if current_trans_model in model_options else 0
            selected_trans_model = st.selectbox(
                "转录模型",
                options=model_options,
                index=trans_index,
                format_func=format_func,
                key='transcription_model_selector'
            )
            model_interface.set_model('transcription', selected_trans_model)

            # 分析模型
            current_analysis_model = model_interface.get_model_name('analysis')
            analysis_index = model_options.index(
                current_analysis_model) if current_analysis_model in model_options else 0
            selected_analysis_model = st.selectbox(
                "分析模型",
                options=model_options,
                index=analysis_index,
                format_func=format_func,
                key='analysis_model_selector'
            )
            model_interface.set_model('analysis', selected_analysis_model)

            # 方案生成模型
            current_proposal_model = model_interface.get_model_name('proposal')
            proposal_index = model_options.index(
                current_proposal_model) if current_proposal_model in model_options else 0
            selected_proposal_model = st.selectbox(
                "方案模型",
                options=model_options,
                index=proposal_index,
                format_func=format_func,
                key='proposal_model_selector'
            )
            model_interface.set_model('proposal', selected_proposal_model)
        else:
            st.caption("请先完成系统设置以配置模型。")

        st.markdown("---")

        # 功能导航说明
        st.markdown("### 🧭 功能导航")
        st.info("""
        **1. 📥 内容输入**: 上传音频或文档
        **2. 🔍 深度分析**: 商业洞察分析
        **3. 📝 方案生成**: 生成专业方案
        **4. ✨ 一键生成**: 端到端处理
        """)

        st.markdown("---")

        # 处理统计
        if 'processing_history' in st.session_state:
            st.markdown("### 📊 处理统计")
            total_processed = len(st.session_state.processing_history)
            st.metric("已处理文件", total_processed)

        # 会话信息
        if 'last_activity' in st.session_state:
            st.markdown("---")
            st.markdown("### ℹ️ 会话信息")
            st.text(f"最后活动: {st.session_state.last_activity.strftime('%H:%M:%S')}")

        # 系统设置
        st.markdown("---")
        st.markdown("### 🛠️ 系统操作")

        if st.button("🧹 清理临时文件"):
            session_manager = st.session_state.get('session_manager')
            if session_manager:
                session_manager.cleanup_all_temp_files()
                st.success("临时文件已清理")

        if st.button("🔄 重置会话"):
            # 保留关键配置信息
            api_configured = st.session_state.get('api_key_configured', False)
            provider = st.session_state.get('model_provider')
            model_if = st.session_state.get('model_interface')
            app_config = st.session_state.get('config')

            for key in list(st.session_state.keys()):
                del st.session_state[key]

            # 恢复关键状态
            st.session_state.api_key_configured = api_configured
            st.session_state.model_provider = provider
            st.session_state.model_interface = model_if
            st.session_state.config = app_config

            # 重新初始化会话状态
            initialize_session_state()
            st.rerun()


def show_main_page():
    """显示主页面"""
    # 主标题
    st.markdown('<h1 class="main-header">🚀 SmartProposal Engine</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">智能商业方案生成系统</p>',
                unsafe_allow_html=True)

    st.markdown("---")

    # 系统介绍
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        ### 👋 欢迎使用SmartProposal Engine

        SmartProposal Engine是一个智能化的商业方案生成系统，能够帮助您快速将原始信息转化为专业的商业文档。

        **核心功能：**
        - 🎤 **智能转录**：支持音频文件的高精度转录，识别多说话人对话
        - 🔍 **深度分析**：基于AI的商业洞察分析，提取关键信息
        - 📝 **方案生成**：自动生成专业的项目建议书和商业方案
        - ✨ **端到端处理**：一键完成从原始输入到最终方案的全流程

        **适用场景：**
        - 客户访谈记录分析
        - 商务谈判要点提取
        - 内部会议决策整理
        - 需求收集与分析
        - 项目方案快速生成
        """)

    with col2:
        # 快速开始指南
        st.markdown("""
        ### ⚡ 快速开始

        **步骤 1**: 选择左侧导航中的功能模块

        **步骤 2**: 上传您的音频或文档文件

        **步骤 3**: 选择合适的分析模板

        **步骤 4**: 获取AI生成的专业方案

        ---

        💡 **提示**: 首次使用建议从"一键生成"功能开始，体验完整流程
        """)

    st.markdown("---")

    # 功能卡片展示
    st.markdown("### 🎯 核心功能模块")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="feature-card">
        <h4>📥 内容输入处理</h4>
        <p>支持多种格式的内容输入：</p>
        <ul>
        <li>音频文件：m4a, mp3, wav等</li>
        <li>文档文件：docx, pdf, txt</li>
        <li>文本直接输入</li>
        </ul>
        <p>智能识别说话人，优化转录质量</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="feature-card">
        <h4>🧠 深度分析引擎</h4>
        <p>基于场景的智能分析：</p>
        <ul>
        <li>客户需求洞察</li>
        <li>商务谈判要点</li>
        <li>会议决策提取</li>
        <li>自定义分析模板</li>
        </ul>
        <p>提供结构化的分析报告</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
        <h4>💡 方案智能生成</h4>
        <p>专业文档自动生成：</p>
        <ul>
        <li>项目建议书</li>
        <li>商务报价方案</li>
        <li>解决方案简报</li>
        <li>会议纪要</li>
        </ul>
        <p>融合企业能力，定制化输出</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="feature-card">
        <h4>🚀 一键全流程处理</h4>
        <p>端到端自动化处理：</p>
        <ul>
        <li>批量文件处理</li>
        <li>自动流程编排</li>
        <li>进度实时跟踪</li>
        <li>结果批量下载</li>
        </ul>
        <p>大幅提升工作效率</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 使用统计
    if 'processing_history' in st.session_state and st.session_state.processing_history:
        st.markdown("### 📊 使用统计")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("""
            <div class="stat-card">
            <div class="stat-number">{}</div>
            <div class="stat-label">总处理数</div>
            </div>
            """.format(len(st.session_state.processing_history)), unsafe_allow_html=True)

    # 页脚
    st.markdown("---")
    st.markdown("""
    <p style="text-align: center; color: #888;">
    SmartProposal Engine v1.1.0 | 
    Powered by AI | 
    © 2025 SmartProposal Team
    </p>
    """, unsafe_allow_html=True)


def main():
    """主函数"""
    # 加载自定义CSS
    load_custom_css()

    # 初始化
    load_config()
    initialize_session_state()
    create_directories()

    # 更新最后活动时间
    if st.session_state.get('initialized'):
        st.session_state.last_activity = datetime.now()

    # "守卫"逻辑：检查API Key是否已配置
    if not st.session_state.get('api_key_configured'):
        show_initialization_page()
    else:
        # 如果已配置，显示正常应用界面
        show_sidebar()
        show_main_page()


if __name__ == "__main__":
    main()