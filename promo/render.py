"""Render the DICK CLI launch film with real CLI results and original music.

Production dependencies live in promo/requirements.txt, never in the CLI.
"""

from __future__ import annotations

import argparse
from functools import lru_cache
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dick.corrupt import corrupt  # noqa: E402
from dick.modes import MODES  # noqa: E402

W, H, FPS, DURATION = 1920, 1080, 30, 30.0
REPO = "https://github.com/az7627/dick-cli"
LOGO_PATH = ROOT / "promo" / ".cache" / "logo.png"
CREDIT = "软件和本视频均由 GPT 6.1 Sol制作"
MINT = "#91FFBC"
WHITE = "#F1F6FB"
MUTED = "#91A4B9"
PURPLE = "#B49AFF"
CORAL = "#FF6B88"
FONT_FILES = {
    "title": "bahnschrift.ttf",
    "mono": "consola.ttf",
    "mono-bold": "consolab.ttf",
    "cjk": "msyh.ttc",
    "cjk-bold": "msyhbd.ttc",
    "emoji": "seguiemj.ttf",
}
FONT_ROOT = Path("C:/Windows/Fonts")
SECTIONS = (0.0, 5.8, 11.7, 17.8, 24.2, 30.0)
TIMES = (0.0, 4.2, 9.0, 15.4, 22.7, 27.5)
EMOJI = re.compile("([💀😭])")


@lru_cache(maxsize=128)
def font(size: int, face: str = "cjk") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_ROOT / FONT_FILES[face]), size)


def chunks(message: str, size: int, face: str):
    for part in EMOJI.split(message):
        if part:
            yield part, font(size, "emoji" if EMOJI.fullmatch(part) else face)


def width(message: str, size: int, face: str) -> float:
    return sum(face_font.getlength(part) for part, face_font in chunks(message, size, face))


def text(
    image: Image.Image,
    xy: tuple[float, float],
    message: str,
    size: int,
    face: str = "cjk",
    color: str = WHITE,
    align: str = "left",
    max_width: int | None = None,
) -> None:
    if max_width:
        while size > 18 and width(message, size, face) > max_width:
            size -= 1
    x, y = xy
    extent = width(message, size, face)
    if align == "center":
        x -= extent / 2
    elif align == "right":
        x -= extent
    draw = ImageDraw.Draw(image)
    for part, face_font in chunks(message, size, face):
        draw.text((round(x), round(y)), part, font=face_font, fill=color, anchor="lm", embedded_color=True)
        x += face_font.getlength(part)


def ease(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return 1 - (1 - value) ** 3


def panel(image: Image.Image, box: tuple[int, int, int, int], radius: int = 24) -> None:
    ImageDraw.Draw(image).rounded_rectangle(box, radius=radius, fill="#0C1420", outline="#25364A", width=2)


def pill(image: Image.Image, xy: tuple[int, int], message: str, color: str = MINT) -> int:
    x, y = xy
    extent = math.ceil(width(message, 26, "cjk") + 48)
    ImageDraw.Draw(image).rounded_rectangle((x, y - 26, x + extent, y + 26), radius=26, fill="#121E2C", outline="#2A3F50")
    text(image, (x + 24, y), message, 26, color=color)
    return extent


@lru_cache(maxsize=1)
def background_base() -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cool = np.exp(-(((xx - 1570) / 620) ** 2 + ((yy - 180) / 680) ** 2))
    violet = np.exp(-(((xx - 280) / 800) ** 2 + ((yy - 950) / 520) ** 2))
    values = np.stack((7 + 3 * cool + 6 * violet, 11 + 14 * cool + 2 * violet, 18 + 14 * cool + 12 * violet), axis=-1)
    return Image.fromarray(values.astype(np.uint8)).convert("RGBA")


def background(t: float) -> Image.Image:
    image = background_base().copy()
    draw = ImageDraw.Draw(image)
    offset = int(t * 7) % 96
    for x in range(-96 + offset, W + 96, 96):
        draw.line((x, 0, x, H), fill="#15232D", width=1)
    for y in range(-96 + offset, H + 96, 96):
        draw.line((0, y, W, y), fill="#15232D", width=1)
    draw.rectangle((0, 0, W, 7), fill=MINT)
    draw.line((128, 1000, 1792, 1000), fill="#2A3949", width=2)
    draw.line((128, 1000, 128 + int(1664 * t / DURATION), 1000), fill=MINT, width=4)
    text(image, (128, 1042), "DICK CLI  /  DISTORTED INPUT CONTEXT KEEPER", 21, "mono", MUTED)
    text(image, (1792, 1042), "v0.1.0  ·  OPEN SOURCE", 21, "mono", MUTED, "right")
    for index in range(12):
        x = int((index * 157 + t * (10 + index % 3)) % W)
        y = 100 + (index * 71) % 800
        draw.rectangle((x, y, x + 3, y + 3), fill="#32504F")
    return image


@lru_cache(maxsize=8)
def logo(size: int) -> Image.Image:
    return Image.open(LOGO_PATH).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)


def mark(image: Image.Image, center: tuple[int, int], size: int) -> None:
    x, y = center
    image.alpha_composite(logo(size), (x - size // 2, y - size // 2))


def heading(image: Image.Image, number: str, title: str, subtitle: str) -> None:
    text(image, (132, 128), number, 24, "mono-bold", MINT)
    text(image, (132, 220), title, 70, "cjk-bold", max_width=1656)
    text(image, (132, 300), subtitle, 32, color=MUTED)


def opening(image: Image.Image, t: float) -> None:
    mark(image, (960, 242), 300)
    text(image, (960, 487), "DICK CLI", 164, "title", WHITE, "center")
    text(image, (960, 605), "Distorted Input Context Keeper.", 35, "mono", MINT, "center")
    text(image, (960, 722), CREDIT, 42, "cjk", WHITE, "center")
    text(image, (960, 804), "仓库地址：" + REPO, 36, "cjk", MUTED, "center")
    text(image, (960, 905), "正常文本，开始有一点精神状态。", 30, color=PURPLE, align="center")


def terminal(image: Image.Image, t: float) -> None:
    heading(image, "01 / KEEP THE CONTEXT", "把文本搞坏。把原意留下。", "Make text worse. Keep it recognizable.")
    panel(image, (132, 364, 1788, 800))
    draw = ImageDraw.Draw(image)
    for index, color in enumerate((CORAL, "#FFC96B", MINT)):
        draw.ellipse((166 + index * 30, 394, 178 + index * 30, 406), fill=color)
    text(image, (260, 400), "dick — seeded run", 24, "mono", MUTED)
    draw.line((134, 440, 1786, 440), fill="#25364A", width=2)
    command = '$ dick --plain --seed 42 "hello world"'
    visible = min(len(command), int(max(0, t - 0.2) * 27))
    text(image, (178, 510), command[:visible], 45, "mono", WHITE)
    if visible < len(command) and int(t * 3) % 2 == 0:
        x = 178 + width(command[:visible], 45, "mono")
        draw.rectangle((int(x), 482, int(x + 20), 534), fill=MINT)
    if t >= 1.65:
        layer = Image.new("RGBA", (W, H))
        text(layer, (178, 666), corrupt("hello world", seed=42).text, 104, "mono-bold", MINT)
        image.alpha_composite(Image.blend(Image.new("RGBA", (W, H)), layer, ease((t - 1.65) / 0.4)))
    text(image, (132, 861), "同一个 seed，同一个结果。", 35, "cjk-bold")
    x = 132
    for message in ("完全离线", "零 AI API", "零运行时依赖"):
        x += pill(image, (x, 936), message) + 18


def intensity(image: Image.Image, t: float) -> None:
    heading(image, "02 / TURN IT UP", "从轻微失常，到终端崩溃感。", "4 级强度 · 始终保留原词与顺序")
    labels = ("轻微", "适中", "明显", "拉满")
    colors = (MINT, "#C1ED97", PURPLE, CORAL)
    for index in range(4):
        visible = ease((t - index * 0.14) / 0.45)
        y = 418 + index * 125
        layer = Image.new("RGBA", (W, H))
        panel(layer, (132, y - 47, 1788, y + 60), 18)
        text(layer, (164, y), f"L{index + 1}", 46, "mono-bold", colors[index])
        text(layer, (245, y), labels[index], 29, color=MUTED)
        for segment in range(4):
            ImageDraw.Draw(layer).rounded_rectangle((340 + segment * 20, y - 16, 352 + segment * 20, y + 16), radius=3, fill=colors[index] if segment <= index else "#263346")
        output = corrupt("hello world", level=index + 1, seed=42).text
        text(layer, (466, y), output, 48 if index < 3 else 38, "mono-bold", colors[index], max_width=1268)
        image.alpha_composite(Image.blend(Image.new("RGBA", (W, H)), layer, visible))
    text(image, (132, 934), "数字、URL、IP、常见路径，按原文保护。", 34, color=MUTED)


def styles(image: Image.Image, t: float) -> None:
    heading(image, "03 / PICK YOUR FLAVOR", "五种风格。还是那句话。", "同一输入 hello world · Level 3 · seed 42")
    colors = (MINT, "#F5CC7A", PURPLE, "#78CAFF", CORAL)
    labels = ("综合破坏", "数字替换", "轻度故障", "终端包装", "互联网精神状态")
    for index, mode in enumerate(MODES):
        y = 407 + index * 108
        active = int(max(0, t - 0.2) / 0.86) % 5 == index
        layer = Image.new("RGBA", (W, H))
        panel(layer, (132, y - 40, 1788, y + 52), 16)
        ImageDraw.Draw(layer).rounded_rectangle((133, y - 28, 140, y + 40), radius=3, fill=colors[index])
        text(layer, (168, y - 2), mode, 39, "mono-bold", colors[index])
        text(layer, (412, y), labels[index], 24, color=MUTED)
        output = corrupt("hello world", mode=mode, level=3, seed=42).text
        text(layer, (736, y), output, 44, "mono", WHITE, max_width=1018)
        if active:
            ImageDraw.Draw(layer).rounded_rectangle((132, y - 40, 1788, y + 52), radius=16, outline=colors[index], width=2)
        image.alpha_composite(Image.blend(Image.new("RGBA", (W, H)), layer, ease((t - index * 0.12) / 0.4)))
    text(image, (132, 966), "支持中文、Emoji、多行与管道输入。", 31, color=MUTED)


def closing(image: Image.Image, t: float) -> None:
    mark(image, (960, 204), 225)
    text(image, (960, 376), "DICK CLI", 132, "title", WHITE, "center")
    text(image, (960, 475), "开源。离线。让文本坏得有点意思。", 41, "cjk-bold", MINT, "center")
    panel(image, (426, 552, 1494, 692), 22)
    text(image, (960, 600), "$ pip install .", 48, "mono-bold", WHITE, "center")
    text(image, (960, 654), '$ dick "hello world"', 36, "mono", MUTED, "center")
    text(image, (960, 782), REPO, 44, "mono-bold", MINT, "center")
    text(image, (960, 880), CREDIT, 35, color=WHITE, align="center")
    text(image, (960, 946), "Make text worse. Keep it recognizable.", 27, "mono", MUTED, "center")


SCENES = (opening, terminal, intensity, styles, closing)


def render_frame(t: float) -> Image.Image:
    index = min(4, next((i for i in range(5) if SECTIONS[i] <= t < SECTIONS[i + 1]), 4))
    image = background(t)
    layer = Image.new("RGBA", (W, H))
    SCENES[index](layer, t - SECTIONS[index])
    if index and t < SECTIONS[index] + 0.3:
        previous = Image.new("RGBA", (W, H))
        SCENES[index - 1](previous, SECTIONS[index] - SECTIONS[index - 1])
        layer = Image.blend(previous, layer, (t - SECTIONS[index]) / 0.3)
    image.alpha_composite(layer)
    return image.convert("RGB")


def previews(output: Path) -> None:
    sheet = Image.new("RGB", (1944, 822), "#070B12")
    draw = ImageDraw.Draw(sheet)
    for index, t in enumerate(TIMES):
        image = render_frame(t)
        image.save(output / f"preview-{index + 1:02d}.png")
        if index == 0:
            image.save(output / "DICK_CLI_poster.png")
        x, y = 12 + (index % 3) * 644, 12 + (index // 3) * 405
        sheet.paste(image.resize((632, 356), Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 4, y + 370), f"{t:04.1f}s", font=font(21, "mono"), fill=MUTED)
    sheet.save(output / "contact-sheet.jpg", quality=92)


def soundtrack(path: Path) -> dict:
    rate = 48000
    count = int(DURATION * rate)
    track = np.zeros((count, 2), dtype=np.float64)
    rng = np.random.default_rng(6142)
    beat = 60 / 128

    def add(at: float, sound: np.ndarray, gain: float, pan: float = 0.0):
        start = max(0, int(at * rate))
        length = min(len(sound), count - start)
        if length > 0:
            track[start:start + length, 0] += sound[:length] * gain * (1 - max(0.0, pan))
            track[start:start + length, 1] += sound[:length] * gain * (1 + min(0.0, pan))

    def hz(note: int) -> float:
        return 440 * 2 ** ((note - 69) / 12)

    chords = ((60, 63, 67), (56, 60, 63), (63, 67, 70), (58, 62, 65))
    for bar in range(16):
        chord = chords[bar % 4] if bar < 15 else chords[0]
        at = bar * 4 * beat
        duration = 4 * beat
        ts = np.arange(int(duration * rate)) / rate
        envelope = np.minimum(1, ts / 0.12) * np.minimum(1, (duration - ts) / 0.3)
        pad = sum(np.sin(2 * math.pi * hz(note) * ts) + 0.45 * np.sin(2 * math.pi * hz(note) * 1.002 * ts) for note in chord) / 5
        add(at, pad * envelope, 0.16, -0.12 if bar % 2 else 0.12)
        for step in range(8):
            note = chord[step % 3] + 12
            ts = np.arange(int(beat * 0.9 * rate)) / rate
            melody = (np.sin(2 * math.pi * hz(note) * ts) + 0.25 * np.sin(4 * math.pi * hz(note) * ts)) * np.exp(-ts * 10)
            add(at + step * beat / 2, melody, 0.07, 0.25 if step % 2 else -0.25)
        for step in range(4):
            onset = at + step * beat
            lift = 0.5 if onset < 5.8 else 1.0
            ts = np.arange(int(0.25 * rate)) / rate
            phase = 2 * math.pi * (48 * ts + 65 * (1 - np.exp(-ts * 20)) / 20)
            kick = np.sin(phase) * np.exp(-ts * 17)
            add(onset, kick, 0.40 * lift)
            bass_time = np.arange(int(beat * 0.75 * rate)) / rate
            bass = np.sin(2 * math.pi * hz(chord[0] - 24) * bass_time) * np.exp(-bass_time * 5)
            add(onset, bass, 0.23 * lift)
            if step in (1, 3):
                ts = np.arange(int(0.12 * rate)) / rate
                noise = rng.normal(0, 1, len(ts))
                snare = (noise * 0.45 + np.sin(2 * math.pi * 175 * ts) * 0.5) * np.exp(-ts * 38)
                add(onset, snare, 0.11 * lift)
            for off in (0, beat / 2):
                ts = np.arange(int(0.035 * rate)) / rate
                noise = rng.normal(0, 1, len(ts))
                hat = (noise - np.roll(noise, 1)) * np.exp(-ts * 140)
                add(onset + off, hat, 0.025 * lift, 0.22)

    # Subtle terminal key clicks, composed rather than sourced from a sample.
    for onset in np.arange(6.05, 7.25, 0.075):
        ts = np.arange(int(0.012 * rate)) / rate
        add(float(onset), np.sin(2 * math.pi * 1700 * ts) * np.exp(-ts * 450), 0.028, -0.2)
    ts = np.arange(count) / rate
    fades = np.minimum(1, ts / 0.2) * np.minimum(1, (DURATION - ts) / 1.0)
    track *= fades[:, None]
    peak = float(np.max(np.abs(track)))
    track *= 0.82 / max(peak, 0.001)
    rms = float(np.sqrt(np.mean(track * track)))
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(2)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes((track * 32767).astype("<i2").tobytes())
    return {"sample_rate": rate, "channels": 2, "duration": DURATION, "peak_dbfs": 20 * math.log10(0.82), "rms_dbfs": 20 * math.log10(rms)}


def encode(output: Path) -> Path:
    audio_info = soundtrack(output / "soundtrack.wav")
    target = output / "DICK_CLI_promo_1080p.mp4"
    command = [
        "ffmpeg", "-hide_banner", "-y", "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0",
        "-i", str(output / "soundtrack.wav"), "-c:v", "libx264", "-preset", "fast",
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-t", str(DURATION), str(target),
    ]
    total = int(FPS * DURATION)
    started = time.perf_counter()
    with (output / "ffmpeg.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
        try:
            for index in range(total):
                process.stdin.write(render_frame(index / FPS).tobytes())
                if index % 90 == 0:
                    print(f"Rendering {index}/{total} frames ({time.perf_counter() - started:.1f}s)", flush=True)
            process.stdin.close()
            code = process.wait()
        except BaseException:
            process.kill()
            process.wait()
            raise
    if code:
        raise RuntimeError(f"FFmpeg exited {code}; see {output / 'ffmpeg.log'}")
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(target)
    ], check=True, capture_output=True, text=True, encoding="utf-8")
    info = json.loads(probe.stdout)
    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
    assert (video["width"], video["height"]) == (W, H)
    assert video["codec_name"] == "h264" and video["pix_fmt"] == "yuv420p"
    assert video["avg_frame_rate"] == "30/1" and int(video["nb_frames"]) == total
    assert audio["codec_name"] == "aac" and int(audio["channels"]) == 2
    assert abs(float(info["format"]["duration"]) - DURATION) < 0.1
    info["original_soundtrack"] = audio_info
    info["repository"] = REPO
    info["credit"] = CREDIT
    (output / "verification.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Verified {target}: 1080p / 30fps / 30 seconds / H.264 + stereo AAC", flush=True)
    return target


def main() -> None:
    global FONT_ROOT, LOGO_PATH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-only", action="store_true")
    parser.add_argument("--font-root", type=Path, default=FONT_ROOT)
    parser.add_argument("--logo", type=Path, default=LOGO_PATH)
    parser.add_argument("--output", type=Path, default=ROOT / "promo" / "output")
    args = parser.parse_args()
    FONT_ROOT = args.font_root
    LOGO_PATH = args.logo
    for filename in FONT_FILES.values():
        if not (FONT_ROOT / filename).is_file():
            parser.error(f"font not found: {FONT_ROOT / filename}")
    if not LOGO_PATH.is_file():
        parser.error("logo not found; download logo.png from the GitHub Release to promo/.cache/ or use --logo PATH")
    if not args.preview_only and (not shutil.which("ffmpeg") or not shutil.which("ffprobe")):
        parser.error("FFmpeg and ffprobe must be available on PATH")
    args.output.mkdir(parents=True, exist_ok=True)
    previews(args.output)
    if not args.preview_only:
        encode(args.output)


if __name__ == "__main__":
    main()
