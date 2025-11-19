## 项目概述

PySslvpn是一个功能完整的开源Python SSL VPN客户端，支持连接通用SSL VPN服务器，具备多配置管理、自动重连、网络配置自动清理等高级功能。
基于纯Python完整实现的SSL VPN客户端。这个方案使用Python进行TLS通信，并包含完整的VPN客户端功能，作者是[zouhong](https://github.com/proyy/PySslvpn)。

使用说明
安装和运行
安装依赖：

bash
pip install tlslite-ng python-tun-tap
运行客户端：

bash
sudo python cli.py connect vpn.example.com -u your_username

带参数运行：

bash
sudo python cli.py connect vpn.example.com -u your_username -p your_password --port 8443 --ignore-cert

使用已保存的配置：

bash
sudo python cli.py connect --config my_config

启用自动重连：

bash
sudo python cli.py connect vpn.example.com -u your_username --auto-reconnect --max-retries 5 --retry-delay 10
功能特性
✅ 纯Python实现：使用tlslite-ng进行TLS通信 

✅ 通用SSL VPN协议：支持标准SSL VPN服务器

✅ 完整的认证流程：用户名/密码认证

✅ 证书错误处理：可配置忽略无效证书

✅ 动态配置接收：接收服务器下发的路由和DNS

✅ 自动资源清理：断开时清理所有网络配置

✅ TUN接口管理：自动创建和配置虚拟接口

✅ 多配置管理：支持多个VPN配置的保存、切换和管理

✅ 自动重连机制：连接中断时自动重连，可配置重试次数和延迟

✅ 完整CLI界面：支持子命令模式，提供友好的命令行交互

协议说明
这个实现使用简单的应用层协议：

数据包格式：5字节头部（1字节类型 + 4字节长度） + 载荷

包类型：

0: IP数据包

1: 控制消息

2: 认证数据

3: 配置信息

## 配置管理

PySslvpn支持多配置管理，可以保存多个VPN服务器配置：

```bash
# 保存配置
sudo python cli.py save my_config vpn.example.com -u username -p password --port 8443

# 列出所有配置
sudo python cli.py list

# 删除配置
sudo python cli.py delete my_config

# 设置默认配置
sudo python cli.py set-default my_config
```

## CLI命令参考

- `connect`: 连接VPN服务器
- `list`: 列出所有保存的配置
- `save`: 保存新的VPN配置
- `delete`: 删除指定的配置
- `set-default`: 设置默认配置

## 注意事项

权限要求：需要root权限创建TUN设备和管理网络配置

证书安全：生产环境不应使用--ignore-cert选项

平台支持：主要在Linux上测试，其他Unix系统可能需要调整

服务器兼容：需要服务器端实现相同的协议格式

自动重连：启用自动重连时，确保网络环境稳定，避免无限重连

这个实现提供了完整的SSL VPN客户端功能，可以连接支持标准SSL VPN协议的服务器，并正确处理路由、DNS等网络配置。


## 开源协议

本项目采用 GNU General Public License v3.0 (GPL-3.0) 开源协议。

**重要条款：**
- 您可以自由使用、修改和分发本软件
- 任何基于本软件的衍生作品必须采用相同的开源协议
- 必须提供完整的源代码
- 禁止商业使用

完整的协议条款请参阅 [LICENSE](LICENSE) 文件。