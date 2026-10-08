#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Replace em/en dashes in a markdown file with honest punctuation, context-aware:
  " — " (spaced)  -> ", "     (parenthetical / appositive)
  "word—word"     -> ", word" style handled by simple rule
  " – " / "–"     -> "-"
Preserves `->` arrows and ASCII hyphens.
"""
import re
import sys

SRC = sys.argv[1]
DST = sys.argv[2] if len(sys.argv) > 2 else SRC

with open(SRC, encoding="utf-8") as f:
    text = f.read()

before = text.count("\u2014") + text.count("\u2013")

# 1. spaced em/en dash used as a parenthetical break:  " — " -> ", "
text = re.sub(r"\s+[\u2014\u2013]\s+", ", ", text)

# 2. any remaining bare em/en dash -> ", " if between word chars, else "-"
text = re.sub(r"(?<=\w)[\u2014\u2013](?=\w)", ", ", text)
text = text.replace("\u2014", "-").replace("\u2013", "-")

# tidy artefacts
text = re.sub(r",\s*,", ",", text)
text = re.sub(r"\(\s*,\s*", "(", text)
text = re.sub(r"\s+,", ",", text)
text = re.sub(r",\s+\.", ".", text)

after = text.count("\u2014") + text.count("\u2013")

with open(DST, "w", encoding="utf-8") as f:
    f.write(text)

print("em/en dashes before: %d  after: %d" % (before, after))
