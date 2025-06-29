# ==============================================================================
# File: utils/ui_utils.py (已更正)
# ==============================================================================
# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/utils/ui_utils.py
功能说明: 提供与Streamlit UI相关的辅助函数，旨在提升用户体验和代码复用性。
作者: SmartProposal Team
创建日期: 2025-06-29
版本: 1.0.1 (已更正)
"""

import streamlit as st
import configparser
from typing import Optional


def check_api_key_setup():
    """
    检查API Key是否已在会话中配置。

    这是一个"页面守卫"函数，应在每个需要使用AI功能的Streamlit子页面的开头调用。
    它的工作逻辑如下：
    1. 读取 `app_config.ini` 中的 `use_internal_api_key` 设置。
    2. 如果设置为 `true`，则认为系统已配置，函数直接返回。
    3. 如果设置为 `false`，则检查 `st.session_state.api_key_configured` 标志位。
    4. 如果标志位为 `False` 或不存在，说明用户尚未在UI中提供API Key。此时，
       函数会显示一条警告消息，提供一个返回主页的链接，并调用 `st.stop()`
       来终止当前页面的进一步渲染，防止后续代码因模型未初始化而报错。
    """
    # 确保应用的配置已经加载到会话状态中
    if 'config' not in st.session_state or not isinstance(st.session_state.config, configparser.ConfigParser):
        # 如果配置不存在，可能是在应用启动的极早期阶段，直接跳过检查。
        # 这种情况下，主应用`app.py`会处理初始化。
        return

    # 从配置中读取是否使用内部密钥
    use_internal = st.session_state.config.getboolean(
        'API_SETTINGS',
        'use_internal_api_key',
        fallback=False
    )

    # 如果配置为使用内部密钥，则我们假定它总是已配置的。
    # 真正的初始化和状态设置在 app.py 中完成。
    if use_internal:
        return

    # 如果不使用内部密钥，则必须检查用户是否通过UI进行了配置。
    # 'api_key_configured' 这个 session_state 变量在 app.py 中成功初始化模型后被设为 True。
    if not st.session_state.get('api_key_configured'):
        # 如果未配置，显示警告信息
        st.warning("系统未配置，请先在主页面设置您的 API 密钥以使用本功能。")

        # 提供一个返回主页的链接，方便用户操作
        st.page_link("app.py", label="返回主页进行设置", icon="🏠")

        # 停止执行当前页面的其余部分，这是防止后续代码出错的关键
        st.stop()


def display_info_sidebar():
    """
    在侧边栏显示一个标准的信息提示框。
    （这是一个可以根据需要添加的额外UI辅助函数示例）
    """
    with st.sidebar:
        st.info(
            """
            **💡 提示**: 
            - 确保在侧边栏选择了合适的模型。
            - 处理大文件可能需要一些时间。
            - 所有结果都可以导出保存。
            """
        )


# 主程序入口，用于模块独立测试或演示
if __name__ == "__main__":
    st.title("UI Utils - 模块测试")

    st.markdown("这是一个用于测试 `utils/ui_utils.py` 中函数的页面。")
    st.markdown("---")

    st.header("1. 测试 `check_api_key_setup` 函数")
    st.write("请在下方模拟会话状态，然后点击按钮进行测试。")

    # 模拟 session_state
    if 'config' not in st.session_state:
        st.session_state.config = configparser.ConfigParser()
        st.session_state.config.read_string("""
        [API_SETTINGS]
        use_internal_api_key = false
        """)

    if 'api_key_configured' not in st.session_state:
        st.session_state.api_key_configured = False

    st.write("当前模拟状态:")
    st.json({
        'use_internal_api_key': st.session_state.config.getboolean('API_SETTINGS', 'use_internal_api_key'),
        'api_key_configured': st.session_state.get('api_key_configured')
    })

    col1, col2 = st.columns(2)
    with col1:
        if st.button("模拟: API Key 已配置"):
            st.session_state.api_key_configured = True
            st.rerun()
    with col2:
        if st.button("模拟: API Key 未配置"):
            st.session_state.api_key_configured = False
            st.rerun()

    # 直接调用守卫函数。
    # 如果条件满足，它会显示警告并调用 st.stop()，此时下面的 st.success 不会被执行。
    # 如果条件不满足，它会直接通过，然后执行下面的 st.success。
    # 这种方式比捕获内部异常更清晰地演示了函数的行为。
    check_api_key_setup()

    # 只有当 check_api_key_setup() 没有停止脚本时，这行代码才会执行
    st.success("✅ `check_api_key_setup` 检查通过，页面可以继续加载。")