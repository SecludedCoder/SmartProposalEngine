# ==============================================================================
# File: core/llm_providers/base_provider.py (修改后)
# ==============================================================================
# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/core/llm_providers/base_provider.py
功能说明: 定义所有LLM（大语言模型）提供商的抽象基类 (ABC)。
          这个基类作为一个接口，确保所有具体的提供商实现（如Gemini, Qwen等）
          都遵循统一的方法签名和行为规范，从而使得ModelInterface可以无缝切换和调度。
作者: SmartProposal Team
创建日期: 2025-06-29
版本: 1.1.0
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Union, Any


class BaseProvider(ABC):
    """
    LLM提供商的抽象基类。
    所有具体的模型提供商都应继承此类并实现其所有抽象方法。
    """

    def __init__(self, api_key: str):
        """
        初始化基础提供商。

        Args:
            api_key (str): 该提供商的API密钥。

        Raises:
            ValueError: 如果API Key为空。
        """
        if not api_key:
            raise ValueError("API Key 不能为空")
        self.api_key = api_key
        self.is_initialized = False

    @abstractmethod
    def initialize(self) -> None:
        """
        初始化提供商的客户端或SDK。
        在子类中实现，例如配置API密钥、设置会话等。
        此方法应在成功初始化后设置 self.is_initialized = True。
        """
        pass

    @abstractmethod
    def generate(self,
                 prompt: Union[str, List[Any]],
                 model_name: str,
                 generation_config: Optional[Dict[str, Any]] = None,
                 safety_settings: Optional[List[Dict[str, Any]]] = None,
                 request_options: Optional[Dict[str, Any]] = None
                 ) -> Tuple[str, Dict[str, Any]]:
        """
        生成内容（非流式）。

        Args:
            prompt (Union[str, List[Any]]): 发送给模型的提示，可以是字符串或内容列表。
            model_name (str): 要使用的具体模型名称。
            generation_config (Optional[Dict[str, Any]]): 生成参数配置。
            safety_settings (Optional[List[Dict[str, Any]]]): 安全设置。
            request_options (Optional[Dict[str, Any]]): 请求选项，如超时。

        Returns:
            Tuple[str, Dict[str, Any]]:
            - 第一个元素是生成的文本内容。
            - 第二个元素是包含统计信息的字典，至少应包含 'input_tokens' 和 'output_tokens'。
        """
        pass

    @abstractmethod
    def stream_generate(self,
                        prompt: Union[str, List[Any]],
                        model_name: str,
                        generation_config: Optional[Dict[str, Any]] = None,
                        callback: Optional[callable] = None
                        ) -> Tuple[str, Dict[str, Any]]:
        """
        流式生成内容。

        Args:
            prompt (Union[str, List[Any]]): 发送给模型的提示。
            model_name (str): 要使用的具体模型名称。
            generation_config (Optional[Dict[str, Any]]): 生成参数配置。
            callback (Optional[callable]): 用于实时处理生成块的回调函数。
                                          回调函数应接收一个参数：(chunk_text: str)。

        Returns:
            Tuple[str, Dict[str, Any]]:
            - 第一个元素是最终生成的完整文本。
            - 第二个元素是包含统计信息的字典，至少应包含 'input_tokens' 和 'output_tokens'。
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str, model_name: str) -> int:
        """
        计算给定文本的token数量。

        Args:
            text (str): 需要计算token的文本。
            model_name (str): 用于计算token的模型名称（不同模型分词方式可能不同）。

        Returns:
            int: token的总数。
        """
        pass

    # --- 新增文件处理相关抽象方法 ---

    @abstractmethod
    def upload_file(self, file_path: str) -> Any:
        """
        上传文件（主要用于音频/视频等多模态输入）。

        Args:
            file_path (str): 本地文件的路径。

        Returns:
            Any: 返回一个代表已上传文件的对象或标识符。
        """
        pass

    @abstractmethod
    def get_file_state(self, file_object: Any) -> str:
        """
        获取已上传文件的状态。

        Args:
            file_object (Any): `upload_file` 返回的文件对象。

        Returns:
            str: 文件的状态字符串 (例如 "PROCESSING", "ACTIVE", "FAILED")。
        """
        pass

    @abstractmethod
    def delete_file(self, file_object: Any) -> None:
        """
        删除已上传的文件。

        Args:
            file_object (Any): `upload_file` 返回的文件对象。
        """
        pass

    def health_check(self) -> Dict[str, Any]:
        """
        对提供商服务进行健康检查。
        子类可以重写此方法以提供更详细的检查。
        """
        if not self.is_initialized:
            return {'status': 'unhealthy', 'reason': 'Provider not initialized.'}
        try:
            return {'status': 'healthy', 'reason': 'Provider is initialized.'}
        except Exception as e:
            return {'status': 'unhealthy', 'reason': f'Health check failed: {str(e)}'}


if __name__ == "__main__":
    print("这是一个抽象基类文件，不应直接运行。")