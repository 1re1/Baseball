# -*- coding: utf-8 -*-
"""openMSX で ROM を動かすテスト。手順を Tcl にして実行する"""
import os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENMSX = r"C:\Program Files\openMSX\openmsx.exe"
SP = r"C:\Users\user\AppData\Local\Temp\claude\82437f8c103fceb4\96b39d11-d807-4146-889b-28b2b0440172\scratchpad"
SHOTS = os.path.join(ROOT, "build", "shots")

KEYS = {  # 名前: (行, ビット)
    "space": (8, 0x01), "left": (8, 0x10), "up": (8, 0x20), "down": (8, 0x40), "right": (8, 0x80),
    "z": (5, 0x80), "x": (5, 0x20), "ret": (7, 0x80), "f1": (6, 0x20), "m": (4, 0x04), "b": (2, 0x80), "esc": (7, 0x04),
}


def symbols():
    mp = open(os.path.join(ROOT, "build", "game.map"), encoding="utf-8", errors="replace").read()
    out = {}
    for m in re.finditer(r"([0-9A-F]{8})\s+(_\w+)", mp):
        out[m.group(2)] = int(m.group(1), 16)
    return out


def run(steps, machine="C-BIOS_MSX2_JP", tag="t", rom=None, extra="", timeout=600, romtype=None):
    """steps: list of ("wait", s) / ("key", name, hold_s) / ("keys", [names], hold_s) / ("shot", name) / ("peek", label, sym_or_addr, n)"""
    rom = rom or os.path.join(ROOT, "MSXSTADIUM.ROM")
    os.makedirs(SHOTS, exist_ok=True)
    sym = symbols()
    res = os.path.join(SHOTS, tag + "_result.txt").replace("\\", "/")
    t = 0.0
    lines = ["set throttle off", f'set f [open "{res}" w]', extra,
             'proc fshot {base k n} { screenshot -raw "${base}_$k.png" ; if {$k + 1 < $n} { after frame [list fshot $base [expr {$k + 1}] $n] } else { set ::throttle off } }']
    for st in steps:
        k = st[0]
        if k == "wait":
            t += st[1]
        elif k in ("key", "keys"):
            names = [st[1]] if k == "key" else st[1]
            for nm in names:
                r, b = KEYS[nm]
                lines.append(f"after time {t:.3f} {{keymatrixdown {r} {b}}}")
                lines.append(f"after time {t + st[2]:.3f} {{keymatrixup {r} {b}}}")
            t += st[2] + 0.05
        elif k == "shot":
            path = os.path.join(SHOTS, f"{tag}_{st[1]}.png").replace("\\", "/")
            lines.append(f'after time {t:.3f} {{set throttle on}}')
            lines.append(f'after time {t + 0.07:.3f} {{screenshot -raw "{path}"; set throttle off}}')
            t += 0.08
        elif k == "frames":
            # 連続した n フレームを撮る
            base = os.path.join(SHOTS, f"{tag}_{st[1]}").replace("\\", "/")
            n = st[2]
            lines.append(f'after time {t:.3f} {{set throttle on; after frame [list fshot "{base}" 0 {n}]}}')
            t += n / 60 + 0.2
        elif k == "peek":
            label, a, n = st[1], st[2], st[3]
            addr = sym[a] if isinstance(a, str) else a
            lines.append(f'after time {t:.3f} {{binary scan [debug read_block memory {addr} {n}] H* hx; puts $f "{label} $hx"; flush $f}}')
        elif k == "tcl":
            lines.append(f"after time {t:.3f} {{{st[1]}}}")
    lines.append(f'after time {t + 0.1:.3f} {{puts $f "pc=[format %04X [reg pc]] t=[machine_info time]"; close $f; exit}}')
    tcl = os.path.join(SP, f"emu_{tag}.tcl")
    open(tcl, "w").write("\n".join(lines) + "\n")
    env = dict(os.environ)
    env["OPENMSX_USER_DATA"] = os.path.join(SP, "omsx", "share")
    cart = ["-cart", rom] + (["-romtype", romtype] if romtype else [])
    r = subprocess.run([OPENMSX, "-machine", machine] + cart + ["-script", tcl],
                       capture_output=True, text=True, timeout=timeout, env=env)
    out = r.stdout + r.stderr
    txt = open(res.replace("/", os.sep), "rb").read() if os.path.exists(res) else b""
    return out, txt


def blk(txt, label):
    m = re.search(label.encode() + rb" (.*)", txt)
    return m.group(1) if m else None


if __name__ == "__main__":
    steps = [("wait", 3.0), ("shot", "title"), ("key", "space", 0.1), ("wait", 1.0), ("shot", "select"),
             ("key", "space", 0.1), ("wait", 0.5), ("key", "space", 0.1), ("wait", 2.5), ("shot", "game"),
             ("peek", "gstate", "_gstate", 1), ("wait", 3), ("shot", "game2")]
    out, txt = run(steps, tag="smoke")
    print(out[-2000:])
    print(txt.decode("latin1"))


def watch_event(dbg_index, tag, shots=14, interval=0.35, max_secs=3000, machine="C-BIOS_MSX2_JP"):
    """デモ試合を回し、dbg[dbg_index] が増えたらスクリーンショットを続けて撮る"""
    sym = symbols()
    addr = sym["_dbg"] + dbg_index * 2
    base = os.path.join(SHOTS, tag).replace("\\", "/")
    tcl = f'''
set ::ev_last -1
set ::ev_n 0
proc ev_shot {{k}} {{
  set ::ev_n [expr {{$::ev_n + 1}}]
  set ::throttle on
  after time 0.06 [list ev_take $k]
}}
proc ev_take {{k}} {{
  screenshot -raw "{base}_$k.png"
  set ::throttle off
  if {{$k < {shots - 1}}} {{ after time {interval} [list ev_shot [expr {{$k + 1}}]] }} else {{ exit }}
}}
proc ev_poll {{}} {{
  set v [peek16 {addr}]
  if {{$::ev_last < 0}} {{ set ::ev_last $v }}
  if {{$v != $::ev_last}} {{ ev_shot 0 ; return }}
  after frame ev_poll
}}
'''
    one = tcl.replace(chr(10), " ; ").replace("{ ;", "{").replace("; }", "}")
    steps = [("tcl", one), ("wait", 20), ("tcl", "ev_poll"), ("wait", max_secs)]
    return run(steps, tag=tag, machine=machine, timeout=1800)


def sheet(tag, n, cols=4, out=None):
    from PIL import Image
    ims = []
    for k in range(n):
        p = os.path.join(SHOTS, f"{tag}_{k}.png")
        if os.path.exists(p):
            ims.append(Image.open(p).convert("RGB"))
    if not ims:
        return None
    W, H = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    s = Image.new("RGB", (W * cols, H * rows))
    for k, im in enumerate(ims):
        s.paste(im, ((k % cols) * W, (k // cols) * H))
    out = out or os.path.join(SHOTS, f"{tag}_sheet.png")
    s.save(out)
    return out
