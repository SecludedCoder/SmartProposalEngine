# pages/0_🔑_Configuration.py

import streamlit as st
import configparser
from pathlib import Path
import sys
import os

# 确保能找到核心模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.model_interface import ModelInterface

st.set_page_config(page_title="初始化配置", page_icon="🔑", layout="centered")

st.title("🔑 系统初始化配置")
st.markdown("在使用前，请先完成API Key和模型的配置。")

# --- Session State 初始化 ---
if 'app_settings' not in st.session_state:
    st.session_state.app_settings = {
        "api_key": "",
        "model_provider": "Gemini", # 默认提供商
        "transcription_model": "",
        "analysis_model": "",
        "proposal_model": "",
        "config_completed": False
    }

# --- 加载模型配置 ---
# (此处的模型加载逻辑将在第二阶段重构 ModelInterface 后变得更优雅)
# 暂时用一个简化的方式来演示
def load_available_models():
    # 在第二阶段，这里会从 ModelInterface 获取
    # 假设 models.conf 已经按新格式修改
    return {
        "Gemini": ["models/gemini-2.5-flash", "models/gemini-2.5-pro", "models/gemini-1.5-pro-latest"],
        "Qwen": ["qwen-turbo", "qwen-long"],
        # ... 其他模型提供商
    }

available_models = load_available_models()
model_providers = list(available_models.keys())

# --- 界面表单 ---
with st.form("config_form"):
    st.subheader("1. API 配置")
    api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="请输入您的API Key",
        help="您的API Key将仅在本次会话中保存，不会被存储到服务器。",
        value=st.session_state.app_settings.get("api_key", "")
    )

    st.subheader("2. 模型选择")
    model_provider = st.selectbox(
        "选择模型提供商",
        options=model_providers,
        index=model_providers.index(st.session_state.app_settings.get("model_provider", "Gemini"))
    )

    # 根据选择的提供商，动态更新子模型列表
    sub_models = available_models.get(model_provider, [])

    transcription_model = st.selectbox(
        "转录模型 (用于音频处理)",
        options=sub_models,
        help="推荐使用针对音频优化的模型，如 gemini-2.5-flash"
    )

    analysis_model = st.selectbox(
        "分析模型 (用于深度分析)",
        options=sub_models,
        help="推荐使用能力更强的模型，如 gemini-2.5-pro"
    )

    proposal_model = st.selectbox(
        "方案生成模型 (用于最终输出)",
        options=sub_models,
        help="推荐使用能力最强的模型，如 gemini-2.5-pro"
    )

    submitted = st.form_submit_button("✅ 保存配置", use_container_width=True, type="primary")

# --- 表单提交逻辑 ---
if submitted:
    if not api_key:
        st.error("API Key 不能为空！")
    else:
        # 保存配置到 session_state
        st.session_state.app_settings["api_key"] = api_key
        st.session_state.app_settings["model_provider"] = model_provider
        st.session_state.app_settings["transcription_model"] = transcription_model
        st.session_state.app_settings["analysis_model"] = analysis_model
        st.session_state.app_settings["proposal_model"] = proposal_model
        st.session_state.app_settings["config_completed"] = True

        # 真正的初始化在这里发生
        if 'model_interface' in st.session_state:
            try:
                # 使用用户输入的Key和模型选择来配置 ModelInterface
                model_interface = st.session_state.model_interface
                model_interface.set_api_key(api_key) # 需要在ModelInterface中新增此方法
                model_interface.set_model('transcription', transcription_model)
                model_interface.set_model('analysis', analysis_model)
                model_interface.set_model('proposal', proposal_model)
                model_interface.initialize_genai() # 需要在ModelInterface中新增此方法
                st.session_state.model_initialized = True
                st.success("配置成功！现在可以使用其他功能了。")
            except Exception as e:
                st.session_state.model_initialized = False
                st.error(f"配置失败，请检查API Key是否正确: {e}")
        else:
            st.error("核心模型接口未加载，请刷新页面重试。")