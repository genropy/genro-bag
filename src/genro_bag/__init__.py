# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
genro-bag: Modernized bag system for the Genropy framework.
"""

from genro_bag.bag import Bag, BagException
from genro_bag.bagnode import BagNode, BagNodeContainer, BagNodeException
from genro_bag.builder import BagBuilderBase
from genro_bag.resolver import BagResolver

__version__ = "0.6.0"

__all__ = [
    "Bag",
    "BagBuilderBase",
    "BagException",
    "BagNode",
    "BagNodeContainer",
    "BagNodeException",
    "BagResolver",
]
