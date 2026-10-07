"""Readable corruption with protected spans and a single local RNG."""

from dataclasses import dataclass
import random
import re
import unicodedata

from .modes import GLITCH, LEET, MARKS, MODES, Rules, rules_for

LINE_BREAKS = "\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029"
_PATH_START = r"(?:[A-Za-z]:[\\/]|\\\\|~[\\/]|\.{1,2}[\\/]|/)"
# Match original spans directly, rather than introducing mutable placeholders.
# Token boundaries also prevent repeated scans inside long dotted/dashed words.
_PROTECTED = re.compile(
    r"(?i:(?<![\w.+-])(?:[a-z][a-z0-9+.-]*://|www\.))[^\s<>\"\x00-\x1f]+"
    + r"|\"(?:" + _PATH_START + r"[^\"\r\n]*|[^\"\r\n]*[\\/][^\"\r\n]*)\""
    + r"|'(?:" + _PATH_START + r"[^'\r\n]*|[^'\r\n]*[\\/][^'\r\n]*)'"
    + r"|(?<!\w)" + _PATH_START + r"[^\s<>\"|?*\x00-\x1f]*"
    + r"|(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"
    + r"|(?<![\w:])(?:[A-Fa-f0-9]{0,4}:){2,}[A-Fa-f0-9:.]*(?:%[\w.-]+)?(?![\w:])"
    + r"|(?<![\w.@~+-])(?:[\w.@~+-]+[\\/])+[\w.@~+-]+[\\/]?"
    + r"|(?i:(?<![\w.-])[\w.-]+\.(?:txt|md|log|json|csv|yaml|yml|toml|ini|py|rs|go|js|ts|exe|dll|db|sqlite|bak|zip|pdf|png|jpg)\b)"
    + r"|\b0(?:[xX][0-9A-Fa-f]+|[bB][01]+|[oO][0-7]+)\b"
    + r"|[+-]?\d+(?:[.,:/-]\d+)*(?:[eE][+-]?\d+)?%?"
)
_PUNCTUATION = {".": "..", ",": ",,", "!": "!!", "?": "??", ":": "::", ";": ";;"}


@dataclass(frozen=True)
class CorruptionResult:
    text: str
    mode: str
    level: int


@dataclass
class _Budget:
    repeats: int
    unicode: int
    marks: int


def _is_cjk(char: str) -> bool:
    value = ord(char)
    return (
        0x3400 <= value <= 0x4DBF
        or 0x4E00 <= value <= 0x9FFF
        or 0xF900 <= value <= 0xFAFF
        or 0x20000 <= value <= 0x323AF
    )


def _mutate(text: str, rng: random.Random, rules: Rules, budget: _Budget) -> str:
    pieces: list[str] = []
    cjk_run = 0
    index = 0
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if char == " ":
            end = index + 1
            while end < len(text) and text[end] == " ":
                end += 1
            pieces.append(rng.choice(rules.separators) if rng.random() < rules.space else text[index:end])
            index = end
            cjk_run = 0
            continue
        if char.isascii() and char.isalpha():
            cjk_run = 0
            lower = char.lower()
            changed = char
            if lower in LEET and rng.random() < rules.leet:
                changed = LEET[lower]
            elif rng.random() < rules.case:
                changed = char.swapcase()
            has_mark = bool(following and unicodedata.category(following).startswith("M"))
            if changed.isalpha() and not has_mark:
                if lower in GLITCH and budget.unicode and rng.random() < rules.unicode:
                    changed = GLITCH[lower]
                    if char.isupper():
                        changed = changed.upper()
                    budget.unicode -= 1
                if budget.repeats and rng.random() < rules.repeat:
                    changed *= 2
                    budget.repeats -= 1
                # At most one combining mark on a character and three on a line.
                if budget.marks and rng.random() < rules.mark:
                    changed += rng.choice(MARKS)
                    budget.marks -= 1
            pieces.append(changed)
        elif _is_cjk(char):
            cjk_run += 1
            pieces.append(char)
            if cjk_run % 2 == 0 and following and _is_cjk(following) and rng.random() < rules.cjk:
                pieces.append(rng.choice(rules.separators))
        else:
            cjk_run = 0
            if char in _PUNCTUATION and rng.random() < rules.punctuation:
                pieces.append(_PUNCTUATION[char])
            else:
                pieces.append(char)
        index += 1
    return "".join(pieces)


def _extension(text: str, rng: random.Random, protected_tail: bool) -> str:
    # A suffix must not become part of an existing URL, path or number.
    gap = " " if protected_tail else ""
    return text + gap + rng.choice((".exe", ".tmp", ".bak", ".log"))


def _decorate(text: str, mode: str, level: int, rng: random.Random, protected_tail: bool) -> str:
    if level == 1:
        return text
    if mode == "normal":
        if level == 2:
            return text
        if level == 3:
            style = rng.randrange(3)
            if style == 0:
                return _extension(text, rng, protected_tail)
            return f"[WARN] {text}" if style == 1 else f"{text} //"
        return f"[ERR_0x69] {_extension(text, rng, protected_tail)} :: integrity={rng.randint(60, 89)}%"
    if mode == "leet":
        return _extension(text, rng, protected_tail) if level == 4 else text
    if mode == "glitch":
        if level == 2:
            return text
        if level == 3:
            return f"{text} //"
        return f"[GLITCH] {text} // checksum=0x{rng.randrange(256):02X}"
    if mode == "terminal":
        if level == 2:
            return f"{rng.choice(('[DICK::OK]', '[0x00]', '[DEBUG]'))} {text}"
        if level == 3:
            return f"{rng.choice(('[WARN]', '[DICK::DEBUG]', '[ERROR::0x01]'))} {_extension(text, rng, protected_tail)}"
        prefix = rng.choice(("[CRITICAL::0x69]", "[ERR_0xDEAD]", "[PANIC::0x01]"))
        return f"{prefix} {_extension(text, rng, protected_tail)} :: integrity={rng.randint(60, 89)}%"
    if level == 2:
        return f"{text} {rng.choice(('fr', 'bro', '💀', '😭'))}"
    if level == 3:
        return f"{text} {rng.choice(('fr 💀', 'actually 😭', 'skill issue', 'bro 💀'))}"
    return f"{rng.choice(('bro', 'nah', 'actually'))} {_extension(text, rng, protected_tail)} {rng.choice(('fr 💀', 'skill issue 😭', 'fr fr 💀'))}"


def _fallback(text: str, matches: list[re.Match[str]]) -> str:
    """Ensure a nonblank plain sentence still changes if every roll misses."""
    cursor = 0
    for match in matches:
        for index in range(cursor, match.start()):
            if text[index].isascii() and text[index].isalpha():
                return text[:index] + text[index].swapcase() + text[index + 1:]
        cursor = match.end()
    for index in range(cursor, len(text)):
        if text[index].isascii() and text[index].isalpha():
            return text[:index] + text[index].swapcase() + text[index + 1:]
    # Wrapping keeps protected tokens intact and does not attach to a URL.
    return f"({text})"


def _line(text: str, mode: str, level: int, rng: random.Random, rules: Rules) -> str:
    if not text.strip():
        return text
    start = len(text) - len(text.lstrip(" \t"))
    end = len(text.rstrip(" \t"))
    core = text[start:end]
    matches = list(_PROTECTED.finditer(core))
    letters = sum(char.isascii() and char.isalpha() for char in core)
    budget = _Budget(min(3, 1 + letters // 15), min(3, 1 + letters // 12), min(3, 1 + letters // 12))
    pieces: list[str] = []
    cursor = 0
    for match in matches:
        pieces.append(_mutate(core[cursor:match.start()], rng, rules, budget))
        pieces.append(match.group())
        cursor = match.end()
    pieces.append(_mutate(core[cursor:], rng, rules, budget))
    changed = "".join(pieces)
    protected_tail = bool(matches and matches[-1].end() == len(core))
    changed = _decorate(changed, mode, level, rng, protected_tail)
    if changed == core:
        changed = _fallback(core, matches)
    return text[:start] + changed + text[end:]


def corrupt(
    text: str,
    *,
    level: int = 2,
    mode: str = "normal",
    seed: int | None = None,
    random_mode: bool = False,
) -> CorruptionResult:
    """Corrupt text without dropping words, protected spans, or line endings.

    Equal text/options/seed give equal output, including random mode selection.
    An omitted seed uses Python's system-seeded local RNG, never global state.
    """
    if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 4:
        raise ValueError("level must be between 1 and 4")
    if not random_mode and mode not in MODES:
        raise ValueError(f"unknown mode '{mode}'")
    rng = random.Random(seed)
    selected_mode = rng.choice(MODES) if random_mode else mode
    rules = rules_for(selected_mode, level)
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        content = line.rstrip(LINE_BREAKS)
        ending = line[len(content):]
        lines.append(_line(content, selected_mode, level, rng, rules) + ending)
    return CorruptionResult("".join(lines), selected_mode, level)
