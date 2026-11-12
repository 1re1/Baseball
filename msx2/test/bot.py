# -*- coding: utf-8 -*-
"""人の操作をまねる自動プレーヤー（1P VS COM の 1P 側）
打撃：投球の来る位置を読んで打席内を動き、決まったタイミングで振る（ぶれ付き）
投球：A で投げるだけ。守備：自動で追い、捕ったら一塁へ投げる"""
import os, re, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu


def bot_tcl(aim=0, lead=6, jitter=1, zone=14, steer=0, move=1):
    s = emu.symbols()
    B = s["_ball"]
    return f'''
set ::swung 0
set ::thrown 0
set ::lead {lead}
proc s16 {{a}} {{ set v [peek16 $a] ; if {{$v >= 32768}} {{ incr v -65536 }} ; return $v }}
proc key {{r b on}} {{ if {{$on}} {{ keymatrixdown $r $b }} else {{ keymatrixup $r $b }} }}
proc tap {{r b}} {{ keymatrixdown $r $b ; after time 0.05 [list keymatrixup $r $b] }}
proc bot {{}} {{
  set gs [peek {s["_gstate"]}]
  set half [peek {s["_half"]}]
  set mode [peek {B + 12}]
  set wl 0 ; set wr 0
  if {{$half == 0}} {{
    if {{$gs == 1 && $mode == 2}} {{
      set x [s16 {B}] ; set y [s16 {B + 2}] ; set vx [s16 {B + 6}] ; set vy [s16 {B + 8}]
      if {{$vy > 0}} {{
        set px [expr {{($x + $vx * (6016 - $y) / $vy) / 16}}]
        set bx [s16 {s["_bat_x"]}]
        if {{[peek {s["_batter_left"]}]}} {{ set tg [expr {{$px + 15 + {aim}}}] }} else {{ set tg [expr {{$px - 15 - {aim}}}] }}
        if {{{move} && $bx < $tg - 1}} {{ set wr 1 }}
        if {{{move} && $bx > $tg + 1}} {{ set wl 1 }}
        set yc [expr {{([s16 {s["_bat_y"]}] - 4) * 16}}]
        set fr [expr {{($yc - $y) / $vy}}]
        if {{!$::swung && abs($px - 256) <= {zone} && $fr <= $::lead}} {{ tap 8 1 ; set ::swung 1 }}
      }}
    }}
    if {{$gs != 1}} {{ set ::swung 0 ; set ::lead [expr {{{lead} + int(rand() * {2 * jitter + 1}) - {jitter}}}] }}
  }} else {{
    if {{$gs == 0 && [peek16 {s["_gtimer"]}] > 40 && [peek16 {s["_gtimer"]}] < 43}} {{ tap 8 1 }}
    if {{$gs == 1 && {steer} && $mode == 2}} {{ set wl [expr {{int(rand()*2)}}] }}
    if {{$gs == 2 && $mode == 1 && !$::thrown}} {{ keymatrixdown 8 0x80 ; tap 8 1 ; after time 0.1 {{keymatrixup 8 0x80}} ; set ::thrown 1 }}
    if {{$mode != 1}} {{ set ::thrown 0 }}
  }}
  if {{$gs == 4 || $gs == 5}} {{ if {{[expr {{int(rand()*90)}}] == 0}} {{ tap 8 1 }} }}
  key 8 0x10 $wl
  key 8 0x80 $wr
  after frame bot
}}
'''


def play(secs=1500, innings=3, tag="bot", **kw):
    s = emu.symbols()
    tcl = bot_tcl(**kw)
    one = tcl.replace(chr(10), " ; ").replace("{ ;", "{").replace("; }", "}")
    left = {9: 0, 6: 1, 3: 2}[innings]
    steps = [("wait", 6.5)]
    for _ in range(left):
        steps += [("key", "left", 0.1), ("wait", 0.2)]
    steps += [("key", "space", 0.1), ("wait", 0.8), ("key", "space", 0.1), ("wait", 0.5),
              ("key", "down", 0.1), ("wait", 0.2), ("key", "space", 0.1), ("wait", 1.5),
              ("key", "space", 0.1), ("wait", 1.0),
              ("tcl", one), ("tcl", "bot")]
    for i in range(int(secs // 30)):
        steps += [("wait", 30), ("peek", f"sd{i:03d}", "_side", 60), ("peek", f"db{i:03d}", "_dbg", 32)]
    out, txt = emu.run(steps, tag=tag, timeout=3000)
    sides = re.findall(rb"sd\d+ (\w+)", txt)
    dbgs = re.findall(rb"db\d+ (\w+)", txt)
    games = []
    prev = None
    for sd, db in zip(sides, dbgs):
        b = bytes.fromhex(sd.decode())
        d = struct.unpack("<16H", bytes.fromhex(db.decode()))
        r0, r1 = b[27], b[30 + 27]
        if prev and d[13] > prev[0]:
            games.append(prev[1])
        prev = (d[13], (r0, r1))
    last = struct.unpack("<16H", bytes.fromhex(dbgs[-1].decode())) if dbgs else None
    return games, last, out


if __name__ == "__main__":
    games, d, out = play()
    print("finished games (1P runs, COM runs):", games)
    print(dict(zip(["pitch", "swing", "contact", "foul", "HR", "hit", "SO", "BB", "flyout", "out", "run", "2B", "3B",
                    "games", "timeout", "steal"], d)))
