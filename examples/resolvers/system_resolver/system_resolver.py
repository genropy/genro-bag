# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""SystemResolver - Collects system information from multiple sources.

Gathers platform, Python, user, CPU, disk and network info using only
standard library modules. Optionally adds memory/CPU usage if psutil is available.
"""

import getpass
import os
import platform
import shutil
import socket
import sys
from pathlib import Path
from typing import Any

from genro_bag import Bag
from genro_bag.resolvers import BagResolver

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False


class SystemResolver(BagResolver):
    """Resolver that collects system information into a Bag.

    Collects info from: os, platform, sys, socket, shutil, getpass.
    If psutil is installed, adds CPU/memory usage stats.

    Parameters (class_kwargs):
        cache_time: Cache duration in seconds. Default 5.
        include_env: If True, include environment variables. Default False.

    Example:
        >>> resolver = SystemResolver()
        >>> info = resolver()
        >>> info['platform.system']
        'Darwin'
        >>> info['cpu.count']
        8
    """

    class_kwargs: dict[str, Any] = {
        **BagResolver.class_kwargs,
        "cache_time": 5,
        "include_env": False,
    }
    internal_params = BagResolver.internal_params | {"include_env"}

    def load(self) -> Bag:
        """Collect system information into a Bag."""
        result = Bag()

        # Platform/OS info
        result["platform.system"] = platform.system()
        result["platform.release"] = platform.release()
        result["platform.version"] = platform.version()
        result["platform.machine"] = platform.machine()
        result["platform.node"] = platform.node()
        result["platform.processor"] = platform.processor()

        # Python info
        result["python.version"] = platform.python_version()
        result["python.implementation"] = platform.python_implementation()
        result["python.executable"] = sys.executable
        result["python.prefix"] = sys.prefix

        # User info
        result["user.name"] = getpass.getuser()
        result["user.home"] = str(Path.home())
        result["user.cwd"] = os.getcwd()

        # CPU info
        result["cpu.count"] = os.cpu_count()

        # Disk info (root partition)
        disk = shutil.disk_usage("/")
        result["disk.total_gb"] = round(disk.total / (1024**3), 2)
        result["disk.used_gb"] = round(disk.used / (1024**3), 2)
        result["disk.free_gb"] = round(disk.free / (1024**3), 2)
        result["disk.percent"] = round(disk.used / disk.total * 100, 1)

        # Network info
        result["network.hostname"] = socket.gethostname()
        result["network.fqdn"] = socket.getfqdn()

        # Environment variables (optional)
        if self._kw.get("include_env"):
            for key, value in os.environ.items():
                result[f"env.{key}"] = value

        # Extra info if psutil available
        if HAS_PSUTIL:
            result["cpu.percent"] = psutil.cpu_percent(interval=0.1)
            freq = psutil.cpu_freq()
            if freq:
                result["cpu.freq_mhz"] = round(freq.current)

            mem = psutil.virtual_memory()
            result["memory.total_gb"] = round(mem.total / (1024**3), 2)
            result["memory.available_gb"] = round(mem.available / (1024**3), 2)
            result["memory.percent"] = mem.percent

        return result
