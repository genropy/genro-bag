# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Example: using SystemResolver to collect system information.

SystemResolver gathers platform, Python, user, CPU, disk and network info.
Optionally adds memory/CPU usage if psutil is available.
"""

from genro_bag import Bag
from genro_bag.resolvers.contrib.system_resolver import SystemResolver


def main():
    bag = Bag()

    # Basic system info (cached 5 seconds)
    bag["system"] = SystemResolver()
    print("Platform:", bag["system.platform.system"])
    print("CPU count:", bag["system.cpu.count"])
    print("Disk free:", bag["system.disk.free_gb"], "GB")
    print("Hostname:", bag["system.network.hostname"])

    # With environment variables
    bag["system_env"] = SystemResolver(include_env=True)
    print("HOME:", bag["system_env.env.HOME"])

    # Full tree
    print("\nFull system info:")
    print(bag["system"])


if __name__ == "__main__":
    main()
