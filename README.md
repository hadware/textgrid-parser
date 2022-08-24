# Textgrid parser

A barebone,  `sly`-based (LALR(1)) parser for textgrid files

## Installation

This repo will be uploaded to pipy's repository at some point. For the time being,

```shell
    pip install git+ssh://git@github.com/hadware/textgrid-parser.git
```

## Parsing a Textgrid

```python

from textgrid_parser import parse_textgrid

tiers = parse_textgrid("my_textgrid.TextGrid", check_consistency=True, textgrid_format="full")

```