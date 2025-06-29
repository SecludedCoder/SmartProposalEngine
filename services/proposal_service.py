#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/services/proposal_service.py
功能说明: 方案生成服务，基于分析结果生成各类商业文档
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-29
版本: 1.0.0
"""
import re
import os
import sys
import time
import json
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime
from pathlib import Path

# 【新增】导入streamlit库以访问session_state
import streamlit as st

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base_service import BaseService, ProcessingResult
from services.document_service import DocumentService
from core.prompt_manager import PromptManager
from core.model_interface import ModelInterface
from utils.format_utils import clean_text, format_timestamp, format_money


class ProposalService(BaseService):
    """
    方案生成服务

    主要功能:
    1. 基于分析结果生成方案
    2. 支持多种方案模板
    3. 整合企业能力文档（可选）
    4. 生成专业格式的输出文档

    使用示例:
        service = ProposalService()
        result = service.process(
            analysis_report,
            template='project_proposal',
            options={'capability_docs': ['company_intro.docx']}
        )
    """

    # 预定义的方案类型
    PROPOSAL_TYPES = {
        'project_proposal': {
            'name': '项目建议书',
            'description': '完整的项目实施方案，包含背景、方案、计划、预算等',
            'sections': ['执行摘要', '需求分析', '解决方案', '实施计划', '投资回报', '团队介绍', '商务条款']
        },
        'quotation_proposal': {
            'name': '商务报价方案',
            'description': '详细的服务报价单，包含项目明细和价格',
            'sections': ['方案概述', '服务内容', '报价明细', '付款方式', '服务承诺']
        },
        'solution_brief': {
            'name': '解决方案简报',
            'description': '简洁的方案说明，适合快速展示',
            'sections': ['问题陈述', '解决方案', '实施步骤', '预期效果']
        },
        'meeting_minutes': {
            'name': '会议纪要及行动计划',
            'description': '会议总结和后续行动安排',
            'sections': ['会议概要', '讨论要点', '决策事项', '行动计划', '后续安排']
        },
        'technical_proposal': {
            'name': '技术方案书',
            'description': '详细的技术实现方案',
            'sections': ['技术背景', '架构设计', '技术选型', '实施方案', '风险评估']
        }
    }

    def __init__(self):
        super().__init__()
        self.prompt_manager = PromptManager()
        # 【修改】不再创建新的ModelInterface实例，而是从session_state获取共享的实例
        self.model_interface = st.session_state.get("model_interface")
        self.document_service = DocumentService()

    def get_available_templates(self) -> List[str]:
        """获取可用的方案模板列表"""
        # 预定义模板
        templates = list(self.PROPOSAL_TYPES.keys())

        # 文件系统中的自定义模板
        custom_templates = self.prompt_manager.list_templates('proposal')

        # 合并并去重
        all_templates = list(set(templates + custom_templates))
        return all_templates

    def get_proposal_type_info(self, proposal_type: str) -> Dict:
        """获取方案类型的详细信息"""
        return self.PROPOSAL_TYPES.get(proposal_type, {})

    def validate_input(self, input_data: Union[str, Dict]) -> bool:
        """验证输入数据"""
        if isinstance(input_data, str):
            # 检查是否是有效的分析报告
            return len(input_data.strip()) > 100
        elif isinstance(input_data, dict):
            # 检查必要字段
            return 'analysis_report' in input_data or 'content' in input_data
        return False

    def process(self,
                input_data: Union[str, Dict],
                template: Optional[str] = 'project_proposal',
                options: Optional[Dict] = None) -> ProcessingResult:
        """
        生成商业方案

        Args:
            input_data: 分析报告或包含分析报告的字典
            template: 方案模板名称
            options: 生成选项
                - capability_docs: 企业能力文档列表
                - custom_prompt: 自定义提示词
                - include_pricing: 是否包含报价
                - language: 语言（'zh', 'en'）
                - format: 输出格式（'markdown', 'text'）
                - client_info: 客户信息
                - progress_callback: 进度回调函数

        Returns:
            ProcessingResult: 生成的方案
        """
        start_time = time.time()
        options = options or {}
        progress_callback = options.get('progress_callback')

        # 【新增】在处理开始时，再次确认model_interface实例存在且已初始化
        if not self.model_interface or not self.model_interface.is_initialized:
            return ProcessingResult(
                content='',
                metadata={'error': "Model interface not properly initialized."},
                source_type='proposal',
                processing_time=time.time() - start_time,
                model_used='',
                tokens_consumed={},
                error="模型接口未初始化。请返回主页设置API Key。"
            )

        try:
            # 提取分析报告内容
            if isinstance(input_data, str):
                analysis_report = input_data
                metadata = {}
            else:
                analysis_report = input_data.get('analysis_report') or input_data.get('content', '')
                metadata = input_data.get('metadata', {})

            if not self.validate_input(analysis_report):
                raise ValueError("分析报告内容太短或格式不正确")

            if progress_callback:
                progress_callback("正在准备生成方案...")

            # 处理企业能力文档
            capability_content = ""
            if options.get('capability_docs'):
                capability_content = self._process_capability_docs(
                    options['capability_docs'],
                    progress_callback
                )

            # 获取生成提示词
            if options.get('custom_prompt'):
                # 使用自定义提示词
                generation_prompt = options['custom_prompt']
                # 替换变量
                generation_prompt = generation_prompt.replace('{analysis_report}', analysis_report)
                if capability_content:
                    generation_prompt = generation_prompt.replace('{capability_docs}', capability_content)
            else:
                # 使用模板
                try:
                    # 准备模板变量
                    template_vars = {
                        'analysis_report': analysis_report,
                        'capability_docs': capability_content,
                        'proposal_type_info': self.get_proposal_type_info(template),
                        'client_info': options.get('client_info', {}),
                        'include_pricing': options.get('include_pricing', False),
                        'language': options.get('language', 'zh')
                    }

                    generation_prompt = self.prompt_manager.get_template(
                        'proposal',
                        template,
                        variables=template_vars
                    )
                except Exception as e:
                    # 如果模板不存在，使用默认模板
                    print(f"模板 {template} 加载失败，使用默认模板: {e}")
                    generation_prompt = self._get_default_prompt(
                        analysis_report,
                        template,
                        capability_content,
                        options
                    )

            if progress_callback:
                progress_callback("正在调用 AI 模型生成方案...")

            # 调用模型生成方案
            response, stats = self.model_interface.generate_content(
                generation_prompt,
                model_type='proposal',
                generation_config={
                    'temperature': 0.7,
                    'top_p': 0.95,
                    'max_output_tokens': 16384
                },
                request_options={"timeout": 1200}  # 20分钟超时
            )

            # 处理输出格式
            proposal_content = self._format_proposal(
                response,
                template,
                options.get('format', 'markdown')
            )

            # 添加版权和生成信息
            proposal_content = self._add_footer(proposal_content, template)

            if progress_callback:
                progress_callback(f"方案生成完成，耗时 {time.time() - start_time:.1f} 秒")

            # 构建完整的元数据
            result_metadata = {
                'proposal_type': template,
                'proposal_name': self.PROPOSAL_TYPES.get(template, {}).get('name', template),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'has_capability_docs': bool(capability_content),
                'output_format': options.get('format', 'markdown'),
                'generation_time': time.time() - start_time,
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

            # 添加内容统计
            result_metadata.update(self._analyze_proposal(proposal_content))

            processing_time = time.time() - start_time

            return ProcessingResult(
                content=proposal_content,
                metadata=result_metadata,
                source_type='proposal',
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
                progress_callback(f"方案生成失败：{e}")

            processing_time = time.time() - start_time

            return ProcessingResult(
                content='',
                metadata={
                    'error': str(e),
                    'proposal_type': template,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                source_type='proposal',
                processing_time=processing_time,
                model_used='',
                tokens_consumed={},
                error=str(e)
            )

    def _process_capability_docs(self,
                                 doc_paths: List[Union[str, Path]],
                                 progress_callback=None) -> str:
        """处理企业能力文档"""
        capability_parts = []

        for i, doc_path in enumerate(doc_paths):
            if progress_callback:
                progress_callback(f"正在处理能力文档 {i + 1}/{len(doc_paths)}")

            # 使用文档服务处理文档
            result = self.document_service.process(doc_path)

            if result.is_success:
                doc_name = Path(doc_path).name
                capability_parts.append(f"## 文档：{doc_name}\n\n{result.content}")
            else:
                print(f"处理能力文档失败 {doc_path}: {result.error}")

        if capability_parts:
            return "\n\n---\n\n".join(capability_parts)

        return ""

    def _get_default_prompt(self,
                            analysis_report: str,
                            template: str,
                            capability_content: str,
                            options: Dict) -> str:
        """获取默认的方案生成提示词"""
        proposal_info = self.get_proposal_type_info(template)
        proposal_name = proposal_info.get('name', '商业方案')
        sections = proposal_info.get('sections', [])

        # 构建能力文档部分
        capability_section = ""
        if capability_content:
            capability_section = f"""
## 三、企业能力参考

请参考以下企业能力信息，在方案中适当引用和体现我们的优势：

{capability_content}
"""

        return f"""# {proposal_name}生成任务

## 一、角色定位
你是一位资深的商业方案撰写专家，拥有15年的方案策划经验，擅长将复杂的技术和业务需求转化为清晰、有说服力的商业文档。

## 二、任务说明
基于以下分析报告，生成一份专业的{proposal_name}。

### 分析报告：
{analysis_report}

{capability_section}

## 四、方案结构要求

请按照以下结构生成方案：
{chr(10).join(f'{i + 1}. {section}' for i, section in enumerate(sections))}

## 五、写作要求

1. **专业性**：使用专业的商业语言，逻辑清晰，论述严谨
2. **针对性**：紧密结合客户需求，提供定制化的解决方案
3. **可读性**：结构清晰，重点突出，便于快速理解
4. **说服力**：突出价值主张，用数据和案例支撑观点
5. **完整性**：涵盖所有必要的商业要素，形成完整的方案体系

## 六、格式要求

- 使用Markdown格式
- 标题层级清晰（最多使用三级标题）
- 重要内容使用加粗或列表突出
- 数据使用表格展示
- 保持专业的版式风格

请开始生成{proposal_name}："""

    def _format_proposal(self, raw_content: str, template: str, output_format: str) -> str:
        """格式化方案内容"""
        if output_format == 'markdown':
            # 确保是规范的Markdown格式
            if not raw_content.startswith('#'):
                proposal_name = self.PROPOSAL_TYPES.get(template, {}).get('name', '商业方案')
                raw_content = f"# {proposal_name}\n\n{raw_content}"

            # 清理多余的空行
            lines = raw_content.split('\n')
            formatted_lines = []
            empty_count = 0

            for line in lines:
                if line.strip() == '':
                    empty_count += 1
                    if empty_count <= 2:  # 最多保留两个连续空行
                        formatted_lines.append(line)
                else:
                    empty_count = 0
                    formatted_lines.append(line)

            return '\n'.join(formatted_lines)

        elif output_format == 'text':
            # 转换为纯文本格式
            # 移除Markdown标记
            text = raw_content
            # 移除标题标记
            text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
            # 移除加粗
            text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
            # 移除其他Markdown元素
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

            return text

        return raw_content

    def _add_footer(self, content: str, template: str) -> str:
        """添加页脚信息"""
        footer = f"""

---

*本方案由 SmartProposal Engine 自动生成*  
*生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}*  
*方案类型：{self.PROPOSAL_TYPES.get(template, {}).get('name', template)}*  
*版权所有 © 2025 SmartProposal Team*
"""
        return content + footer

    def _analyze_proposal(self, content: str) -> Dict[str, Any]:
        """分析方案内容，提取统计信息"""
        # 字数统计
        word_count = len(content.split())
        char_count = len(content)

        # 段落和章节统计
        lines = content.split('\n')
        section_count = sum(1 for line in lines if line.strip().startswith('#'))
        paragraph_count = len([p for p in content.split('\n\n') if p.strip()])

        # 特殊元素统计
        table_count = content.count('|---')  # 简单的表格检测
        list_count = sum(1 for line in lines if line.strip().startswith(('- ', '* ', '1. ')))

        # 预估阅读时间（假设每分钟阅读200个中文字）
        estimated_reading_time = max(1, char_count // 400)

        return {
            'word_count': word_count,
            'character_count': char_count,
            'section_count': section_count,
            'paragraph_count': paragraph_count,
            'table_count': table_count,
            'list_count': list_count,
            'estimated_reading_time_minutes': estimated_reading_time
        }

    def generate_proposal(self,
                          analysis_report: str,
                          proposal_type: str = 'project_proposal',
                          capability_docs: Optional[List[str]] = None,
                          progress_callback=None) -> Tuple[str, Dict[str, Any]]:
        """
        生成方案（兼容旧接口）

        Args:
            analysis_report: 分析报告
            proposal_type: 方案类型
            capability_docs: 能力文档列表
            progress_callback: 进度回调

        Returns:
            (proposal_content, stats): 方案内容和统计信息
        """
        result = self.process(
            analysis_report,
            template=proposal_type,
            options={
                'capability_docs': capability_docs,
                'progress_callback': progress_callback
            }
        )

        if result.error:
            return f"方案生成失败：{result.error}", {
                'error': result.error,
                'generation_time': result.processing_time
            }

        stats = {
            'generation_time': result.processing_time,
            'input_tokens': result.tokens_consumed.get('input', 0),
            'output_tokens': result.tokens_consumed.get('output', 0),
            'model_used': result.model_used,
            'proposal_type': result.metadata.get('proposal_type', ''),
            'word_count': result.metadata.get('word_count', 0)
        }

        return result.content, stats

    def merge_capability_docs(self, doc_paths: List[Union[str, Path]]) -> str:
        """
        合并企业能力文档

        Args:
            doc_paths: 文档路径列表

        Returns:
            str: 合并后的内容
        """
        return self._process_capability_docs(doc_paths)

    def customize_proposal(self,
                           base_proposal: str,
                           customization_options: Dict[str, Any]) -> str:
        """
        定制化方案

        Args:
            base_proposal: 基础方案
            customization_options: 定制选项
                - client_name: 客户名称
                - project_name: 项目名称
                - special_requirements: 特殊要求
                - pricing_info: 报价信息

        Returns:
            str: 定制化后的方案
        """
        customized = base_proposal

        # 替换客户名称
        if 'client_name' in customization_options:
            customized = customized.replace(
                '[客户名称]',
                customization_options['client_name']
            )
            customized = customized.replace(
                '[CLIENT_NAME]',
                customization_options['client_name']
            )

        # 替换项目名称
        if 'project_name' in customization_options:
            customized = customized.replace(
                '[项目名称]',
                customization_options['project_name']
            )

        # 添加特殊要求
        if 'special_requirements' in customization_options:
            requirements = customization_options['special_requirements']
            if isinstance(requirements, list):
                requirements_text = '\n'.join(f"- {req}" for req in requirements)
                customized = customized.replace(
                    '[特殊要求]',
                    requirements_text
                )

        # 添加报价信息
        if 'pricing_info' in customization_options:
            pricing = customization_options['pricing_info']
            if isinstance(pricing, dict):
                total_price = pricing.get('total', 0)
                currency = pricing.get('currency', '¥')
                customized = customized.replace(
                    '[总价]',
                    format_money(total_price, currency)
                )

        return customized

    def export_proposal(self,
                        proposal_content: str,
                        export_format: str = 'markdown',
                        file_path: Optional[Union[str, Path]] = None) -> str:
        """
        导出方案到文件

        Args:
            proposal_content: 方案内容
            export_format: 导出格式 ('markdown', 'txt', 'json')
            file_path: 文件路径（如果为None则自动生成）

        Returns:
            str: 导出的文件路径
        """
        if file_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"proposal_{timestamp}.{export_format}"
            file_path = os.path.join('output', file_name)

        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if export_format == 'json':
            # 导出为JSON格式（包含元数据）
            export_data = {
                'content': proposal_content,
                'metadata': {
                    'exported_at': datetime.now().isoformat(),
                    'format': export_format,
                    'engine': 'SmartProposal Engine',
                    'version': '1.0.0'
                }
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
        else:
            # 导出为文本格式
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(proposal_content)

        return str(file_path)

    def get_proposal_outline(self, proposal_type: str) -> List[Dict[str, Any]]:
        """
        获取方案大纲

        Args:
            proposal_type: 方案类型

        Returns:
            List[Dict]: 大纲结构
        """
        proposal_info = self.get_proposal_type_info(proposal_type)
        sections = proposal_info.get('sections', [])

        outline = []
        for i, section in enumerate(sections):
            outline.append({
                'level': 1,
                'title': section,
                'number': f"{i + 1}",
                'description': self._get_section_description(proposal_type, section)
            })

        return outline

    def _get_section_description(self, proposal_type: str, section: str) -> str:
        """获取章节描述"""
        # 这里可以扩展为从配置或模板中读取详细描述
        descriptions = {
            '执行摘要': '项目的核心价值和关键要点概述',
            '需求分析': '深入理解客户需求和业务挑战',
            '解决方案': '针对性的技术和业务解决方案',
            '实施计划': '详细的项目实施步骤和时间安排',
            '投资回报': '项目的成本效益分析和ROI计算',
            '团队介绍': '项目团队的专业背景和成功经验',
            '商务条款': '合作条款、付款方式和服务承诺'
        }

        return descriptions.get(section, f'{section}的详细内容')