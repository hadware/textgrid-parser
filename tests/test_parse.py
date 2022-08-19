from pathlib import Path

from textgrid_parser import parse_textgrid, IntervalTier, TextTier

data_path = Path(__file__).parent / "data"
full_tg_path = data_path / "full.TextGrid"
full_simple_tg_path = data_path / "full_simple.TextGrid"
minimal_tg_path = data_path / "minimal.TextGrid"


def test_parse_full():
    tiers = parse_textgrid(full_tg_path,
                           check_consistency=True,
                           textgrid_format="full")
    assert len(tiers) == 3
    assert isinstance(tiers[0], IntervalTier)
    assert isinstance(tiers[1], IntervalTier)
    assert isinstance(tiers[2], TextTier)

    assert len(tiers[0].intervals) == 1
    assert len(tiers[1].intervals) == 3
    assert len(tiers[2].points) == 2

    assert tiers[0].name == "sentence"
    assert tiers[1].name == "phonemes"
    assert tiers[2].name == "bell"

    for tier in tiers:
        assert tier.xmin >= 0
        assert tier.xmax <= 2.3

    for tier in tiers[0:1]:
        for interval in tier.intervals:
            assert isinstance(interval.start, float)
            assert isinstance(interval.end, float)
            assert isinstance(interval.text, str)

    for point in tiers[2].points:
        assert isinstance(point.number, float)
        assert isinstance(point.mark, str)


def test_parse_full_simple():
    tiers = parse_textgrid(full_simple_tg_path,
                           check_consistency=True,
                           textgrid_format="full")
    assert len(tiers) == 3
    assert isinstance(tiers[0], IntervalTier)
    assert isinstance(tiers[1], IntervalTier)
    assert isinstance(tiers[2], TextTier)

    assert len(tiers[0].intervals) == 1
    assert len(tiers[1].intervals) == 1
    assert len(tiers[2].points) == 0

    assert tiers[0].name == "Mary"
    assert tiers[1].name == "John"
    assert tiers[2].name == "bell"


def test_parse_minimal():
    tiers = parse_textgrid(minimal_tg_path,
                           check_consistency=True,
                           textgrid_format="minimal")
    assert len(tiers) == 3
