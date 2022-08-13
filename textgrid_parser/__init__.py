from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import List, Union, Dict, Any, Tuple, Optional

from sly import Lexer, Parser

# maybe add ordering using start/end
from sly.yacc import YaccProduction
from sly.lex import Token


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
    mark: str


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

    ignore = '[ \t]+'

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

    @_(r'".*"')
    def STRING_LITERAL(self, t):
        t.value = t.value.strip("")
        return t

    INTERVAL_TIER = '"IntervalTier"'
    TEXT_TIER = '"TextTier"'
    TIERS_EXIST = r"tiers\?"
    IDENTIFIER = r"[a-zA-Z ?]+"
    IDENTIFIER["size"] = "SIZE"
    IDENTIFIER["intervals"] = "INTERVALS"
    IDENTIFIER["points"] = "POINTS"
    IDENTIFIER["class"] = "CLASS"
    IDENTIFIER["item"] = "ITEM"
    #ITEM = r"ITEM"


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

        self.parse(self.lexer.tokenize(tg_text))  # noqa

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

    @_('item_header CLASS "=" INTERVAL_TIER { tg_property } { interval }')
    def interval_tier(self, p: YaccProduction) -> Tier:
        tier_properties = dict(p.tg_property)
        return IntervalTier(tier_properties["name"], p.interval)

    @_('item_header tg_property tg_property tg_property')
    def interval(self, p: YaccProduction) -> Interval:
        point_properties = dict([p[1], p[2], p[3]])
        return Interval(point_properties["start"],
                        point_properties["end"],
                        point_properties["mark"])

    @_('item_header CLASS "=" TEXT_TIER { tg_property } { point }')
    def text_tier(self, p: YaccProduction) -> Tier:
        tier_properties = dict(p.tg_property)
        return TextTier(tier_properties["name"], p.interval)

    @_('item_header tg_property tg_property')
    def point(self, p: YaccProduction) -> Point:
        point_properties = dict([p[1], p[2]])
        return Point(point_properties["number"],
                     point_properties["mark"])

    @_('IDENTIFIER "=" STRING_LITERAL',
       'IDENTIFIER "=" INT_LITERAL',
       'IDENTIFIER "=" FLOAT_LITERAL')
    def tg_property(self, p: YaccProduction):
        return p[0], p[2]

    @_('TIERS_EXIST "<" IDENTIFIER ">"')
    def tg_property(self, p: YaccProduction) -> Tuple[str, bool]:
        return "has_tiers", True

    @_('INTERVALS ":" SIZE "=" INT_LITERAL',
       'POINTS ":" SIZE "=" INT_LITERAL')
    def tg_property(self, p: YaccProduction):
        return p[2], p[4]

    @_('ITEM "[" INT_LITERAL "]" ":"',
       'INTERVALS "[" INT_LITERAL "]" ":"',
       'POINTS "[" INT_LITERAL "]" ":"',)
    def item_header(self, p: YaccProduction) -> Tuple[str, int]:
        return p[0], p.INT_LITERAL

    def error(self, token):
        raise ParsingError(token)
