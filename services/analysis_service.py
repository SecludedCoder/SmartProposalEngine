#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/services/analysis_service.py
功能说明: 深度分析服务模块，负责对转录文本进行商业洞察分析
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

import os
import sys
import time
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path

import google.generativeai as genai

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base_service import BaseService, ProcessingResult
from core.prompt_manager import PromptManager
from core.model_interface import ModelInterface


class DeepAnalysisService(BaseService):
    """
    深度分析服务类

    主要功能:
    - 对转录文本进行商业洞察分析
    - 支持多种分析场景模板
    - 支持自定义分析模板
    - 生成结构化的分析报告

    使用示例:
        service = DeepAnalysisService()
        result = service.process(transcript_text, template='customer_interview')
    """

    # 预定义的分析场景
    ANALYSIS_SCENARIOS = {
        'customer_interview': {
            'name': '客户访谈深度分析',
            'description': '适用于客户需求访谈、用户调研等场景',
            'focus_areas': ['需求识别', '痛点分析', '决策链路', '商机评估']
        },
        'business_negotiation': {
            'name': '商务谈判要点分析',
            'description': '适用于商务洽谈、合作协商等场景',
            'focus_areas': ['关键条款', '谈判立场', '利益诉求', '风险点']
        },
        'internal_meeting': {
            'name': '内部会议决策分析',
            'description': '适用于内部讨论、决策会议等场景',
            'focus_areas': ['决策要点', '行动项', '责任分配', '时间节点']
        },
        'requirements_gathering': {
            'name': '需求收集分析',
            'description': '适用于产品需求收集、功能规划等场景',
            'focus_areas': ['功能需求', '非功能需求', '优先级', '实现难度']
        },
        'project_review': {
            'name': '项目复盘分析',
            'description': '适用于项目总结、经验分享等场景',
            'focus_areas': ['成功经验', '问题教训', '改进建议', '最佳实践']
        }
    }

    def __init__(self):
        super().__init__()
        self.prompt_manager = PromptManager()
        self.model_interface = ModelInterface()

    def get_available_templates(self) -> List[str]:
        """获取可用的分析模板列表"""
        # 预定义模板
        templates = list(self.ANALYSIS_SCENARIOS.keys())

        # 文件系统中的自定义模板
        custom_templates = self.prompt_manager.list_templates('analysis')

        # 合并并去重
        all_templates = list(set(templates + custom_templates))
        return all_templates

    def get_scenario_info(self, scenario: str) -> Dict:
        """获取分析场景的详细信息"""
        return self.ANALYSIS_SCENARIOS.get(scenario, {})

    def validate_input(self, input_data: Union[str, Dict]) -> bool:
        """验证输入数据"""
        if isinstance(input_data, str):
            # 验证文本长度
            if len(input_data.strip()) < 50:
                return False
            return True
        elif isinstance(input_data, dict):
            # 验证必要字段
            return 'transcript' in input_data or 'content' in input_data
        return False

    def process(self,
                input_data: Union[str, Dict],
                template: Optional[str] = 'customer_interview',
                options: Optional[Dict] = None) -> ProcessingResult:
        """
        执行深度分析

        Args:
            input_data: 待分析的文本或包含文本的字典
            template: 分析模板名称
            options: 分析选项
                - custom_prompt: 自定义提示词
                - additional_context: 额外的上下文信息
                - output_format: 输出格式 ('markdown', 'json')
                - include_recommendations: 是否包含建议
                - progress_callback: 进度回调函数

        Returns:
            ProcessingResult: 分析结果
        """
        start_time = time.time()
        options = options or {}
        progress_callback = options.get('progress_callback')

        try:
            # 提取文本内容
            if isinstance(input_data, str):
                transcript = input_data
                metadata = {}
            else:
                transcript = input_data.get('transcript') or input_data.get('content', '')
                metadata = input_data.get('metadata', {})

            if not self.validate_input(transcript):
                raise ValueError("输入文本太短或格式不正确")

            if progress_callback:
                progress_callback("正在准备分析...")

            # 获取分析提示词
            if options.get('custom_prompt'):
                # 使用自定义提示词
                analysis_prompt = options['custom_prompt']
                if '{transcript}' in analysis_prompt:
                    analysis_prompt = analysis_prompt.format(transcript=transcript)
                else:
                    # 如果自定义提示词没有占位符，则将文本附加在后面
                    analysis_prompt = f"{analysis_prompt}\n\n### 待分析内容：\n{transcript}"
            else:
                # 使用模板
                try:
                    analysis_prompt = self.prompt_manager.get_template(
                        'analysis',
                        template,
                        variables={
                            'transcript': transcript,
                            'additional_context': options.get('additional_context', ''),
                            'scenario_info': self.get_scenario_info(template)
                        }
                    )
                except Exception as e:
                    # 如果模板不存在，使用默认的客户访谈模板
                    print(f"模板 {template} 加载失败，使用默认模板: {e}")
                    analysis_prompt = self._get_default_prompt(transcript, template)

            if progress_callback:
                progress_callback(f"正在调用 AI 模型进行深度分析...")

            # 调用模型进行分析
            response, stats = self.model_interface.generate_content(
                analysis_prompt,
                model_type='analysis',
                request_options={"timeout": 900}  # 15分钟超时
            )

            # 处理输出格式
            analysis_result = self._format_analysis_result(
                response,
                options.get('output_format', 'markdown')
            )

            if progress_callback:
                progress_callback(f"深度分析完成，耗时 {time.time() - start_time:.1f} 秒")

            # 构建完整的元数据
            result_metadata = {
                'analysis_template': template,
                'analysis_scenario': self.ANALYSIS_SCENARIOS.get(template, {}).get('name', template),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'input_length': len(transcript),
                'analysis_time': time.time() - start_time,
                **metadata  # 保留原始元数据
            }

            # 添加统计信息
            result_metadata.update({
                'input_tokens': stats.get('input_tokens', 0),
                'output_tokens': stats.get('output_tokens', 0),
                'total_tokens': stats.get('total_tokens', 0),
                'model_used': stats.get('model_used', ''),
                'estimated_cost': stats.get('estimated_cost', 0)
            })

            processing_time = time.time() - start_time

            return ProcessingResult(
                content=analysis_result,
                metadata=result_metadata,
                source_type='analysis',
                processing_time=processing_time,
                model_used=stats.get('model_used', ''),
                tokens_consumed={
                    'input': stats.get('input_tokens', 0),
                    'output': stats.get('output_tokens', 0),
                    'total': stats.get('total_tokens', 0)
                }
            )

        except Exception as e:
            if progress_callback:
                progress_callback(f"深度分析失败：{e}")

            processing_time = time.time() - start_time

            return ProcessingResult(
                content='',
                metadata={
                    'error': str(e),
                    'analysis_template': template,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                source_type='analysis',
                processing_time=processing_time,
                model_used='',
                tokens_consumed={},
                error=str(e)
            )

    def _get_default_prompt(self, transcript: str, template: str) -> str:
        """获取默认的分析提示词（当模板加载失败时使用）"""
        scenario_info = self.get_scenario_info(template)
        scenario_name = scenario_info.get('name', '商业分析')
        focus_areas = scenario_info.get('focus_areas', ['关键信息', '主要观点', '行动建议'])

        return f"""# {scenario_name}

## 一、角色定位
你是一位拥有15年经验的资深商业分析师和战略顾问，专精于从对话记录中提取关键洞察并制定可行的商业策略。

## 二、分析任务
请对以下内容进行深度分析，重点关注以下方面：
{chr(10).join(f'- {area}' for area in focus_areas)}

### 待分析内容：
{transcript}

## 三、分析要求

### 3.1 执行摘要
请用200字以内概括核心内容和关键发现。

### 3.2 详细分析
请根据内容特点，从以下维度进行分析：
1. **核心信息提取**：识别并整理关键信息点
2. **深层洞察挖掘**：分析表象背后的深层含义
3. **机会与风险**：识别潜在的机会和需要注意的风险
4. **行动建议**：提供具体可执行的建议

### 3.3 关键要点总结
请列出3-5个最重要的发现和结论。

## 四、输出要求
1. 分析要基于原文事实，避免过度推测
2. 使用专业但易懂的商业语言
3. 提供具体、可执行的建议
4. 保持客观中立的分析视角"""

    def _format_analysis_result(self, raw_result: str, output_format: str) -> str:
        """格式化分析结果"""
        if output_format == 'markdown':
            # 确保输出是规范的Markdown格式
            if not raw_result.startswith('#'):
                raw_result = f"# 分析报告\n\n{raw_result}"
            return raw_result
        elif output_format == 'json':
            # TODO: 实现JSON格式转换
            # 这里暂时返回原始结果
            return raw_result
        else:
            return raw_result

    def analyze_transcript(self,
                           transcript: str,
                           template: str = 'customer_interview',
                           progress_callback=None) -> Tuple[str, Dict[str, any]]:
        """
        分析转录文本（兼容旧接口）

        Args:
            transcript: 转录文本
            template: 分析模板
            progress_callback: 进度回调函数

        Returns:
            (分析结果文本, 统计信息字典)
        """
        result = self.process(
            transcript,
            template=template,
            options={'progress_callback': progress_callback}
        )

        if result.error:
            return f"分析过程中发生错误：{result.error}", {
                'error': result.error,
                'analysis_time': result.processing_time
            }

        stats = {
            'analysis_time': result.processing_time,
            'input_tokens': result.tokens_consumed.get('input', 0),
            'output_tokens': result.tokens_consumed.get('output', 0),
            'model_used': result.model_used,
            'timestamp': result.metadata.get('timestamp', '')
        }

        return result.content, stats

    def batch_analyze(self,
                      documents: List[Dict],
                      template: str = 'customer_interview',
                      options: Optional[Dict] = None) -> List[ProcessingResult]:
        """
        批量分析多个文档

        Args:
            documents: 文档列表，每个文档包含 'id', 'content' 等字段
            template: 分析模板
            options: 分析选项

        Returns:
            List[ProcessingResult]: 分析结果列表
        """
        results = []
        options = options or {}
        progress_callback = options.get('progress_callback')

        for i, doc in enumerate(documents):
            if progress_callback:
                progress_callback(f"正在分析文档 {i + 1}/{len(documents)}: {doc.get('id', 'unknown')}")

            # 为每个文档创建独立的选项
            doc_options = options.copy()
            doc_options['document_id'] = doc.get('id')

            result = self.process(
                doc.get('content', ''),
                template=template,
                options=doc_options
            )

            # 添加文档ID到元数据
            result.metadata['document_id'] = doc.get('id')
            results.append(result)

            # 避免请求过于频繁
            if i < len(documents) - 1:
                time.sleep(2)

        return results

    def compare_analyses(self,
                         analyses: List[ProcessingResult],
                         comparison_prompt: Optional[str] = None) -> ProcessingResult:
        """
        比较多个分析结果，生成综合报告

        Args:
            analyses: 分析结果列表
            comparison_prompt: 自定义比较提示词

        Returns:
            ProcessingResult: 综合比较报告
        """
        start_time = time.time()

        try:
            # 准备比较内容
            comparison_content = "# 多文档分析比较\n\n"
            for i, analysis in enumerate(analyses):
                doc_id = analysis.metadata.get('document_id', f'文档{i + 1}')
                comparison_content += f"## {doc_id}\n\n"
                comparison_content += analysis.content
                comparison_content += "\n\n---\n\n"

            # 构建比较提示词
            if not comparison_prompt:
                comparison_prompt = """请对以上多个分析报告进行综合比较，生成一份整合报告。

要求：
1. 识别共同点和差异点
2. 提取跨文档的关键洞察
3. 综合各文档的发现，形成整体结论
4. 提供基于全局视角的建议

请以结构化的方式呈现比较结果。"""

            full_prompt = f"{comparison_content}\n\n{comparison_prompt}"

            # 调用模型
            response, stats = self.model_interface.generate_content(
                full_prompt,
                model_type='analysis'
            )

            processing_time = time.time() - start_time

            return ProcessingResult(
                content=response,
                metadata={
                    'comparison_type': 'multi_document',
                    'document_count': len(analyses),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'processing_time': processing_time
                },
                source_type='comparison',
                processing_time=processing_time,
                model_used=stats.get('model_used', ''),
                tokens_consumed={
                    'input': stats.get('input_tokens', 0),
                    'output': stats.get('output_tokens', 0),
                    'total': stats.get('total_tokens', 0)
                }
            )

        except Exception as e:
            processing_time = time.time() - start_time
            return ProcessingResult(
                content='',
                metadata={'error': str(e)},
                source_type='comparison',
                processing_time=processing_time,
                model_used='',
                tokens_consumed={},
                error=str(e)
            )

    def extract_action_items(self, analysis_result: ProcessingResult) -> List[Dict]:
        """
        从分析结果中提取行动项

        Args:
            analysis_result: 分析结果

        Returns:
            List[Dict]: 行动项列表
        """
        # TODO: 实现智能提取行动项的逻辑
        # 这里提供一个简单的实现
        action_items = []

        content = analysis_result.content
        lines = content.split('\n')

        in_action_section = False
        for line in lines:
            line = line.strip()
            if '行动' in line and ('建议' in line or '计划' in line or '项' in line):
                in_action_section = True
                continue

            if in_action_section and line:
                # 简单的模式匹配
                if line.startswith(('1.', '2.', '3.', '-', '*', '•')):
                    action_items.append({
                        'description': line.lstrip('1234567890.-*• '),
                        'priority': 'medium',
                        'source': 'auto_extracted'
                    })

        return action_items

    def generate_executive_summary(self,
                                   analysis_result: ProcessingResult,
                                   max_length: int = 500) -> str:
        """
        生成执行摘要

        Args:
            analysis_result: 分析结果
            max_length: 最大长度

        Returns:
            str: 执行摘要
        """
        try:
            prompt = f"""请为以下分析报告生成一份简洁的执行摘要，不超过{max_length}字：

{analysis_result.content}

要求：
1. 突出最关键的发现
2. 明确主要结论
3. 简述核心建议
4. 语言精炼专业"""

            response, _ = self.model_interface.generate_content(
                prompt,
                model_type='analysis'
            )

            return response

        except Exception as e:
            # 如果生成失败，尝试简单提取
            content = analysis_result.content
            if '执行摘要' in content:
                # 尝试提取已有的摘要部分
                start = content.find('执行摘要')
                end = content.find('\n##', start)
                if end == -1:
                    end = start + max_length
                return content[start:end].strip()

            # 返回前面部分作为摘要
            return content[:max_length] + '...' if len(content) > max_length else content