# config_manager.py
# 配置管理模块
# author: zouhong
# date: 2025-11-19
# 说明：
# 本文件实现了VPN客户端的配置管理功能，包括保存、加载、列出、删除VPN连接配置，以及设置默认配置。
# 主要功能包括：
# - 保存VPN连接配置到JSON文件
# - 从JSON文件加载VPN连接配置
# - 列出所有保存的VPN配置名称
# - 删除指定的VPN配置
# - 设置默认VPN配置
import json
import os
from pathlib import Path
from typing import List, Dict, Optional

class VPNConfigManager:
    """管理VPN配置文件"""
    
    def __init__(self, config_dir: str = "~/.sslvpn"):
        self.config_dir = Path(config_dir).expanduser()
        self.config_dir.mkdir(exist_ok=True)
    
    def save_connection_config(self, name: str, config: dict):
        """保存连接配置"""
        config_file = self.config_dir / f"{name}.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def load_connection_config(self, name: str) -> dict:
        """加载连接配置"""
        config_file = self.config_dir / f"{name}.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def list_configs(self) -> List[str]:
        """列出所有保存的配置名称"""
        configs = []
        for file in self.config_dir.glob("*.json"):
            configs.append(file.stem)
        return sorted(configs)
    
    def delete_config(self, name: str) -> bool:
        """删除指定的配置"""
        config_file = self.config_dir / f"{name}.json"
        if config_file.exists():
            config_file.unlink()
            return True
        return False
    
    def get_default_config(self) -> Optional[str]:
        """获取默认配置名称"""
        default_file = self.config_dir / "default"
        if default_file.exists():
            return default_file.read_text().strip()
        return None
    
    def set_default_config(self, name: str):
        """设置默认配置"""
        default_file = self.config_dir / "default"
        default_file.write_text(name)
    
    def create_config_from_args(self, args) -> dict:
        """从命令行参数创建配置字典"""
        config = {
            "server": args.server,
            "port": args.port,
            "username": args.username,
            "ignore_cert_errors": args.ignore_cert
        }
        if hasattr(args, 'password') and args.password:
            config["password"] = args.password
        return config
    
    def validate_config(self, config: dict) -> bool:
        """验证配置是否完整"""
        required_fields = ["server", "port", "username"]
        for field in required_fields:
            if field not in config or not config[field]:
                return False
        return True