# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Simple HTML page example."""

from pathlib import Path

from genro_bag import Bag
from genro_bag.builders import HtmlBuilder

page = Bag(builder=HtmlBuilder)
head = page.head()
head.title(value="Simple Page")

body = page.body()
body.h1(value="Hello World")
body.p(value="This is a simple paragraph.")

html = page.builder.compile(destination=Path(__file__).with_suffix(".html"))
print(html)
