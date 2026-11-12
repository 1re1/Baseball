import sys, re, collections
sys.path.insert(0, 'test')
import emu
def sprline(secs=200, tag="sl"):
    sym = emu.symbols()
    G = sym['_gstate']
    outp = "D:/Program/Pyxel/Game/Baseball/msx2/build/shots/%s.txt" % tag
    # 毎フレーム：状態・R#23・属性表 128 バイト（画面を消しているフレームは数えない）
    tcl = ('set ::sf [open "%s" w] ; proc smp {} { set r [debug read_block {VDP regs} 0 24] ; binary scan $r c* v ; '
           'binary scan [debug read_block VRAM 0x5E00 128] H* s ; if {[lindex $v 1] & 0x40} { puts $::sf "[peek %d] [expr {[lindex $v 23] & 255}] $s" } ; after frame smp }') % (outp, G)
    emu.run([("wait", 20), ("tcl", tcl), ("tcl", "smp"), ("wait", secs), ("tcl", "close $::sf")], tag=tag, timeout=2000)
    res = collections.defaultdict(lambda: [0, 0, collections.Counter()])
    for l in open(outp.replace("/", "\\")):
        p = l.split()
        if len(p) < 3:
            continue
        gs, r23, sat = int(p[0]), int(p[1]), bytes.fromhex(p[2])
        lines = [0] * 212
        for i in range(32):
            y = sat[i * 4]
            if y == 216:
                break
            top = (y + 1 - r23) & 255
            for k in range(16):
                ln = (top + k) & 255
                if ln < 212:
                    lines[ln] += 1
        m = max(lines)
        r = res[gs]
        r[0] += 1
        if m > 8:
            r[1] += 1
        r[2][min(m, 12)] += 1
    names = {0: "ATBAT", 1: "PITCH", 2: "PLAY", 3: "RESULT", 4: "CHANGE"}
    for gs, (n, over, hist) in sorted(res.items()):
        print(f"{names.get(gs, gs):7s} frames {n:6d}  lines>8: {over:5d} ({over * 100 / n:.1f}%)  max-per-line hist {sorted(hist.items())}")
if __name__ == "__main__":
    sprline()
