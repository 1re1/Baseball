# -*- coding: utf-8 -*-
"""ビルド：アセット生成 → C/asm のコンパイル → リンク → 512KB（4M ビット）の ROM（ASCII16）"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS = r"D:\Program\MSX\MSXgl\MSXgl-1.3.2\tools"
SDCC = os.path.join(TOOLS, "sdcc", "bin", "sdcc.exe")
SDAS = os.path.join(TOOLS, "sdcc", "bin", "sdasz80.exe")
SJASM = os.path.join(TOOLS, "build", "Asm", "sjasmplus.exe")
B = os.path.join(ROOT, "build")
OBJ = os.path.join(B, "obj")
GEN = os.path.join(B, "gen")
ROM_NAME = "MSXSTADIUM.ROM"

CODE_LOC = 0x4000
IMAGE_END = 0xF000         # 本体＋変数の終わり（F000h〜 は ROM 読み込み関数とスタック）

C_SRC = ["main.c", "vdp.c", "scroll.c", "sprite.c", "game.c", "play.c", "ai.c", "sound.c", "menu.c", "screens.c", "play2.c"]
# オーバーレイ（screens.c）：RAM の OVL_ADDR〜 で動く。ROM ではバンク 7 の先頭に置く
OVL_FILES = {"screens.c"}
# オーバーレイ A の後ろの 512 バイト（F000h〜F1FFh）：球場マップ（E300h〜EFFFh）に上書きされないので、
# 試合中に呼ぶ関数を置ける（play2.c）。ROM ではオーバーレイ A と同じバンク 7 の 1300h〜
OVLT_FILES = {"play2.c"}
OVLT_ADDR = 0xF000
OVL_ADDR = 0xDD00
OVL_END = 0xF200
OVL_ROM = 7 * 0x4000
OVB_SRC = "ovlb.c"         # オーバーレイ B：タイトル・トーナメント（本体とは別にリンク、OVL_ADDR で動く）
OVB_ROM = 8 * 0x4000
OVC_SRC = "ovlc.c"         # オーバーレイ C：EDIT モード
OVC_ROM = 9 * 0x4000
ROM_SIZE = 0x80000         # 4M ビット（512KB）のメガROM：16KB × 32 バンク（バンク 8〜31 はこれから使う空き）


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        print(" ".join(cmd))
        print(out)
        sys.exit(1)
    warn = [l for l in out.splitlines() if "warning" in l.lower() and "EVELYN" not in l]
    for w in warn[:20]:
        print(w)
    return out


def ihx_to_bin(path):
    mem = {}
    for line in open(path):
        line = line.strip()
        if not line.startswith(":"):
            continue
        n = int(line[1:3], 16)
        addr = int(line[3:7], 16)
        typ = int(line[7:9], 16)
        if typ != 0:
            continue
        for i in range(n):
            mem[addr + i] = int(line[9 + i * 2:11 + i * 2], 16)
    lo, hi = min(mem), max(mem)
    data = bytearray(hi - CODE_LOC + 1)
    for a, v in mem.items():
        data[a - CODE_LOC] = v
    return lo, hi, data


def main_end(img):
    """本体（コード・定数・初期値）の最後の番地。マップの各エリアの始まり＋長さから（OVL と変数は除く）"""
    mp = open(os.path.join(B, "game.map"), encoding="utf-8", errors="replace").read()
    s = {m.group(2): int(m.group(1), 16) for m in re.finditer(r"([0-9A-F]{8})\s+([sl]__\w+)", mp)}
    end = CODE_LOC
    for k, v in s.items():
        if not k.startswith("s__"):
            continue
        a = k[3:]
        if a in ("OVL", "OVLT", "DATA", "INITIALIZED", "BSS", "BSEG", "HEAP", "CABS", "DABS"):
            continue
        ln = s.get("l__" + a, 0)
        if ln and v + ln - 1 > end:
            end = v + ln - 1
    return end


def ovl_size():
    mp = open(os.path.join(B, "game.map"), encoding="utf-8", errors="replace").read()
    m = re.search(r"([0-9A-F]{8})\s+l__OVL\b", mp)
    return int(m.group(1), 16) if m else 0


def build_ovb(mainmap, srcname=OVB_SRC, seg="OVLB", title=True):
    """オーバーレイ B・C：コンパイル → 本体の記号を番地で与えてリンク → バイト列"""
    base = os.path.splitext(srcname)[0]
    src = os.path.join(ROOT, "src", srcname)
    rel = os.path.join(OBJ, base + ".rel")
    run([SDCC, "-mz80", "-c", "--opt-code-size", "--max-allocs-per-node", "6000", "--codeseg", seg, "--constseg", seg,
         "-I" + os.path.join(ROOT, "src"), "-I" + GEN, src, "-o", rel])
    txt = open(rel, encoding="latin-1").read()
    refs = set(re.findall(r"^S (\w+) Ref", txt, re.M))
    defs = set(re.findall(r"^S (\w+) Def", txt, re.M))
    mainsyms = {m.group(2): int(m.group(1), 16) for m in re.finditer(r"([0-9A-F]{8})\s+(_\w+)\s", mainmap)}
    lines = ["\t.module mainsyms"]
    for r in sorted(refs - defs):
        if r.startswith("s__") or r.startswith("l__"):
            continue
        assert r in mainsyms, "overlay B needs a symbol the main program does not have: " + r
        lines.append(f"{r} == 0x{mainsyms[r]:04X}")
    asm = os.path.join(OBJ, base + "_syms.s")
    open(asm, "w").write("\n".join(lines) + "\n")
    srel = os.path.join(OBJ, base + "_syms.rel")
    run([SDAS, "-plosgff", "-o", srel, asm])
    ihx = os.path.join(B, base + ".ihx")
    run([SDCC, "-mz80", "--no-std-crt0", "--code-loc", "0xF300", "--data-loc", "0xF380",
         "-Wl-b_" + seg + "=" + hex(OVL_ADDR), "-o", ihx, rel, srel])
    mp = open(os.path.join(B, base + ".map"), encoding="utf-8", errors="replace").read()

    def msym(name):
        m = re.search(r"([0-9A-F]{8})\s+" + re.escape(name) + r"\b", mp)
        return int(m.group(1), 16) if m else 0
    for a in ("l__CODE", "l__DATA", "l__INITIALIZED", "l__BSS"):
        assert msym(a) == 0, srcname + " must not have " + a + " (no RAM variables, no library code)"
    n = msym("l__" + seg)
    print(f"{srcname}: {n} / {OVL_END - OVL_ADDR} bytes")
    assert n <= OVL_END - OVL_ADDR, srcname + " too big"
    if title:
        e = msym("_ovlb_title_end")
        print(f"  title {OVL_ADDR:04X}-{e:04X}")
        assert e <= 0xE300, "title past E300h"
    mem = {}
    for line in open(ihx):
        line = line.strip()
        if line.startswith(":") and int(line[7:9], 16) == 0:
            k, ad = int(line[1:3], 16), int(line[3:7], 16)
            for i in range(k):
                mem[ad + i] = int(line[9 + i * 2:11 + i * 2], 16)
    return bytes(mem.get(OVL_ADDR + i, 0) for i in range(n))


def main():
    os.makedirs(OBJ, exist_ok=True)
    run([sys.executable, os.path.join(ROOT, "tools", "gen_assets.py")])
    objs = []
    run([SDAS, "-plosgff", "-o", os.path.join(OBJ, "crt0.rel"), os.path.join(ROOT, "src", "crt0.s")])
    objs.append(os.path.join(OBJ, "crt0.rel"))
    srcs = [os.path.join(ROOT, "src", f) for f in C_SRC if os.path.exists(os.path.join(ROOT, "src", f))]
    srcs.append(os.path.join(GEN, "assets.c"))
    for s in srcs:
        o = os.path.join(OBJ, os.path.splitext(os.path.basename(s))[0] + ".rel")
        seg = ["--codeseg", "OVL", "--constseg", "OVL"] if os.path.basename(s) in OVL_FILES else []
        if os.path.basename(s) in OVLT_FILES:
            seg = ["--codeseg", "OVLT", "--constseg", "OVLT"]
        cmd = [SDCC, "-mz80", "-c", "--opt-code-size", "--max-allocs-per-node", "200000"] + seg +             ["-I" + os.path.join(ROOT, "src"), "-I" + GEN, s, "-o", o]
        # 同じ中身（ソース・ヘッダ・オプション）ならコンパイルし直さない（最適化が重いので）
        import hashlib, glob as _g
        hsh = hashlib.sha1(" ".join(cmd).encode())
        for f in [s] + sorted(_g.glob(os.path.join(ROOT, "src", "*.h"))) + sorted(_g.glob(os.path.join(GEN, "*.h"))):
            hsh.update(open(f, "rb").read())
        hf = o + ".hash"
        if not (os.path.exists(o) and os.path.exists(hf) and open(hf).read() == hsh.hexdigest()):
            run(cmd)
            open(hf, "w").write(hsh.hexdigest())
        objs.append(o)
    ihx = os.path.join(B, "game.ihx")

    def link(data_loc):
        run([SDCC, "-mz80", "--no-std-crt0", "--code-loc", hex(CODE_LOC), "--data-loc", hex(data_loc),
             "-Wl-b_OVL=" + hex(OVL_ADDR), "-Wl-b_OVLT=" + hex(OVLT_ADDR), "-o", ihx] + objs)
        return ihx_to_bin(ihx)
    lo, hi, img = link(0xD000)
    hi = main_end(img)
    data_loc = (hi + 0x10) & ~0x0F
    lo, hi, img = link(data_loc)
    hi = main_end(img)
    ovl_used = ovl_size()
    mpt = open(os.path.join(B, "game.map"), encoding="utf-8", errors="replace").read()
    mt = re.search(r"([0-9A-F]{8})\s+l__OVLT\b", mpt)
    ovlt_used = int(mt.group(1), 16) if mt else 0
    print(f"overlay: {ovl_used} / {OVLT_ADDR - OVL_ADDR} bytes  + tail (F000h-) {ovlt_used} / {OVL_END - OVLT_ADDR} bytes")
    assert ovl_used <= OVLT_ADDR - OVL_ADDR, "overlay A runs into the tail area (F000h)"
    assert ovlt_used <= OVL_END - OVLT_ADDR, "tail area (play2.c) too big"
    img += bytes(max(0, OVL_END - CODE_LOC - len(img)))
    ovl = bytes(img[OVL_ADDR - CODE_LOC:OVL_END - CODE_LOC])
    mpx = open(os.path.join(B, "game.map"), encoding="utf-8", errors="replace").read()
    t1 = int(re.search(r"([0-9A-F]{8})\s+_ovl_persist_end\b", mpx).group(1), 16)
    print(f"overlay A resident part: {OVL_ADDR:04X}-{t1:04X}")
    assert t1 <= 0xE300, "in-game overlay functions must stay below the field map (E300h)"
    ovb = build_ovb(mpx)
    ovc = build_ovb(mpx, OVC_SRC, "OVLC", False)
    img[OVL_ADDR - CODE_LOC:] = bytes(len(img) - (OVL_ADDR - CODE_LOC))
    mp = open(os.path.join(B, "game.map"), encoding="utf-8", errors="replace").read()

    def sym(name):
        m = re.search(r"([0-9A-F]{8})\s+" + re.escape(name) + r"\s", mp)
        return int(m.group(1), 16) if m else None
    s_data = sym("s__DATA")
    l_data = sym("l__DATA")
    s_init = sym("s__INITIALIZED")
    l_init = sym("l__INITIALIZED")
    vend = max(s_data + (l_data or 0), (s_init or 0) + (l_init or 0))
    print(f"code+const: {lo:04X}-{hi:04X} ({hi - lo + 1} bytes)  vars: {data_loc:04X}-{vend:04X} ({vend - data_loc} bytes)"
          f"  free: {OVL_ADDR - vend} bytes")
    assert vend <= OVL_ADDR, "RAM overflow"
    assert img[0] == 0xC3, "entry is not JP"
    # 本体は 3 バンク（4000h-EFFFh）
    img = img[:0xB000]
    img += bytes(0xC000 - len(img))
    run([SJASM, "--nologo", "--raw=" + os.path.join(B, "boot.bin"), "--sym=" + os.path.join(B, "boot.sym"), os.path.join(ROOT, "boot", "boot.asm")])
    boot = open(os.path.join(B, "boot.bin"), "rb").read()
    assert len(boot) == 0x4000, len(boot)
    banks = open(os.path.join(GEN, "banks.bin"), "rb").read()
    rom = bytearray(boot) + img + banks
    rom += bytes([0xFF]) * (ROM_SIZE - len(rom))
    assert len(boot) + len(img) + len(banks) <= OVL_ROM, "assets overlap the overlay bank"
    rom[OVL_ROM:OVL_ROM + len(ovl)] = ovl
    rom[OVB_ROM:OVB_ROM + len(ovb)] = ovb
    rom[OVC_ROM:OVC_ROM + len(ovc)] = ovc
    assert len(rom) == ROM_SIZE, hex(len(rom))
    out = os.path.join(ROOT, ROM_NAME)
    open(out, "wb").write(rom)
    print("ROM:", out, len(rom), "bytes")


if __name__ == "__main__":
    main()
