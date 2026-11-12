"""全ての関数（static も）のアドレス：.lst の中の位置 + 地図（map）の大域記号から求めたモジュールの先頭"""
import re, glob, os, bisect, collections, sys

def all_syms():
    mp = open('build/game.map', encoding='utf-8', errors='replace').read()
    glob_ = {m.group(2): int(m.group(1), 16) for m in re.finditer(r"([0-9A-F]{8})\s+(_\w+)\s", mp)}
    out = []
    for f in glob.glob('build/obj/*.lst'):
        area = None
        labs = []
        for line in open(f, encoding='utf-8', errors='replace'):
            m = re.search(r"\.area\s+(\w+)", line)
            if m: area = m.group(1); continue
            m = re.match(r"\s+([0-9A-F]{8})\s+\d+\s+(_\w+)::?\s*$", line)
            if m and area in ('_CODE', 'OVL'):
                labs.append((area, int(m.group(1), 16), m.group(2)))
        for ar in ('_CODE', 'OVL'):
            L = [(o, n) for a, o, n in labs if a == ar]
            base = None
            for o, n in L:
                if n in glob_: base = glob_[n] - o; break
            if base is None: continue
            out += [(base + o, n) for o, n in L]
    return sorted(set(out))

if __name__ == "__main__":
    S = all_syms()
    addrs = [a for a, _ in S]
    pcs = [int(l, 16) for l in open('build/shots/prof.txt') if l.strip()]
    c = collections.Counter()
    for pc in pcs:
        if pc < 0x4000: c['BIOS'] += 1; continue
        if pc >= 0xF200: c['stub'] += 1; continue
        c[S[bisect.bisect_right(addrs, pc) - 1][1]] += 1
    for k, v in c.most_common(30):
        print(f"{v * 100 / len(pcs):5.1f}% {k}")
