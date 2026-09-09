#!/usr/bin/env python3
"""Fail a commit whose comments run longer than MAX_LINES. Tune the number, do not disable."""

import ast
import re
import sys
import textwrap
from pathlib import Path

MAX_LINES = 2

# Directives and metadata a tool reads. These are never narration.
EXEMPT = re.compile(
	r"noqa|ponytail|type:\s*ignore|pragma|pylint|ruff:|mypy:|isort:|fmt:\s*(on|off)"
	r"|eslint|biome-ignore|@ts-|prettier-ignore|prettier|Copyright|SPDX|License|coding[:=]"
)

MARKUP_BLOCK = re.compile(r"<!--.*?-->|\{#.*?#\}|/\*.*?\*/", re.S)
MARKUP_SUFFIXES = {".html", ".vue", ".js", ".ts", ".css", ".scss"}


def content_lines(text: str) -> int:
	"""Lines that actually carry words, ignoring the delimiters and blank lines."""
	stripped = re.sub(r"^\s*(<!--|\{#|/\*+|\"\"\"|''')|(-->|#\}|\*+/|\"\"\"|''')\s*$", "", text.strip())
	return len([line for line in stripped.splitlines() if line.strip(" \t*#-")])


def check_python(path: Path, source: str) -> list[str]:
	problems = []
	try:
		tree = ast.parse(source)
	except SyntaxError:
		return []  # a broken file is another hook's problem

	for node in ast.walk(tree):
		if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
			continue
		docstring = ast.get_docstring(node, clean=False)
		if docstring and not EXEMPT.search(docstring) and content_lines(docstring) > MAX_LINES:
			line = getattr(node, "lineno", 1)
			problems.append(f"{path}:{line}: docstring is {content_lines(docstring)} lines (max {MAX_LINES})")

	problems += check_comment_runs(path, source, "#", is_commented_out_python)
	return problems


def is_commented_out_python(block: list[str]) -> bool:
	"""Commented-out code is code, not narration. hooks.py is mostly this."""
	lines = [re.sub(r"^\s*#\s?", "", line) for line in block]
	if not "".join(lines).strip():
		return True
	# Frappe's generated hooks.py leads its commented-out examples with a sentence, so try
	# again without the opening lines before calling it prose.
	statements = (ast.Assign, ast.AnnAssign, ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)
	for start in range(len(lines)):
		try:
			tree = ast.parse(textwrap.dedent("\n".join(lines[start:])))
		except SyntaxError:
			continue
		# A bare word parses too, so only a real statement counts as commented-out code.
		if any(isinstance(node, statements) for node in tree.body):
			return True
	return False


def is_banner(block: list[str]) -> bool:
	"""Dividers and short labels that section a long table. Prose has sentences; a banner does not."""
	for line in block:
		body = re.sub(r"^\s*(#|//)\s?", "", line).strip()
		if body and not re.fullmatch(r"[-=*_~ ]+", body) and len(body.split()) > 4:
			return False
	return True


def check_comment_runs(path: Path, source: str, marker: str, looks_like_code) -> list[str]:
	"""Flag runs of single-line comments, sparing directives and commented-out code."""
	problems, run, start = [], [], 0
	for number, raw in enumerate([*source.splitlines(), ""], start=1):
		line = raw.strip()
		if line.startswith(marker) and not line.startswith("#!"):
			run.append(raw)
			start = start or number
			continue
		if (
			len(run) > MAX_LINES
			and not any(EXEMPT.search(x) for x in run)
			and not looks_like_code(run)
			and not is_banner(run)
		):
			problems.append(f"{path}:{start}: comment block is {len(run)} lines (max {MAX_LINES})")
		run, start = [], 0
	return problems


def check_markup(path: Path, source: str) -> list[str]:
	problems = []
	for match in MARKUP_BLOCK.finditer(source):
		block = match.group(0)
		if EXEMPT.search(block):
			continue
		# Commented-out markup opens with a tag. Prose that merely mentions <nav> does not.
		if re.match(r"^\s*<\w", re.sub(r"^\s*(<!--|\{#|/\*+)", "", block)):
			continue
		if content_lines(block) > MAX_LINES:
			line = source.count("\n", 0, match.start()) + 1
			problems.append(f"{path}:{line}: comment is {content_lines(block)} lines (max {MAX_LINES})")

	problems += check_comment_runs(path, source, "//", lambda block: False)
	return problems


def main(argv: list[str]) -> int:
	problems = []
	for name in argv:
		path = Path(name)
		if not path.is_file():
			continue
		source = path.read_text(errors="ignore")
		if path.suffix == ".py":
			problems += check_python(path, source)
		elif path.suffix in MARKUP_SUFFIXES:
			problems += check_markup(path, source)

	if problems:
		print("Comments longer than %d lines are narration - cut them to the gotcha:\n" % MAX_LINES)
		print("\n".join("  " + p for p in problems))
		print("\nKeep: a quirk, a version constraint, an ordering requirement, a defect reference.")
		print("Drop: why it is built this way. That belongs in the commit message.")
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main(sys.argv[1:]))
