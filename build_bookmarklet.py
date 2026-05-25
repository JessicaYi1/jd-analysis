"""Generate bookmarklet from bookmarklet.js source."""
import re

SRC = "d:/vibe-coding/jd analysis/bookmarklet.js"
OUT = "d:/vibe-coding/jd analysis/bookmarklet.txt"

with open(SRC, "r", encoding="utf-8") as f:
    code = f.read()

# Remove block comments
code = re.sub(r"/\*[\s\S]*?\*/", "", code)

# Remove line comments
lines = []
for line in code.split("\n"):
    # crude but safe: skip lines that start with // after stripping
    stripped = line.strip()
    if stripped.startswith("//"):
        continue
    # handle trailing comments by finding // not inside a string
    cleaned = []
    in_str = False
    str_ch = None
    i = 0
    while i < len(line):
        ch = line[i]
        if not in_str and ch in ('"', "'"):
            in_str = True
            str_ch = ch
        elif in_str and ch == str_ch and (i == 0 or line[i-1] != "\\"):
            in_str = False
        elif not in_str and ch == "/" and i+1 < len(line) and line[i+1] == "/":
            break
        cleaned.append(ch)
        i += 1
    line = "".join(cleaned)
    if line.strip():
        lines.append(line.strip())

code = " ".join(lines)
# Remove spaces around brackets/braces/parens/semicolons/commas (but NOT colons!)
code = re.sub(r"\s*([{},();\[\]])\s*", r"\1", code)
code = "javascript:" + code.strip()

with open(OUT, "w", encoding="utf-8") as f:
    f.write(code)

print(f"Done, length: {len(code)}")
