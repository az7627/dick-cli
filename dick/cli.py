"""UTF-8 command line interface, with no runtime dependencies."""

import argparse
import os
import sys
from typing import Sequence

from . import __version__
from .corrupt import LINE_BREAKS, corrupt
from .modes import MODES


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, f"error: {message}\n")


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="dick",
        description="DICK - Distorted Input Context Keeper\n\nMake text worse. Keep it recognizable.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Modes:\n  " + "\n  ".join(MODES)
            + '\n\nExamples:\n  dick "hello world"\n  dick -l 4 "hello world"'
            + '\n  dick -m terminal "download completed"'
            + '\n  dick --random --seed 42 "hello world"'
            + '\n  echo "hello world" | dick --plain'
            + '\n\nTEXT takes precedence over stdin. Use -- before text starting with a dash.'
        ),
    )
    parser.add_argument("text", nargs="?", metavar="TEXT", help="input text; otherwise read UTF-8 stdin")
    parser.add_argument("-l", "--level", default="2", metavar="1-4", help="DICK intensity [default: 2]")
    parser.add_argument("-m", "--mode", default="normal", metavar="MODE", help="corruption mode [default: normal]")
    parser.add_argument("-r", "--random", action="store_true", help="choose a random mode; ignore --mode")
    parser.add_argument("--seed", type=int, metavar="NUMBER", help="use deterministic randomness")
    parser.add_argument("--plain", action="store_true", help="print only processed text")
    parser.add_argument("-V", "--version", action="version", version=f"DICK v{__version__}")
    return parser


def _utf8_streams() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            # Keep CRLF and LF unchanged, including through Windows pipelines.
            stream.reconfigure(encoding="utf-8", errors="strict", newline="")


def _silence_broken_pipe() -> None:
    # Prevent Python's shutdown flush from reporting a second broken pipe.
    try:
        descriptor = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(descriptor, sys.stdout.fileno())
        finally:
            os.close(descriptor)
    except (OSError, ValueError, AttributeError):
        pass


def main(argv: Sequence[str] | None = None) -> int:
    _utf8_streams()
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        level = int(args.level)
    except ValueError:
        parser.error("level must be between 1 and 4")
    if not 1 <= level <= 4:
        parser.error("level must be between 1 and 4")
    if not args.random and args.mode not in MODES:
        parser.error(f"unknown mode '{args.mode}'\n\nAvailable modes:\n  " + "\n  ".join(MODES))
    try:
        text = args.text if args.text is not None else ("" if sys.stdin.isatty() else sys.stdin.read())
    except UnicodeError:
        print("error: input must be valid UTF-8", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"error: could not read input: {error}", file=sys.stderr)
        return 1
    if not text.strip():
        print('error: no input text\n\nTry:\n  dick "hello world"\n  echo "hello world" | dick', file=sys.stderr)
        return 1

    result = corrupt(text, level=level, mode=args.mode, seed=args.seed, random_mode=args.random)
    try:
        if args.plain:
            sys.stdout.write(result.text)
            if not result.text.endswith(tuple(LINE_BREAKS)):
                sys.stdout.write("\n")
        else:
            print("DICK - Distorted Input Context Keeper")
            print(f"\nInput:\n{text}\n\nOutput:\n{result.text}")
            print(f"\nMode: {result.mode}\nDICK level: {result.level}/4")
        sys.stdout.flush()
    except BrokenPipeError:
        _silence_broken_pipe()
        return 0
    except (OSError, UnicodeError) as error:
        print(f"error: could not write output: {error}", file=sys.stderr)
        return 1
    return 0
