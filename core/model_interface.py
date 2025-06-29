#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/core/model_interface.py
功能说明: 统一的AI模型接口，封装Gemini API调用
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

import os
import sys
import time
import configparser
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path

import google.generativeai as genai

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ModelConfig:
    """模型配置类"""
    
    def __init__(self, api_name: str, display_name: str, 
                 input_price: float, output_price: float):
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
    1. 统一的模型调用接口
    2. 自动重试和错误处理
    3. Token使用量统计
    4. 费用计算
    5. 模型切换支持
    
    使用示例:
        model = ModelInterface()
        response, stats = model.generate_content(prompt, model_type='analysis')
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化模型接口
        
        Args:
            config_path: 配置文件路径，默认使用项目根目录的配置
        """
        self.models = {}
        self.current_models = {}
        self.api_key = None
        self.is_initialized = False
        
        # 加载配置
        self._load_config(config_path)
        self._load_model_config()
        self._initialize_genai()
    
    def _load_config(self, config_path: Optional[str] = None):
        """加载应用配置"""
        if config_path is None:
            # 默认配置文件路径
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'app_config.ini'
            )
        
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        # 获取API密钥
        if self.config.getboolean('API_SETTINGS', 'use_internal_api_key', fallback=False):
            api_key_file = self.config.get('API_SETTINGS', 'api_key_file', fallback='api_key.txt')
            api_key_path = os.path.join(os.path.dirname(config_path), api_key_file)
            
            if os.path.exists(api_key_path):
                with open(api_key_path, 'r') as f:
                    self.api_key = f.read().strip()
            else:
                print(f"警告：API密钥文件 {api_key_path} 不存在")
        else:
            # 从环境变量获取
            self.api_key = os.getenv('GOOGLE_API_KEY')
        
        # 设置默认模型
        self.current_models = {
            'transcription': self.config.get('MODEL_SETTINGS', 'transcription_model', 
                                           fallback='models/gemini-2.5-flash'),
            'analysis': self.config.get('MODEL_SETTINGS', 'analysis_model', 
                                      fallback='models/gemini-2.5-pro'),
            'proposal': self.config.get('MODEL_SETTINGS', 'proposal_model', 
                                      fallback='models/gemini-2.5-pro'),
            'optimization': self.config.get('MODEL_SETTINGS', 'optimization_model',
                                          fallback='models/gemini-2.5-flash')
        }

    def _load_model_config(self):
        """从models.conf加载模型配置"""
        models_conf_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models.conf'
        )

        if not os.path.exists(models_conf_path):
            print(f"警告：模型配置文件 {models_conf_path} 不存在")
            self._use_default_models()
            return

        try:
            with open(models_conf_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith('#'):
                        continue

                    # 解析配置行
                    parts = [part.strip() for part in line.split(',')]
                    if len(parts) >= 4:
                        try:
                            api_name = parts[0]
                            display_name = parts[1]
                            input_price = float(parts[2])
                            output_price = float(parts[3])

                            self.models[api_name] = ModelConfig(
                                api_name, display_name, input_price, output_price
                            )
                        except ValueError as e:
                            print(f"警告：第 {line_num} 行配置解析失败: {e}")
                            print(f"  问题行: {line}")
                            continue
                    else:
                        print(f"警告：第 {line_num} 行配置格式不正确，需要4个字段")

            print(f"成功加载 {len(self.models)} 个模型配置")

            if len(self.models) == 0:
                print("警告：没有成功加载任何模型配置，使用默认配置")
                self._use_default_models()

        except Exception as e:
            print(f"加载模型配置失败: {e}")
            self._use_default_models()
    
    def _use_default_models(self):
        """使用默认模型配置"""
        self.models = {
            'models/gemini-2.5-pro': ModelConfig(
                'models/gemini-2.5-pro',
                'Gemini 2.5 Pro (最强, 推荐)',
                1.25, 10.00
            ),
            'models/gemini-2.5-flash': ModelConfig(
                'models/gemini-2.5-flash',
                'Gemini 2.5 Flash (音频优化)',
                1.00, 2.50
            ),
            'models/gemini-1.5-pro-latest': ModelConfig(
                'models/gemini-1.5-pro-latest',
                'Gemini 1.5 Pro (经典旗舰)',
                1.25, 5.00
            ),
            'models/gemini-1.5-flash-latest': ModelConfig(
                'models/gemini-1.5-flash-latest',
                'Gemini 1.5 Flash (高性价比)',
                0.075, 0.30
            )
        }
    
    def _initialize_genai(self):
        """初始化Google Generative AI"""
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.is_initialized = True
        else:
            print("警告：未配置API密钥，某些功能可能无法使用")
    
    def get_model_name(self, model_type: str) -> str:
        """
        获取指定类型的模型名称
        
        Args:
            model_type: 模型类型 (transcription/analysis/proposal/optimization)
        
        Returns:
            str: 模型API名称
        """
        return self.current_models.get(model_type, 'models/gemini-2.5-flash')
    
    def set_model(self, model_type: str, model_name: str) -> bool:
        """
        设置特定类型使用的模型
        
        Args:
            model_type: 模型类型
            model_name: 模型名称
        
        Returns:
            bool: 设置是否成功
        """
        if model_name in self.models:
            self.current_models[model_type] = model_name
            return True
        return False
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """
        获取所有可用的模型列表
        
        Returns:
            List[Dict]: 模型信息列表
        """
        return [
            {
                'api_name': model.api_name,
                'display_name': model.display_name,
                'input_price': model.input_price_per_million,
                'output_price': model.output_price_per_million
            }
            for model in self.models.values()
        ]
    
    def generate_content(self,
                        prompt: Union[str, List],
                        model_type: str = 'analysis',
                        generation_config: Optional[Dict] = None,
                        safety_settings: Optional[List] = None,
                        request_options: Optional[Dict] = None,
                        retry_count: int = 0,
                        max_retries: int = 3) -> Tuple[str, Dict[str, Any]]:
        """
        生成内容的统一接口
        
        Args:
            prompt: 提示词或包含提示词和文件的列表
            model_type: 模型类型
            generation_config: 生成配置
            safety_settings: 安全设置
            request_options: 请求选项
            retry_count: 当前重试次数
            max_retries: 最大重试次数
        
        Returns:
            (response_text, statistics): 响应文本和统计信息
        """
        if not self.is_initialized:
            raise RuntimeError("ModelInterface未正确初始化，请检查API密钥配置")
        
        start_time = time.time()
        model_name = self.get_model_name(model_type)
        
        try:
            # 获取模型实例
            model = genai.GenerativeModel(model_name)
            
            # 默认生成配置
            if generation_config is None:
                generation_config = {
                    'temperature': 0.7,
                    'top_p': 0.95,
                    'max_output_tokens': 16384,
                    'response_mime_type': 'text/plain'
                }
            
            # 默认安全设置
            if safety_settings is None:
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
                ]
            
            # 默认请求选项
            if request_options is None:
                request_options = {"timeout": 900}  # 15分钟超时
            
            # 生成内容
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings,
                request_options=request_options
            )
            
            # 提取响应文本
            response_text = response.text
            
            # 计算Token使用量
            # 注意：实际的token计数需要从response对象中获取
            # 这里使用估算值
            input_tokens = self._estimate_tokens(str(prompt))
            output_tokens = self._estimate_tokens(response_text)
            total_tokens = input_tokens + output_tokens
            
            # 计算费用
            cost = self.calculate_cost(input_tokens, output_tokens, model_type)
            
            # 构建统计信息
            statistics = {
                'model_used': model_name,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'estimated_cost': cost,
                'generation_time': time.time() - start_time,
                'model_type': model_type
            }
            
            return response_text, statistics
            
        except Exception as e:
            # 错误处理和重试逻辑
            error_msg = str(e)
            
            # 判断是否需要重试
            if retry_count < max_retries and self._should_retry(error_msg):
                wait_time = 2 ** retry_count  # 指数退避
                print(f"请求失败，{wait_time}秒后重试... (尝试 {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
                
                return self.generate_content(
                    prompt, model_type, generation_config,
                    safety_settings, request_options,
                    retry_count + 1, max_retries
                )
            
            # 无法重试，返回错误
            raise Exception(f"模型调用失败: {error_msg}")
    
    def _should_retry(self, error_msg: str) -> bool:
        """判断错误是否应该重试"""
        retry_keywords = [
            'rate limit',
            'quota exceeded',
            'timeout',
            'temporary',
            'unavailable',
            '429',  # Too Many Requests
            '503',  # Service Unavailable
            '504'   # Gateway Timeout
        ]
        
        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in retry_keywords)
    
    def _estimate_tokens(self, text: Union[str, Any]) -> int:
        """
        估算文本的token数量
        
        简单估算：平均每个字符约0.5个token（英文），中文约1个token
        """
        if not isinstance(text, str):
            text = str(text)
        
        # 简单的估算逻辑
        # 可以根据需要使用更精确的tokenizer
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(text) - chinese_chars
        
        estimated_tokens = chinese_chars + (other_chars * 0.5)
        return int(estimated_tokens)
    
    def calculate_cost(self, 
                      input_tokens: int, 
                      output_tokens: int,
                      model_type: str) -> float:
        """
        计算API调用成本
        
        Args:
            input_tokens: 输入token数
            output_tokens: 输出token数
            model_type: 模型类型
        
        Returns:
            float: 预估成本（美元）
        """
        model_name = self.get_model_name(model_type)
        model_config = self.models.get(model_name)
        
        if model_config:
            return model_config.calculate_cost(input_tokens, output_tokens)
        
        # 如果找不到模型配置，使用默认价格
        default_input_price = 1.0
        default_output_price = 2.0
        
        input_cost = (input_tokens / 1_000_000) * default_input_price
        output_cost = (output_tokens / 1_000_000) * default_output_price
        
        return input_cost + output_cost
    
    def count_tokens(self, text: str, model_type: str = 'analysis') -> int:
        """
        精确计算文本的token数量
        
        Args:
            text: 要计算的文本
            model_type: 模型类型
        
        Returns:
            int: token数量
        """
        if not self.is_initialized:
            # 如果未初始化，返回估算值
            return self._estimate_tokens(text)
        
        try:
            model_name = self.get_model_name(model_type)
            model = genai.GenerativeModel(model_name)
            
            # 使用模型的count_tokens方法
            result = model.count_tokens(text)
            return result.total_tokens
            
        except Exception as e:
            print(f"Token计算失败，使用估算值: {e}")
            return self._estimate_tokens(text)
    
    def check_content_safety(self, text: str) -> Dict[str, Any]:
        """
        检查内容安全性
        
        Args:
            text: 要检查的文本
        
        Returns:
            Dict: 安全检查结果
        """
        # TODO: 实现内容安全检查
        # 这里提供基础实现
        return {
            'is_safe': True,
            'categories': [],
            'confidence': 1.0
        }
    
    def stream_generate_content(self,
                               prompt: Union[str, List],
                               model_type: str = 'analysis',
                               generation_config: Optional[Dict] = None,
                               callback=None) -> Tuple[str, Dict[str, Any]]:
        """
        流式生成内容（用于实时显示）
        
        Args:
            prompt: 提示词
            model_type: 模型类型
            generation_config: 生成配置
            callback: 回调函数，用于处理每个chunk
        
        Returns:
            (complete_response, statistics): 完整响应和统计信息
        """
        if not self.is_initialized:
            raise RuntimeError("ModelInterface未正确初始化")
        
        start_time = time.time()
        model_name = self.get_model_name(model_type)
        
        try:
            model = genai.GenerativeModel(model_name)
            
            if generation_config is None:
                generation_config = {
                    'temperature': 0.7,
                    'top_p': 0.95,
                    'max_output_tokens': 8192
                }
            
            # 流式生成
            response_stream = model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=True
            )
            
            complete_response = ""
            for chunk in response_stream:
                if chunk.text:
                    complete_response += chunk.text
                    if callback:
                        callback(chunk.text)
            
            # 计算统计信息
            input_tokens = self._estimate_tokens(str(prompt))
            output_tokens = self._estimate_tokens(complete_response)
            cost = self.calculate_cost(input_tokens, output_tokens, model_type)
            
            statistics = {
                'model_used': model_name,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens,
                'estimated_cost': cost,
                'generation_time': time.time() - start_time,
                'model_type': model_type,
                'stream_mode': True
            }
            
            return complete_response, statistics
            
        except Exception as e:
            raise Exception(f"流式生成失败: {str(e)}")
    
    def get_model_info(self, model_type: str) -> Dict[str, Any]:
        """
        获取指定类型模型的详细信息
        
        Args:
            model_type: 模型类型
        
        Returns:
            Dict: 模型详细信息
        """
        model_name = self.get_model_name(model_type)
        model_config = self.models.get(model_name)
        
        if model_config:
            return {
                'api_name': model_config.api_name,
                'display_name': model_config.display_name,
                'input_price_per_million': model_config.input_price_per_million,
                'output_price_per_million': model_config.output_price_per_million,
                'model_type': model_type,
                'is_active': True
            }
        
        return {
            'api_name': model_name,
            'display_name': model_name,
            'model_type': model_type,
            'is_active': False,
            'error': 'Model configuration not found'
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        health_status = {
            'status': 'unknown',
            'api_key_configured': bool(self.api_key),
            'models_loaded': len(self.models),
            'is_initialized': self.is_initialized,
            'errors': []
        }
        
        try:
            # 尝试一个简单的API调用
            if self.is_initialized:
                model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
                response = model.generate_content(
                    "Hello",
                    generation_config={'max_output_tokens': 10}
                )
                health_status['status'] = 'healthy'
                health_status['api_accessible'] = True
            else:
                health_status['status'] = 'unhealthy'
                health_status['errors'].append('Not initialized')
                
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['api_accessible'] = False
            health_status['errors'].append(str(e))
        
        return health_status
