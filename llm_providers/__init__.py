# ==============================================================================
# File: core/llm_providers/__init__.py (新增文件)
# ==============================================================================
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/core/llm_providers/__init__.py
功能说明: 初始化llm_providers包，使其可以被Python解释器识别和导入。
          同时，为了方便外部调用，这里直接导出了包内的核心Provider类。
作者: SmartProposal Team
创建日期: 2025-06-29
版本: 1.0.0
"""

# 导入基类，使其可以在包级别访问
from .base_provider import BaseProvider

# 导入具体的提供商实现类
from .gemini_provider import GeminiProvider
from .qwen_provider import QwenProvider

# 定义 __all__，明确指定从该包中 "from core.llm_providers import *" 时会导入哪些模块。
# 这是一种良好的编程习惯，可以控制包的公共API。
__all__ = [
    'BaseProvider',
    'GeminiProvider',
    'QwenProvider'
]