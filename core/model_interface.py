# ==============================================================================
# File: core/model_interface.py (修改后)
# ==============================================================================
# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/core/model_interface.py
功能说明: 统一的AI模型接口，通过调度不同的Provider，封装多提供商（如Gemini, Qwen）的API调用。
          此类作为模型调用的统一入口（Facade Pattern）。
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-29
版本: 1.2.0
"""

import os
import sys
import time
import configparser
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 【修改】导入新的Provider类，不再直接导入任何具体SDK
from llm_providers.base_provider import BaseProvider
from llm_providers.gemini_provider import GeminiProvider
from llm_providers.qwen_provider import QwenProvider


class ModelConfig:
    """模型配置类（保持不变）"""

    def __init__(self, provider: str, api_name: str, display_name: str,
                 input_price: float, output_price: float):
        self.provider = provider
        self.api_name = api_name
        self.display_name = display_name
        self.input_price_per_million = input_price
        self.output_price_per_million = output_price

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """计算使用成本（美元）"""
        input_cost = (input_tokens / 1_000_000) * self.input_price_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_price_per_million
        return input_cost + output_cost


class ModelInterface:
    """
    统一的AI模型接口

    主要功能:
    1. 支持多模型提供商 (Gemini, Qwen等)。
    2. 统一的模型调用接口。
    3. 自动重试和错误处理。
    4. Token使用量统计和费用计算。
    5. 模型动态配置和切换。
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化模型接口。
        """
        self.all_models: Dict[str, ModelConfig] = {}
        self.current_models: Dict[str, str] = {}
        self.api_key: Optional[str] = None
        self.provider: Optional[str] = None
        # 【新增】持有具体的provider实例
        self.provider_client: Optional[BaseProvider] = None
        self.is_initialized = False

        self._load_config(config_path)
        self._load_model_config()

        if self.config.getboolean('API_SETTINGS', 'use_internal_api_key', fallback=False):
            api_key_file = self.config.get('API_SETTINGS', 'api_key_file', fallback='api_key.txt')
            project_root = Path(__file__).parent.parent
            api_key_path = project_root / api_key_file

            if api_key_path.exists():
                with open(api_key_path, 'r', encoding='utf-8') as f:
                    internal_api_key = f.read().strip()
                if internal_api_key:
                    default_provider = self.config.get('MODEL_PROVIDERS', 'default_provider', fallback='Gemini')
                    try:
                        self.initialize_model(internal_api_key, default_provider)
                    except Exception as e:
                        print(f"警告：使用内部密钥初始化失败: {e}")

    def initialize_model(self, api_key: str, provider: str):
        """
        【已重构】使用API Key和提供商来初始化模型。
        """
        if not api_key or not provider:
            self.is_initialized = False
            raise ValueError("API Key和模型提供商不能为空")

        self.api_key = api_key
        self.provider = provider

        try:
            # 根据提供商选择不同的初始化逻辑（工厂模式）
            if self.provider == 'Gemini':
                self.provider_client = GeminiProvider(self.api_key)
            elif self.provider == 'Qwen':
                self.provider_client = QwenProvider(self.api_key)
            else:
                raise NotImplementedError(f"不支持的模型提供商: {self.provider}")

            # 调用具体provider的初始化方法
            self.provider_client.initialize()
            self.is_initialized = True
            print(f"✅ ModelInterface 已使用 {self.provider} 提供商成功初始化。")

        except Exception as e:
            self.is_initialized = False
            self.provider_client = None
            print(f"❌ 模型接口初始化失败: {e}")
            raise ConnectionError(f"无法使用提供的API Key连接到 {self.provider}。请检查Key是否正确以及网络连接。")

    def _load_config(self, config_path: Optional[str] = None):
        """加载应用配置（保持不变）"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'app_config.ini'
            )
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')
        self.current_models = {
            'transcription': self.config.get('MODEL_SETTINGS', 'transcription_model', fallback=''),
            'analysis': self.config.get('MODEL_SETTINGS', 'analysis_model', fallback=''),
            'proposal': self.config.get('MODEL_SETTINGS', 'proposal_model', fallback=''),
            'optimization': self.config.get('MODEL_SETTINGS', 'optimization_model', fallback='')
        }

    def _load_model_config(self):
        """从models.conf加载所有模型配置（保持不变）"""
        models_conf_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models.conf'
        )
        if not os.path.exists(models_conf_path):
            return
        with open(models_conf_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = [part.strip() for part in line.split(',')]
                if len(parts) >= 5:
                    provider, api_name, display_name, input_price, output_price = parts[0], parts[1], parts[2], float(
                        parts[3]), float(parts[4])
                    self.all_models[api_name] = ModelConfig(provider, api_name, display_name, input_price, output_price)

    def get_model_name(self, model_type: str) -> str:
        """获取指定类型的模型名称（保持不变）"""
        return self.current_models.get(model_type, '')

    def set_model(self, model_type: str, model_name: str) -> bool:
        """设置特定类型使用的模型（保持不变）"""
        if model_name in self.all_models:
            self.current_models[model_type] = model_name
            return True
        return False

    def get_available_models(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取可用的模型列表，可按提供商过滤（保持不变）"""
        provider_to_check = provider or self.provider
        if not provider_to_check:
            return []
        available = []
        for model in self.all_models.values():
            if model.provider.lower() == provider_to_check.lower():
                available.append({'api_name': model.api_name, 'display_name': model.display_name})
        return available

    def generate_content(self,
                         prompt: Union[str, List],
                         model_type: str = 'analysis',
                         generation_config: Optional[Dict] = None,
                         safety_settings: Optional[List] = None,
                         request_options: Optional[Dict] = None) -> Tuple[str, Dict[str, Any]]:
        """
        【已重构】生成内容的统一接口，将调用委托给具体的Provider。
        """
        if not self.is_initialized or not self.provider_client:
            raise RuntimeError("ModelInterface未正确初始化，请在主页面设置API密钥。")

        model_name = self.get_model_name(model_type)
        if not model_name:
            raise ValueError(f"未给任务类型 '{model_type}' 配置模型。请在侧边栏设置。")

        start_time = time.time()

        # 将调用委托给具体的provider客户端
        response_text, stats = self.provider_client.generate(
            prompt=prompt,
            model_name=model_name,
            generation_config=generation_config,
            safety_settings=safety_settings,
            request_options=request_options
        )

        end_time = time.time()
        cost = self.calculate_cost(stats.get('input_tokens', 0), stats.get('output_tokens', 0), model_type)

        # 组装最终的、统一格式的统计数据
        final_stats = {
            'model_used': model_name,
            'input_tokens': stats.get('input_tokens', 0),
            'output_tokens': stats.get('output_tokens', 0),
            'total_tokens': stats.get('input_tokens', 0) + stats.get('output_tokens', 0),
            'estimated_cost': cost,
            'generation_time': end_time - start_time,
            'model_type': model_type
        }

        return response_text, final_stats

    def calculate_cost(self, input_tokens: int, output_tokens: int, model_type: str) -> float:
        """计算API调用成本（保持不变）"""
        model_name = self.get_model_name(model_type)
        model_config = self.all_models.get(model_name)
        if model_config:
            return model_config.calculate_cost(input_tokens, output_tokens)
        return 0.0

    def count_tokens(self, text: str, model_type: str = 'analysis') -> int:
        """【已重构】精确计算文本的token数量，委托给Provider。"""
        if not self.is_initialized or not self.provider_client:
            return self._estimate_tokens(text)

        try:
            model_name = self.get_model_name(model_type)
            return self.provider_client.count_tokens(text, model_name)
        except Exception as e:
            print(f"Token计算失败，使用估算值: {e}")
            return self._estimate_tokens(text)

    def _estimate_tokens(self, text: Union[str, Any]) -> int:
        """估算文本的token数量（通用后备方法，保持不变）"""
        if not isinstance(text, str):
            text = str(text)
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(text) - chinese_chars
        estimated_tokens = chinese_chars + (other_chars * 0.5)
        return int(estimated_tokens)

    def stream_generate_content(self,
                                prompt: Union[str, List],
                                model_type: str = 'analysis',
                                generation_config: Optional[Dict] = None,
                                callback=None) -> Tuple[str, Dict[str, Any]]:
        """【已重构】流式生成内容，委托给Provider。"""
        if not self.is_initialized or not self.provider_client:
            raise RuntimeError("ModelInterface未正确初始化")

        start_time = time.time()
        model_name = self.get_model_name(model_type)

        complete_response, stats = self.provider_client.stream_generate(
            prompt, model_name, generation_config, callback
        )

        end_time = time.time()
        cost = self.calculate_cost(stats.get('input_tokens', 0), stats.get('output_tokens', 0), model_type)

        final_stats = {
            'model_used': model_name,
            'input_tokens': stats.get('input_tokens', 0),
            'output_tokens': stats.get('output_tokens', 0),
            'total_tokens': stats.get('input_tokens', 0) + stats.get('output_tokens', 0),
            'estimated_cost': cost,
            'generation_time': end_time - start_time,
            'model_type': model_type,
            'stream_mode': True
        }

        return complete_response, final_stats

    def get_model_info(self, model_type: str) -> Dict[str, Any]:
        """获取指定类型模型的详细信息（保持不变）"""
        model_name = self.get_model_name(model_type)
        model_config = self.all_models.get(model_name)
        if model_config:
            return {
                'api_name': model_config.api_name, 'display_name': model_config.display_name,
                'input_price_per_million': model_config.input_price_per_million,
                'output_price_per_million': model_config.output_price_per_million,
                'model_type': model_type, 'is_active': True
            }
        return {
            'api_name': model_name, 'display_name': model_name, 'model_type': model_type,
            'is_active': False, 'error': 'Model configuration not found'
        }

    def health_check(self) -> Dict[str, Any]:
        """【已重构】健康检查，委托给Provider。"""
        health_status = {
            'status': 'unhealthy', 'api_key_configured': bool(self.api_key),
            'provider': self.provider, 'models_loaded': len(self.all_models),
            'is_initialized': self.is_initialized, 'errors': []
        }

        if self.is_initialized and self.provider_client:
            try:
                provider_health = self.provider_client.health_check()
                health_status.update(provider_health)
                if provider_health.get('status') == 'healthy':
                    health_status['status'] = 'healthy'
                else:
                    health_status['errors'].append(provider_health.get('reason', 'Provider health check failed.'))
            except Exception as e:
                health_status['status'] = 'unhealthy'
                health_status['errors'].append(f"Provider health check raised an exception: {e}")
        else:
            health_status['errors'].append('Not initialized or no provider client.')

        return health_status