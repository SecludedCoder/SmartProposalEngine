#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/utils/format_utils.py
功能说明: 格式化相关工具函数
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

import os
import sys
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
import html
import markdown

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def format_duration(seconds: Optional[Union[int, float]]) -> str:
    """
    格式化时长显示
    
    Args:
        seconds: 秒数
    
    Returns:
        str: 格式化后的时长字符串（如 "1小时23分45秒"）
    """
    if seconds is None:
        return "未知"
    
    if seconds < 0:
        return "无效时长"
    
    # 转换为整数秒
    total_seconds = int(seconds)
    
    # 计算时分秒
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    # 构建结果字符串
    parts = []
    
    if hours > 0:
        parts.append(f"{hours}小时")
    
    if minutes > 0:
        parts.append(f"{minutes}分")
    
    if secs > 0 or len(parts) == 0:  # 如果没有时分，至少显示秒
        parts.append(f"{secs}秒")
    
    return "".join(parts)


def format_timestamp(timestamp: Union[int, float, datetime], 
                    format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳
    
    Args:
        timestamp: 时间戳（秒）或datetime对象
        format_string: 格式化字符串
    
    Returns:
        str: 格式化后的时间字符串
    """
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, datetime):
        dt = timestamp
    else:
        return "无效时间"
    
    return dt.strftime(format_string)


def format_metadata_display(metadata: Dict[str, Any], 
                          exclude_keys: Optional[List[str]] = None) -> str:
    """
    格式化元数据用于显示
    
    Args:
        metadata: 元数据字典
        exclude_keys: 要排除的键列表
    
    Returns:
        str: 格式化后的显示字符串
    """
    if not metadata:
        return "无元数据"
    
    exclude_keys = exclude_keys or []
    
    display_parts = []
    
    # 定义键的显示名称映射
    key_display_names = {
        'file_size': '文件大小',
        'duration': '时长',
        'speakers_count': '说话人数',
        'processing_time': '处理时间',
        'model_used': '使用模型',
        'total_tokens': 'Token总数',
        'estimated_cost': '预估费用',
        'timestamp': '处理时间',
        'analysis_template': '分析模板',
        'source_type': '来源类型',
        'page_count': '页数',
        'word_count': '字数'
    }
    
    # 按优先级排序的键
    priority_keys = [
        'file_size', 'duration', 'page_count', 'word_count',
        'speakers_count', 'processing_time', 'model_used'
    ]
    
    # 先显示优先级高的键
    for key in priority_keys:
        if key in metadata and key not in exclude_keys:
            display_name = key_display_names.get(key, key)
            value = metadata[key]
            
            # 特殊格式化
            if key == 'processing_time' and isinstance(value, (int, float)):
                value = f"{value:.1f}秒"
            elif key == 'estimated_cost' and isinstance(value, (int, float)):
                value = f"${value:.4f}"
            elif key == 'total_tokens' and isinstance(value, int):
                value = f"{value:,}"
            
            display_parts.append(f"{display_name}: {value}")
    
    # 再显示其他键
    for key, value in metadata.items():
        if key not in priority_keys and key not in exclude_keys:
            display_name = key_display_names.get(key, key)
            display_parts.append(f"{display_name}: {value}")
    
    return " | ".join(display_parts)


def format_number(number: Union[int, float], 
                 decimal_places: int = 2,
                 use_comma: bool = True) -> str:
    """
    格式化数字显示
    
    Args:
        number: 数字
        decimal_places: 小数位数
        use_comma: 是否使用千位分隔符
    
    Returns:
        str: 格式化后的数字字符串
    """
    if isinstance(number, int):
        if use_comma:
            return f"{number:,}"
        else:
            return str(number)
    
    if use_comma:
        return f"{number:,.{decimal_places}f}"
    else:
        return f"{number:.{decimal_places}f}"


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """
    格式化百分比显示
    
    Args:
        value: 数值（0-1之间表示百分比，大于1表示已经是百分数）
        decimal_places: 小数位数
    
    Returns:
        str: 格式化后的百分比字符串
    """
    if value <= 1:
        percentage = value * 100
    else:
        percentage = value
    
    return f"{percentage:.{decimal_places}f}%"


def format_money(amount: Union[int, float], 
                currency: str = "¥",
                decimal_places: int = 2) -> str:
    """
    格式化货币显示
    
    Args:
        amount: 金额
        currency: 货币符号
        decimal_places: 小数位数
    
    Returns:
        str: 格式化后的货币字符串
    """
    formatted_number = format_number(amount, decimal_places, use_comma=True)
    return f"{currency}{formatted_number}"


def clean_text(text: str, 
              remove_extra_spaces: bool = True,
              remove_empty_lines: bool = True) -> str:
    """
    清理文本
    
    Args:
        text: 原始文本
        remove_extra_spaces: 是否移除多余空格
        remove_empty_lines: 是否移除空行
    
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    
    # 移除首尾空白
    text = text.strip()
    
    if remove_extra_spaces:
        # 将多个空格替换为一个
        text = re.sub(r'\s+', ' ', text)
        # 但保留换行符
        text = re.sub(r' *\n *', '\n', text)
    
    if remove_empty_lines:
        # 移除空行
        lines = [line for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
    
    return text


def truncate_text(text: str, 
                 max_length: int = 100,
                 suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
    
    Returns:
        str: 截断后的文本
    """
    if not text or len(text) <= max_length:
        return text
    
    # 在词边界截断
    truncated = text[:max_length]
    
    # 尝试在最后一个完整词处截断
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # 如果空格位置合理
        truncated = truncated[:last_space]
    
    return truncated + suffix


def markdown_to_text(markdown_text: str) -> str:
    """
    将Markdown转换为纯文本
    
    Args:
        markdown_text: Markdown格式文本
    
    Returns:
        str: 纯文本
    """
    # 移除Markdown标记
    # 移除标题标记
    text = re.sub(r'^#{1,6}\s+', '', markdown_text, flags=re.MULTILINE)
    
    # 移除加粗和斜体
    text = re.sub(r'\*{1,2}([^\*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
    
    # 移除链接
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # 移除图片
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', text)
    
    # 移除代码块
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # 移除列表标记
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # 移除引用标记
    text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)
    
    # 移除水平线
    text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
    
    # 清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def markdown_to_html(markdown_text: str, 
                    safe_mode: bool = True) -> str:
    """
    将Markdown转换为HTML
    
    Args:
        markdown_text: Markdown格式文本
        safe_mode: 是否启用安全模式（转义HTML）
    
    Returns:
        str: HTML格式文本
    """
    if safe_mode:
        # 转义HTML标签
        markdown_text = html.escape(markdown_text)
    
    # 使用markdown库转换
    html_text = markdown.markdown(
        markdown_text,
        extensions=['extra', 'codehilite', 'toc']
    )
    
    return html_text


def format_list_as_text(items: List[Any], 
                       style: str = "bullet",
                       indent: int = 0) -> str:
    """
    将列表格式化为文本
    
    Args:
        items: 项目列表
        style: 样式 ('bullet', 'number', 'dash')
        indent: 缩进级别
    
    Returns:
        str: 格式化后的文本
    """
    if not items:
        return ""
    
    indent_str = "  " * indent
    formatted_items = []
    
    for i, item in enumerate(items):
        if style == "number":
            prefix = f"{i + 1}."
        elif style == "dash":
            prefix = "-"
        else:  # bullet
            prefix = "•"
        
        formatted_items.append(f"{indent_str}{prefix} {item}")
    
    return "\n".join(formatted_items)


def format_dict_as_text(data: Dict[str, Any],
                       indent: int = 0,
                       exclude_keys: Optional[List[str]] = None) -> str:
    """
    将字典格式化为文本
    
    Args:
        data: 数据字典
        indent: 缩进级别
        exclude_keys: 要排除的键
    
    Returns:
        str: 格式化后的文本
    """
    if not data:
        return ""
    
    exclude_keys = exclude_keys or []
    indent_str = "  " * indent
    formatted_parts = []
    
    for key, value in data.items():
        if key in exclude_keys:
            continue
        
        # 格式化键名（将下划线转换为空格，首字母大写）
        display_key = key.replace('_', ' ').title()
        
        if isinstance(value, dict):
            formatted_parts.append(f"{indent_str}{display_key}:")
            formatted_parts.append(format_dict_as_text(value, indent + 1))
        elif isinstance(value, list):
            formatted_parts.append(f"{indent_str}{display_key}:")
            formatted_parts.append(format_list_as_text(value, indent=indent + 1))
        else:
            formatted_parts.append(f"{indent_str}{display_key}: {value}")
    
    return "\n".join(formatted_parts)


def escape_markdown(text: str) -> str:
    """
    转义Markdown特殊字符
    
    Args:
        text: 原始文本
    
    Returns:
        str: 转义后的文本
    """
    # Markdown特殊字符
    special_chars = ['*', '_', '`', '[', ']', '(', ')', '#', '+', '-', '!', '|', '{', '}']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def format_json_pretty(data: Union[Dict, List], 
                      indent: int = 2,
                      ensure_ascii: bool = False) -> str:
    """
    美化JSON格式
    
    Args:
        data: 数据
        indent: 缩进空格数
        ensure_ascii: 是否确保ASCII编码
    
    Returns:
        str: 美化后的JSON字符串
    """
    return json.dumps(
        data,
        indent=indent,
        ensure_ascii=ensure_ascii,
        sort_keys=True,
        default=str  # 处理不可序列化的对象
    )


def format_table_text(headers: List[str], 
                     rows: List[List[Any]],
                     align: str = "left") -> str:
    """
    格式化表格文本（Markdown格式）
    
    Args:
        headers: 表头列表
        rows: 数据行列表
        align: 对齐方式 ('left', 'center', 'right')
    
    Returns:
        str: Markdown格式的表格
    """
    if not headers or not rows:
        return ""
    
    # 计算每列的最大宽度
    col_widths = [len(str(h)) for h in headers]
    
    for row in rows:
        for i, cell in enumerate(row[:len(headers)]):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # 构建表头
    header_parts = []
    separator_parts = []
    
    for i, header in enumerate(headers):
        header_parts.append(str(header).ljust(col_widths[i]))
        
        if align == "center":
            separator_parts.append(":" + "-" * (col_widths[i] - 2) + ":")
        elif align == "right":
            separator_parts.append("-" * (col_widths[i] - 1) + ":")
        else:  # left
            separator_parts.append("-" * col_widths[i])
    
    # 构建表格
    table_lines = [
        "| " + " | ".join(header_parts) + " |",
        "| " + " | ".join(separator_parts) + " |"
    ]
    
    # 添加数据行
    for row in rows:
        row_parts = []
        for i, cell in enumerate(row[:len(headers)]):
            if i < len(col_widths):
                if align == "right":
                    row_parts.append(str(cell).rjust(col_widths[i]))
                elif align == "center":
                    row_parts.append(str(cell).center(col_widths[i]))
                else:
                    row_parts.append(str(cell).ljust(col_widths[i]))
        
        table_lines.append("| " + " | ".join(row_parts) + " |")
    
    return "\n".join(table_lines)


def format_relative_time(timestamp: Union[datetime, float]) -> str:
    """
    格式化相对时间（如"5分钟前"）
    
    Args:
        timestamp: 时间戳或datetime对象
    
    Returns:
        str: 相对时间字符串
    """
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    else:
        dt = timestamp
    
    now = datetime.now()
    delta = now - dt
    
    # 转换为秒
    total_seconds = int(delta.total_seconds())
    
    if total_seconds < 60:
        return "刚刚"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes}分钟前"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours}小时前"
    elif total_seconds < 604800:
        days = total_seconds // 86400
        return f"{days}天前"
    elif total_seconds < 2592000:
        weeks = total_seconds // 604800
        return f"{weeks}周前"
    elif total_seconds < 31536000:
        months = total_seconds // 2592000
        return f"{months}个月前"
    else:
        years = total_seconds // 31536000
        return f"{years}年前"


def highlight_text(text: str, 
                  keywords: List[str],
                  highlight_style: str = "**{text}**") -> str:
    """
    高亮文本中的关键词
    
    Args:
        text: 原始文本
        keywords: 关键词列表
        highlight_style: 高亮样式模板
    
    Returns:
        str: 高亮后的文本
    """
    if not text or not keywords:
        return text
    
    # 按关键词长度降序排序，避免短词影响长词
    sorted_keywords = sorted(keywords, key=len, reverse=True)
    
    for keyword in sorted_keywords:
        if keyword in text:
            # 使用正则表达式进行大小写不敏感的替换
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            text = pattern.sub(
                lambda m: highlight_style.format(text=m.group(0)),
                text
            )
    
    return text
