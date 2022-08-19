from dataclasses import dataclass
from io import TextIOBase
from pathlib import Path
from typing import List, Union, Dict, Any, Tuple, Optional, Literal, Set

from sly import Lexer, Parser
from sly.lex import Token, LexError
# maybe add ordering using start/end
from sly.yacc import YaccProduction
from typing_extensions import TypedDict


class TextGridProperties(TypedDict):
    size: int
    has_tiers: bool
    xmin: float
    xmax: float


class TierProperties(TypedDict):
    name: str
    size: int
    xmin: float
    xmax: float


class TextgridConsistencyError(ValueError):
    def __init__(self, error: str, *args):
        super().__init__(*args)
        self.error = error

    def __str__(self):
        return self.error + " To deactivate this error, set 'check_consistency' to False"


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

    @property
    def xmin(self):
        raise NotImplemented()

    @property
    def xmax(self):
        raise NotImplemented()


@dataclass
class IntervalTier(Tier):
    intervals: List[Interval]

    @property
    def xmin(self):
        return min(interval.start for interval in self.intervals) if self.intervals else None

    @property
    def xmax(self):
        return max(interval.end for interval in self.intervals) if self.intervals else None


@dataclass
class TextTier(Tier):
    points: List[Point]

    @property
    def xmin(self):
        return min(point.number for point in self.points) if self.points else None

    @property
    def xmax(self):
        return max(point.number for point in self.points) if self.points else None


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


class MinimalTextGridLexer(TextGridLexer):
    tokens = {
        "FLOAT_LITERAL",
        "INT_LITERAL",
        "STRING_LITERAL",
        "IDENTIFIER",
        "INTERVAL_TIER",
        "TEXT_TIER",
    }


class BaseParserMixin:
    lexer: TextGridLexer
    tokens: Set[str]

    _check_consistency: bool

    def parser_textgrid(self, tg_text: str, check_consistency: bool) -> List[Tier]:
        self._check_consistency = check_consistency

        return self.parse(self.lexer.tokenize(tg_text))

    def error(self, token):
        raise ParsingError(token)

    def check_tg_consistency(self, tiers: List[Tier], tg_prop: TextGridProperties):
        if not tg_prop["has_tiers"] and len(tiers) != 0:
            pass  # TODO

        if tg_prop["size"] != len(tiers):
            raise TextgridConsistencyError(
                f"Inconsistent number of tiers : {tg_prop['size']} declared in header, "
                f"found {len(tiers)} in file.")

        for tier in tiers:
            if tier.xmin is None:
                continue
            if tier.xmin < tg_prop["xmin"]:
                raise TextgridConsistencyError(f"xmin for tier {tier.name} is inconsistent with textgrid xmin: "
                                               f"{tier.xmin} < {tg_prop['xmin']}")
            if tier.xmax > tg_prop["xmax"]:
                raise TextgridConsistencyError(f"xmax for tier {tier.name} is inconsistent with textgrid xmax: "
                                               f"{tier.xmax} < {tg_prop['xmax']}")

    def check_tier_consistency(self, tier: Tier, tier_prop: TierProperties):
        if isinstance(tier, IntervalTier):
            items = tier.intervals
        else:
            items = tier.points  # noqa

        if len(items) != tier_prop["size"]:
            raise TextgridConsistencyError(f"Inconsistent number of items in tier {tier_prop['name']} : "
                                           f"{tier_prop['size']} declared in tier header, "
                                           f"found {len(items)} in file.")

        if tier.xmin is not None:
            if tier.xmin < tier_prop["xmin"]:
                raise TextgridConsistencyError(f"xmin for tier {tier.name} is inconsistent with items xmin: "
                                               f"{tier.xmin} < {tier_prop['xmin']}")

            if tier.xmax > tier_prop["xmax"]:
                raise TextgridConsistencyError(f"xmax for tier {tier.name} is inconsistent with items xmax: "
                                               f"{tier.xmax} < {tier_prop['xmax']}")


class FullTextGridParser(BaseParserMixin, Parser):
    tokens = TextGridLexer.tokens
    lexer = TextGridLexer()

    start = 'textgrid'

    @_("{ tg_property } tiers")
    def textgrid(self, p: YaccProduction):
        if self._check_consistency:
            self.check_tg_consistency(p.tiers, dict(p.tg_property))
        return p.tiers

    @_('ITEM "[" "]" ":" { tier }')
    def tiers(self, p: YaccProduction) -> List[Tier]:
        return [e[0] for e in p[4]]

    @_('interval_tier',
       'text_tier')
    def tier(self, p: YaccProduction) -> Tier:
        return p[0]

    @_('item_header CLASS "=" INTERVAL_TIER tier_header { interval }')
    def interval_tier(self, p: YaccProduction) -> IntervalTier:
        tier_properties = dict(p.tier_header)
        tier = IntervalTier(tier_properties["name"], p.interval)
        if self._check_consistency:
            self.check_tier_consistency(tier, tier_properties)
        return tier

    @_('intervals_header tg_property tg_property tg_property')
    def interval(self, p: YaccProduction) -> Interval:
        point_properties = dict([p[1], p[2], p[3]])
        return Interval(float(point_properties["xmin"]),
                        float(point_properties["xmax"]),
                        point_properties["text"])

    @_('item_header CLASS "=" TEXT_TIER tier_header { point }')
    def text_tier(self, p: YaccProduction) -> TextTier:
        tier_properties = dict(p.tier_header)
        tier = TextTier(tier_properties["name"], p.point)
        if self._check_consistency:
            self.check_tier_consistency(tier, tier_properties)
        return tier

    @_('points_header tg_property tg_property')
    def point(self, p: YaccProduction) -> Point:
        point_properties = dict([p[1], p[2]])
        return Point(float(point_properties["number"]),
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

    # todo : add support for no tiers in textgrid
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


class MinimalTextGridParser(BaseParserMixin, Parser):
    tokens = MinimalTextGridLexer.tokens
    lexer = MinimalTextGridLexer()

    start = 'textgrid'

    @_("tg_header { tier }")
    def textgrid(self, p: YaccProduction):
        if self._check_consistency:
            self.check_tg_consistency(p.tier, p.tg_header)
        return p.tier

    @_('tg_property tg_property number number "<" IDENTIFIER ">" INT_LITERAL')
    def tg_header(self, p: YaccProduction) -> Dict[str, Any]:
        return {
            "xmin": p[2],
            "xmax": p[3],
            "has_tiers": p[5] == "exists",
            "size": p[7]
        }

    @_('IDENTIFIER "=" STRING_LITERAL')
    def tg_property(self, p: YaccProduction):
        return p[0], p[2]

    @_('interval_tier',
       'text_tier')
    def tier(self, p: YaccProduction) -> Tier:
        return p[0]

    @_('INTERVAL_TIER STRING_LITERAL number number INT_LITERAL { interval }')
    def interval_tier(self, p: YaccProduction) -> IntervalTier:
        tier_properties = {"name": p.STRING_LITERAL, "size": p.INT_LITERAL, "xmin": p[2], "xmax": p[3]}
        tier = IntervalTier(p.STRING_LITERAL, p.interval)
        if self._check_consistency:
            self.check_tier_consistency(tier, tier_properties)
        return tier

    @_('number number STRING_LITERAL')
    def interval(self, p: YaccProduction) -> Interval:
        return Interval(p[0], p[1], p[2])

    @_('TEXT_TIER STRING_LITERAL number number INT_LITERAL { point }')
    def text_tier(self, p: YaccProduction) -> TextTier:
        tier_properties = {"name": p.STRING_LITERAL, "size": p.INT_LITERAL, "xmin": p[2], "xmax": p[3]}
        tier = TextTier(p.STRING_LITERAL, p.point)
        if self._check_consistency:
            self.check_tier_consistency(tier, tier_properties)
        return tier

    @_('number STRING_LITERAL')
    def point(self, p: YaccProduction) -> Point:
        return Point(p[0], p[1])

    @_("INT_LITERAL", "FLOAT_LITERAL")
    def number(self, p: YaccProduction):
        return p[0]


def parse_textgrid(textgrid: Union[str, Path, TextIOBase],
                   check_consistency: bool = True,
                   textgrid_format: Literal["full", "minimal"] = "full"):
    if isinstance(textgrid, TextIOBase):
        tg_str = textgrid.read()
    else:
        if isinstance(textgrid, str):
            tg_path = Path(textgrid)
        elif isinstance(textgrid, Path):
            tg_path = textgrid
        else:
            raise ValueError("Unsupported argument type for textgrid")

        with open(tg_path) as tg_file:
            tg_str = tg_file.read()

    assert textgrid_format in {"full", "minimal"}
    if textgrid_format == "full":
        tg_parser = FullTextGridParser()
    else:
        tg_parser = MinimalTextGridParser()

    return tg_parser.parser_textgrid(tg_str, check_consistency)
