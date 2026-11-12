import sys, re, collections, statistics
sys.path.insert(0, 'test')
import emu
def frames(secs=200, tag="bp8"):
    sym = emu.symbols()
    G = sym['_gstate']; B = sym['_ball']
    outp = "D:/Program/Pyxel/Game/Baseball/msx2/build/shots/%s.txt" % tag
    tcl = 'set ::bf [open "%s" w] ; ' % outp
    tcl += 'debug set_bp %d {[peek %d] == 2} {puts $::bf "S [machine_info time] [peek %d] [peek %d]"} ; ' % (sym['_input_update'], G, B + 12, B + 14)
    tcl += 'debug set_bp %d {[peek %d] == 2} {puts $::bf "E [machine_info time]"} ; ' % (sym['_frame_sync'], G)
    tcl += 'debug set_bp %d {[peek %d] == 2} {puts $::bf "U"} ; ' % (sym['_play_update'], G)
    tcl += 'debug set_bp %d {[peek %d] == 2} {puts $::bf "D"} ; ' % (sym['_play_draw'], G)
    emu.run([("wait", 20), ("tcl", tcl), ("wait", secs), ("tcl", "close $::bf")], tag=tag, timeout=2000)
    rows = [l.split() for l in open(outp.replace("/", "\\")) if l.strip()]
    # S の間にある U/D で種類を決め、次の S までの時間を測る（frame_sync の入口から入口まで = 1 ループ）
    out = collections.defaultdict(list)
    cur = None
    for r in rows:
        if r[0] == "S":
            cur = [float(r[1]), "", "m%s%s" % (r[2], "b" if int(r[3]) else "")]
        elif r[0] == "E":
            if cur is not None:
                out[(cur[1] or "-", cur[2])].append((float(r[1]) - cur[0]) * 3579545)
            cur = None
        elif cur is not None:
            cur[1] += r[0]
    for k, v in sorted(out.items()):
        v = sorted(v)
        over = sum(1 for x in v if x > 50000)
        print(f"{k[0]:3s} {k[1]:6s} n={len(v):5d} median={int(statistics.median(v)):6d} p90={int(v[int(len(v) * .9)]):6d} max={int(v[-1]):7d} over50K={over}")
if __name__ == "__main__":
    frames()
