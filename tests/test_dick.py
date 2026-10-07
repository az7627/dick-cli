import random
import re
import subprocess
import sys
import unittest
import unicodedata
from pathlib import Path

from dick.corrupt import corrupt
from dick.modes import MODES

ROOT = Path(__file__).resolve().parents[1]


def cli(*args: str, input_text: str = "") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "dick", *args],
        input=input_text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        timeout=15,
    )


class CorruptionTests(unittest.TestCase):
    def test_basic_input(self):
        result = corrupt("hello world", seed=123)
        self.assertTrue(result.text)
        self.assertNotEqual(result.text, "hello world")
        self.assertEqual((result.mode, result.level), ("normal", 2))

    def test_seed_is_deterministic_for_every_mode_and_level(self):
        for mode in MODES:
            for level in range(1, 5):
                with self.subTest(mode=mode, level=level):
                    options = dict(mode=mode, level=level, seed=123)
                    self.assertEqual(corrupt("hello world 你好 💀", **options), corrupt("hello world 你好 💀", **options))

    def test_different_seeds(self):
        self.assertNotEqual(corrupt("hello world", seed=123), corrupt("hello world", seed=456))

    def test_random_mode_is_seeded_and_ignores_explicit_mode(self):
        first = corrupt("hello world", random_mode=True, mode="not-a-mode", seed=42)
        self.assertEqual(first, corrupt("hello world", random_mode=True, mode="leet", seed=42))
        self.assertIn(first.mode, MODES)
        selected = {corrupt("hello world", random_mode=True, seed=seed).mode for seed in range(50)}
        self.assertEqual(selected, set(MODES))

    def test_does_not_change_global_random_state(self):
        previous = random.getstate()
        corrupt("hello world", seed=42, random_mode=True)
        self.assertEqual(random.getstate(), previous)

    def test_level_one_is_light_in_all_modes(self):
        for mode in MODES:
            for seed in range(20):
                with self.subTest(mode=mode, seed=seed):
                    output = corrupt("hello world", mode=mode, level=1, seed=seed).text
                    self.assertTrue(output.isascii())
                    self.assertFalse(any(char.isdigit() for char in output))
                    self.assertLessEqual(len(output), len("hello world") + 2)
                    self.assertNotIn("[", output)
        mild = corrupt("hello world", level=1, seed=42).text
        strong = corrupt("hello world", level=4, seed=42).text
        self.assertGreater(len(strong), len(mild) + 10)

    def test_words_survive_in_order_even_at_level_four(self):
        sentence = "I forgot to backup the database download completed successfully"
        variants = {"a": "aA4àÀ", "e": "eE3ëË", "i": "iI1ïÏ", "o": "oO0øØ", "s": "sS5", "t": "tT7", "u": "uUüÜ"}
        for mode in MODES:
            for seed in range(40):
                with self.subTest(mode=mode, seed=seed):
                    output = corrupt(sentence, mode=mode, level=4, seed=seed).text
                    readable = "".join(char for char in output if not unicodedata.category(char).startswith("M"))
                    cursor = 0
                    for word in sentence.lower().split():
                        pattern = "".join("[" + variants.get(char, char + char.upper()) + "]+" for char in word)
                        match = re.search(pattern, readable[cursor:])
                        self.assertIsNotNone(match, (word, output))
                        cursor += match.end()

    def test_numbers_urls_ips_emails_and_paths_are_exact(self):
        tokens = (
            "192.168.1.1", "8080", "-12.50", "2026-10-07", "12:30:45", "0xDEAD", "1.25e-3",
            "2001:db8::1", "fe80::1%eth0", "::1", "https://example.com/test?q=42#anchor",
            "www.example.com/test", "user.name@example.com", r"C:\Users\me\backup.db",
            r"\\server\share\backup.txt", "/var/lib/data.db", "./data/backup.json", "../data/a.txt",
            "~/data/test.csv", "src/main.py", r"folder\backup.txt", "backup.sqlite",
            '"C:\\Program Files\\app\\data.txt"', '"/home/a user/backup.db"',
            '"folder with spaces/backup.txt"', "C:\\", "/", "./", "../", "~/",
        )
        for mode in MODES:
            for level in range(1, 5):
                for seed in range(5):
                    with self.subTest(mode=mode, level=level, seed=seed):
                        output = corrupt("open " + " and ".join(tokens) + " successfully", mode=mode, level=level, seed=seed).text
                        for token in tokens:
                            self.assertIn(token, output)

    def test_extension_does_not_attach_to_a_protected_tail(self):
        for token in ("https://example.com/test", r"C:\data\backup.txt", "8080"):
            for mode in ("normal", "leet", "terminal", "brainrot"):
                output = corrupt(token, level=4, mode=mode, seed=42).text
                self.assertRegex(output, re.escape(token) + r" \.\w+")

    def test_chinese_characters_and_original_emoji_survive(self):
        chinese = "数据库备份成功你好世界"
        emoji = "💀 👩🏽‍💻 👨‍👩‍👧‍👦 🇭🇰 1️⃣ #️⃣ *️⃣ ❤️"
        for mode in MODES:
            for level in range(1, 5):
                with self.subTest(mode=mode, level=level):
                    output = corrupt(chinese + " hello " + emoji, mode=mode, level=level, seed=42).text
                    self.assertEqual("".join(char for char in output if char in chinese), chinese)
                    for token in emoji.split():
                        self.assertIn(token, output)

    def test_multiline_preserves_endings_blank_lines_and_indentation(self):
        text = "  Hello world\r\n\tThis is a test  \n\nGoodbye\r\n\t \r"
        for mode in MODES:
            with self.subTest(mode=mode):
                output = corrupt(text, level=4, mode=mode, seed=42).text
                self.assertEqual(re.findall(r"\r\n|\r|\n", output), re.findall(r"\r\n|\r|\n", text))
                lines = output.splitlines()
                self.assertTrue(lines[0].startswith("  "))
                self.assertTrue(lines[1].startswith("\t"))
                self.assertTrue(lines[1].endswith("  "))
                self.assertEqual(lines[2], "")
                self.assertEqual(lines[4], "\t ")

    def test_unicode_line_separators_are_preserved(self):
        text = "hello\u2028world\u2029goodbye\x85"
        output = corrupt(text, level=4, seed=42).text
        self.assertEqual(re.findall(r"[\u2028\u2029\x85]", output), ["\u2028", "\u2029", "\x85"])

    def test_glitch_has_bounded_combining_marks(self):
        for seed in range(20):
            output = corrupt("hello world " * 100, level=4, mode="glitch", seed=seed).text
            added = [char for char in output if unicodedata.category(char).startswith("M")]
            self.assertLessEqual(len(added), 3)
            self.assertNotRegex(output, r"[\u0336-\u0338]{2}")

    def test_long_unicode_input(self):
        text = ("hello 数据库 💀 8080 " * 5000) + "\n"
        output = corrupt(text, level=4, mode="glitch", seed=42).text
        self.assertEqual(output.count("💀"), 5000)
        self.assertEqual(output.count("8080"), 5000)
        self.assertTrue(output.endswith("\n"))

    def test_long_dotted_and_dashed_input(self):
        for separator in (".", "-"):
            text = ("a" + separator) * 50000
            output = corrupt(text, level=4, mode="glitch", seed=42).text
            self.assertGreaterEqual(len(output), len(text))
            self.assertNotIn("\n", output)

    def test_empty_library_input_and_invalid_options(self):
        self.assertEqual(corrupt("", seed=1).text, "")
        self.assertEqual(corrupt("\n\t \r\n", seed=1).text, "\n\t \r\n")
        for level in (0, 5, True, 1.5):
            with self.assertRaisesRegex(ValueError, "level must be between 1 and 4"):
                corrupt("hello", level=level)
        with self.assertRaisesRegex(ValueError, "unknown mode"):
            corrupt("hello", mode="abc")


class CliTests(unittest.TestCase):
    def test_plain_contains_only_result(self):
        process = cli("--plain", "--seed", "123", "hello world")
        expected = corrupt("hello world", seed=123).text + "\n"
        self.assertEqual(process.returncode, 0)
        self.assertEqual(process.stdout.decode("utf-8"), expected)
        self.assertEqual(process.stderr, b"")

    def test_default_output_has_input_mode_level_and_result(self):
        process = cli("--seed", "123", "hello world")
        self.assertEqual(process.returncode, 0)
        output = process.stdout.decode("utf-8")
        for part in ("Distorted Input Context Keeper", "Input:\nhello world", "Output:\n", "Mode: normal", "DICK level: 2/4"):
            self.assertIn(part, output)

    def test_seed_repeats_across_processes(self):
        for args in (("--seed", "123"), ("--random", "--seed", "123")):
            self.assertEqual(cli(*args, "hello world").stdout, cli(*args, "hello world").stdout)

    def test_stdin_and_exact_multiline_output(self):
        text = "你好 hello 💀\r\n\r\n  Goodbye  \n"
        process = cli("--plain", "--seed", "42", input_text=text)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(process.stdout, corrupt(text, seed=42).text.encode("utf-8"))
        self.assertEqual(process.stderr, b"")

    def test_explicit_text_takes_precedence_even_if_empty(self):
        process = cli("--plain", "--seed", "42", "hello world", input_text="ignored stdin")
        self.assertEqual(process.stdout.decode("utf-8"), corrupt("hello world", seed=42).text + "\n")
        empty = cli("", input_text="hello world")
        self.assertEqual(empty.returncode, 1)
        self.assertIn(b"error: no input text", empty.stderr)

    def test_no_input(self):
        for input_text in ("", "  \t\r\n"):
            process = cli(input_text=input_text)
            self.assertEqual(process.returncode, 1)
            self.assertEqual(process.stdout, b"")
            self.assertIn(b"error: no input text", process.stderr)
            self.assertIn(b'Try:\n  dick "hello world"', process.stderr)

    def test_invalid_levels_modes_and_seed(self):
        for level in ("0", "10", "abc", "2.5"):
            process = cli("-l", level, "hello")
            self.assertEqual(process.returncode, 2)
            self.assertEqual(process.stderr, b"error: level must be between 1 and 4\n")
            self.assertEqual(process.stdout, b"")
        process = cli("-m", "abc", "hello")
        self.assertEqual(process.returncode, 2)
        self.assertIn(b"error: unknown mode 'abc'", process.stderr)
        self.assertIn(b"Available modes:", process.stderr)
        for mode in MODES:
            self.assertIn(mode.encode(), process.stderr)
        seed = cli("--seed", "abc", "hello")
        self.assertEqual(seed.returncode, 2)
        self.assertNotIn(b"Traceback", seed.stderr)

    def test_random_ignores_invalid_mode_and_reports_actual_mode(self):
        process = cli("--random", "--seed", "42", "-m", "abc", "hello world")
        self.assertEqual(process.returncode, 0)
        actual = corrupt("hello world", seed=42, random_mode=True).mode
        self.assertIn(f"Mode: {actual}".encode(), process.stdout)

    def test_help_and_version(self):
        help_output = cli("--help")
        self.assertEqual(help_output.returncode, 0)
        for flag in ("--level", "--mode", "--random", "--seed", "--plain", "--help", "--version"):
            self.assertIn(flag.encode(), help_output.stdout)
        version = cli("-V")
        self.assertEqual(version.returncode, 0)
        self.assertEqual(version.stdout, b"DICK v0.1.0\n")

    def test_option_terminator(self):
        text = "--hello world"
        process = cli("--plain", "--seed", "42", "--", text)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(process.stdout.decode("utf-8"), corrupt(text, seed=42).text + "\n")

    def test_invalid_utf8_stdin(self):
        process = subprocess.run(
            [sys.executable, "-m", "dick", "--plain"], input=b"\xff", capture_output=True, cwd=ROOT, timeout=15
        )
        self.assertEqual(process.returncode, 1)
        self.assertEqual(process.stdout, b"")
        self.assertIn(b"error: input must be valid UTF-8", process.stderr)


if __name__ == "__main__":
    unittest.main()
