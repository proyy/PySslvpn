#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

# 读取README文件内容
with open("README.MD", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# 读取requirements.txt
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="pysslvpn",
    version="1.0.0",
    author="PySslvpn Developer",
    author_email="admin@proyy.com",
    description="A pure Python SSL VPN client implementation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/proyy/PySslvpn",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Networking",
        "Topic :: Security",
        "Topic :: Internet",
    ],
    python_requires=">=3.7",
    install_requires=[
        'tlslite-ng>=0.8.0',
    ],
    entry_points={
        "console_scripts": [
            "pysslvpn=pysslvpn.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="vpn ssl client networking security",
    project_urls={
        "Bug Reports": "https://github.com/proyy/PySslvpn/issues",
        "Source": "https://github.com/proyy/PySslvpn",
    },
)