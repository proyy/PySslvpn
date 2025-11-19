# cli.py
# 命令行接口
# author: zouhong
# date: 2025-11-19
# 说明：
# 本文件实现了VPN客户端的命令行接口，用户可以通过命令行参数配置和管理VPN连接。
# 主要功能包括：
# - 连接到VPN服务器
# - 列出所有保存的VPN配置
# - 保存新的VPN配置
# - 删除指定的VPN配置
# - 设置默认VPN配置
import argparse
import asyncio
import getpass
import sys
import os
from .config_manager import VPNConfigManager

async def start_vpn_connection(args, config_manager: VPNConfigManager):
    """启动VPN连接"""
    from main import SSLVPNClient
    
    # 获取配置
    if args.config:
        config = config_manager.load_connection_config(args.config)
        if not config:
            print(f"错误: 配置 '{args.config}' 不存在")
            return
        
        server = config["server"]
        port = config["port"]
        username = config["username"]
        password = config.get("password")
        ignore_cert = config.get("ignore_cert_errors", False)
    else:
        server = args.server
        port = args.port
        username = args.username
        password = args.password
        ignore_cert = args.ignore_cert
    
    # 密码处理
    if not password:
        password = getpass.getpass("请输入VPN密码: ")
    
    vpn_client = SSLVPNClient(
        server_ip=server,
        server_port=port,
        username=username,
        password=password,
        ignore_cert_errors=ignore_cert
    )
    
    # 设置自动重连
    vpn_client.auto_reconnect = args.auto_reconnect
    vpn_client.max_retries = args.max_retries
    vpn_client.retry_delay = args.retry_delay
    
    try:
        if await vpn_client.connect():
            if vpn_client.setup_tun_interface():
                vpn_client.apply_network_configuration()
                await vpn_client.start_tunnel()
    except KeyboardInterrupt:
        print("\n断开连接...")
    finally:
        await vpn_client.cleanup()

async def list_configs(config_manager: VPNConfigManager):
    """列出所有配置"""
    configs = config_manager.list_configs()
    default_config = config_manager.get_default_config()
    
    if not configs:
        print("没有保存的配置")
        return
    
    print("已保存的VPN配置:")
    for config_name in configs:
        marker = "*" if config_name == default_config else " "
        print(f"  {marker} {config_name}")
    print("\n(* 表示默认配置)")

async def save_config(args, config_manager: VPNConfigManager):
    """保存配置"""
    config = config_manager.create_config_from_args(args)
    
    if not config_manager.validate_config(config):
        print("错误: 配置不完整，请检查服务器地址、端口和用户名")
        return
    
    config_manager.save_connection_config(args.name, config)
    
    if args.set_default:
        config_manager.set_default_config(args.name)
        print(f"配置 '{args.name}' 已保存并设为默认")
    else:
        print(f"配置 '{args.name}' 已保存")

async def delete_config(args, config_manager: VPNConfigManager):
    """删除配置"""
    if config_manager.delete_config(args.name):
        print(f"配置 '{args.name}' 已删除")
    else:
        print(f"错误: 配置 '{args.name}' 不存在")

async def set_default_config(args, config_manager: VPNConfigManager):
    """设置默认配置"""
    config = config_manager.load_connection_config(args.name)
    if config:
        config_manager.set_default_config(args.name)
        print(f"配置 '{args.name}' 已设为默认")
    else:
        print(f"错误: 配置 '{args.name}' 不存在")

def main():
    config_manager = VPNConfigManager()
    
    parser = argparse.ArgumentParser(description="SSL VPN客户端")
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # connect 子命令
    connect_parser = subparsers.add_parser('connect', help='连接VPN')
    connect_parser.add_argument("server", nargs='?', help="VPN服务器地址")
    connect_parser.add_argument("-p", "--port", type=int, default=443, help="VPN服务器端口")
    connect_parser.add_argument("-u", "--username", help="用户名")
    connect_parser.add_argument("-P", "--password", help="密码（可选，不提供则会提示输入）")
    connect_parser.add_argument("--ignore-cert", action="store_true", 
                               help="忽略服务器证书错误")
    connect_parser.add_argument("-c", "--config", help="使用已保存的配置")
    connect_parser.add_argument("--auto-reconnect", action="store_true",
                               help="自动重连")
    connect_parser.add_argument("--max-retries", type=int, default=3,
                               help="最大重试次数")
    connect_parser.add_argument("--retry-delay", type=int, default=5,
                               help="重试延迟（秒）")
    
    # list 子命令
    subparsers.add_parser('list', help='列出所有配置')
    
    # save 子命令
    save_parser = subparsers.add_parser('save', help='保存当前配置')
    save_parser.add_argument("name", help="配置名称")
    save_parser.add_argument("server", help="VPN服务器地址")
    save_parser.add_argument("-p", "--port", type=int, default=443, help="VPN服务器端口")
    save_parser.add_argument("-u", "--username", required=True, help="用户名")
    save_parser.add_argument("-P", "--password", help="密码")
    save_parser.add_argument("--ignore-cert", action="store_true", 
                           help="忽略服务器证书错误")
    save_parser.add_argument("--set-default", action="store_true",
                           help="设为默认配置")
    
    # delete 子命令
    delete_parser = subparsers.add_parser('delete', help='删除配置')
    delete_parser.add_argument("name", help="配置名称")
    
    # set-default 子命令
    default_parser = subparsers.add_parser('set-default', help='设置默认配置')
    default_parser.add_argument("name", help="配置名称")
    
    args = parser.parse_args()
    
    # 检查root权限（仅连接时需要）
    if args.command == 'connect' and os.geteuid() != 0:
        print("错误: 需要root权限运行此程序")
        sys.exit(1)
    
    # 处理子命令
    if args.command == 'connect':
        if not args.config and not args.server:
            print("错误: 需要指定服务器地址或使用 --config 选项")
            sys.exit(1)
        asyncio.run(start_vpn_connection(args, config_manager))
    elif args.command == 'list':
        asyncio.run(list_configs(config_manager))
    elif args.command == 'save':
        asyncio.run(save_config(args, config_manager))
    elif args.command == 'delete':
        asyncio.run(delete_config(args, config_manager))
    elif args.command == 'set-default':
        asyncio.run(set_default_config(args, config_manager))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()