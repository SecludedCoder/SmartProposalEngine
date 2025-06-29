#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/app.py
功能说明: SmartProposal Engine主应用入口
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

import os
import sys
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
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/smartproposal/engine',
        'Report a bug': 'https://github.com/smartproposal/engine/issues',
        'About': """
        # SmartProposal Engine MVP
        
        智能商业方案生成系统
        
        版本: 1.0.0 MVP
        """
    }
)


def load_custom_css():
    """加载自定义CSS样式"""
    css_file = Path(__file__).parent / "assets" / "styles" / "custom.css"
    if css_file.exists():
        with open(css_file) as f:
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
        st.session_state.processing_history = []
        st.session_state.current_workflow = None
        st.session_state.last_activity = datetime.now()
    
    # 初始化模型接口（全局共享）
    if 'model_interface' not in st.session_state:
        try:
            st.session_state.model_interface = ModelInterface()
            st.session_state.model_initialized = True
        except Exception as e:
            st.session_state.model_initialized = False
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
        config.read(config_path)
        st.session_state.config = config
    else:
        st.warning("配置文件未找到，使用默认配置")
        st.session_state.config = None


def show_sidebar():
    """显示侧边栏"""
    with st.sidebar:
        st.markdown("## 🚀 SmartProposal Engine")
        st.markdown("---")
        
        # 显示当前状态
        if st.session_state.get('model_initialized', False):
            st.success("✅ 系统已就绪")
        else:
            st.error("❌ 模型初始化失败")
            if 'model_error' in st.session_state:
                st.error(st.session_state.model_error)
        
        st.markdown("---")
        
        # 功能导航说明
        st.markdown("### 📌 功能导航")
        st.info("""
        **1. 📄 内容输入**: 上传音频或文档
        **2. 🔍 深度分析**: 商业洞察分析
        **3. 📋 方案生成**: 生成专业方案
        **4. 🚀 一键生成**: 端到端处理
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
            st.markdown("### ⏰ 会话信息")
            st.text(f"最后活动: {st.session_state.last_activity.strftime('%H:%M:%S')}")
        
        # 系统设置
        st.markdown("---")
        st.markdown("### ⚙️ 系统设置")
        
        if st.button("🗑️ 清理临时文件"):
            session_manager = st.session_state.get('session_manager')
            if session_manager:
                session_manager.cleanup_all_temp_files()
                st.success("临时文件已清理")
        
        if st.button("🔄 重置会话"):
            for key in list(st.session_state.keys()):
                if key not in ['model_interface', 'model_initialized', 'config']:
                    del st.session_state[key]
            st.rerun()


def show_main_page():
    """显示主页面"""
    # 主标题
    st.markdown('<h1 class="main-header">🎯 SmartProposal Engine</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">智能商业方案生成系统 - MVP版本</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 系统介绍
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 🌟 欢迎使用SmartProposal Engine
        
        SmartProposal Engine是一个智能化的商业方案生成系统，能够帮助您快速将原始信息转化为专业的商业文档。
        
        **核心功能：**
        - 🎙️ **智能转录**：支持音频文件的高精度转录，识别多说话人对话
        - 📊 **深度分析**：基于AI的商业洞察分析，提取关键信息
        - 📝 **方案生成**：自动生成专业的项目建议书和商业方案
        - ⚡ **端到端处理**：一键完成从原始输入到最终方案的全流程
        
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
        ### 🚀 快速开始
        
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
        <h4>📄 内容输入处理</h4>
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
        <h4>🔍 深度分析引擎</h4>
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
        <h4>📋 方案智能生成</h4>
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
        
        # 可以添加更多统计信息
        
    # 页脚
    st.markdown("---")
    st.markdown("""
    <p style="text-align: center; color: #888;">
    SmartProposal Engine MVP v1.0.0 | 
    Powered by Google Gemini | 
    © 2025 SmartProposal Team
    </p>
    """, unsafe_allow_html=True)


def main():
    """主函数"""
    # 加载自定义CSS
    load_custom_css()
    
    # 初始化
    initialize_session_state()
    create_directories()
    load_config()
    
    # 更新最后活动时间
    st.session_state.last_activity = datetime.now()
    
    # 显示侧边栏
    show_sidebar()
    
    # 显示主页面
    show_main_page()


if __name__ == "__main__":
    main()
