import sys, re, struct
sys.path.insert(0, 'test')
import emu, bot
games, d, out = bot.play(secs=2400, innings=9, tag="botfinal2", move=0, lead=6, jitter=1)
print("bot 1P games (1P,COM):", games, "timeouts", d[14], flush=True)
extra = 'set too_fast_vram_access real ; proc vramcb {args} {global f ; puts $f "TOO_FAST_VRAM [format %04X [reg pc]]" ; flush $f} ; set VDP.too_fast_vram_access_callback vramcb'
for m in ["Panasonic_FS-A1", "Sony_HB-F1XD", "Philips_NMS_8245", "Sony_HB-F1XV", "Panasonic_FS-A1GT"]:
    out, txt = emu.run([("wait", 14), ("peek", "a", "_dbg", 32), ("wait", 150), ("peek", "b", "_dbg", 32), ("shot", "end")], tag="mf2_" + m, machine=m, extra=extra, timeout=900)
    v = [struct.unpack("<16H", bytes.fromhex(x.decode()))[0] for x in re.findall(rb"\b[ab] (\w+)", txt)]
    print(m, "pitches", v, "fast-vram", txt.count(b"TOO_FAST"), flush=True)
for rt in ["ASCII8", "ASCII16"]:
    out, txt = emu.run([("wait", 60), ("peek", "a", "_dbg", 32)], tag="rtf2_" + rt, romtype=rt)
    v = [struct.unpack("<16H", bytes.fromhex(x.decode()))[0] for x in re.findall(rb"\ba (\w+)", txt)]
    print(rt, "pitches after 60s", v, flush=True)
