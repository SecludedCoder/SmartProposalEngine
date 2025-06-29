#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件路径: smart_proposal_engine/run_app.py
功能说明: SmartProposal Engine启动脚本，支持在PyCharm中直接运行
作者: SmartProposal Team
创建日期: 2025-06-27
最后修改: 2025-06-27
版本: 1.0.0
"""

import os
import sys
import subprocess
import socket
import webbrowser
import time
import argparse
import json
import configparser
from pathlib import Path
from typing import Optional, Dict, Any
import streamlit.web.cli as stcli


def check_port_available(port: int) -> bool:
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return True
        except socket.error:
            return False


def find_available_port(start_port: int = 8501, max_attempts: int = 10) -> Optional[int]:
    """查找可用端口"""
    for i in range(max_attempts):
        port = start_port + i
        if check_port_available(port):
            return port
    return None


def check_dependencies():
    """检查必要的依赖是否已安装"""
    missing_deps = []
    
    # 检查核心依赖
    try:
        import streamlit
    except ImportError:
        missing_deps.append("streamlit")
    
    try:
        import google.generativeai
    except ImportError:
        missing_deps.append("google-generativeai")
    
    try:
        import docx
    except ImportError:
        missing_deps.append("python-docx")
    
    try:
        import PyPDF2
    except ImportError:
        missing_deps.append("PyPDF2")
    
    if missing_deps:
        print("❌ 缺少必要的依赖包:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n请运行以下命令安装依赖:")
        print("   pip install -r requirements.txt")
        return False
    
    return True


def check_environment():
    """检查环境配置"""
    warnings = []
    
    # 检查API密钥配置
    api_key_from_env = os.getenv('GOOGLE_API_KEY')
    api_key_file = Path('api_key.txt')
    
    if not api_key_from_env and not api_key_file.exists():
        warnings.append("""
⚠️  未找到Google API密钥配置
   请使用以下方式之一配置API密钥:
   1. 设置环境变量: export GOOGLE_API_KEY=your_key
   2. 创建.env文件并添加: GOOGLE_API_KEY=your_key
   3. 创建api_key.txt文件并写入密钥
        """)
    
    # 检查必要的目录
    required_dirs = ['temp', 'output', 'prompts']
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"✅ 创建目录: {dir_name}/")
            except Exception as e:
                warnings.append(f"⚠️  无法创建目录 {dir_name}: {e}")
    
    # 检查配置文件
    if not Path('app_config.ini').exists():
        warnings.append("⚠️  未找到app_config.ini配置文件，将使用默认配置")
    
    # 显示警告信息
    if warnings:
        print("\n" + "="*50)
        print("环境检查警告:")
        for warning in warnings:
            print(warning)
        print("="*50 + "\n")
    
    return True  # 即使有警告也继续运行


def load_env_file():
    """加载.env文件中的环境变量"""
    env_file = Path('.env')
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✅ 已加载.env文件")
        except ImportError:
            print("ℹ️  python-dotenv未安装，跳过.env文件加载")


def load_run_config() -> Dict[str, Any]:
    """加载运行配置文件"""
    config = {
        'port': 8501,
        'host': 'localhost',
        'open_browser': True,
        'debug': False,
        'subprocess': False,
        'env_vars': {}
    }
    
    # 尝试多种配置文件格式
    config_files = ['run_config.json', 'run_config.ini', 'run_config.conf']
    
    for config_file in config_files:
        config_path = Path(config_file)
        if config_path.exists():
            print(f"📄 找到配置文件: {config_file}")
            
            if config_file.endswith('.json'):
                # 加载JSON配置
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        file_config = json.load(f)
                        config.update(file_config)
                        print(f"✅ 已加载配置文件: {config_file}")
                        break
                except Exception as e:
                    print(f"⚠️  加载JSON配置失败: {e}")
                    
            elif config_file.endswith(('.ini', '.conf')):
                # 加载INI配置
                try:
                    parser = configparser.ConfigParser()
                    parser.read(config_path, encoding='utf-8')
                    
                    if 'server' in parser:
                        server_config = parser['server']
                        config['port'] = server_config.getint('port', config['port'])
                        config['host'] = server_config.get('host', config['host'])
                        config['open_browser'] = server_config.getboolean('open_browser', config['open_browser'])
                        config['debug'] = server_config.getboolean('debug', config['debug'])
                        config['subprocess'] = server_config.getboolean('subprocess', config['subprocess'])
                    
                    if 'environment' in parser:
                        config['env_vars'] = dict(parser['environment'])
                    
                    print(f"✅ 已加载配置文件: {config_file}")
                    break
                except Exception as e:
                    print(f"⚠️  加载INI配置失败: {e}")
    
    # 设置环境变量
    for key, value in config.get('env_vars', {}).items():
        os.environ[key] = str(value)
        print(f"   设置环境变量: {key}")
    
    return config


def run_streamlit_app(port: int = 8501, 
                     host: str = "localhost",
                     open_browser: bool = True,
                     debug: bool = False):
    """运行Streamlit应用"""
    
    # 设置Streamlit配置
    os.environ['STREAMLIT_SERVER_PORT'] = str(port)
    os.environ['STREAMLIT_SERVER_ADDRESS'] = host
    
    if debug:
        os.environ['STREAMLIT_SERVER_RUN_ON_SAVE'] = 'true'
        os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'auto'
    
    # 构建启动参数
    sys.argv = [
        "streamlit",
        "run",
        "app.py",
        f"--server.port={port}",
        f"--server.address={host}",
    ]
    
    if not open_browser:
        sys.argv.append("--server.headless=true")
    
    if debug:
        sys.argv.extend([
            "--server.runOnSave=true",
            "--server.fileWatcherType=auto",
            "--logger.level=info"
        ])
    
    # 打印启动信息
    print(f"""
╔══════════════════════════════════════════════════════╗
║         SmartProposal Engine 正在启动...             ║
╠══════════════════════════════════════════════════════╣
║  访问地址: http://{host}:{port}                      ║
║  按 Ctrl+C 停止服务                                  ║
╚══════════════════════════════════════════════════════╝
    """)
    
    # 启动Streamlit
    sys.exit(stcli.main())


def run_with_subprocess(port: int = 8501, 
                       host: str = "localhost",
                       open_browser: bool = True,
                       debug: bool = False):
    """使用子进程运行Streamlit（备选方案）"""
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        f"--server.port={port}",
        f"--server.address={host}",
    ]
    
    if not open_browser:
        cmd.append("--server.headless=true")
    
    if debug:
        cmd.extend([
            "--server.runOnSave=true",
            "--server.fileWatcherType=auto",
            "--logger.level=info"
        ])
    
    # 打印启动信息
    print(f"""
╔══════════════════════════════════════════════════════╗
║         SmartProposal Engine 正在启动...             ║
╠══════════════════════════════════════════════════════╣
║  访问地址: http://{host}:{port}                      ║
║  按 Ctrl+C 停止服务                                  ║
╚══════════════════════════════════════════════════════╝
    """)
    
    # 在新窗口中打开浏览器
    if open_browser:
        time.sleep(2)  # 等待服务启动
        webbrowser.open(f"http://{host}:{port}")
    
    # 启动子进程
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n✅ 服务已停止")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='SmartProposal Engine 启动脚本')
    parser.add_argument('--port', type=int, default=8501, help='服务端口 (默认: 8501)')
    parser.add_argument('--host', type=str, default='localhost', help='服务地址 (默认: localhost)')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    parser.add_argument('--subprocess', action='store_true', help='使用子进程模式运行')
    
    args = parser.parse_args()
    
    # 显示启动横幅
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║            🚀 SmartProposal Engine v1.0.0 🚀             ║
    ║                                                           ║
    ║         智能商业方案生成系统 - MVP Edition                ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # 加载环境变量
    load_env_file()
    
    # 检查依赖
    print("🔍 检查系统依赖...")
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请先安装必要的依赖包")
        sys.exit(1)
    print("✅ 依赖检查通过")
    
    # 检查环境
    print("\n🔍 检查运行环境...")
    check_environment()
    
    # 检查端口
    if not check_port_available(args.port):
        print(f"\n⚠️  端口 {args.port} 已被占用，正在查找可用端口...")
        available_port = find_available_port(args.port)
        if available_port:
            args.port = available_port
            print(f"✅ 使用端口: {available_port}")
        else:
            print("❌ 无法找到可用端口，请手动指定端口")
            sys.exit(1)
    
    # 启动应用
    try:
        if args.subprocess:
            # 使用子进程模式
            run_with_subprocess(
                port=args.port,
                host=args.host,
                open_browser=not args.no_browser,
                debug=args.debug
            )
        else:
            # 使用默认模式
            run_streamlit_app(
                port=args.port,
                host=args.host,
                open_browser=not args.no_browser,
                debug=args.debug
            )
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 确保在正确的目录下运行
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # 运行主函数
    main()
