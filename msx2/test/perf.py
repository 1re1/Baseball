import sys, re, struct, collections, bisect
sys.path.insert(0, 'test')
import emu
def perf(secs=900, profile=False, tag="perf"):
    sym = emu.symbols()
    G = sym['_gstate']
    steps = [("wait", 20)]
    outp = "D:/Program/Pyxel/Game/Baseball/msx2/build/shots/prof.txt"
    if profile:
        tcl = ('set ::pf [open "%s" w] ; proc samp {} { if {[peek %d] == 2} { puts $::pf [format %%04X [reg pc]] } ; after time 0.00173 samp }') % (outp, G)
        steps += [("tcl", tcl), ("tcl", "samp")]
    steps += [("peek", "d0", "_dbg", 32), ("peek", "f0", "_frame_count", 2), ("wait", secs),
              ("peek", "d1", "_dbg", 32), ("peek", "f1", "_frame_count", 2)]
    if profile:
        steps += [("tcl", "close $::pf")]
    out, txt = emu.run(steps, tag=tag, timeout=3000)
    d = [struct.unpack("<16H", bytes.fromhex(x.decode())) for x in re.findall(rb"d[01] (\w+)", txt)]
    f = [struct.unpack("<H", bytes.fromhex(x.decode()))[0] for x in re.findall(rb"f[01] (\w+)", txt)]
    frames = (f[1] - f[0]) & 0xFFFF
    over = d[1][15] - d[0][15]
    print(f"frames {frames}  overruns {over} ({over * 100 / max(1, frames):.1f}%)  pitches {d[1][0] - d[0][0]}")
    if profile:
        pcs = [int(l, 16) for l in open(outp.replace("/", "\\")) if l.strip()]
        mp = open('build/game.map', encoding='utf-8', errors='replace').read()
        funcs = sorted({(int(m.group(1), 16), m.group(2)) for m in re.finditer(r"([0-9A-F]{8})\s+(_\w+)\s", mp)})
        addrs = [a for a, _ in funcs]
        c = collections.Counter()
        for pc in pcs:
            if pc < 0x4000: c['BIOS'] += 1; continue
            if pc >= 0xF200: c['stub'] += 1; continue
            c[funcs[bisect.bisect_right(addrs, pc) - 1][1]] += 1
        for k, v in c.most_common(22):
            print(f"{v * 100 / len(pcs):5.1f}% {k}")
if __name__ == "__main__":
    perf(int(sys.argv[1]) if len(sys.argv) > 1 else 900, profile=len(sys.argv) > 2)
