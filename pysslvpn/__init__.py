"""
PySslvpn - A pure Python SSL VPN client implementation

This package provides a complete SSL VPN client implementation in pure Python,
supporting connection to generic SSL VPN servers with features like automatic
reconnection, multiple configuration management, and network configuration
handling.
"""

__version__ = "1.0.2"
__author__ = "PySslvpn Developer"
__email__ = "admin@proyy.com"
__license__ = "GPL-3.0-or-later"

from .main import SSLVPNAuthentication, SSLVPNSession, SSLVPNTunnelProtocol, NetworkConfigManager, SSLVPNClient
from .config_manager import VPNConfigManager
from .cli import main

__all__ = [
    "SSLVPNAuthentication",
    "SSLVPNSession", 
    "SSLVPNTunnelProtocol",
    "NetworkConfigManager",
    "SSLVPNClient",
    "VPNConfigManager",
    "main",
]