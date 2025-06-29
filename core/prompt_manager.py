#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/core/prompt_manager.py
功能说明: Prompt模板管理器，负责模板的加载、缓存和管理
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

import os
import sys
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import re

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PromptTemplate:
    """Prompt模板类"""
    
    def __init__(self, template_id: str, content: str, 
                 category: str, metadata: Optional[Dict] = None):
        self.template_id = template_id
        self.content = content
        self.category = category
        self.metadata = metadata or {}
        self.load_time = datetime.now()
        self.version = self.metadata.get('version', '1.0.0')
        
        # 解析模板中的变量
        self.variables = self._extract_variables()
    
    def _extract_variables(self) -> List[str]:
        """提取模板中的变量占位符"""
        # 匹配 {variable_name} 格式的占位符
        pattern = r'\{([^}]+)\}'
        variables = re.findall(pattern, self.content)
        return list(set(variables))  # 去重
    
    def render(self, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        渲染模板，替换变量
        
        Args:
            variables: 变量字典
        
        Returns:
            str: 渲染后的内容
        """
        if not variables:
            return self.content
        
        rendered = self.content
        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            rendered = rendered.replace(placeholder, str(var_value))
        
        return rendered
    
    def validate_variables(self, provided_variables: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证提供的变量是否满足模板要求
        
        Returns:
            (is_valid, missing_variables)
        """
        provided_keys = set(provided_variables.keys())
        required_keys = set(self.variables)
        
        missing = list(required_keys - provided_keys)
        is_valid = len(missing) == 0
        
        return is_valid, missing
    
    def get_info(self) -> Dict[str, Any]:
        """获取模板信息"""
        return {
            'template_id': self.template_id,
            'category': self.category,
            'version': self.version,
            'variables': self.variables,
            'metadata': self.metadata,
            'load_time': self.load_time.isoformat()
        }


class PromptManager:
    """
    Prompt模板管理器
    
    主要功能:
    1. 从文件系统加载内置模板
    2. 支持运行时加载自定义模板
    3. 模板参数化和变量替换
    4. 模板缓存管理
    5. 模板版本控制
    
    使用示例:
        pm = PromptManager()
        template = pm.get_template('analysis', 'customer_interview', variables={'transcript': text})
    """
    
    # 默认模板（当文件系统模板不可用时使用）
    DEFAULT_TEMPLATES = {
        'transcription': {
            'multi_speaker': """请准确转录这段音频内容。

要求：
1. 准确识别不同说话人，使用"说话人A:"、"说话人B:"等格式标记
2. 保留所有对话内容，包括语气词
3. 适当添加标点符号，提高可读性
4. 如有背景噪音或不清晰部分，用[听不清]标记

请直接输出转录结果，不要添加任何额外说明。""",
            
            'single_speaker': """请准确转录这段音频内容。

要求：
1. 完整保留所有内容
2. 适当添加标点符号
3. 保持原始语言风格
4. 不清晰部分用[听不清]标记

请直接输出转录结果。""",
            
            'optimization': """# 转录文本优化任务

## 第一部分：错误识别与修正建议

请仔细分析以下转录文本，识别可能的错误并提供修正建议：

{transcript}

请列出：
1. 明显的拼写或用词错误
2. 语法问题
3. 标点符号使用不当
4. 上下文逻辑不通的地方

## 第二部分：优化后转录文本

基于上述分析，请提供优化后的完整转录文本。保持原意的同时：
- 修正错误
- 改善语言流畅性
- 确保专业术语准确
- 保留说话人标记"""
        },
        
        'analysis': {
            'customer_interview': """# 客户访谈深度分析

## 一、角色定位
你是一位拥有15年经验的资深商业分析师和客户洞察专家，专精于从客户访谈中提取关键信息并制定商业策略。

## 二、分析任务
请对以下客户访谈记录进行深度分析，重点关注：
- 客户的核心需求和痛点
- 决策过程和关键影响因素
- 预算范围和时间线
- 潜在的商业机会

### 访谈内容：
{transcript}

## 三、分析框架

### 3.1 执行摘要（200字以内）
简要概括访谈的核心发现和关键洞察。

### 3.2 客户画像
- **基本信息**：行业、规模、角色
- **业务现状**：当前挑战和机遇
- **决策特征**：决策流程、关键人物

### 3.3 需求分析
- **显性需求**：客户明确表达的需求
- **隐性需求**：从对话中推断的潜在需求
- **需求优先级**：基于紧迫性和重要性排序

### 3.4 商机评估
- **项目规模**：预估的项目价值
- **成功概率**：基于客户态度和匹配度
- **风险因素**：可能影响合作的因素

### 3.5 行动建议
提供3-5条具体、可执行的后续行动建议。

## 四、输出要求
1. 分析基于事实，避免过度推测
2. 使用专业但易懂的商业语言
3. 突出关键信息，便于快速决策""",
            
            'business_negotiation': """# 商务谈判要点分析

## 一、角色定位
你是一位资深的商务谈判专家，擅长分析谈判动态、识别各方立场并制定谈判策略。

## 二、分析任务
请对以下商务谈判记录进行深度分析：

{transcript}

## 三、分析维度

### 3.1 谈判概况
- 参与方及其角色
- 谈判主题和目标
- 当前谈判阶段

### 3.2 各方立场分析
- **我方立场**：核心诉求、底线、筹码
- **对方立场**：主要关注点、让步空间
- **分歧焦点**：主要争议和障碍

### 3.3 谈判动态
- 谈判氛围和进展
- 关键转折点
- 双方策略变化

### 3.4 条款要点
- 已达成共识的条款
- 待商议的条款
- 潜在风险条款

### 3.5 策略建议
- 下一步谈判策略
- 可能的让步方案
- 风险防范措施""",
            
            'internal_meeting': """# 内部会议决策分析

## 一、角色定位
你是一位经验丰富的管理顾问，专注于会议效率提升和决策质量优化。

## 二、分析任务
请对以下内部会议记录进行分析：

{transcript}

## 三、分析要点

### 3.1 会议概述
- 会议主题和目标
- 参会人员和角色
- 会议类型（决策/讨论/汇报）

### 3.2 关键议题
列出讨论的主要议题及其重要性。

### 3.3 决策事项
- **已决策事项**：明确的决定和结论
- **待决策事项**：需要进一步讨论的问题
- **决策依据**：支撑决策的关键信息

### 3.4 行动计划
- 具体行动项
- 责任人分配
- 完成时限
- 所需资源

### 3.5 后续跟进
- 需要跟进的事项
- 下次会议安排
- 风险和注意事项"""
        },
        
        'proposal': {
            'project_proposal': """# 项目建议书生成

## 一、角色定位
你是一位资深的商务方案专家，擅长撰写专业、有说服力的项目建议书。

## 二、生成任务
基于以下分析报告{analysis_report}，生成一份完整的项目建议书。

{capability_docs}

## 三、建议书结构

### 1. 执行摘要
- 项目背景和机遇
- 核心价值主张
- 预期成果

### 2. 客户需求理解
- 业务挑战分析
- 需求解读
- 成功标准定义

### 3. 解决方案
- 整体方案架构
- 核心功能模块
- 技术路线
- 创新亮点

### 4. 实施计划
- 项目阶段划分
- 时间线和里程碑
- 资源配置
- 风险管理

### 5. 价值收益
- 直接收益
- 间接收益
- ROI分析

### 6. 为什么选择我们
- 核心优势
- 成功案例
- 团队实力

### 7. 商务条款
- 报价方案
- 付款方式
- 服务承诺

## 四、写作要求
1. 专业严谨，逻辑清晰
2. 突出价值，打动客户
3. 方案具体，可操作性强
4. 篇幅适中，重点突出""",
            
            'quotation_proposal': """# 商务报价方案生成

## 一、任务说明
基于客户需求分析{analysis_report}，生成专业的商务报价方案。

{capability_docs}

## 二、报价方案结构

### 1. 方案概述
- 项目背景
- 服务范围
- 交付成果

### 2. 详细报价
- 服务项目明细
- 单价和数量
- 优惠政策
- 总价

### 3. 服务说明
- 各项服务详细说明
- 服务标准
- 质量保证

### 4. 付款方式
- 付款节点
- 付款比例
- 付款条件

### 5. 其他条款
- 有效期
- 售后服务
- 特别说明""",
            
            'solution_brief': """# 解决方案简报

## 一、任务说明
基于分析结果{analysis_report}，生成简洁的解决方案简报。

## 二、简报结构

### 1. 问题陈述
简明扼要地描述客户面临的核心问题。

### 2. 解决方案
- 方案概述
- 关键特性
- 实施步骤

### 3. 预期效果
- 短期收益
- 长期价值

### 4. 下一步行动
明确的行动建议和时间安排。"""
        }
    }
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        初始化Prompt管理器
        
        Args:
            template_dir: 模板目录路径
        """
        if template_dir is None:
            # 默认模板目录
            template_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'prompts'
            )
        
        self.template_dir = Path(template_dir)
        self.templates: Dict[str, Dict[str, PromptTemplate]] = {}
        self.custom_templates: Dict[str, PromptTemplate] = {}
        self.cache_enabled = True
        
        # 加载所有模板
        self._load_all_templates()

    def _load_all_templates(self):
        """加载所有模板文件"""
        # 先加载默认模板
        self._load_default_templates()

        if not self.template_dir.exists():
            print(f"警告：模板目录 {self.template_dir} 不存在，使用默认模板")
            return

        # 遍历模板目录
        for category_dir in self.template_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith('_'):
                category = category_dir.name

                # 如果该类别还没有模板，初始化空字典
                if category not in self.templates:
                    self.templates[category] = {}

                # 加载该类别下的所有模板
                for template_file in category_dir.glob('*.md'):
                    template_id = template_file.stem
                    try:
                        content = self._load_template_file(template_file)
                        metadata = self._extract_metadata(content)

                        template = PromptTemplate(
                            template_id=template_id,
                            content=content,
                            category=category,
                            metadata=metadata
                        )

                        self.templates[category][template_id] = template

                    except Exception as e:
                        print(f"加载模板 {template_file} 失败: {e}")

        print(f"成功加载 {sum(len(cat) for cat in self.templates.values())} 个模板")
    
    def _load_default_templates(self):
        """加载默认模板"""
        for category, templates in self.DEFAULT_TEMPLATES.items():
            self.templates[category] = {}
            for template_id, content in templates.items():
                template = PromptTemplate(
                    template_id=template_id,
                    content=content,
                    category=category,
                    metadata={'source': 'default', 'version': '1.0.0'}
                )
                self.templates[category][template_id] = template
    
    def _load_template_file(self, file_path: Path) -> str:
        """加载单个模板文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """从模板内容中提取元数据"""
        metadata = {}
        
        # 尝试从内容开头提取YAML格式的元数据
        if content.startswith('---'):
            try:
                end_index = content.find('---', 3)
                if end_index > 0:
                    yaml_content = content[3:end_index].strip()
                    # 简单的YAML解析（可以使用yaml库进行更复杂的解析）
                    for line in yaml_content.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            metadata[key.strip()] = value.strip()
            except:
                pass
        
        return metadata

    def get_template(self,
                     category: str,
                     template_id: str,
                     variables: Optional[Dict[str, Any]] = None) -> str:
        """
        获取并渲染模板

        Args:
            category: 模板类别
            template_id: 模板ID
            variables: 变量字典

        Returns:
            str: 渲染后的模板内容
        """
        # 先检查自定义模板
        custom_key = f"{category}/{template_id}"
        if custom_key in self.custom_templates:
            template = self.custom_templates[custom_key]
            return template.render(variables)

        # 检查文件系统模板
        if category in self.templates and template_id in self.templates[category]:
            template = self.templates[category][template_id]
            return template.render(variables)

        # 尝试从默认模板获取
        if category in self.DEFAULT_TEMPLATES and template_id in self.DEFAULT_TEMPLATES[category]:
            default_content = self.DEFAULT_TEMPLATES[category][template_id]
            template = PromptTemplate(
                template_id=template_id,
                content=default_content,
                category=category,
                metadata={'source': 'default_fallback'}
            )
            # 缓存到模板中以避免重复创建
            if category not in self.templates:
                self.templates[category] = {}
            self.templates[category][template_id] = template
            return template.render(variables)

        # 如果都没找到，抛出异常
        raise ValueError(f"模板 {category}/{template_id} 不存在")
    
    def register_custom_template(self,
                                category: str,
                                template_id: str,
                                content: str,
                                metadata: Optional[Dict] = None) -> bool:
        """
        注册自定义模板
        
        Args:
            category: 模板类别
            template_id: 模板ID
            content: 模板内容
            metadata: 模板元数据
        
        Returns:
            bool: 是否注册成功
        """
        try:
            template = PromptTemplate(
                template_id=template_id,
                content=content,
                category=category,
                metadata=metadata or {}
            )
            
            custom_key = f"{category}/{template_id}"
            self.custom_templates[custom_key] = template
            
            return True
            
        except Exception as e:
            print(f"注册自定义模板失败: {e}")
            return False
    
    def list_templates(self, category: Optional[str] = None) -> List[str]:
        """
        列出可用的模板
        
        Args:
            category: 模板类别，如果为None则列出所有模板
        
        Returns:
            List[str]: 模板ID列表
        """
        templates = []
        
        # 文件系统模板
        if category:
            if category in self.templates:
                templates.extend(self.templates[category].keys())
        else:
            for cat, temps in self.templates.items():
                templates.extend([f"{cat}/{tid}" for tid in temps.keys()])
        
        # 自定义模板
        for custom_key in self.custom_templates.keys():
            if category:
                if custom_key.startswith(f"{category}/"):
                    templates.append(custom_key.split('/', 1)[1])
            else:
                templates.append(custom_key)
        
        return sorted(list(set(templates)))
    
    def get_template_info(self, category: str, template_id: str) -> Dict[str, Any]:
        """
        获取模板详细信息
        
        Args:
            category: 模板类别
            template_id: 模板ID
        
        Returns:
            Dict: 模板信息
        """
        # 检查自定义模板
        custom_key = f"{category}/{template_id}"
        if custom_key in self.custom_templates:
            return self.custom_templates[custom_key].get_info()
        
        # 检查文件系统模板
        if category in self.templates and template_id in self.templates[category]:
            return self.templates[category][template_id].get_info()
        
        raise ValueError(f"模板 {category}/{template_id} 不存在")
    
    def validate_template(self,
                         category: str,
                         template_id: str,
                         variables: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证模板变量
        
        Args:
            category: 模板类别
            template_id: 模板ID
            variables: 提供的变量
        
        Returns:
            (is_valid, missing_variables)
        """
        # 获取模板
        custom_key = f"{category}/{template_id}"
        if custom_key in self.custom_templates:
            template = self.custom_templates[custom_key]
        elif category in self.templates and template_id in self.templates[category]:
            template = self.templates[category][template_id]
        else:
            return False, [f"模板 {category}/{template_id} 不存在"]
        
        return template.validate_variables(variables)
    
    def reload_templates(self):
        """重新加载所有模板"""
        self.templates.clear()
        self._load_all_templates()
        print("模板重新加载完成")
    
    def export_template(self, 
                       category: str,
                       template_id: str,
                       output_path: str) -> bool:
        """
        导出模板到文件
        
        Args:
            category: 模板类别
            template_id: 模板ID
            output_path: 输出路径
        
        Returns:
            bool: 是否导出成功
        """
        try:
            content = self.get_template(category, template_id)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            print(f"导出模板失败: {e}")
            return False
    
    def get_categories(self) -> List[str]:
        """获取所有模板类别"""
        categories = set(self.templates.keys())
        
        # 添加自定义模板的类别
        for custom_key in self.custom_templates.keys():
            category = custom_key.split('/')[0]
            categories.add(category)
        
        return sorted(list(categories))
    
    def clear_cache(self):
        """清除模板缓存（未来扩展用）"""
        # 当前实现中模板是立即加载的，这里预留缓存清理接口
        pass
    
    def get_template_stats(self) -> Dict[str, Any]:
        """获取模板统计信息"""
        stats = {
            'total_templates': 0,
            'categories': {},
            'custom_templates': len(self.custom_templates),
            'load_time': datetime.now().isoformat()
        }
        
        for category, templates in self.templates.items():
            stats['categories'][category] = len(templates)
            stats['total_templates'] += len(templates)
        
        stats['total_templates'] += len(self.custom_templates)
        
        return stats
