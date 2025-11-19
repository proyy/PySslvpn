#!/usr/bin/env python3
# main.py
# 主程序入口
# author: zouhong
# date: 2025-11-19
# 说明：
# 本文件实现了VPN客户端的主程序入口，负责解析命令行参数、初始化配置管理、连接VPN服务器、处理用户交互等功能。
# 主要功能包括：
# - 解析命令行参数，包括VPN配置名称、用户名、密码、忽略证书错误等
# - 初始化VPN配置管理模块，加载保存的VPN配置
# - 连接到指定的VPN服务器，处理认证和会话建立
# - 处理用户交互，包括显示连接状态、路由配置、DNS服务器配置等
# - 支持自动重连功能，在连接中断后尝试重新连接
"""
Pure Python SSL VPN Client
支持通用SSL VPN服务器连接，路由/DNS配置管理
"""

import asyncio
import json
import struct
import socket
import os
import sys
import logging
from typing import Optional, Dict, List
from pathlib import Path

# 第三方库导入
from tlslite import TLSConnection, HandshakeSettings, Session
try:
    import tuntap
except ImportError:
    from pytuntap import TunTap as tuntap

class SSLVPNAuthentication:
    """处理VPN认证逻辑"""
    
    def __init__(self, username: str, password: str, ignore_cert_errors: bool = False):
        self.username = username
        self.password = password
        self.ignore_cert_errors = ignore_cert_errors
        
    def get_handshake_settings(self) -> HandshakeSettings:
        """配置TLS握手参数"""
        settings = HandshakeSettings()
        settings.supportedVersions = ["TLS 1.3", "TLS 1.2"]
        # 根据是否忽略证书错误调整设置
        if self.ignore_cert_errors:
            settings.verify = False
        return settings

class SSLVPNSession:
    """管理VPN会话状态"""
    
    def __init__(self):
        self.routes: List[str] = []
        self.dns_servers: List[str] = []
        self.interface_ip: Optional[str] = None
        self.is_connected = False
        
    def update_configuration(self, config_data: dict):
        """更新服务器下发的配置"""
        if 'routes' in config_data:
            self.routes = config_data['routes']
        if 'dns_servers' in config_data:
            self.dns_servers = config_data['dns_servers']
        if 'interface_ip' in config_data:
            self.interface_ip = config_data['interface_ip']
            
        logging.info(f"会话配置更新 - IP: {self.interface_ip}, 路由: {self.routes}, DNS: {self.dns_servers}")

class SSLVPNTunnelProtocol:
    """处理VPN隧道数据包协议"""
    
    @staticmethod
    def create_packet_header(packet_type: int, payload_length: int) -> bytes:
        """创建数据包头部
        packet_type: 0=数据, 1=控制, 2=认证, 3=配置
        """
        return struct.pack('!BI', packet_type, payload_length)
    
    @staticmethod
    def parse_packet_header(header: bytes) -> tuple:
        """解析数据包头部"""
        if len(header) < 5:
            raise ValueError("头部长度不足")
        packet_type, payload_length = struct.unpack('!BI', header[:5])
        return packet_type, payload_length
    
    @staticmethod
    def create_auth_packet(username: str, password: str) -> bytes:
        """创建认证数据包"""
        auth_data = json.dumps({
            'username': username,
            'password': password
        }).encode('utf-8')
        
        header = SSLVPNTunnelProtocol.create_packet_header(2, len(auth_data))
        return header + auth_data
    
    @staticmethod
    def create_data_packet(ip_packet: bytes) -> bytes:
        """创建数据包"""
        header = SSLVPNTunnelProtocol.create_packet_header(0, len(ip_packet))
        return header + ip_packet

class NetworkConfigManager:
    """管理系统网络配置（路由、DNS）"""
    
    def __init__(self):
        self.original_resolv_conf = None
        self.added_routes = []
        
    def backup_dns_config(self):
        """备份当前DNS配置"""
        try:
            with open('/etc/resolv.conf', 'r') as f:
                self.original_resolv_conf = f.read()
        except Exception as e:
            logging.warning(f"无法备份DNS配置: {e}")
    
    def restore_dns_config(self):
        """恢复原始DNS配置"""
        if self.original_resolv_conf:
            try:
                with open('/etc/resolv.conf', 'w') as f:
                    f.write(self.original_resolv_conf)
                logging.info("DNS配置已恢复")
            except Exception as e:
                logging.error(f"恢复DNS配置失败: {e}")
    
    def apply_dns_servers(self, dns_servers: List[str]):
        """应用DNS服务器配置"""
        try:
            with open('/etc/resolv.conf', 'w') as f:
                if self.original_resolv_conf:
                    f.write(f"# 由SSL VPN客户端临时配置\n")
                for dns in dns_servers:
                    f.write(f"nameserver {dns}\n")
            logging.info(f"DNS服务器已设置: {dns_servers}")
        except Exception as e:
            logging.error(f"设置DNS服务器失败: {e}")
    
    def add_routes(self, routes: List[str], interface: str):
        """添加路由规则"""
        for route in routes:
            try:
                os.system(f"ip route add {route} dev {interface}")
                self.added_routes.append((route, interface))
                logging.info(f"路由已添加: {route} -> {interface}")
            except Exception as e:
                logging.error(f"添加路由失败 {route}: {e}")
    
    def cleanup_routes(self):
        """清理添加的所有路由"""
        for route, interface in self.added_routes:
            try:
                os.system(f"ip route del {route} dev {interface}")
                logging.info(f"路由已删除: {route}")
            except Exception as e:
                logging.error(f"删除路由失败 {route}: {e}")
        self.added_routes.clear()

class SSLVPNClient:
    """主SSL VPN客户端类"""
    
    def __init__(self, server_ip: str, server_port: int, 
                 username: str, password: str,
                 ignore_cert_errors: bool = False):
        
        self.server_ip = server_ip
        self.server_port = server_port
        self.auth = SSLVPNAuthentication(username, password, ignore_cert_errors)
        self.session = SSLVPNSession()
        self.protocol = SSLVPNTunnelProtocol()
        self.config_manager = NetworkConfigManager()
        
        self.tls_conn: Optional[TLSConnection] = None
        self.tun_interface: Optional[tuntap.TunInterface] = None
        self.is_running = False
        
        # 自动重连配置
        self.auto_reconnect = False
        self.max_retries = 3
        self.retry_delay = 5
        self.current_retries = 0
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    async def connect(self) -> bool:
        """连接到SSL VPN服务器"""
        while True:
            try:
                logging.info(f"连接到SSL VPN服务器 {self.server_ip}:{self.server_port}")
                
                # 创建TCP连接
                reader, writer = await asyncio.open_connection(
                    self.server_ip, self.server_port
                )
                
                # 创建TLS连接
                self.tls_conn = TLSConnection(reader, writer)
                
                # 进行TLS握手
                await self.tls_conn.handshake(
                    settings=self.auth.get_handshake_settings()
                )
                
                logging.info(f"TLS连接建立成功，版本: {self.tls_conn.version}")
                
                # 发送认证信息
                auth_packet = self.protocol.create_auth_packet(
                    self.auth.username, self.auth.password
                )
                await self.tls_conn.write(auth_packet)
                
                # 等待服务器响应
                response = await self.tls_conn.read(1024)
                if await self._handle_server_response(response):
                    self.session.is_connected = True
                    self.current_retries = 0  # 重置重试计数
                    logging.info("VPN连接成功")
                    return True
                    
            except Exception as e:
                logging.error(f"连接失败: {e}")
                await self.cleanup()
                
                # 自动重连逻辑
                if self.auto_reconnect and self.current_retries < self.max_retries:
                    self.current_retries += 1
                    logging.info(f"第 {self.current_retries}/{self.max_retries} 次重试，{self.retry_delay}秒后重连...")
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    return False
    
    async def _handle_server_response(self, response: bytes) -> bool:
        """处理服务器响应"""
        if not response:
            logging.error("服务器无响应")
            return False
            
        try:
            packet_type, length = self.protocol.parse_packet_header(response[:5])
            payload = response[5:5+length]
            
            if packet_type == 3:  # 配置数据包
                config_data = json.loads(payload.decode('utf-8'))
                self.session.update_configuration(config_data)
                return True
            elif packet_type == 1:  # 控制数据包
                control_msg = json.loads(payload.decode('utf-8'))
                if control_msg.get('status') == 'success':
                    return True
                else:
                    logging.error(f"服务器拒绝连接: {control_msg.get('message', '未知错误')}")
                    return False
                    
        except Exception as e:
            logging.error(f"处理服务器响应失败: {e}")
            return False
    
    def setup_tun_interface(self) -> bool:
        """设置TUN虚拟接口"""
        try:
            self.tun_interface = tuntap.TunInterface(name='tun0')
            self.tun_interface.up()
            
            # 配置接口IP
            if self.session.interface_ip:
                os.system(f"ip addr add {self.session.interface_ip} dev tun0")
            
            logging.info("TUN接口设置完成")
            return True
            
        except Exception as e:
            logging.error(f"设置TUN接口失败: {e}")
            return False
    
    def apply_network_configuration(self):
        """应用网络配置（路由、DNS）"""
        # 备份当前DNS配置
        self.config_manager.backup_dns_config()
        
        # 应用DNS服务器
        if self.session.dns_servers:
            self.config_manager.apply_dns_servers(self.session.dns_servers)
        
        # 添加路由
        if self.session.routes:
            self.config_manager.add_routes(self.session.routes, 'tun0')
    
    async def start_tunnel(self):
        """启动VPN隧道"""
        if not self.session.is_connected or not self.tun_interface:
            logging.error("VPN未正确连接")
            return
        
        self.is_running = True
        logging.info("启动VPN隧道数据转发...")
        
        try:
            while self.is_running:
                try:
                    # 同时等待TUN接口和TLS连接的数据
                    tun_ready = asyncio.create_task(
                        asyncio.get_event_loop().run_in_executor(
                            None, self.tun_interface.read, 1500
                        )
                    )
                    tls_ready = asyncio.create_task(self.tls_conn.read(1520))
                    
                    done, pending = await asyncio.wait(
                        [tun_ready, tls_ready],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # 处理TUN到隧道的流量
                    if tun_ready in done:
                        try:
                            packet = tun_ready.result()
                            if packet:
                                tunnel_packet = self.protocol.create_data_packet(packet)
                                await self.tls_conn.write(tunnel_packet)
                        except Exception as e:
                            logging.error(f"处理TUN数据失败: {e}")
                    
                    # 处理隧道到TUN的流量
                    if tls_ready in done:
                        try:
                            data = tls_ready.result()
                            if data:
                                packet_type, length = self.protocol.parse_packet_header(data[:5])
                                if packet_type == 0:  # 数据包
                                    ip_packet = data[5:5+length]
                                    await asyncio.get_event_loop().run_in_executor(
                                        None, self.tun_interface.write, ip_packet
                                    )
                        except Exception as e:
                            logging.error(f"处理隧道数据失败: {e}")
                    
                    # 取消未完成的任务
                    for task in pending:
                        task.cancel()
                        
                except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError) as e:
                    logging.warning(f"连接中断: {e}")
                    
                    # 自动重连逻辑
                    if self.auto_reconnect and self.current_retries < self.max_retries:
                        self.current_retries += 1
                        logging.info(f"第 {self.current_retries}/{self.max_retries} 次重连，{self.retry_delay}秒后重连...")
                        await asyncio.sleep(self.retry_delay)
                        
                        # 尝试重新连接
                        if await self.connect():
                            logging.info("重连成功，恢复隧道")
                            continue
                        else:
                            logging.error("重连失败")
                            break
                    else:
                        logging.error("连接中断且未启用自动重连或达到最大重试次数")
                        break
                    
        except Exception as e:
            logging.error(f"隧道运行错误: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """清理所有资源"""
        self.is_running = False
        self.session.is_connected = False
        
        logging.info("开始清理VPN客户端资源...")
        
        try:
            # 清理网络配置
            self.config_manager.cleanup_routes()
            self.config_manager.restore_dns_config()
            
            # 关闭TUN接口
            if self.tun_interface:
                try:
                    self.tun_interface.down()
                    self.tun_interface.close()
                except Exception as e:
                    logging.error(f"关闭TUN接口失败: {e}")
            
            # 关闭TLS连接
            if self.tls_conn:
                try:
                    await self.tls_conn.close()
                except Exception as e:
                    logging.error(f"关闭TLS连接失败: {e}")
            
            logging.info("VPN客户端清理完成")
            
        except Exception as e:
            logging.error(f"清理资源时出错: {e}")
            # 即使清理出错，也要继续执行，确保资源释放

async def main():
    """主函数示例"""
    # 配置VPN连接参数
    vpn_client = SSLVPNClient(
        server_ip="your-vpn-server.com",
        server_port=443,
        username="your-username",
        password="your-password",
        ignore_cert_errors=True  # 测试环境使用，生产环境应设为False
    )
    
    try:
        # 连接VPN服务器
        if await vpn_client.connect():
            # 设置TUN接口
            if vpn_client.setup_tun_interface():
                # 应用网络配置
                vpn_client.apply_network_configuration()
                # 启动隧道
                await vpn_client.start_tunnel()
        else:
            logging.error("无法连接到VPN服务器")
            
    except KeyboardInterrupt:
        logging.info("用户中断连接")
    finally:
        await vpn_client.cleanup()

if __name__ == "__main__":
    # 需要root权限运行
    if os.geteuid() != 0:
        print("请使用root权限运行此脚本")
        sys.exit(1)
    
    asyncio.run(main())