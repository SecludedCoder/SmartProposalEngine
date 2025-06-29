#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/core/session_manager.py
功能说明: 会话状态管理器，管理跨页面的数据流转
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

import os
import sys
import json
import pickle
import shutil
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import tempfile

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base_service import ProcessingResult
from utils.file_utils import ensure_directory_exists, cleanup_directory


class SessionData:
    """会话数据类，存储单个处理会话的所有信息"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.workflow_type = None  # 工作流类型
        self.current_step = None   # 当前步骤
        self.data = {}            # 各步骤的数据
        self.files = {}           # 关联的文件路径
        self.metadata = {}        # 元数据
        self.status = "active"    # 状态：active, completed, error
        
    def update(self, key: str, value: Any):
        """更新数据"""
        self.data[key] = value
        self.updated_at = datetime.now()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取数据"""
        return self.data.get(key, default)
    
    def add_file(self, file_type: str, file_path: str):
        """添加文件引用"""
        self.files[file_type] = file_path
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'workflow_type': self.workflow_type,
            'current_step': self.current_step,
            'data': self.data,
            'files': self.files,
            'metadata': self.metadata,
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionData':
        """从字典创建实例"""
        session = cls(data['session_id'])
        session.created_at = datetime.fromisoformat(data['created_at'])
        session.updated_at = datetime.fromisoformat(data['updated_at'])
        session.workflow_type = data.get('workflow_type')
        session.current_step = data.get('current_step')
        session.data = data.get('data', {})
        session.files = data.get('files', {})
        session.metadata = data.get('metadata', {})
        session.status = data.get('status', 'active')
        return session


class SessionManager:
    """
    会话状态管理器
    
    主要功能:
    1. 管理Streamlit session state
    2. 数据在各环节间的传递
    3. 临时文件管理
    4. 结果缓存
    
    使用示例:
        sm = SessionManager()
        sm.save_result('transcription', result)
        result = sm.get_result('transcription')
    """
    
    def __init__(self, temp_dir: Optional[str] = None, max_sessions: int = 100):
        """
        初始化会话管理器
        
        Args:
            temp_dir: 临时文件目录
            max_sessions: 最大会话数量
        """
        if temp_dir is None:
            temp_dir = os.path.join(tempfile.gettempdir(), 'smartproposal_sessions')
        
        self.temp_dir = Path(temp_dir)
        self.max_sessions = max_sessions
        self.sessions: Dict[str, SessionData] = {}
        self.current_session_id: Optional[str] = None
        
        # 确保临时目录存在
        ensure_directory_exists(self.temp_dir)
        
        # 加载已有会话（如果需要持久化）
        self._load_sessions()
    
    def create_session(self, workflow_type: str = 'default') -> str:
        """
        创建新会话
        
        Args:
            workflow_type: 工作流类型
        
        Returns:
            str: 会话ID
        """
        # 生成唯一会话ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = hashlib.md5(os.urandom(16)).hexdigest()[:8]
        session_id = f"{workflow_type}_{timestamp}_{random_suffix}"
        
        # 创建会话数据
        session = SessionData(session_id)
        session.workflow_type = workflow_type
        
        # 创建会话目录
        session_dir = self.temp_dir / session_id
        ensure_directory_exists(session_dir)
        
        # 保存会话
        self.sessions[session_id] = session
        self.current_session_id = session_id
        
        # 清理过期会话
        self._cleanup_old_sessions()
        
        return session_id
    
    def get_current_session(self) -> Optional[SessionData]:
        """获取当前会话"""
        if self.current_session_id and self.current_session_id in self.sessions:
            return self.sessions[self.current_session_id]
        return None
    
    def set_current_session(self, session_id: str) -> bool:
        """
        设置当前会话
        
        Args:
            session_id: 会话ID
        
        Returns:
            bool: 是否设置成功
        """
        if session_id in self.sessions:
            self.current_session_id = session_id
            return True
        return False
    
    def save_result(self, 
                   step_name: str, 
                   result: Union[ProcessingResult, Dict, str],
                   session_id: Optional[str] = None) -> bool:
        """
        保存处理结果
        
        Args:
            step_name: 步骤名称（如 'transcription', 'analysis', 'proposal'）
            result: 处理结果
            session_id: 会话ID（如果为None则使用当前会话）
        
        Returns:
            bool: 是否保存成功
        """
        session_id = session_id or self.current_session_id
        if not session_id or session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        # 转换ProcessingResult为可序列化格式
        if isinstance(result, ProcessingResult):
            result_data = result.to_dict()
        else:
            result_data = result
        
        # 保存到会话数据
        session.update(f"{step_name}_result", result_data)
        session.current_step = step_name
        
        # 如果结果包含文件内容，考虑保存到文件
        if isinstance(result, ProcessingResult) and len(result.content) > 10000:
            # 大内容保存到文件
            file_path = self._save_content_to_file(
                session_id, 
                step_name, 
                result.content
            )
            session.add_file(f"{step_name}_content", str(file_path))
        
        return True
    
    def get_result(self, 
                  step_name: str,
                  session_id: Optional[str] = None) -> Optional[ProcessingResult]:
        """
        获取处理结果
        
        Args:
            step_name: 步骤名称
            session_id: 会话ID
        
        Returns:
            ProcessingResult: 处理结果
        """
        session_id = session_id or self.current_session_id
        if not session_id or session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        result_data = session.get(f"{step_name}_result")
        
        if not result_data:
            return None
        
        # 如果内容保存在文件中，读取文件
        content_file = session.files.get(f"{step_name}_content")
        if content_file and os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                result_data['content'] = f.read()
        
        # 转换回ProcessingResult对象
        if isinstance(result_data, dict) and 'content' in result_data:
            return ProcessingResult.from_dict(result_data)
        
        return result_data
    
    def save_file(self,
                 file_type: str,
                 file_path: str,
                 session_id: Optional[str] = None) -> bool:
        """
        保存文件引用
        
        Args:
            file_type: 文件类型
            file_path: 文件路径
            session_id: 会话ID
        
        Returns:
            bool: 是否保存成功
        """
        session_id = session_id or self.current_session_id
        if not session_id or session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        session.add_file(file_type, file_path)
        return True
    
    def get_file(self,
                file_type: str,
                session_id: Optional[str] = None) -> Optional[str]:
        """
        获取文件路径
        
        Args:
            file_type: 文件类型
            session_id: 会话ID
        
        Returns:
            str: 文件路径
        """
        session_id = session_id or self.current_session_id
        if not session_id or session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        return session.files.get(file_type)
    
    def transfer_between_steps(self,
                             from_step: str,
                             to_step: str,
                             transform_func: Optional[callable] = None) -> bool:
        """
        在步骤间传递数据
        
        Args:
            from_step: 源步骤
            to_step: 目标步骤
            transform_func: 数据转换函数（可选）
        
        Returns:
            bool: 是否传递成功
        """
        # 获取源数据
        source_result = self.get_result(from_step)
        if not source_result:
            return False
        
        # 应用转换函数（如果提供）
        if transform_func:
            try:
                transformed_data = transform_func(source_result)
            except Exception as e:
                print(f"数据转换失败: {e}")
                return False
        else:
            transformed_data = source_result
        
        # 保存到目标步骤
        return self.save_result(to_step, transformed_data)
    
    def get_workflow_status(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取工作流状态
        
        Returns:
            Dict: 工作流状态信息
        """
        session_id = session_id or self.current_session_id
        if not session_id or session_id not in self.sessions:
            return {'status': 'no_session'}
        
        session = self.sessions[session_id]
        
        # 检查各步骤完成情况
        steps_status = {
            'transcription': bool(session.get('transcription_result')),
            'analysis': bool(session.get('analysis_result')),
            'proposal': bool(session.get('proposal_result'))
        }
        
        return {
            'session_id': session_id,
            'workflow_type': session.workflow_type,
            'current_step': session.current_step,
            'steps_completed': steps_status,
            'status': session.status,
            'created_at': session.created_at,
            'updated_at': session.updated_at
        }
    
    def export_all_results(self, 
                          session_id: Optional[str] = None,
                          output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        导出所有结果
        
        Args:
            session_id: 会话ID
            output_dir: 输出目录
        
        Returns:
            Dict[str, str]: 导出的文件路径映射
        """
        session_id = session_id or self.current_session_id
        if not session_id or session_id not in self.sessions:
            return {}
        
        session = self.sessions[session_id]
        
        if output_dir is None:
            output_dir = os.path.join('output', session_id)
        
        ensure_directory_exists(output_dir)
        
        exported_files = {}
        
        # 导出各步骤结果
        for step in ['transcription', 'analysis', 'proposal']:
            result = self.get_result(step, session_id)
            if result and isinstance(result, ProcessingResult):
                # 导出内容
                file_name = f"{step}_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                file_path = os.path.join(output_dir, file_name)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    # 写入元数据
                    f.write(f"# {step.capitalize()} Result\n\n")
                    f.write(f"**Generated at**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"**Model**: {result.model_used}\n")
                    f.write(f"**Processing Time**: {result.processing_time:.2f}s\n\n")
                    f.write("---\n\n")
                    
                    # 写入内容
                    f.write(result.content)
                
                exported_files[step] = file_path
        
        # 导出会话信息
        session_info_path = os.path.join(output_dir, 'session_info.json')
        with open(session_info_path, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
        
        exported_files['session_info'] = session_info_path
        
        return exported_files
    
    def clear_session(self, session_id: Optional[str] = None) -> bool:
        """
        清理会话数据
        
        Args:
            session_id: 会话ID
        
        Returns:
            bool: 是否清理成功
        """
        session_id = session_id or self.current_session_id
        if not session_id or session_id not in self.sessions:
            return False
        
        # 清理会话目录
        session_dir = self.temp_dir / session_id
        if session_dir.exists():
            cleanup_directory(session_dir, safe_mode=False)
        
        # 删除会话数据
        del self.sessions[session_id]
        
        # 如果是当前会话，清空当前会话ID
        if session_id == self.current_session_id:
            self.current_session_id = None
        
        return True
    
    def list_sessions(self, 
                     active_only: bool = True,
                     limit: int = 10) -> List[Dict[str, Any]]:
        """
        列出会话
        
        Args:
            active_only: 是否只列出活动会话
            limit: 限制数量
        
        Returns:
            List[Dict]: 会话列表
        """
        sessions_list = []
        
        for session_id, session in self.sessions.items():
            if active_only and session.status != 'active':
                continue
            
            sessions_list.append({
                'session_id': session_id,
                'workflow_type': session.workflow_type,
                'current_step': session.current_step,
                'status': session.status,
                'created_at': session.created_at,
                'updated_at': session.updated_at
            })
        
        # 按更新时间排序
        sessions_list.sort(key=lambda x: x['updated_at'], reverse=True)
        
        return sessions_list[:limit]
    
    def _save_content_to_file(self, 
                            session_id: str,
                            step_name: str,
                            content: str) -> Path:
        """保存内容到文件"""
        session_dir = self.temp_dir / session_id
        ensure_directory_exists(session_dir)
        
        file_name = f"{step_name}_content.txt"
        file_path = session_dir / file_name
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def _cleanup_old_sessions(self):
        """清理过期会话"""
        if len(self.sessions) <= self.max_sessions:
            return
        
        # 按更新时间排序
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1].updated_at
        )
        
        # 删除最旧的会话
        to_remove = len(self.sessions) - self.max_sessions
        for session_id, _ in sorted_sessions[:to_remove]:
            self.clear_session(session_id)
    
    def _load_sessions(self):
        """加载已保存的会话（如果需要持久化）"""
        # MVP版本暂不实现持久化
        pass
    
    def _save_sessions(self):
        """保存会话（如果需要持久化）"""
        # MVP版本暂不实现持久化
        pass
    
    def cleanup_all_temp_files(self):
        """清理所有临时文件"""
        try:
            if self.temp_dir.exists():
                for session_dir in self.temp_dir.iterdir():
                    if session_dir.is_dir():
                        cleanup_directory(session_dir, safe_mode=False)
            return True
        except Exception as e:
            print(f"清理临时文件失败: {e}")
            return False
    
    def get_session_size(self, session_id: Optional[str] = None) -> int:
        """
        获取会话占用的磁盘空间
        
        Returns:
            int: 字节数
        """
        session_id = session_id or self.current_session_id
        if not session_id:
            return 0
        
        session_dir = self.temp_dir / session_id
        if not session_dir.exists():
            return 0
        
        total_size = 0
        for file_path in session_dir.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_sessions = len(self.sessions)
        active_sessions = sum(1 for s in self.sessions.values() if s.status == 'active')
        completed_sessions = sum(1 for s in self.sessions.values() if s.status == 'completed')
        
        # 计算总磁盘使用
        total_disk_usage = 0
        for session_id in self.sessions:
            total_disk_usage += self.get_session_size(session_id)
        
        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'completed_sessions': completed_sessions,
            'total_disk_usage_mb': total_disk_usage / (1024 * 1024),
            'current_session_id': self.current_session_id
        }
