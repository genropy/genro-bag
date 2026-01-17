# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""System Explorer - Explore your system via a Bag.

Usage (REPL):
    >>> from examples.resolvers.system_explorer import explorer
    >>> list(explorer.keys())
    ['system', 'home', 'cwd']
    >>> explorer['system.cpu.count']
    8
    >>> explorer['system.memory.percent']
    65.2
    >>> list(explorer['home'].keys())[:5]
    ['Desktop', 'Documents', 'Downloads', ...]

Requires: pip install psutil
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

from genro_bag import Bag
from genro_bag.resolvers import BagCbResolver, DirectoryResolver

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False


def get_system_info() -> Bag:
    """Collect system information into a Bag."""
    if not HAS_PSUTIL:
        result = Bag()
        result['error'] = 'psutil not installed - run: pip install psutil'
        return result

    result = Bag()

    # CPU info
    result['cpu.count'] = psutil.cpu_count()
    result['cpu.percent'] = psutil.cpu_percent(interval=0.1)
    freq = psutil.cpu_freq()
    if freq:
        result['cpu.freq_mhz'] = round(freq.current)

    # Memory info
    mem = psutil.virtual_memory()
    result['memory.total_gb'] = round(mem.total / (1024**3), 2)
    result['memory.available_gb'] = round(mem.available / (1024**3), 2)
    result['memory.percent'] = mem.percent

    # Disk info (root partition)
    disk = psutil.disk_usage('/')
    result['disk.total_gb'] = round(disk.total / (1024**3), 2)
    result['disk.free_gb'] = round(disk.free / (1024**3), 2)
    result['disk.percent'] = disk.percent

    # Network info
    result['network.hostname'] = socket.gethostname()
    interfaces = list(psutil.net_if_addrs().keys())
    for i, iface in enumerate(interfaces[:5]):
        result[f'network.interfaces.if_{i}'] = iface

    # Current process info
    proc = psutil.Process()
    result['process.pid'] = proc.pid
    result['process.cwd'] = proc.cwd()

    return result


def create_explorer() -> Bag:
    """Create an explorer Bag with system info and directories."""
    bag = Bag()

    # System info (lazy, cached 5 seconds)
    bag['system'] = BagCbResolver(get_system_info, cache_time=5)

    # Home directory (lazy, no file content)
    bag['home'] = DirectoryResolver(str(Path.home()), max_depth=1, ext='')

    # Current working directory (lazy, no file content)
    bag['cwd'] = DirectoryResolver(os.getcwd(), max_depth=2, ext='')

    return bag


# Pre-built explorer for REPL use
explorer = create_explorer()


if __name__ == '__main__':
    print("System Explorer")
    print("=" * 50)
    print()
    print("Keys:", list(explorer.keys()))
    print()
    print("System info:")
    print(f"  CPU cores: {explorer['system.cpu.count']}")
    print(f"  CPU usage: {explorer['system.cpu.percent']}%")
    print(f"  Memory: {explorer['system.memory.available_gb']} GB free")
    print(f"  Disk: {explorer['system.disk.free_gb']} GB free")
    print(f"  Hostname: {explorer['system.network.hostname']}")
    print()
    print("Home directory (first 5):")
    for name in list(explorer['home'].keys())[:5]:
        print(f"  - {name}")
    print()
    print("Use in REPL:")
    print("  >>> from examples.resolvers.system_explorer import explorer")
    print("  >>> explorer['system.cpu.count']")
    print("  >>> list(explorer['home'].keys())[:5]")
