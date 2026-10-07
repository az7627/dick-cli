"""Small, shared rule tables; every choice uses the caller's RNG."""

from dataclasses import dataclass

MODES = ("normal", "leet", "glitch", "terminal", "brainrot")
LEET = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7"}
GLITCH = {"a": "à", "e": "ë", "i": "ï", "o": "ø", "u": "ü"}
MARKS = ("\u0336", "\u0337", "\u0338")


@dataclass(frozen=True)
class Rules:
    case: float
    leet: float
    space: float
    repeat: float
    punctuation: float
    cjk: float
    unicode: float
    mark: float
    separators: tuple[str, ...]


def rules_for(mode: str, level: int) -> Rules:
    case = (0.0, 0.12, 0.28, 0.45, 0.62)[level]
    leet = (0.0, 0.0, 0.23, 0.40, 0.58)[level]
    repeat = (0.0, 0.015, 0.025, 0.04, 0.055)[level]
    separators = ("_", "-") if level == 1 else ("_", "-", ".", "::")
    if mode == "leet":
        leet = min(0.65, leet + 0.12) if level > 1 else 0.0
        case /= 3
        repeat /= 2
        separators = ("_", "-")
    elif mode == "glitch":
        leet *= 0.8
        if level > 1:
            separators = ("_", "::", " // ")
    elif mode == "terminal":
        separators = ("_", "-") if level == 1 else ("_", "::")
    elif mode == "brainrot":
        separators = ("_", "-", " ")

    return Rules(
        case=case,
        leet=leet,
        space=(0.0, 0.65, 0.85, 0.95, 1.0)[level],
        repeat=repeat,
        punctuation=(0.0, 0.08, 0.13, 0.21, 0.28)[level],
        cjk=(0.0, 0.0, 0.25, 0.40, 0.60)[level],
        unicode=(0.0, 0.0, 0.0, 0.055, 0.08)[level] if mode == "glitch" else 0.0,
        mark=(0.0, 0.0, 0.0, 0.045, 0.07)[level] if mode == "glitch" else 0.0,
        separators=separators,
    )
