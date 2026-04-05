import os, re

results = []
skip_patterns = [
    re.compile(r'\{\{.*?\.(icon|avatar).*?\}\}'),
    re.compile(r'subject_icon'),
    re.compile(r'for emoji in'),
    re.compile(r'data-lucide'),
    re.compile(r"'avatar'"),
]

for root, dirs, files in os.walk('app/templates'):
    for fname in files:
        if not fname.endswith('.html'):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, encoding='utf-8') as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            skip = False
            for pat in skip_patterns:
                if pat.search(line):
                    skip = True
                    break
            if skip:
                continue
            for ch in line:
                cp = ord(ch)
                if (0x1F300 <= cp <= 0x1F9FF) or (0x2600 <= cp <= 0x27BF) or (0x23E0 <= cp <= 0x23FF):
                    rel = os.path.relpath(fpath, 'app/templates')
                    results.append(f'{rel}:{i}: {line.rstrip()[:100]}')
                    break

for r in sorted(set(results)):
    print(r)
print('DONE')
