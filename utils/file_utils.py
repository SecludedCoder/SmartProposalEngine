#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/utils/file_utils.py
功能说明: 文件处理相关工具函数
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

import os
import sys
import shutil
import tempfile
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Union
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 文件大小单位
SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB']

# 支持的文件格式
SUPPORTED_AUDIO_FORMATS = ['.m4a', '.mp3', '.wav', '.aac', '.ogg', '.flac', '.mp4', '.wma', '.opus']
SUPPORTED_DOCUMENT_FORMATS = ['.docx', '.pdf', '.txt', '.doc', '.rtf', '.odt']
SUPPORTED_IMAGE_FORMATS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.svg']
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 字节数
    
    Returns:
        str: 格式化后的大小字符串（如 "1.5 MB"）
    """
    if size_bytes == 0:
        return "0 B"
    
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(SIZE_UNITS) - 1:
        size /= 1024
        unit_index += 1
    
    # 根据大小决定小数位数
    if unit_index == 0:  # 字节
        return f"{int(size)} {SIZE_UNITS[unit_index]}"
    elif size >= 100:
        return f"{size:.0f} {SIZE_UNITS[unit_index]}"
    elif size >= 10:
        return f"{size:.1f} {SIZE_UNITS[unit_index]}"
    else:
        return f"{size:.2f} {SIZE_UNITS[unit_index]}"


def get_file_extension(file_path: Union[str, Path]) -> str:
    """
    获取文件扩展名（小写）
    
    Args:
        file_path: 文件路径
    
    Returns:
        str: 小写的文件扩展名（包含点号）
    """
    return Path(file_path).suffix.lower()


def get_file_type(file_path: Union[str, Path]) -> str:
    """
    判断文件类型
    
    Args:
        file_path: 文件路径
    
    Returns:
        str: 文件类型 ('audio', 'document', 'image', 'video', 'unknown')
    """
    ext = get_file_extension(file_path)
    
    if ext in SUPPORTED_AUDIO_FORMATS:
        return 'audio'
    elif ext in SUPPORTED_DOCUMENT_FORMATS:
        return 'document'
    elif ext in SUPPORTED_IMAGE_FORMATS:
        return 'image'
    elif ext in SUPPORTED_VIDEO_FORMATS:
        return 'video'
    else:
        return 'unknown'


def validate_file_size(file_path: Union[str, Path], max_size_mb: float = 200) -> Tuple[bool, str]:
    """
    验证文件大小是否在允许范围内
    
    Args:
        file_path: 文件路径
        max_size_mb: 最大允许大小（MB）
    
    Returns:
        (is_valid, message): 验证结果和消息
    """
    try:
        file_size = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            return False, f"文件太大（{format_file_size(file_size)}），最大允许 {max_size_mb} MB"
        
        return True, f"文件大小: {format_file_size(file_size)}"
        
    except Exception as e:
        return False, f"无法获取文件大小: {str(e)}"


def validate_file_format(file_path: Union[str, Path], allowed_formats: List[str]) -> Tuple[bool, str]:
    """
    验证文件格式是否允许
    
    Args:
        file_path: 文件路径
        allowed_formats: 允许的格式列表
    
    Returns:
        (is_valid, message): 验证结果和消息
    """
    ext = get_file_extension(file_path)
    
    if ext in allowed_formats:
        return True, f"文件格式: {ext}"
    else:
        return False, f"不支持的文件格式: {ext}，允许的格式: {', '.join(allowed_formats)}"


def create_temp_directory(prefix: str = "smartproposal_") -> str:
    """
    创建临时目录
    
    Args:
        prefix: 目录前缀
    
    Returns:
        str: 临时目录路径
    """
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    return temp_dir


def cleanup_directory(directory: Union[str, Path], safe_mode: bool = True) -> bool:
    """
    清理目录
    
    Args:
        directory: 要清理的目录
        safe_mode: 安全模式（只清理临时目录）
    
    Returns:
        bool: 是否清理成功
    """
    try:
        directory = Path(directory)
        
        # 安全检查
        if safe_mode:
            temp_dir = Path(tempfile.gettempdir())
            if not str(directory).startswith(str(temp_dir)):
                print(f"安全模式下只能清理临时目录: {directory}")
                return False
        
        if directory.exists():
            shutil.rmtree(directory)
            return True
        
        return True
        
    except Exception as e:
        print(f"清理目录失败: {e}")
        return False


def save_uploaded_file(uploaded_file, save_directory: Union[str, Path], 
                      new_filename: Optional[str] = None) -> Tuple[bool, str, str]:
    """
    保存上传的文件（Streamlit文件对象）
    
    Args:
        uploaded_file: Streamlit的上传文件对象
        save_directory: 保存目录
        new_filename: 新文件名（可选）
    
    Returns:
        (success, file_path, message): 保存结果
    """
    try:
        save_directory = Path(save_directory)
        save_directory.mkdir(parents=True, exist_ok=True)
        
        # 确定文件名
        if new_filename:
            filename = new_filename
        else:
            # 使用原始文件名，但添加时间戳避免冲突
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_parts = uploaded_file.name.rsplit('.', 1)
            if len(name_parts) == 2:
                filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
            else:
                filename = f"{uploaded_file.name}_{timestamp}"
        
        file_path = save_directory / filename
        
        # 保存文件
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        return True, str(file_path), f"文件保存成功: {filename}"
        
    except Exception as e:
        return False, "", f"保存文件失败: {str(e)}"


def generate_file_hash(file_path: Union[str, Path], algorithm: str = 'md5') -> str:
    """
    生成文件哈希值
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法 ('md5', 'sha1', 'sha256')
    
    Returns:
        str: 文件哈希值
    """
    hash_func = getattr(hashlib, algorithm)()
    
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def get_file_metadata(file_path: Union[str, Path]) -> Dict[str, any]:
    """
    获取文件元数据
    
    Args:
        file_path: 文件路径
    
    Returns:
        Dict: 文件元数据
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {'error': '文件不存在'}
    
    stat = file_path.stat()
    
    metadata = {
        'filename': file_path.name,
        'path': str(file_path.absolute()),
        'size': stat.st_size,
        'size_formatted': format_file_size(stat.st_size),
        'extension': file_path.suffix.lower(),
        'file_type': get_file_type(file_path),
        'created_time': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
        'modified_time': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        'mime_type': mimetypes.guess_type(str(file_path))[0] or 'unknown'
    }
    
    return metadata


def prepare_download_file(file_path: Union[str, Path], download_name: Optional[str] = None) -> Tuple[bytes, str, str]:
    """
    准备文件供下载
    
    Args:
        file_path: 文件路径
        download_name: 下载时的文件名
    
    Returns:
        (file_data, download_name, mime_type): 文件数据、下载名称、MIME类型
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    # 读取文件数据
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    # 确定下载文件名
    if not download_name:
        download_name = file_path.name
    
    # 获取MIME类型
    mime_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
    
    return file_data, download_name, mime_type


def batch_process_files(file_list: List[Union[str, Path]], 
                       process_func: callable,
                       progress_callback: Optional[callable] = None) -> List[Dict[str, any]]:
    """
    批量处理文件
    
    Args:
        file_list: 文件路径列表
        process_func: 处理函数
        progress_callback: 进度回调函数
    
    Returns:
        List[Dict]: 处理结果列表
    """
    results = []
    total_files = len(file_list)
    
    for i, file_path in enumerate(file_list):
        if progress_callback:
            progress_callback(f"处理文件 {i + 1}/{total_files}: {Path(file_path).name}")
        
        try:
            result = process_func(file_path)
            results.append({
                'file': str(file_path),
                'success': True,
                'result': result
            })
        except Exception as e:
            results.append({
                'file': str(file_path),
                'success': False,
                'error': str(e)
            })
    
    return results


def get_audio_duration(file_path: Union[str, Path]) -> Optional[float]:
    """
    获取音频文件时长（秒）
    
    Args:
        file_path: 音频文件路径
    
    Returns:
        float: 时长（秒），如果无法获取则返回None
    """
    try:
        # 尝试使用pydub获取时长
        from pydub import AudioSegment
        audio = AudioSegment.from_file(file_path)
        duration_seconds = len(audio) / 1000.0
        return duration_seconds
    except ImportError:
        # pydub未安装，尝试其他方法
        pass
    except Exception as e:
        print(f"使用pydub获取音频时长失败: {e}")
    
    # 这里可以添加其他获取音频时长的方法
    # 例如使用ffprobe或其他库
    
    return None


def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
    
    Returns:
        Path: 目录Path对象
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def copy_file_safe(source: Union[str, Path], destination: Union[str, Path], 
                  overwrite: bool = False) -> Tuple[bool, str]:
    """
    安全地复制文件
    
    Args:
        source: 源文件路径
        destination: 目标路径
        overwrite: 是否覆盖已存在的文件
    
    Returns:
        (success, message): 操作结果
    """
    try:
        source = Path(source)
        destination = Path(destination)
        
        if not source.exists():
            return False, f"源文件不存在: {source}"
        
        # 如果目标是目录，使用源文件名
        if destination.is_dir():
            destination = destination / source.name
        
        # 检查是否覆盖
        if destination.exists() and not overwrite:
            return False, f"目标文件已存在: {destination}"
        
        # 确保目标目录存在
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # 复制文件
        shutil.copy2(source, destination)
        
        return True, f"文件复制成功: {destination}"
        
    except Exception as e:
        return False, f"文件复制失败: {str(e)}"


def list_files_in_directory(directory: Union[str, Path], 
                           pattern: str = "*",
                           recursive: bool = False) -> List[Path]:
    """
    列出目录中的文件
    
    Args:
        directory: 目录路径
        pattern: 文件匹配模式（如 "*.txt"）
        recursive: 是否递归搜索子目录
    
    Returns:
        List[Path]: 文件路径列表
    """
    directory = Path(directory)
    
    if not directory.exists():
        return []
    
    if recursive:
        return list(directory.rglob(pattern))
    else:
        return list(directory.glob(pattern))


def get_recent_files(directory: Union[str, Path], 
                    count: int = 10,
                    file_types: Optional[List[str]] = None) -> List[Dict[str, any]]:
    """
    获取目录中最近的文件
    
    Args:
        directory: 目录路径
        count: 获取数量
        file_types: 文件类型过滤（如 ['.txt', '.pdf']）
    
    Returns:
        List[Dict]: 文件信息列表
    """
    directory = Path(directory)
    
    if not directory.exists():
        return []
    
    # 获取所有文件
    files = []
    for file_path in directory.iterdir():
        if file_path.is_file():
            if file_types:
                if file_path.suffix.lower() not in file_types:
                    continue
            
            files.append({
                'path': str(file_path),
                'name': file_path.name,
                'size': format_file_size(file_path.stat().st_size),
                'modified': file_path.stat().st_mtime,
                'modified_str': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    
    # 按修改时间排序
    files.sort(key=lambda x: x['modified'], reverse=True)
    
    return files[:count]


def create_unique_filename(directory: Union[str, Path], 
                         base_name: str,
                         extension: str) -> str:
    """
    在目录中创建唯一的文件名
    
    Args:
        directory: 目录路径
        base_name: 基础文件名
        extension: 文件扩展名
    
    Returns:
        str: 唯一的文件名
    """
    directory = Path(directory)
    counter = 1
    
    # 确保扩展名以点开头
    if not extension.startswith('.'):
        extension = f'.{extension}'
    
    # 基础文件名
    filename = f"{base_name}{extension}"
    file_path = directory / filename
    
    # 如果文件已存在，添加数字后缀
    while file_path.exists():
        filename = f"{base_name}_{counter}{extension}"
        file_path = directory / filename
        counter += 1
    
    return filename
