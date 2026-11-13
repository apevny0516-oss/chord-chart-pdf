"""python -m chordchart IN.chart OUT.pdf"""
import sys

from .parser import ChartError, parse
from .render import render


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m chordchart IN.chart OUT.pdf", file=sys.stderr)
        return 2
    try:
        with open(argv[0], encoding="utf-8") as f:
            chart = parse(f.read())
        render(chart, argv[1])
    except ChartError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
