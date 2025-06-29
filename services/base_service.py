#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/services/base_service.py
功能说明: 所有服务的基类，定义统一接口和数据结构
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
from datetime import datetime


@dataclass
class ProcessingResult:
    """
    统一的处理结果数据结构
    
    所有服务处理后返回的统一格式，确保数据在各模块间顺畅流转
    """
    content: str                          # 主要内容（转录文本、分析报告、方案文档等）
    metadata: Dict[str, Any]              # 元数据（包含处理过程的各种信息）
    source_type: str                      # 来源类型（audio/document/text/analysis/proposal等）
    processing_time: float                # 处理耗时（秒）
    model_used: str                       # 使用的模型名称
    tokens_consumed: Dict[str, int]       # Token消耗统计
    error: Optional[str] = None           # 错误信息（如果有）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化和存储"""
        return {
            'content': self.content,
            'metadata': self.metadata,
            'source_type': self.source_type,
            'processing_time': self.processing_time,
            'model_used': self.model_used,
            'tokens_consumed': self.tokens_consumed,
            'error': self.error,
            'timestamp': datetime.now().isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingResult':
        """从字典创建实例"""
        # 移除timestamp字段（如果存在），因为它不是dataclass的字段
        data_copy = data.copy()
        data_copy.pop('timestamp', None)
        return cls(**data_copy)
    
    @property
    def is_success(self) -> bool:
        """判断处理是否成功"""
        return self.error is None and bool(self.content)
    
    @property
    def total_tokens(self) -> int:
        """获取总Token数"""
        return self.tokens_consumed.get('total', 0)
    
    def get_summary(self) -> str:
        """获取处理结果摘要"""
        if self.error:
            return f"处理失败: {self.error}"
        
        summary_parts = [
            f"来源类型: {self.source_type}",
            f"处理时间: {self.processing_time:.2f}秒",
            f"使用模型: {self.model_used}",
            f"Token消耗: {self.total_tokens}"
        ]
        
        # 添加特定类型的额外信息
        if self.source_type == 'audio' and 'duration' in self.metadata:
            summary_parts.append(f"音频时长: {self.metadata['duration']}")
        elif self.source_type == 'document' and 'page_count' in self.metadata:
            summary_parts.append(f"文档页数: {self.metadata['page_count']}")
        
        return " | ".join(summary_parts)


class BaseService(ABC):
    """
    所有服务的基类
    
    定义了统一的服务接口，确保所有服务遵循相同的处理模式
    主要方法：
    - process(): 主处理方法
    - validate_input(): 输入验证
    - get_available_templates(): 获取可用模板
    - configure(): 服务配置
    - format_result(): 结果格式化
    """
    
    def __init__(self):
        """初始化基础服务"""
        self.config = {}
        self.is_configured = False
        self.service_name = self.__class__.__name__
        self.version = "1.0.0"
    
    @abstractmethod
    def process(self, 
                input_data: Union[str, Dict, bytes],
                template: Optional[str] = None,
                options: Optional[Dict] = None) -> ProcessingResult:
        """
        主处理方法（必须实现）
        
        Args:
            input_data: 输入数据，可以是字符串、字典或字节数据
            template: 使用的模板名称（可选）
            options: 处理选项字典（可选）
                常见选项：
                - progress_callback: 进度回调函数
                - output_format: 输出格式
                - custom_prompt: 自定义提示词
                - additional_context: 额外上下文
        
        Returns:
            ProcessingResult: 统一格式的处理结果
        """
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Union[str, Dict, bytes]) -> bool:
        """
        验证输入数据是否合法（必须实现）
        
        Args:
            input_data: 待验证的输入数据
        
        Returns:
            bool: 验证是否通过
        """
        pass
    
    @abstractmethod
    def get_available_templates(self) -> List[str]:
        """
        获取可用的模板列表（必须实现）
        
        Returns:
            List[str]: 模板名称列表
        """
        pass
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        配置服务
        
        Args:
            config: 配置字典
        """
        self.config.update(config)
        self.is_configured = True
    
    def format_result(self, 
                     content: str,
                     metadata: Dict[str, Any],
                     processing_time: float,
                     model_info: Dict[str, Any],
                     error: Optional[str] = None) -> ProcessingResult:
        """
        格式化处理结果
        
        统一的结果格式化方法，供子类使用
        
        Args:
            content: 处理后的内容
            metadata: 元数据
            processing_time: 处理时间
            model_info: 模型信息（包含model_used和tokens信息）
            error: 错误信息（如果有）
        
        Returns:
            ProcessingResult: 格式化后的结果
        """
        # 确保元数据包含服务信息
        metadata['service_name'] = self.service_name
        metadata['service_version'] = self.version
        
        # 提取模型信息
        model_used = model_info.get('model_used', '')
        tokens_consumed = {
            'input': model_info.get('input_tokens', 0),
            'output': model_info.get('output_tokens', 0),
            'total': model_info.get('total_tokens', 0)
        }
        
        # 添加费用信息（如果有）
        if 'estimated_cost' in model_info:
            metadata['estimated_cost'] = model_info['estimated_cost']
        
        return ProcessingResult(
            content=content,
            metadata=metadata,
            source_type=self._get_source_type(),
            processing_time=processing_time,
            model_used=model_used,
            tokens_consumed=tokens_consumed,
            error=error
        )
    
    def _get_source_type(self) -> str:
        """
        获取服务对应的源类型
        
        子类可以覆盖此方法返回特定的源类型
        """
        # 根据服务名称推断源类型
        service_type_map = {
            'TranscriptionService': 'audio',
            'DocumentService': 'document',
            'AnalysisService': 'analysis',
            'DeepAnalysisService': 'analysis',
            'ProposalService': 'proposal'
        }
        
        return service_type_map.get(self.service_name, 'unknown')
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        获取服务信息
        
        Returns:
            Dict: 包含服务名称、版本、配置状态等信息
        """
        return {
            'name': self.service_name,
            'version': self.version,
            'is_configured': self.is_configured,
            'available_templates': self.get_available_templates(),
            'source_type': self._get_source_type()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        服务健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        try:
            # 尝试验证一个简单的输入
            test_input = "test"
            is_healthy = True
            
            # 检查是否可以获取模板
            templates = self.get_available_templates()
            
            return {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'service': self.service_name,
                'version': self.version,
                'configured': self.is_configured,
                'template_count': len(templates),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'service': self.service_name,
                'version': self.version,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.service_name}(version={self.version}, configured={self.is_configured})"
