import sys, re, collections
sys.path.insert(0, 'test')
import emu
def smooth(secs=300, tag="sm"):
    sym = emu.symbols()
    G = sym['_gstate']; VC = sym['_nt_cx']
    outp = "D:/Program/Pyxel/Game/Baseball/msx2/build/shots/%s.txt" % tag
    # 表示の途中（フレームの始まりから 5ms 後 ≒ 80 ライン目）で読む。帰線期間で書き換えている途中を読まないように
    tcl = ('set ::sf [open "%s" w] ; proc rd {} { set r [debug read_block {VDP regs} 0 24] ; binary scan $r c* v ; '
           'puts $::sf "[peek %d] [peek [expr {%d + ([lindex $v 2] & 1)}]] [expr {[lindex $v 18] & 15}] [expr {[lindex $v 23] & 255}]" } ; '
           'proc smp {} { after time 0.005 rd ; after frame smp }') % (outp, G, VC)
    emu.run([("wait", 20), ("tcl", tcl), ("tcl", "smp"), ("wait", secs), ("tcl", "close $::sf")], tag=tag, timeout=2000)
    rows = [list(map(int, l.split())) for l in open(outp.replace("/", "\\")) if l.strip()]
    stalls = jumps = moving = 0
    prev = None
    hist = collections.Counter()
    for gs, vcx, fine, r23 in rows:
        x = vcx * 8 + fine
        if prev and gs == 2 and prev[0] == 2:
            dx = x - prev[1]
            dy = (r23 - prev[2] + 128) % 256 - 128
            hist[(dx, dy)] += 1
        prev = (gs, x, r23)
    # 動いている途中で止まった（前後は動いているのに Δ=0）
    seq = []
    prev = None
    for gs, vcx, fine, r23 in rows:
        x = vcx * 8 + fine
        if prev and gs == 2 and prev[0] == 2:
            seq.append((x - prev[1], (r23 - prev[2] + 128) % 256 - 128))
        prev = (gs, x, r23)
    for i in range(1, len(seq) - 1):
        a, b, c = seq[i - 1], seq[i], seq[i + 1]
        if b == (0, 0) and a != (0, 0) and c != (0, 0):
            stalls += 1
        if abs(b[0]) > 3 or abs(b[1]) > 5:
            jumps += 1
        if b != (0, 0):
            moving += 1
    print(f"play frames {len(seq)}  moving {moving}  stalls(mid-motion) {stalls}  jumps {jumps}")
    print("most common (dx,dy):", hist.most_common(12))
if __name__ == "__main__":
    smooth()
