# SystemResolver Demo

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolvers import DirectoryResolver
>>> from system_resolver import SystemResolver
>>>
>>> computer = Bag()
>>> computer['sys'] = SystemResolver()
>>> computer['home'] = DirectoryResolver('~')
>>>
>>> list(computer.keys())
['sys', 'home']
>>>
>>> list(computer['sys'].keys())
['platform', 'python', 'user', 'cpu', 'disk', 'network', 'memory']
>>>
>>> list(computer['sys.platform'].keys())
['system', 'release', 'version', 'machine', 'node', 'processor']
>>>
>>> computer['sys.platform.system']
'Darwin'
>>>
>>> computer['sys.platform.machine']
'arm64'
>>>
>>> computer['sys.cpu.count']
10
>>>
>>> computer['sys.disk.free_gb']
182.45
>>>
>>> computer['sys.user.name']
'gporcari'
>>>
>>> computer['sys.python.version']
'3.12.8'
>>>
>>> list(computer['home'].keys())[:5]
['Desktop', 'Documents', 'Downloads', 'Library', 'Movies']
>>>
>>> print(computer.to_string(static=False))
├── sys
│   ├── platform
│   │   ├── system: 'Darwin'
│   │   ├── release: '25.1.0'
│   │   ├── version: 'Darwin Kernel Version 25.1.0...'
│   │   ├── machine: 'arm64'
│   │   ├── node: 'MacBook-Pro.local'
│   │   └── processor: 'arm'
│   ├── python
│   │   ├── version: '3.12.8'
│   │   ├── implementation: 'CPython'
│   │   ├── executable: '/usr/local/bin/python3'
│   │   └── prefix: '/usr/local'
│   ├── user
│   │   ├── name: 'gporcari'
│   │   ├── home: '/Users/gporcari'
│   │   └── cwd: '/Users/gporcari/projects'
│   ├── cpu
│   │   ├── count: 10
│   │   ├── percent: 12.5
│   │   └── freq_mhz: 3228
│   ├── disk
│   │   ├── total_gb: 460.43
│   │   ├── used_gb: 277.98
│   │   ├── free_gb: 182.45
│   │   └── percent: 60.4
│   ├── network
│   │   ├── hostname: 'MacBook-Pro'
│   │   └── fqdn: 'MacBook-Pro.local'
│   └── memory
│       ├── total_gb: 36.0
│       ├── available_gb: 18.23
│       └── percent: 49.4
└── home
    ├── Desktop
    ├── Documents
    ├── Downloads
    └── ...
```
