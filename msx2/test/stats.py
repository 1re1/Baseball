import sys, struct, re, time
sys.path.insert(0, 'test')
import emu
NAMES = ["pitch","swing","contact","foul","HR","hit","SO","BB","flyout","out","run","2B","3B","games","timeout","overrun"]
def stats(secs=2400, tag="stats", machine="C-BIOS_MSX2_JP", teams=0):
    steps = [("wait", 6.0)] + ([("tcl", "poke %d %d" % (emu.symbols()["_test_teams"], teams))] if teams else []) + [("wait", secs), ("peek", "dbg", "_dbg", 32), ("shot", "end")]
    t0 = time.time()
    out, txt = emu.run(steps, tag=tag, machine=machine, timeout=3000)
    m = re.search(rb"dbg (\w+)", txt)
    d = struct.unpack("<16H", bytes.fromhex(m.group(1).decode()))
    res = dict(zip(NAMES, d))
    print(f"{secs}s emu in {time.time()-t0:.1f}s:", res)
    g = max(1, res["games"])
    print(f"per game: runs {res['run']/g:.1f}  hits {res['hit']/g:.1f}  HR {res['HR']/g:.2f}  SO {res['SO']/g:.1f}  BB {res['BB']/g:.1f}  pitches {res['pitch']/g:.0f}  fouls {res['foul']/g:.1f}")
    return res
if __name__ == "__main__":
    stats(int(sys.argv[1]) if len(sys.argv) > 1 else 2400, teams=int(sys.argv[2], 16) if len(sys.argv) > 2 else 0)
