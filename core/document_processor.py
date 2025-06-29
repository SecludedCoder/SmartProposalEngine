#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/core/document_processor.py
功能说明: 文档处理器，负责协调各种文档和音频处理服务
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

import os
import sys
from typing import Dict, List, Optional, Union, Tuple, Any
from pathlib import Path
from datetime import datetime
import mimetypes

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base_service import ProcessingResult
from services.transcription_service import TranscriptionService
from services.document_service import DocumentService
from utils.file_utils import get_file_type, get_file_extension, validate_file_size
from utils.validation_utils import validate_file_type


class DocumentProcessor:
    """
    文档处理器

    主要功能:
    1. 统一的文件处理接口
    2. 自动识别文件类型并调用相应服务
    3. 支持音频和文档的统一处理
    4. 批量文件处理支持

    使用示例:
        processor = DocumentProcessor()
        result = processor.process_file(file_path, options)
    """

    def __init__(self):
        """初始化文档处理器"""
        self.transcription_service = TranscriptionService()
        self.document_service = DocumentService()
        self.supported_types = self._get_supported_types()

    def _get_supported_types(self) -> Dict[str, List[str]]:
        """获取支持的文件类型"""
        return {
            'audio': ['.m4a', '.mp3', '.wav', '.aac', '.ogg', '.flac', '.mp4'],
            'document': ['.docx', '.pdf', '.txt', '.doc', '.rtf', '.odt']
        }

    def process_file(self,
                     file_path: Union[str, Path],
                     options: Optional[Dict] = None) -> ProcessingResult:
        """
        处理单个文件

        Args:
            file_path: 文件路径
            options: 处理选项
                - max_file_size_mb: 最大文件大小限制
                - enable_text_optimization: 是否启用文本优化（音频）
                - extract_metadata: 是否提取元数据（文档）
                - progress_callback: 进度回调函数

        Returns:
            ProcessingResult: 处理结果
        """
        options = options or {}
        progress_callback = options.get('progress_callback')

        try:
            # 验证文件
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")

            # 验证文件大小
            max_size_mb = options.get('max_file_size_mb', 200)
            is_valid_size, size_msg = validate_file_size(file_path, max_size_mb)
            if not is_valid_size:
                raise ValueError(size_msg)

            # 获取文件类型
            file_type = get_file_type(file_path)
            file_ext = get_file_extension(file_path)

            if progress_callback:
                progress_callback(f"正在处理 {file_type} 文件: {file_path.name}")

            # 根据文件类型调用相应服务
            if file_type == 'audio':
                # 音频文件使用转录服务
                result = self.transcription_service.process(
                    file_path,
                    options=options
                )
            elif file_type == 'document':
                # 文档文件使用文档服务
                result = self.document_service.process(
                    file_path,
                    options=options
                )
            else:
                # 尝试作为文本文档处理
                if progress_callback:
                    progress_callback(f"未知文件类型 {file_ext}，尝试作为文本处理")

                result = self.document_service.process(
                    file_path,
                    options=options
                )

            # 添加处理器信息到元数据
            result.metadata['processor'] = 'DocumentProcessor'
            result.metadata['file_type_detected'] = file_type

            return result

        except Exception as e:
            if progress_callback:
                progress_callback(f"文件处理失败: {str(e)}")

            return ProcessingResult(
                content='',
                metadata={
                    'error': str(e),
                    'file_path': str(file_path),
                    'processor': 'DocumentProcessor'
                },
                source_type='unknown',
                processing_time=0,
                model_used='',
                tokens_consumed={},
                error=str(e)
            )

    def process_text_input(self,
                           text: str,
                           input_type: str = 'text',
                           options: Optional[Dict] = None) -> ProcessingResult:
        """
        处理文本输入

        Args:
            text: 输入文本
            input_type: 输入类型 ('text', 'transcript')
            options: 处理选项

        Returns:
            ProcessingResult: 处理结果
        """
        options = options or {}

        try:
            # 如果是转录文本且需要优化
            if input_type == 'transcript' and options.get('enable_text_optimization', False):
                result = self.transcription_service.process_web_text(text, options)
            else:
                # 直接返回文本作为结果
                result = ProcessingResult(
                    content=text,
                    metadata={
                        'input_type': input_type,
                        'text_length': len(text),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    },
                    source_type='text',
                    processing_time=0,
                    model_used='',
                    tokens_consumed={}
                )

            return result

        except Exception as e:
            return ProcessingResult(
                content=text,
                metadata={'error': str(e)},
                source_type='text',
                processing_time=0,
                model_used='',
                tokens_consumed={},
                error=str(e)
            )

    def batch_process_files(self,
                            file_paths: List[Union[str, Path]],
                            options: Optional[Dict] = None) -> List[ProcessingResult]:
        """
        批量处理文件

        Args:
            file_paths: 文件路径列表
            options: 处理选项

        Returns:
            List[ProcessingResult]: 处理结果列表
        """
        options = options or {}
        results = []
        progress_callback = options.get('progress_callback')

        total_files = len(file_paths)

        for i, file_path in enumerate(file_paths):
            if progress_callback:
                progress_callback(f"处理文件 {i + 1}/{total_files}")

            # 为每个文件创建独立的选项
            file_options = options.copy()
            file_options['file_index'] = i
            file_options['total_files'] = total_files

            result = self.process_file(file_path, file_options)
            results.append(result)

        return results

    def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        获取文件信息（不处理文件）

        Args:
            file_path: 文件路径

        Returns:
            Dict: 文件信息
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return {'error': '文件不存在'}

        file_type = get_file_type(file_path)
        file_ext = get_file_extension(file_path)
        file_size = file_path.stat().st_size

        info = {
            'name': file_path.name,
            'path': str(file_path.absolute()),
            'type': file_type,
            'extension': file_ext,
            'size_bytes': file_size,
            'size_formatted': f"{file_size / (1024 * 1024):.2f} MB",
            'mime_type': mimetypes.guess_type(str(file_path))[0] or 'unknown',
            'created': datetime.fromtimestamp(file_path.stat().st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        }

        # 音频文件特有信息
        if file_type == 'audio':
            from utils.file_utils import get_audio_duration
            duration = get_audio_duration(file_path)
            if duration:
                info['duration_seconds'] = duration
                info['duration_formatted'] = f"{int(duration // 60)}:{int(duration % 60):02d}"

        return info

    def validate_file(self,
                      file_path: Union[str, Path],
                      file_type_required: Optional[str] = None) -> Tuple[bool, str]:
        """
        验证文件是否可以处理

        Args:
            file_path: 文件路径
            file_type_required: 要求的文件类型 ('audio', 'document', None表示任意)

        Returns:
            (is_valid, message): 验证结果
        """
        file_path = Path(file_path)

        # 检查文件存在性
        if not file_path.exists():
            return False, "文件不存在"

        # 检查文件类型
        file_type = get_file_type(file_path)
        file_ext = get_file_extension(file_path)

        if file_type_required:
            if file_type != file_type_required:
                return False, f"文件类型不匹配，需要 {file_type_required}，实际为 {file_type}"

        # 检查是否支持该格式
        supported = False
        for ftype, extensions in self.supported_types.items():
            if file_ext in extensions:
                supported = True
                break

        if not supported:
            return False, f"不支持的文件格式: {file_ext}"

        return True, f"文件有效: {file_type} ({file_ext})"

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """获取支持的文件格式"""
        return self.supported_types.copy()

    def estimate_processing_time(self,
                                 file_path: Union[str, Path]) -> Optional[int]:
        """
        估算处理时间（秒）

        Args:
            file_path: 文件路径

        Returns:
            int: 估算的处理时间（秒）
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return None

        file_type = get_file_type(file_path)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)

        # 基于文件类型和大小的简单估算
        if file_type == 'audio':
            # 音频文件：考虑时长
            from utils.file_utils import get_audio_duration
            duration = get_audio_duration(file_path)
            if duration:
                # 大约每分钟音频需要10秒处理时间
                return int(duration / 60 * 10)
            else:
                # 基于文件大小估算
                return int(file_size_mb * 5)

        elif file_type == 'document':
            # 文档文件：基于大小
            # 大约每MB需要2秒处理时间
            return int(file_size_mb * 2)

        else:
            # 未知类型：保守估算
            return int(file_size_mb * 3)