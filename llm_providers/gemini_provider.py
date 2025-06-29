# ==============================================================================
# File: core/llm_providers/gemini_provider.py (新增文件)
# ==============================================================================
# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/core/llm_providers/gemini_provider.py
功能说明: 实现了针对Google Gemini模型的具体Provider。
          该类封装了所有与Gemini API交互的细节，包括初始化、内容生成、
          流式处理、Token计算以及错误处理和重试逻辑。
作者: SmartProposal Team
创建日期: 2025-06-29
版本: 1.0.0
"""

import os
import sys
import time
from typing import Dict, List, Optional, Tuple, Union, Any

# 动态添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import google.generativeai as genai
except ImportError:
    # 友好提示，避免在未安装依赖时程序崩溃
    raise ImportError(
        "Google Gemini的依赖库 'google-generativeai' 未安装。"
        "请运行 'pip install google-generativeai' 进行安装。"
    )

from .base_provider import BaseProvider


class GeminiProvider(BaseProvider):
    """
    针对Google Gemini模型的LLM Provider实现。
    """

    def __init__(self, api_key: str, max_retries: int = 3):
        """
        初始化GeminiProvider。

        Args:
            api_key (str): Google AI Studio的API密钥。
            max_retries (int): API请求失败时的最大重试次数。
        """
        super().__init__(api_key)
        self.max_retries = max_retries

    def initialize(self) -> None:
        """
        配置Gemini API密钥并验证。
        """
        try:
            genai.configure(api_key=self.api_key)
            # 可选：进行一次轻量级的健康检查来确认API Key的有效性
            # 例如，列出模型，这是一个低成本的操作
            models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if not models:
                raise ConnectionError("API Key有效，但未找到可用的生成模型。")
            self.is_initialized = True
            print("✅ Gemini Provider 初始化成功。")
        except Exception as e:
            self.is_initialized = False
            print(f"❌ Gemini Provider 初始化失败: {e}")
            # 重新抛出异常，以便上层可以捕获
            raise ConnectionError(f"无法配置Gemini API，请检查API Key是否正确。错误: {e}")

    def generate(self,
                 prompt: Union[str, List[Any]],
                 model_name: str,
                 generation_config: Optional[Dict[str, Any]] = None,
                 safety_settings: Optional[List[Dict[str, Any]]] = None,
                 request_options: Optional[Dict[str, Any]] = None
                 ) -> Tuple[str, Dict[str, Any]]:
        """
        使用Gemini模型生成内容（非流式）。
        """
        if not self.is_initialized:
            raise RuntimeError("Gemini Provider尚未初始化。")

        return self._generate_with_retry(
            prompt, model_name, generation_config,
            safety_settings, request_options, retry_count=0
        )

    def _generate_with_retry(self,
                             prompt: Union[str, List[Any]],
                             model_name: str,
                             generation_config: Optional[Dict[str, Any]],
                             safety_settings: Optional[List[Dict[str, Any]]],
                             request_options: Optional[Dict[str, Any]],
                             retry_count: int) -> Tuple[str, Dict[str, Any]]:
        """内部方法，包含重试逻辑的生成实现。"""
        try:
            model = genai.GenerativeModel(model_name)

            # 设置默认配置
            final_gen_config = {
                'temperature': 0.7, 'top_p': 0.95,
                'max_output_tokens': 16384, 'response_mime_type': 'text/plain'
            }
            if generation_config:
                final_gen_config.update(generation_config)

            final_safety_settings = safety_settings or [
                {"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in
                ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                 "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
            ]

            final_request_options = {"timeout": 900}
            if request_options:
                final_request_options.update(request_options)

            # 调用API
            response = model.generate_content(
                prompt,
                generation_config=final_gen_config,
                safety_settings=final_safety_settings,
                request_options=final_request_options
            )

            response_text = response.text

            # 优先从API返回的元数据中获取精确的token数
            if hasattr(response, 'usage_metadata'):
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
            else:
                # 如果API未返回，则进行估算
                input_tokens = self._estimate_tokens(str(prompt))
                output_tokens = self._estimate_tokens(response_text)

            stats = {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
            }

            return response_text, stats

        except Exception as e:
            error_msg = str(e)
            if retry_count < self.max_retries and self._should_retry(error_msg):
                wait_time = 2 ** retry_count
                print(f"Gemini请求失败，{wait_time}秒后重试... (尝试 {retry_count + 1}/{self.max_retries})")
                time.sleep(wait_time)
                return self._generate_with_retry(
                    prompt, model_name, generation_config, safety_settings,
                    request_options, retry_count + 1
                )
            # 重试次数用尽或遇到不可重试错误，则直接抛出
            raise Exception(f"模型调用失败: {error_msg}")

    def stream_generate(self,
                        prompt: Union[str, List[Any]],
                        model_name: str,
                        generation_config: Optional[Dict[str, Any]] = None,
                        callback: Optional[callable] = None
                        ) -> Tuple[str, Dict[str, Any]]:
        """
        使用Gemini模型流式生成内容。
        """
        if not self.is_initialized:
            raise RuntimeError("Gemini Provider尚未初始化。")

        try:
            model = genai.GenerativeModel(model_name)
            final_gen_config = {'temperature': 0.7, 'top_p': 0.95, 'max_output_tokens': 16384}
            if generation_config:
                final_gen_config.update(generation_config)

            response_stream = model.generate_content(
                prompt, generation_config=final_gen_config, stream=True
            )

            complete_response = ""
            for chunk in response_stream:
                if chunk.text:
                    complete_response += chunk.text
                    if callback:
                        try:
                            callback(chunk.text)
                        except Exception as cb_e:
                            print(f"流式回调函数执行出错: {cb_e}")

            # 流式传输完成后，从响应对象获取token使用量
            if hasattr(response_stream, 'usage_metadata'):
                input_tokens = response_stream.usage_metadata.prompt_token_count
                output_tokens = response_stream.usage_metadata.candidates_token_count
            else:
                input_tokens = self._estimate_tokens(str(prompt))
                output_tokens = self._estimate_tokens(complete_response)

            stats = {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
            }

            return complete_response, stats
        except Exception as e:
            raise Exception(f"流式生成失败: {str(e)}")

    def count_tokens(self, text: str, model_name: str) -> int:
        """
        使用Gemini API计算文本的token数量。
        """
        if not self.is_initialized:
            print("警告: Gemini Provider未初始化，使用估算方法计算token。")
            return self._estimate_tokens(text)

        try:
            model = genai.GenerativeModel(model_name)
            result = model.count_tokens(text)
            return result.total_tokens
        except Exception as e:
            print(f"调用Gemini API计算Token失败，使用估算值: {e}")
            return self._estimate_tokens(text)

    def _should_retry(self, error_msg: str) -> bool:
        """判断错误是否应该重试"""
        retry_keywords = [
            'rate limit', 'quota exceeded', 'timeout', 'temporary', 'unavailable',
            '503 service unavailable', 'resource has been exhausted',
            '429', '500', '503', '504'
        ]
        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in retry_keywords)

    def _estimate_tokens(self, text: Union[str, Any]) -> int:
        """后备方法：估算文本的token数量"""
        if not isinstance(text, str):
            text = str(text)

        # 一个更通用的估算方法：平均每个字符约0.3个token
        return int(len(text) * 0.3) + 1


# 模块独立测试代码
if __name__ == "__main__":
    print("这是一个具体的Provider实现文件，不应直接运行。")
    print("请通过 ModelInterface 来调用。")