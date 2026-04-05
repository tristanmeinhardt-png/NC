import pathlib

p = pathlib.Path(r"C:\Users\meinh\NC\standart_imports\more_physics.nc")
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

targets = {110, 111, 112, 292}

for i in sorted(targets):
    if 1 <= i <= len(lines):
        l = lines[i-1]
        prefix = l[:len(l)-len(l.lstrip())]
        print(f"\nLINE {i}:")
        print(repr(l))
        print("INDENT CHARS:", [(ch, ord(ch)) for ch in prefix], "len=", len(prefix))
