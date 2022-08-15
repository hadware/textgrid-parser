from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import List, Union, Dict, Any, Tuple, Optional

from sly import Lexer, Parser

# maybe add ordering using start/end
from sly.yacc import YaccProduction
from sly.lex import Token, LexError


class TextgridConsistencyError(ValueError):
    def __init__(self, error, ):
        pass


class ParsingError(Exception):

    def __init__(self, token: Token, msg: Optional[str] = None):
        self.token = token
        self.msg = msg

    def __str__(self):

        if self.msg is None:
            if self.token is None:
                return "Unexpected end of string."
            else:
                return f"Parsing error at index {self.token.index}, line {self.token.lineno}, " \
                       f"unexpected token \"{self.token.value}\" (type {self.token.type})."
        else:
            if self.token is None:
                return f"{self.msg} at EOF"
            else:
                return f"{self.msg}, at index {self.token.index}, line {self.token.lineno}."


@dataclass
class Interval:
    start: float
    end: float
    text: str


@dataclass
class Point:
    number: float
    mark: str


@dataclass
class Tier:
    name: str


@dataclass
class IntervalTier(Tier):
    intervals: List[Interval]


@dataclass
class TextTier(Tier):
    intervals: List[Point]


class TextGridLexer(Lexer):
    tokens = {
        "FLOAT_LITERAL",
        "INT_LITERAL",
        "STRING_LITERAL",
        "SIZE",
        "INTERVALS",
        "POINTS",
        "CLASS",
        "INTERVAL_TIER",
        "TEXT_TIER",
        "IDENTIFIER",
        "ITEM",
        "TIERS_EXIST"
    }
    literals = {"=", ":", "[", "]", "<", ">"}

    ignore = ' \t'

    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    @_(r"[0-9]+\.[0-9]+")
    def FLOAT_LITERAL(self, t):
        t.value = float(t.value)
        return t

    @_(r"[0-9]+")
    def INT_LITERAL(self, t):
        t.value = int(t.value)
        return t

    INTERVAL_TIER = '"IntervalTier"'
    TEXT_TIER = '"TextTier"'

    @_(r'".*"')
    def STRING_LITERAL(self, t):
        t.value = t.value.strip('"')
        return t

    TIERS_EXIST = r"tiers\?"
    ITEM = r"item"
    SIZE = r"size"
    INTERVALS = r"intervals"
    POINTS = r"points"
    CLASS = r"class"

    @_(r"[a-zA-Z ]+")
    def IDENTIFIER(self, t):
        t.value = t.value.strip()
        return t

    def error(self, t):
        raise LexError(f"Unexpected character {t.value[0]!r} at index {self.index}, line {self.lineno}",
                       t.value, self.index)


class TextGridParser(Parser):
    debugfile = 'parser.out'
    tokens = TextGridLexer.tokens
    lexer = TextGridLexer()

    start = 'textgrid'
    _check_consistency: bool

    def parse_textgrid(self, tg_file: Union[str, StringIO, Path],
                       check_consistency: bool = True) -> List[Tier]:

        self._check_consistency = check_consistency

        if isinstance(tg_file, StringIO):
            tg_text = tg_file.read()
        elif isinstance(tg_file, Path):
            with open(tg_file) as tg:
                tg_text = tg.read()
        elif isinstance(tg_file, str):
            tg_text = tg_file
        else:
            ValueError("Unsupported type for tg_file")

        return self.parse(self.lexer.tokenize(tg_text))  # noqa

    @_("{ tg_property } tiers")
    def textgrid(self, p: YaccProduction):
        # TODO: consistency checks
        return p.tiers

    @_('ITEM "[" "]" ":" { tier }')
    def tiers(self, p: YaccProduction) -> List[Tier]:
        return p[4]

    @_('interval_tier',
       'text_tier')
    def tier(self, p: YaccProduction) -> Union[Tier]:
        return p[0]

    @_('item_header CLASS "=" INTERVAL_TIER tier_header { interval }')
    def interval_tier(self, p: YaccProduction) -> Tier:
        tier_properties = dict(p.tier_header)
        return IntervalTier(tier_properties["name"], p.interval)

    @_('intervals_header tg_property tg_property tg_property')
    def interval(self, p: YaccProduction) -> Interval:
        point_properties = dict([p[1], p[2], p[3]])
        return Interval(point_properties["xmin"],
                        point_properties["xmax"],
                        point_properties["text"])

    @_('item_header CLASS "=" TEXT_TIER tier_header { point }')
    def text_tier(self, p: YaccProduction) -> Tier:
        tier_properties = dict(p.tg_property)
        return TextTier(tier_properties["name"], p.interval)

    @_('points_header tg_property tg_property')
    def point(self, p: YaccProduction) -> Point:
        point_properties = dict([p[1], p[2]])
        return Point(point_properties["number"],
                     point_properties["mark"])

    @_('tg_property tg_property tg_property size_property')
    def tier_header(self, p: YaccProduction) -> Dict[str, Any]:
        return dict(p[i] for i in range(4))

    @_('IDENTIFIER "=" STRING_LITERAL',
       'IDENTIFIER "=" INT_LITERAL',
       'IDENTIFIER "=" FLOAT_LITERAL',
       'SIZE "=" INT_LITERAL')
    def tg_property(self, p: YaccProduction):
        return p[0], p[2]

    @_('TIERS_EXIST "<" IDENTIFIER ">"')
    def tg_property(self, p: YaccProduction) -> Tuple[str, bool]:
        return "has_tiers", True

    @_('INTERVALS ":" SIZE "=" INT_LITERAL',
       'POINTS ":" SIZE "=" INT_LITERAL')
    def size_property(self, p: YaccProduction):
        return p[2], p[4]

    @_('ITEM "[" INT_LITERAL "]" ":"')
    def item_header(self, p: YaccProduction) -> Tuple[str, int]:
        return p[0], p.INT_LITERAL

    @_('INTERVALS "[" INT_LITERAL "]" ":"')
    def intervals_header(self, p: YaccProduction) -> Tuple[str, int]:
        return p[0], p.INT_LITERAL

    @_('POINTS "[" INT_LITERAL "]" ":"', )
    def points_header(self, p: YaccProduction) -> Tuple[str, int]:
        return p[0], p.INT_LITERAL

    def error(self, token):
        raise ParsingError(token)
