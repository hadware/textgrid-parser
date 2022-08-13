from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import List, Union

from sly import Lexer, Parser


# maybe add ordering using start/end
@dataclass
class Interval:
    start: float
    end: float
    mark: str


@dataclass
class Tier:
    name: str
    intervals: List[Interval]


class TextGridLexer(Lexer):
    tokens = {

    }


class TextGridParser(Parser):
    tokens = TextGridLexer.tokens

    start = 'textgrid'
    _check_consistency: bool

    def parse_textgrid(self, tg_file: Union[StringIO, Path],
                       check_consistency: bool = True) -> List[Tier]:
        pass

    @_("header tiers")
    def textgrid(self):
        pass

    @_("{tg_property}")
    def header(self):
        pass

    def tiers(self):
        pass

    def tier(self):
        pass

    def tier_header(self):
        pass

    def interval(self):
        pass

    @_("PROPERTY_NAME '=' FLOAT_LITERAL",
       "PROPERTY_NAME '=' STRING_LITERAL")
    def tg_property(self):
        pass
