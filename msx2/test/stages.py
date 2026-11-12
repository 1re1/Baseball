import sys, re, collections, statistics, struct
sys.path.insert(0, 'test')
import emu
def stages(secs=200, tag="bp"):
    sym = emu.symbols()
    G = sym['_gstate']
    pts = ["_play_update", "_scroll_update", "_spr_frame_begin", "_play_draw", "_msg_draw", "_frame_sync", "_spr_commit", "_scroll_commit"]
    outp = "D:/Program/Pyxel/Game/Baseball/msx2/build/shots/bp.txt"
    tcl = 'set ::bf [open "%s" w] ; ' % outp
    for p in pts:
        tcl += 'debug set_bp %d {[peek %d] == 2} {puts $::bf "%s [machine_info time]"} ; ' % (sym[p], G, p)
    out, txt = emu.run([("wait", 20), ("tcl", tcl), ("wait", secs), ("tcl", "close $::bf")], tag=tag, timeout=2000)
    seq = [(l.split()[0], float(l.split()[1])) for l in open(outp.replace("/", "\\")) if l.strip()]
    dur = collections.defaultdict(list)
    for (n1, t1), (n2, t2) in zip(seq, seq[1:]):
        dur[(n1, n2)].append((t2 - t1) * 3579545)
    for k, v in sorted(dur.items(), key=lambda kv: -statistics.median(kv[1])):
        print(f"{k[0]:18s} -> {k[1]:18s} n={len(v):5d} median={statistics.median(v):8.0f}T  p90={sorted(v)[int(len(v) * 0.9)]:8.0f}T")
if __name__ == "__main__":
    stages()
