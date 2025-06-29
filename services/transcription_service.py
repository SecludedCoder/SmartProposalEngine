#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/services/transcription_service.py
功能说明: 音频转录服务模块，负责处理音频文件的转录和优化
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

import os
import sys
import time
import re
import shutil
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Literal
from dataclasses import dataclass
from pathlib import Path

import google.generativeai as genai

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base_service import BaseService, ProcessingResult
from core.prompt_manager import PromptManager
from core.model_interface import ModelInterface
from utils.file_utils import format_file_size, get_audio_duration
from utils.format_utils import format_duration


@dataclass
class TranscriptionSegment:
    """转录片段数据结构"""
    segment_index: int
    start_time: float
    end_time: float
    text: str
    speakers: List[str]
    segment_id: str = ""


@dataclass
class SpeakerMapping:
    """说话人映射数据结构"""
    segment_speaker: str
    global_speaker: str
    characteristics: str


class TextOptimizer:
    """文本优化器，使用Gemini进行转录文本的校正和优化"""

    def __init__(self, model_interface: ModelInterface, prompt_manager: PromptManager):
        self.model_interface = model_interface
        self.prompt_manager = prompt_manager

    def optimize_transcript(self, original_text: str, progress_callback=None) -> Tuple[str, Dict[str, any]]:
        """优化转录文本"""
        start_time = time.time()

        if progress_callback:
            progress_callback("正在调用Gemini进行文本优化...")

        try:
            # 获取优化模板
            optimization_prompt = self.prompt_manager.get_template(
                'transcription',
                'optimization',
                variables={'transcript': original_text}
            )

            # 调用模型
            response, stats = self.model_interface.generate_content(
                optimization_prompt,
                model_type='optimization'
            )

            stats['optimization_time'] = time.time() - start_time

            # 解析优化结果
            full_response = response
            if "第二部分：优化后转录文本" in full_response:
                parts = full_response.split("第二部分：优化后转录文本")
                if len(parts) > 1:
                    optimized_text = parts[1].strip()
                    optimized_text = optimized_text.replace("```", "").strip()
                else:
                    optimized_text = full_response
            else:
                optimized_text = full_response

            if progress_callback:
                progress_callback(f"文本优化完成，耗时 {stats['optimization_time']:.1f} 秒")

            return optimized_text, stats

        except Exception as e:
            if progress_callback:
                progress_callback(f"文本优化失败：{e}")
            return original_text, {'error': str(e), 'optimization_time': time.time() - start_time}


class AudioProcessor:
    """音频处理类，负责音频文件的分割和预处理"""

    def __init__(self, temp_folder: str):
        self.temp_folder = temp_folder
        self.pydub_available = self._check_pydub_availability()
        self.silence_threshold = -35
        self.min_silence_length = 800

    def _check_pydub_availability(self) -> bool:
        """检查是否安装了 pydub 库"""
        try:
            import pydub
            return True
        except ImportError:
            print("注意：未安装 pydub 库，无法进行音频分割。")
            print("如需处理超长音频，请运行：pip install pydub")
            return False

    def get_audio_duration(self, file_path: str) -> Optional[float]:
        """获取音频文件时长（分钟）"""
        if not self.pydub_available:
            return None

        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(file_path)
            duration_minutes = len(audio) / (1000 * 60)
            return duration_minutes
        except Exception as e:
            print(f"无法获取音频时长：{e}")
            return None

    def get_audio_duration_seconds(self, file_path: str) -> Optional[float]:
        """获取音频文件时长（秒）"""
        if not self.pydub_available:
            return None

        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(file_path)
            duration_seconds = len(audio) / 1000.0
            return duration_seconds
        except Exception as e:
            print(f"无法获取音频时长：{e}")
            return None

    def split_audio(self, file_path: str, max_duration_minutes: int) -> List[Tuple[str, float, float]]:
        """将音频文件按分钟分割成多个片段"""
        if not self.pydub_available:
            return [(file_path, 0, 0)]

        try:
            from pydub import AudioSegment
            from pydub.silence import detect_silence

            print(f"正在分析音频文件...")
            audio = AudioSegment.from_file(file_path)
            total_duration = len(audio)
            max_duration_ms = max_duration_minutes * 60 * 1000

            if total_duration <= max_duration_ms:
                return [(file_path, 0, total_duration / 1000)]

            os.makedirs(self.temp_folder, exist_ok=True)

            print("正在检测静音片段以优化分割点...")
            silence_chunks = detect_silence(
                audio,
                min_silence_len=self.min_silence_length,
                silence_thresh=self.silence_threshold
            )

            segments = []
            current_start = 0
            segment_index = 0

            while current_start < total_duration:
                ideal_end = min(current_start + max_duration_ms, total_duration)
                best_split_point = ideal_end
                search_window = 30000

                for silence_start, silence_end in silence_chunks:
                    if ideal_end - search_window <= silence_start <= ideal_end + search_window:
                        best_split_point = silence_start
                        break

                if best_split_point >= total_duration - 5000:
                    best_split_point = total_duration

                segment = audio[current_start:best_split_point]
                segment_filename = f"segment_{segment_index:03d}.m4a"
                segment_path = os.path.join(self.temp_folder, segment_filename)

                print(f"正在导出片段 {segment_index + 1}: {current_start / 1000:.1f}s - {best_split_point / 1000:.1f}s")
                segment.export(segment_path, format="mp4", codec="aac")

                segments.append((
                    segment_path,
                    current_start / 1000,
                    best_split_point / 1000
                ))

                current_start = best_split_point
                segment_index += 1

            print(f"音频分割完成，共生成 {len(segments)} 个片段")
            return segments

        except Exception as e:
            print(f"音频分割失败：{e}")
            return [(file_path, 0, 0)]

    def cleanup_temp_files(self):
        """清理临时文件"""
        if os.path.exists(self.temp_folder):
            try:
                shutil.rmtree(self.temp_folder)
                print("临时文件已清理")
            except Exception as e:
                print(f"清理临时文件失败：{e}")


class SpeakerAnalyzer:
    """说话人分析器，负责处理说话人识别和一致性维护"""

    def __init__(self):
        self.global_speaker_map: Dict[str, str] = {}
        self.speaker_characteristics: Dict[str, List[str]] = {}
        self.next_global_speaker_id = 1

    def extract_speakers(self, text: str) -> List[str]:
        """从文本中提取说话人标识"""
        speaker_pattern = r'(说话人[A-Z]|说话人\d+|发言人[A-Z]|发言人\d+|Speaker [A-Z]|Speaker \d+)(?=[:：])'
        speakers = list(set(re.findall(speaker_pattern, text)))
        return speakers

    def extract_speaker_characteristics(self, text: str, speaker: str) -> List[str]:
        """提取说话人的语言特征"""
        characteristics = []

        pattern = f'{re.escape(speaker)}[:：](.*?)(?=(说话人|发言人|Speaker|$))'
        matches = re.findall(pattern, text, re.DOTALL)

        if matches:
            combined_text = ' '.join(matches)

            # 提取常用词
            words = re.findall(r'[\u4e00-\u9fa5]+', combined_text)
            word_freq = {}
            for word in words:
                if len(word) >= 2:
                    word_freq[word] = word_freq.get(word, 0) + 1

            frequent_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            if frequent_words:
                characteristics.append(f"常用词：{', '.join([w[0] for w in frequent_words])}")

            # 语言特征分析
            if '嗯' in combined_text or '啊' in combined_text or '呃' in combined_text:
                characteristics.append("有口头禅")
            if '请' in combined_text or '谢谢' in combined_text:
                characteristics.append("礼貌用语多")
            if '我觉得' in combined_text or '我认为' in combined_text:
                characteristics.append("主观表达多")

        return characteristics

    def map_speakers_across_segments(self, segments: List[TranscriptionSegment]) -> Dict[str, str]:
        """跨片段映射说话人，保持一致性"""
        print("\n正在分析说话人特征以保持一致性...")

        for segment in segments:
            for speaker in segment.speakers:
                characteristics = self.extract_speaker_characteristics(segment.text, speaker)

                best_match = None
                best_score = 0

                for global_speaker, char_list in self.speaker_characteristics.items():
                    score = len(set(characteristics) & set(char_list))
                    if score > best_score:
                        best_score = score
                        best_match = global_speaker

                if best_score >= 2:
                    self.global_speaker_map[f"{segment.segment_index}_{speaker}"] = best_match
                    self.speaker_characteristics[best_match].extend(characteristics)
                    self.speaker_characteristics[best_match] = list(set(self.speaker_characteristics[best_match]))
                else:
                    global_speaker = f"说话人{self.next_global_speaker_id}"
                    self.next_global_speaker_id += 1
                    self.global_speaker_map[f"{segment.segment_index}_{speaker}"] = global_speaker
                    self.speaker_characteristics[global_speaker] = characteristics

        return self.global_speaker_map

    def apply_speaker_mapping(self, segment: TranscriptionSegment, mapping: Dict[str, str]) -> str:
        """应用说话人映射到转录文本"""
        text = segment.text

        for speaker in segment.speakers:
            segment_key = f"{segment.segment_index}_{speaker}"
            if segment_key in mapping:
                global_speaker = mapping[segment_key]
                text = text.replace(f"{speaker}:", f"{global_speaker}:")
                text = text.replace(f"{speaker}：", f"{global_speaker}：")

        return text


class TranscriptionService(BaseService):
    """
    音频转录服务

    主要功能:
    - 支持多种音频格式的转录
    - 支持超长音频自动分割
    - 支持多人对话识别
    - 支持文本优化

    使用示例:
        service = TranscriptionService()
        result = service.process(audio_file, options)
    """

    def __init__(self):
        super().__init__()
        self.audio_processor = None
        self.text_optimizer = None
        self.speaker_analyzer = None
        self.prompt_manager = PromptManager()
        self.model_interface = ModelInterface()
        self.temp_folder = "temp_segments"
        self.max_retries = 3
        self.delete_uploaded_files = True

    def get_available_templates(self) -> List[str]:
        """获取可用的转录优化模板"""
        return self.prompt_manager.list_templates('transcription')

    def validate_input(self, input_data: Union[str, bytes, Path]) -> bool:
        """验证输入是否为支持的音频格式"""
        if isinstance(input_data, str):
            # 检查文件扩展名
            supported_formats = ['.m4a', '.mp3', '.wav', '.aac', '.ogg', '.flac', '.mp4']
            return any(input_data.lower().endswith(fmt) for fmt in supported_formats)
        return True

    def process(self,
                input_data: Union[str, bytes, Path],
                template: Optional[str] = None,
                options: Optional[Dict] = None) -> ProcessingResult:
        """
        处理音频文件转录

        Args:
            input_data: 音频文件路径或数据
            template: 转录模板（未使用，保持接口一致）
            options: 处理选项
                - enable_speaker_diarization: 是否启用说话人识别
                - maintain_speaker_consistency: 是否保持说话人一致性
                - max_segment_duration_minutes: 最大片段时长（分钟）
                - enable_text_optimization: 是否启用文本优化
                - mode: 运行模式 ("standard", "enhanced")

        Returns:
            ProcessingResult: 处理结果
        """
        start_time = time.time()

        # 解析选项
        options = options or {}
        enable_speaker_diarization = options.get('enable_speaker_diarization', True)
        maintain_speaker_consistency = options.get('maintain_speaker_consistency', True)
        max_segment_duration_minutes = options.get('max_segment_duration_minutes', 20)
        enable_text_optimization = options.get('enable_text_optimization', False)
        mode = options.get('mode', 'standard')
        progress_callback = options.get('progress_callback', None)

        try:
            # 确保输入是文件路径
            if isinstance(input_data, (bytes, str)) and not os.path.exists(str(input_data)):
                # 如果是字节数据，先保存为临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tmp_file:
                    if isinstance(input_data, bytes):
                        tmp_file.write(input_data)
                    file_path = tmp_file.name
            else:
                file_path = str(input_data)

            # 初始化处理器
            self.audio_processor = AudioProcessor(self.temp_folder)
            if enable_text_optimization:
                self.text_optimizer = TextOptimizer(self.model_interface, self.prompt_manager)
            if enable_speaker_diarization and maintain_speaker_consistency:
                self.speaker_analyzer = SpeakerAnalyzer()

            # 获取文件信息
            file_size = os.path.getsize(file_path)
            duration_minutes = self.audio_processor.get_audio_duration(file_path)
            duration_seconds = duration_minutes * 60 if duration_minutes else None

            # 执行转录
            transcribed_text, metadata = self._transcribe_audio(
                file_path=file_path,
                duration_minutes=duration_minutes,
                enable_speaker_diarization=enable_speaker_diarization,
                maintain_speaker_consistency=maintain_speaker_consistency,
                max_segment_duration_minutes=max_segment_duration_minutes,
                enable_text_optimization=enable_text_optimization,
                progress_callback=progress_callback
            )

            # 构建元数据
            metadata.update({
                'original_file': os.path.basename(file_path),
                'file_size': format_file_size(file_size),
                'duration': format_duration(duration_seconds) if duration_seconds else '未知',
                'processing_mode': mode,
                'enable_text_optimization': enable_text_optimization
            })

            # 统计说话人信息
            if transcribed_text and enable_speaker_diarization:
                speakers = self.speaker_analyzer.extract_speakers(transcribed_text) if self.speaker_analyzer else []
                metadata['speakers_count'] = len(speakers)
                metadata['speakers'] = sorted(speakers)

            processing_time = time.time() - start_time

            return ProcessingResult(
                content=transcribed_text,
                metadata=metadata,
                source_type='audio',
                processing_time=processing_time,
                model_used=metadata.get('model_used', ''),
                tokens_consumed={
                    'input': metadata.get('input_tokens', 0),
                    'output': metadata.get('output_tokens', 0),
                    'total': metadata.get('total_tokens', 0)
                }
            )

        except Exception as e:
            processing_time = time.time() - start_time
            return ProcessingResult(
                content='',
                metadata={'error': str(e)},
                source_type='audio',
                processing_time=processing_time,
                model_used='',
                tokens_consumed={},
                error=str(e)
            )
        finally:
            # 清理资源
            if self.audio_processor:
                self.audio_processor.cleanup_temp_files()

    def _transcribe_audio(self,
                          file_path: str,
                          duration_minutes: Optional[float],
                          enable_speaker_diarization: bool,
                          maintain_speaker_consistency: bool,
                          max_segment_duration_minutes: int,
                          enable_text_optimization: bool,
                          progress_callback) -> Tuple[str, Dict]:
        """内部方法：执行音频转录"""

        total_input_tokens = 0
        total_output_tokens = 0
        model_used = self.model_interface.get_model_name('transcription')

        # 判断是否需要分割
        if duration_minutes and duration_minutes > max_segment_duration_minutes:
            if progress_callback:
                progress_callback(f"检测到长音频文件（{format_duration(duration_minutes * 60)}），将进行分段处理...")

            segments_info = self.audio_processor.split_audio(file_path, max_segment_duration_minutes)

            if len(segments_info) == 1:
                # 无需分割
                transcribed_text, tokens = self._transcribe_single_segment(
                    segments_info[0][0],
                    enable_speaker_diarization,
                    progress_callback
                )
                total_input_tokens += tokens['input']
                total_output_tokens += tokens['output']
            else:
                # 多段处理
                transcription_segments = []
                for i, (segment_path, start_time, end_time) in enumerate(segments_info):
                    if progress_callback:
                        progress_callback(f"正在处理片段 {i + 1}/{len(segments_info)}...")

                    segment_text, tokens = self._transcribe_single_segment(
                        segment_path,
                        enable_speaker_diarization,
                        progress_callback
                    )

                    total_input_tokens += tokens['input']
                    total_output_tokens += tokens['output']

                    if segment_text:
                        segment = TranscriptionSegment(
                            segment_index=i,
                            start_time=start_time,
                            end_time=end_time,
                            text=segment_text,
                            speakers=self.speaker_analyzer.extract_speakers(
                                segment_text) if self.speaker_analyzer else [],
                            segment_id=f"seg{i:03d}"
                        )
                        transcription_segments.append(segment)

                    if i < len(segments_info) - 1:
                        time.sleep(3)

                # 处理说话人一致性
                speaker_mapping = {}
                if maintain_speaker_consistency and self.speaker_analyzer and transcription_segments:
                    speaker_mapping = self.speaker_analyzer.map_speakers_across_segments(transcription_segments)

                # 合并结果
                transcribed_text = self._merge_segments(transcription_segments, speaker_mapping, duration_minutes)
        else:
            # 短音频直接处理
            transcribed_text, tokens = self._transcribe_single_segment(
                file_path,
                enable_speaker_diarization,
                progress_callback
            )
            total_input_tokens += tokens['input']
            total_output_tokens += tokens['output']

        # 文本优化
        original_text = transcribed_text
        if enable_text_optimization and self.text_optimizer and transcribed_text:
            optimized_text, opt_stats = self.text_optimizer.optimize_transcript(
                transcribed_text,
                progress_callback
            )
            if not opt_stats.get('error'):
                transcribed_text = optimized_text
                total_input_tokens += opt_stats.get('input_tokens', 0)
                total_output_tokens += opt_stats.get('output_tokens', 0)

        # 构建元数据
        metadata = {
            'model_used': model_used,
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens,
            'total_tokens': total_input_tokens + total_output_tokens,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        if enable_text_optimization:
            metadata['original_text'] = original_text
            metadata['optimized_text'] = transcribed_text

        # 计算费用
        cost = self.model_interface.calculate_cost(
            total_input_tokens,
            total_output_tokens,
            'transcription'
        )
        metadata['estimated_cost'] = cost

        return transcribed_text, metadata

    def _transcribe_single_segment(self,
                                   file_path: str,
                                   enable_speaker_diarization: bool,
                                   progress_callback,
                                   retry_count: int = 0) -> Tuple[str, Dict[str, int]]:
        """转录单个音频片段"""

        audio_file = None

        try:
            # 上传文件
            if progress_callback:
                progress_callback("正在上传文件到 Google...")

            try:
                audio_file = genai.upload_file(path=file_path)
            except Exception as e:
                if retry_count < self.max_retries:
                    time.sleep(2 ** retry_count)
                    return self._transcribe_single_segment(
                        file_path, enable_speaker_diarization,
                        progress_callback, retry_count + 1
                    )
                else:
                    raise Exception(f"文件上传失败: {e}")

            # 等待文件处理
            while audio_file.state.name == "PROCESSING":
                time.sleep(10)
                audio_file = genai.get_file(audio_file.name)

            if audio_file.state.name == "FAILED":
                raise Exception(f"文件处理失败: {audio_file.state}")

            # 获取转录提示词
            if enable_speaker_diarization:
                prompt = self.prompt_manager.get_template('transcription', 'multi_speaker')
            else:
                prompt = self.prompt_manager.get_template('transcription', 'single_speaker')

            if progress_callback:
                progress_callback(f"正在调用模型进行转录...")

            # 调用模型
            response, stats = self.model_interface.generate_content(
                [prompt, audio_file],
                model_type='transcription'
            )

            return response, {
                'input': stats.get('input_tokens', 0),
                'output': stats.get('output_tokens', 0)
            }

        except Exception as e:
            if retry_count < self.max_retries:
                time.sleep(2 ** retry_count)
                return self._transcribe_single_segment(
                    file_path, enable_speaker_diarization,
                    progress_callback, retry_count + 1
                )
            else:
                raise Exception(f"转录失败: {e}")

        finally:
            # 清理上传的文件
            if audio_file and self.delete_uploaded_files:
                try:
                    genai.delete_file(audio_file.name)
                except:
                    pass

    def _merge_segments(self,
                        segments: List[TranscriptionSegment],
                        speaker_mapping: Dict[str, str],
                        duration_minutes: Optional[float]) -> str:
        """合并转录片段"""
        if not segments:
            return ""

        final_text_parts = []

        # 添加摘要信息
        if speaker_mapping:
            unique_speakers = set(speaker_mapping.values())
            summary = f"===== 转录摘要 =====\n"
            summary += f"总时长：{format_duration(duration_minutes * 60) if duration_minutes else '未知'}\n"
            summary += f"识别到的说话人数：{len(unique_speakers)}\n"
            summary += f"说话人列表：{', '.join(sorted(unique_speakers))}\n"
            summary += "=" * 50 + "\n"
            final_text_parts.append(summary)

        # 处理每个片段
        for segment in segments:
            # 添加时间戳标记
            time_marker = f"\n[{format_duration(segment.start_time)} - {format_duration(segment.end_time)}]\n"
            final_text_parts.append(time_marker)

            # 应用说话人映射
            if speaker_mapping and self.speaker_analyzer:
                mapped_text = self.speaker_analyzer.apply_speaker_mapping(segment, speaker_mapping)
                final_text_parts.append(mapped_text)
            else:
                final_text_parts.append(segment.text)

        return "\n".join(final_text_parts)

    def process_web_text(self, text: str, options: Optional[Dict] = None) -> ProcessingResult:
        """
        处理Web输入的文本（预留接口）

        Args:
            text: 输入的文本内容
            options: 处理选项

        Returns:
            ProcessingResult: 处理结果
        """
        # 对于纯文本输入，如果需要优化，可以直接调用文本优化器
        start_time = time.time()
        options = options or {}

        try:
            if options.get('enable_text_optimization', False):
                if not self.text_optimizer:
                    self.text_optimizer = TextOptimizer(self.model_interface, self.prompt_manager)

                optimized_text, stats = self.text_optimizer.optimize_transcript(
                    text,
                    options.get('progress_callback')
                )

                metadata = {
                    'original_text': text,
                    'optimized_text': optimized_text,
                    'optimization_stats': stats,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                content = optimized_text
            else:
                content = text
                metadata = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

            processing_time = time.time() - start_time

            return ProcessingResult(
                content=content,
                metadata=metadata,
                source_type='text',
                processing_time=processing_time,
                model_used='',
                tokens_consumed={}
            )

        except Exception as e:
            processing_time = time.time() - start_time
            return ProcessingResult(
                content=text,
                metadata={'error': str(e)},
                source_type='text',
                processing_time=processing_time,
                model_used='',
                tokens_consumed={},
                error=str(e)
            )