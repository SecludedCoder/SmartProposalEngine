#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/utils/validation_utils.py
功能说明: 验证相关工具函数
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

import os
import sys
import re
from typing import Dict, List, Optional, Union, Tuple, Any
from pathlib import Path
import mimetypes

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.file_utils import (
    SUPPORTED_AUDIO_FORMATS, 
    SUPPORTED_DOCUMENT_FORMATS,
    get_file_extension
)


# 验证规则配置
VALIDATION_RULES = {
    'file_size': {
        'max_audio_mb': 200,
        'max_document_mb': 50,
        'max_total_mb': 500
    },
    'text_length': {
        'min_analysis_chars': 50,
        'max_analysis_chars': 100000,
        'min_proposal_chars': 100,
        'max_proposal_chars': 200000
    },
    'api_limits': {
        'max_tokens_per_request': 32768,
        'max_requests_per_minute': 60
    }
}


def validate_file_type(file_path: Union[str, Path], 
                      allowed_types: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    验证文件类型
    
    Args:
        file_path: 文件路径
        allowed_types: 允许的文件类型列表（如 ['audio', 'document']）
    
    Returns:
        (is_valid, message): 验证结果和消息
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return False, f"文件不存在: {file_path}"
    
    ext = get_file_extension(file_path)
    
    # 如果没有指定允许类型，则允许所有已知类型
    if allowed_types is None:
        all_formats = SUPPORTED_AUDIO_FORMATS + SUPPORTED_DOCUMENT_FORMATS
        if ext in all_formats:
            return True, f"文件类型有效: {ext}"
        else:
            return False, f"不支持的文件类型: {ext}"
    
    # 检查特定类型
    valid = False
    file_type = None
    
    if 'audio' in allowed_types and ext in SUPPORTED_AUDIO_FORMATS:
        valid = True
        file_type = 'audio'
    elif 'document' in allowed_types and ext in SUPPORTED_DOCUMENT_FORMATS:
        valid = True
        file_type = 'document'
    
    if valid:
        return True, f"文件类型有效: {file_type} ({ext})"
    else:
        return False, f"文件类型 {ext} 不在允许的类型中: {allowed_types}"


def validate_text_input(text: str, 
                       min_length: Optional[int] = None,
                       max_length: Optional[int] = None,
                       required_patterns: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    验证文本输入
    
    Args:
        text: 输入文本
        min_length: 最小长度
        max_length: 最大长度
        required_patterns: 必须包含的模式列表（正则表达式）
    
    Returns:
        (is_valid, message): 验证结果和消息
    """
    if not text:
        return False, "文本不能为空"
    
    text = text.strip()
    text_length = len(text)
    
    # 检查最小长度
    if min_length is not None and text_length < min_length:
        return False, f"文本太短，最少需要 {min_length} 个字符，当前 {text_length} 个"
    
    # 检查最大长度
    if max_length is not None and text_length > max_length:
        return False, f"文本太长，最多允许 {max_length} 个字符，当前 {text_length} 个"
    
    # 检查必需的模式
    if required_patterns:
        for pattern in required_patterns:
            if not re.search(pattern, text):
                return False, f"文本不符合要求的格式: 缺少 {pattern}"
    
    return True, f"文本有效，长度: {text_length}"


def validate_email(email: str) -> Tuple[bool, str]:
    """
    验证邮箱地址
    
    Args:
        email: 邮箱地址
    
    Returns:
        (is_valid, message): 验证结果和消息
    """
    if not email:
        return False, "邮箱地址不能为空"
    
    # 基本的邮箱正则表达式
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(email_pattern, email):
        return True, "邮箱地址格式正确"
    else:
        return False, "邮箱地址格式无效"


def validate_phone(phone: str, region: str = 'CN') -> Tuple[bool, str]:
    """
    验证电话号码
    
    Args:
        phone: 电话号码
        region: 地区代码（'CN' 中国，'US' 美国等）
    
    Returns:
        (is_valid, message): 验证结果和消息
    """
    if not phone:
        return False, "电话号码不能为空"
    
    # 移除空格和特殊字符
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # 根据地区验证
    if region == 'CN':
        # 中国手机号码
        if re.match(r'^1[3-9]\d{9}$', phone):
            return True, "手机号码格式正确"
        # 中国固定电话
        elif re.match(r'^0\d{2,3}\d{7,8}$', phone):
            return True, "固定电话格式正确"
        else:
            return False, "电话号码格式无效（需要11位手机号或区号+电话）"
    
    elif region == 'US':
        # 美国电话号码
        if re.match(r'^1?\d{10}$', phone):
            return True, "电话号码格式正确"
        else:
            return False, "电话号码格式无效（需要10位数字）"
    
    else:
        # 通用验证（只检查是否为数字）
        if re.match(r'^\+?\d{7,15}$', phone):
            return True, "电话号码格式正确"
        else:
            return False, "电话号码格式无效"


def validate_url(url: str) -> Tuple[bool, str]:
    """
    验证URL地址
    
    Args:
        url: URL地址
    
    Returns:
        (is_valid, message): 验证结果和消息
    """
    if not url:
        return False, "URL不能为空"
    
    # URL正则表达式
    url_pattern = r'^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)$'
    
    if re.match(url_pattern, url):
        return True, "URL格式正确"
    else:
        return False, "URL格式无效"


def validate_api_key(api_key: str, 
                    key_type: str = 'google') -> Tuple[bool, str]:
    """
    验证API密钥格式
    
    Args:
        api_key: API密钥
        key_type: 密钥类型（'google', 'openai'等）
    
    Returns:
        (is_valid, message): 验证结果和消息
    """
    if not api_key:
        return False, "API密钥不能为空"
    
    api_key = api_key.strip()
    
    if key_type == 'google':
        # Google API密钥通常是39个字符
        if len(api_key) == 39 and api_key.startswith('AIza'):
            return True, "Google API密钥格式正确"
        else:
            return False, "Google API密钥格式无效（应为39个字符，以AIza开头）"
    
    elif key_type == 'openai':
        # OpenAI API密钥
        if api_key.startswith('sk-') and len(api_key) > 20:
            return True, "OpenAI API密钥格式正确"
        else:
            return False, "OpenAI API密钥格式无效（应以sk-开头）"
    
    else:
        # 通用验证
        if len(api_key) >= 16:
            return True, "API密钥格式正确"
        else:
            return False, "API密钥太短（至少需要16个字符）"


def validate_json_structure(data: Dict[str, Any], 
                          required_fields: List[str],
                          field_types: Optional[Dict[str, type]] = None) -> Tuple[bool, str]:
    """
    验证JSON/字典结构
    
    Args:
        data: 要验证的数据
        required_fields: 必需的字段列表
        field_types: 字段类型映射（可选）
    
    Returns:
        (is_valid, message): 验证结果和消息
    """
    if not isinstance(data, dict):
        return False, "数据必须是字典类型"
    
    # 检查必需字段
    missing_fields = []
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
    
    if missing_fields:
        return False, f"缺少必需字段: {', '.join(missing_fields)}"
    
    # 检查字段类型
    if field_types:
        type_errors = []
        for field, expected_type in field_types.items():
            if field in data and not isinstance(data[field], expected_type):
                actual_type = type(data[field]).__name__
                expected_name = expected_type.__name__
                type_errors.append(f"{field} 应为 {expected_name} 类型，实际为 {actual_type}")
        
        if type_errors:
            return False, "字段类型错误: " + "; ".join(type_errors)
    
    return True, "数据结构有效"


def validate_template_variables(template: str, 
                              provided_vars: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证模板变量
    
    Args:
        template: 模板字符串
        provided_vars: 提供的变量字典
    
    Returns:
        (is_valid, missing_vars): 是否有效和缺失的变量列表
    """
    # 提取模板中的变量
    pattern = r'\{([^}]+)\}'
    required_vars = set(re.findall(pattern, template))
    
    # 检查缺失的变量
    provided_keys = set(provided_vars.keys())
    missing_vars = list(required_vars - provided_keys)
    
    is_valid = len(missing_vars) == 0
    
    return is_valid, missing_vars


def validate_batch_files(file_paths: List[Union[str, Path]], 
                        max_total_size_mb: Optional[float] = None,
                        max_file_count: Optional[int] = None) -> Tuple[bool, str, List[str]]:
    """
    验证批量文件
    
    Args:
        file_paths: 文件路径列表
        max_total_size_mb: 最大总大小（MB）
        max_file_count: 最大文件数量
    
    Returns:
        (is_valid, message, invalid_files): 验证结果、消息和无效文件列表
    """
    invalid_files = []
    total_size = 0
    
    # 检查文件数量
    if max_file_count and len(file_paths) > max_file_count:
        return False, f"文件数量超过限制（最多 {max_file_count} 个）", []
    
    # 验证每个文件
    for file_path in file_paths:
        file_path = Path(file_path)
        
        # 检查文件存在性
        if not file_path.exists():
            invalid_files.append(str(file_path))
            continue
        
        # 累计文件大小
        total_size += file_path.stat().st_size
    
    # 检查总大小
    total_size_mb = total_size / (1024 * 1024)
    if max_total_size_mb and total_size_mb > max_total_size_mb:
        return False, f"文件总大小超过限制（{total_size_mb:.1f} MB > {max_total_size_mb} MB）", invalid_files
    
    if invalid_files:
        return False, f"有 {len(invalid_files)} 个文件无效", invalid_files
    
    return True, f"所有文件有效，总大小: {total_size_mb:.1f} MB", []


def validate_model_input(text: str, 
                        model_type: str = 'gemini') -> Tuple[bool, str]:
    """
    验证模型输入
    
    Args:
        text: 输入文本
        model_type: 模型类型
    
    Returns:
        (is_valid, message): 验证结果和消息
    """
    if not text:
        return False, "输入文本不能为空"
    
    # 估算token数量（简单估算）
    estimated_tokens = len(text) // 4  # 英文约4个字符一个token
    chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
    estimated_tokens += chinese_chars * 0.5  # 中文字符额外计算
    
    max_tokens = VALIDATION_RULES['api_limits']['max_tokens_per_request']
    
    if estimated_tokens > max_tokens:
        return False, f"输入文本过长，预估 {int(estimated_tokens)} tokens，超过限制 {max_tokens}"
    
    return True, f"输入有效，预估 {int(estimated_tokens)} tokens"


def validate_workflow_state(state: Dict[str, Any], 
                          workflow_type: str) -> Tuple[bool, str]:
    """
    验证工作流状态
    
    Args:
        state: 工作流状态
        workflow_type: 工作流类型
    
    Returns:
        (is_valid, message): 验证结果和消息
    """
    # 定义各工作流的必需步骤
    workflow_requirements = {
        'full_process': ['transcription', 'analysis', 'proposal'],
        'analysis_only': ['input', 'analysis'],
        'proposal_only': ['analysis', 'proposal']
    }
    
    required_steps = workflow_requirements.get(workflow_type, [])
    
    if not required_steps:
        return True, "工作流类型未定义要求"
    
    # 检查必需步骤是否完成
    missing_steps = []
    for step in required_steps:
        if not state.get(f'{step}_completed', False):
            missing_steps.append(step)
    
    if missing_steps:
        return False, f"工作流未完成，缺少步骤: {', '.join(missing_steps)}"
    
    return True, "工作流状态有效"


def sanitize_filename(filename: str, 
                     max_length: int = 255) -> str:
    """
    清理文件名，使其安全
    
    Args:
        filename: 原始文件名
        max_length: 最大长度
    
    Returns:
        str: 清理后的文件名
    """
    # 移除路径分隔符
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # 移除特殊字符
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # 移除控制字符
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # 处理保留名称（Windows）
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + \
                    [f'COM{i}' for i in range(1, 10)] + \
                    [f'LPT{i}' for i in range(1, 10)]
    
    name_without_ext = filename.rsplit('.', 1)[0].upper()
    if name_without_ext in reserved_names:
        filename = f'_{filename}'
    
    # 限制长度
    if len(filename) > max_length:
        # 保留扩展名
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            max_name_length = max_length - len(ext) - 1
            filename = f"{name[:max_name_length]}.{ext}"
        else:
            filename = filename[:max_length]
    
    # 确保不为空
    if not filename:
        filename = 'unnamed_file'
    
    return filename


def validate_date_range(start_date: str, 
                       end_date: str,
                       date_format: str = '%Y-%m-%d') -> Tuple[bool, str]:
    """
    验证日期范围
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        date_format: 日期格式
    
    Returns:
        (is_valid, message): 验证结果和消息
    """
    from datetime import datetime
    
    try:
        start = datetime.strptime(start_date, date_format)
        end = datetime.strptime(end_date, date_format)
        
        if start > end:
            return False, "开始日期不能晚于结束日期"
        
        # 检查日期范围是否合理（例如不超过1年）
        delta = end - start
        if delta.days > 365:
            return False, "日期范围不能超过1年"
        
        return True, f"日期范围有效: {delta.days} 天"
        
    except ValueError as e:
        return False, f"日期格式错误: {str(e)}"


def validate_config_file(config_path: Union[str, Path]) -> Tuple[bool, str, Dict[str, List[str]]]:
    """
    验证配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        (is_valid, message, issues): 验证结果、消息和问题详情
    """
    import configparser
    
    config_path = Path(config_path)
    issues = {'errors': [], 'warnings': []}
    
    if not config_path.exists():
        return False, f"配置文件不存在: {config_path}", issues
    
    try:
        config = configparser.ConfigParser()
        config.read(config_path)
        
        # 检查必需的部分
        required_sections = ['API_SETTINGS', 'MODEL_SETTINGS', 'FILE_SETTINGS']
        for section in required_sections:
            if section not in config:
                issues['errors'].append(f"缺少必需的配置部分: [{section}]")
        
        # 检查API设置
        if 'API_SETTINGS' in config:
            if config.getboolean('API_SETTINGS', 'use_internal_api_key', fallback=False):
                api_key_file = config.get('API_SETTINGS', 'api_key_file', fallback='')
                if not api_key_file:
                    issues['errors'].append("使用内部API密钥但未指定密钥文件")
        
        # 检查文件设置
        if 'FILE_SETTINGS' in config:
            max_size = config.getint('FILE_SETTINGS', 'max_file_size_mb', fallback=0)
            if max_size <= 0:
                issues['warnings'].append("未设置有效的最大文件大小限制")
        
        if issues['errors']:
            return False, "配置文件有错误", issues
        elif issues['warnings']:
            return True, "配置文件有效但有警告", issues
        else:
            return True, "配置文件完全有效", issues
        
    except Exception as e:
        issues['errors'].append(f"配置文件解析错误: {str(e)}")
        return False, "配置文件解析失败", issues
