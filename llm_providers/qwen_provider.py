# ==============================================================================
# File: core/llm_providers/qwen_provider.py (新增文件)
# ==============================================================================
# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/core/llm_providers/qwen_provider.py
功能说明: 实现了针对阿里通义千问（Qwen）模型的具体Provider。
          该类使用dashscope SDK，封装了与Qwen模型交互的所有细节，
          包括初始化、内容生成、流式处理、Token计算以及错误处理。
作者: SmartProposal Team
创建日期: 2025-06-29
版本: 1.0.0
"""

import os
import sys
import time
from http import HTTPStatus
from typing import Dict, List, Optional, Tuple, Union, Any

# 动态添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import dashscope
except ImportError:
    # 友好提示，避免在未安装依赖时程序崩溃
    raise ImportError(
        "通义千问的依赖库 'dashscope' 未安装。"
        "请运行 'pip install \"dashscope>=1.16.1\"' 进行安装。"
    )

from .base_provider import BaseProvider


class QwenProvider(BaseProvider):
    """
    针对阿里通义千问（Qwen）模型的LLM Provider实现。
    """

    def __init__(self, api_key: str, max_retries: int = 3):
        """
        初始化QwenProvider。

        Args:
            api_key (str): DashScope的API密钥。
            max_retries (int): API请求失败时的最大重试次数。
        """
        super().__init__(api_key)
        self.max_retries = max_retries

    def initialize(self) -> None:
        """
        配置DashScope API密钥并验证。
        """
        try:
            dashscope.api_key = self.api_key
            # 通过列出模型来验证API Key的有效性
            models = dashscope.Model.list()
            if not models or models.get('data') is None:
                raise ConnectionError("API Key可能无效，无法获取模型列表。")
            self.is_initialized = True
            print("✅ Qwen Provider (DashScope) 初始化成功。")
        except Exception as e:
            self.is_initialized = False
            print(f"❌ Qwen Provider 初始化失败: {e}")
            raise ConnectionError(f"无法配置DashScope API，请检查API Key是否正确。错误: {e}")

    def generate(self,
                 prompt: Union[str, List[Any]],
                 model_name: str,
                 generation_config: Optional[Dict[str, Any]] = None,
                 safety_settings: Optional[List[Dict[str, Any]]] = None,  # Qwen暂不直接使用此格式的safety_settings
                 request_options: Optional[Dict[str, Any]] = None
                 ) -> Tuple[str, Dict[str, Any]]:
        """
        使用Qwen模型生成内容（非流式）。
        """
        if not self.is_initialized:
            raise RuntimeError("Qwen Provider尚未初始化。")

        # Qwen API通常需要一个字符串prompt，我们将列表转换为字符串
        if isinstance(prompt, list):
            prompt = "\n".join(str(p) for p in prompt)

        return self._generate_with_retry(
            prompt, model_name, generation_config, request_options, retry_count=0
        )

    def _generate_with_retry(self,
                             prompt: str,
                             model_name: str,
                             generation_config: Optional[Dict[str, Any]],
                             request_options: Optional[Dict[str, Any]],
                             retry_count: int) -> Tuple[str, Dict[str, Any]]:
        """内部方法，包含重试逻辑的生成实现。"""
        try:
            # 合并和准备参数
            final_gen_config = generation_config or {}
            timeout = request_options.get('timeout', 600) if request_options else 600

            response = dashscope.Generation.call(
                model=model_name,
                prompt=prompt,
                stream=False,
                timeout=timeout,
                **final_gen_config
            )

            if response.status_code == HTTPStatus.OK:
                response_text = response.output.text
                stats = {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                }
                return response_text, stats
            else:
                # API返回非200状态码
                raise Exception(f"API Error: {response.code} - {response.message}")

        except Exception as e:
            error_msg = str(e)
            if retry_count < self.max_retries and self._should_retry(error_msg):
                wait_time = 2 ** retry_count
                print(f"Qwen请求失败，{wait_time}秒后重试... (尝试 {retry_count + 1}/{self.max_retries})")
                time.sleep(wait_time)
                return self._generate_with_retry(
                    prompt, model_name, generation_config, request_options, retry_count + 1
                )
            # 重试次数用尽或遇到不可重试错误
            raise Exception(f"模型调用失败: {error_msg}")

    def stream_generate(self,
                        prompt: Union[str, List[Any]],
                        model_name: str,
                        generation_config: Optional[Dict[str, Any]] = None,
                        callback: Optional[callable] = None
                        ) -> Tuple[str, Dict[str, Any]]:
        """
        使用Qwen模型流式生成内容。
        """
        if not self.is_initialized:
            raise RuntimeError("Qwen Provider尚未初始化。")

        if isinstance(prompt, list):
            prompt = "\n".join(str(p) for p in prompt)

        try:
            final_gen_config = generation_config or {}
            response_stream = dashscope.Generation.call(
                model=model_name,
                prompt=prompt,
                stream=True,
                **final_gen_config
            )

            complete_response = ""
            last_chunk = None
            for chunk in response_stream:
                if chunk.status_code == HTTPStatus.OK:
                    partial_text = chunk.output.text
                    # dashscope流式返回的是累积文本，需要取增量部分
                    new_text = partial_text[len(complete_response):]
                    complete_response = partial_text

                    if callback and new_text:
                        try:
                            callback(new_text)
                        except Exception as cb_e:
                            print(f"流式回调函数执行出错: {cb_e}")
                    last_chunk = chunk
                else:
                    raise Exception(f"流式API错误: {chunk.code} - {chunk.message}")

            if last_chunk:
                stats = {
                    'input_tokens': last_chunk.usage.input_tokens,
                    'output_tokens': last_chunk.usage.output_tokens
                }
            else:
                # 如果流为空，则估算
                stats = {
                    'input_tokens': self._estimate_tokens(prompt),
                    'output_tokens': 0
                }

            return complete_response, stats

        except Exception as e:
            raise Exception(f"流式生成失败: {str(e)}")

    def count_tokens(self, text: str, model_name: str) -> int:
        """
        使用DashScope API计算文本的token数量。
        """
        if not self.is_initialized:
            print("警告: Qwen Provider未初始化，使用估算方法计算token。")
            return self._estimate_tokens(text)

        try:
            response = dashscope.Tokenization.call(
                model=model_name,
                prompt=text
            )
            if response.status_code == HTTPStatus.OK:
                return response.usage.prompt_tokens
            else:
                print(f"调用DashScope API计算Token失败: {response.message}，使用估算值。")
                return self._estimate_tokens(text)
        except Exception as e:
            print(f"调用DashScope API计算Token时发生异常: {e}，使用估算值。")
            return self._estimate_tokens(text)

    def _should_retry(self, error_msg: str) -> bool:
        """判断错误是否应该重试"""
        # DashScope 常见的可重试错误码或信息
        retry_keywords = [
            'throttling', 'qps rate-limit', 'service is unavailable', 'timeout',
            'serviceunavailable', 'systemerror', 'internalservererror',
            '503', '504'
        ]
        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in retry_keywords)

    def _estimate_tokens(self, text: Union[str, Any]) -> int:
        """后备方法：估算文本的token数量"""
        if not isinstance(text, str):
            text = str(text)

        # Qwen的分词对中文更友好，简单估算可以认为1个汉字约等于1个token
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(text) - chinese_chars
        # 其他字符（英文、数字、符号）大致按每4个字符1个token估算
        estimated_tokens = chinese_chars + (other_chars // 4)
        return int(estimated_tokens) + 1


# 模块独立测试代码
if __name__ == "__main__":
    print("这是一个具体的Provider实现文件，不应直接运行。")
    print("请通过 ModelInterface 来调用。")