# -*- coding: utf-8 -*-
"""マニュアル用の画面写真を openMSX で撮る（manual/img/*.png、256x212 の画面部分）"""
import os
import shutil
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "test"))
import emu
from PIL import Image

IMG = os.path.join(HERE, "img")
SHOTS = os.path.join(ROOT, "build", "shots")


def crop_all(tag, names):
    os.makedirs(IMG, exist_ok=True)
    for nm in names:
        src = os.path.join(SHOTS, f"{tag}_{nm}.png")
        if not os.path.exists(src):
            print("missing", nm)
            continue
        im = Image.open(src).convert("RGB")
        if im.size == (320, 240):
            im = im.crop((32, 14, 288, 226))
        im.save(os.path.join(IMG, nm + ".png"))


def menus():
    """タイトル → チーム選択 → オーダー → 打席（1P VS COM、3 回）→ 代打の画面。
    タイトルの行：モード 6 つ・イニング・SPEED（↑ で 1P VS COM の行からそのまま SPEED の行へ回る）"""
    st = [("wait", 7.0), ("shot", "title"),
          ("key", "down", 0.08), ("wait", 0.3), ("shot", "title_mode"),
          ("key", "up", 0.08), ("wait", 0.2), ("key", "up", 0.08), ("wait", 0.2),
          ("key", "right", 0.08), ("wait", 0.3), ("shot", "title_speed"),
          ("key", "left", 0.08), ("wait", 0.2),
          ("key", "down", 0.08), ("wait", 0.2),
          ("key", "left", 0.08), ("wait", 0.1), ("key", "left", 0.08), ("wait", 0.3), ("shot", "title_inning"),
          ("key", "space", 0.08), ("wait", 1.2), ("shot", "select1"),
          ("key", "down", 0.08), ("wait", 0.2), ("key", "down", 0.08), ("wait", 0.3), ("shot", "select2"),
          ("key", "space", 0.08), ("wait", 0.5),
          ("key", "down", 0.08), ("wait", 0.2), ("key", "down", 0.08), ("wait", 0.2), ("key", "down", 0.08), ("wait", 0.4),
          ("shot", "select3"),
          ("key", "space", 0.08), ("wait", 1.6), ("shot", "lineup"),
          ("key", "space", 0.08), ("wait", 0.9), ("shot", "playball"),
          ("wait", 1.3), ("key", "f1", 0.06), ("wait", 0.4), ("shot", "pinch"),
          ("key", "space", 0.08), ("wait", 0.8), ("shot", "after_pinch"),
          ("wait", 1.2), ("shot", "atbat1p")]
    emu.run(st, tag="man", timeout=900)
    crop_all("man", ["title", "title_mode", "title_inning", "select1", "select2", "select3", "lineup",
                     "playball", "atbat1p", "pinch", "after_pinch", "title_speed"])


# openMSX が SRAM を残す場所（ROM のファイル名ごと）。撮る前にどけて、初めて起動したときの中身から撮る
SRAM = os.path.join(os.path.expanduser("~"), "Documents", "openMSX", "persistent", "roms", "MSXSTADIUM.ROM",
                    "MSXSTADIUM.ROM.SRAM")


def sram_aside():
    if os.path.exists(SRAM):
        shutil.move(SRAM, os.path.join(ROOT, "build", "sram_prev.SRAM"))


def keys(*names, wait=0.25):
    out = []
    for nm in names:
        out += [("key", nm, 0.08), ("wait", wait)]
    return out


def edit():
    """EDIT：チームの一覧 → DOL の画面 → 打率を変える → 名前を書く（START で保存はしない）"""
    sram_aside()
    st = [("wait", 7.0)] + keys("down", "down", "down") + [("shot", "title_edit")]
    st += keys("space", wait=1.0) + [("shot", "edit_list")]
    st += keys("space", wait=1.0) + [("shot", "edit_team")]
    st += keys("right", "space") + keys("up", "up", "up", "up", "up", wait=0.15) + [("wait", 0.3), ("shot", "edit_num")]
    st += keys("space", "left") + keys("space", wait=1.0)
    st += keys("right", "right", "right", wait=0.15) + [("wait", 0.3), ("shot", "edit_name")]
    emu.run(st, tag="man", timeout=600, romtype="ASCII16SRAM2")
    crop_all("man", ["title_edit", "edit_list", "edit_team", "edit_num", "edit_name"])


def tour():
    """トーナメント：6 チームを選ぶ → 組み合わせ → COM 同士の試合の結果 → 1P の試合の前（ここで終わる＝保存される）。
    そのあと、新しく起動して CONTINUE（続きの試合の前）"""
    sram_aside()
    st = [("wait", 7.0)] + keys("down", "down", "down", "down") + [("shot", "title_tour")]
    st += keys("space", wait=1.0) + [("shot", "tour_pick")]
    st += keys("ret", wait=1.0) + keys("down", "down", "space", "down", "space", wait=0.3) + [("shot", "tour_arrange")]
    st += keys("ret", wait=1.5) + [("shot", "tour_sim")]
    st += keys("space", wait=1.5) + keys("space", wait=1.5) + [("shot", "tour_play")]
    emu.run(st, tag="man", timeout=600, romtype="ASCII16SRAM2")
    st = [("wait", 7.0)] + keys("down", "down", "down", "down", "down") + [("shot", "title_cont")]
    st += keys("space", wait=1.5) + [("shot", "tour_cont")]
    emu.run(st, tag="man", timeout=600, romtype="ASCII16SRAM2")
    crop_all("man", ["title_tour", "tour_pick", "tour_arrange", "tour_sim", "tour_play", "title_cont", "tour_cont"])
    sram_aside()


def rundown():
    """COM の挟殺（デモ試合で chase_k が 0 でなくなってから 0.5〜1.5 秒後）"""
    s = emu.symbols()
    base = os.path.join(SHOTS, "dem_rundown").replace("\\", "/")
    tcl = ('set ::rdn 0 ; proc rw {} { if {[peek %d] != 0 && $::rdn == 0} { set ::rdn 1 ; set ::throttle on ; '
           'after time 0.5 {screenshot -raw "%s1.png"} ; after time 1.0 {screenshot -raw "%s2.png"} ; '
           'after time 1.5 {screenshot -raw "%s3.png" ; set ::throttle off} } ; if {$::rdn == 0} {after frame rw} } ; rw'
           % (s["_chase_k"], base, base, base))
    emu.run([("wait", 6), ("tcl", "poke %d %d ; poke %d %d" % (s["_seed"], 101 & 255, s["_seed"] + 1, 101 >> 8)),
             ("wait", 2), ("tcl", tcl), ("wait", 900)], tag="dem", timeout=3000)
    crop_all("dem", ["rundown1", "rundown2", "rundown3"])


def bunt():
    """バントの構え（1P が打つ。B を押したまま投球を待つ）"""
    st = [("wait", 3.0)]
    for i in range(7):
        st += [("key", "space", 0.1), ("wait", 1.2)]
    st += [("wait", 3.0), ("tcl", "keymatrixdown 2 0x80"), ("wait", 1.5), ("shot", "bunt"), ("tcl", "keymatrixup 2 0x80")]
    emu.run(st, tag="man", timeout=600)
    crop_all("man", ["bunt"])


def tclshot(name, delay=0.0):
    p = os.path.join(SHOTS, f"dem_{name}.png").replace("\\", "/")
    return ('after time %.3f {set ::throttle on ; after time 0.03 {screenshot -raw "%s" ; set ::throttle off}}' % (delay, p))


def framesshot(name, n):
    base = os.path.join(SHOTS, f"dem_{name}").replace("\\", "/")
    return 'set ::throttle on ; after frame [list fshot "%s" 0 %d]' % (base, n)


def demo():
    """COM VS COM のデモ試合の中の場面"""
    s = emu.symbols()
    D = s["_dbg"]
    B = s["_ball"]
    G = s["_gstate"]
    tcl = []
    # 打った瞬間（連続 12 コマ）と、その後の守備
    tcl.append('set ::c 0 ; debug set_watchpoint write_mem %d {} {incr ::c ; if {$::c == 3} { %s ; %s ; %s }}'
               % (D + 4, framesshot("contact", 12), tclshot("field1", 0.9), tclshot("field2", 1.6)))
    # 送球（ボールが送球中）
    tcl.append('set ::t 0 ; proc wthrow {} { if {[peek %d] == 4 && [peek %d] == 2} { incr ::t ; if {$::t == 2} { %s ; return } ; after time 3 wthrow ; return } ; after frame wthrow } ; after time 30 wthrow'
               % (B + 12, G, tclshot("throw", 0.15)))
    # 本塁打
    tcl.append('set ::h 0 ; debug set_watchpoint write_mem %d {} {incr ::h ; if {$::h == 1} { %s ; %s }}'
               % (D + 8, tclshot("homerun", 0.6), tclshot("homerun2", 1.4)))
    # ストライク・ボール・ファウルの判定（2 回目の三振で「ストライク」→「アウト」）
    tcl.append('set ::k 0 ; debug set_watchpoint write_mem %d {[peek %d] == 3} {incr ::k ; if {$::k == 2} { %s ; %s }}'
               % (s["_strikes"], s["_strikes"], tclshot("so_strike", 0.4), tclshot("so_out", 1.3)))
    tcl.append('set ::f 0 ; debug set_watchpoint write_mem %d {} {incr ::f ; if {$::f == 4} { %s }}' % (D + 6, tclshot("foul", 0.3)))
    # 投球中のボール（投げてから 0.25 秒）
    tcl.append('set ::p 0 ; debug set_watchpoint write_mem %d {} {incr ::p ; if {$::p == 6} { %s ; %s }}' % (D + 0, tclshot("pitch1", 0.12), tclshot("pitch2", 0.28)))
    # セーフ（2 回目）：判定の文字と、両手を広げる塁審
    tcl.append('set ::sf 0 ; debug set_bp %d {[reg a] == 3} {incr ::sf ; if {$::sf == 2} { %s }}' % (s["_msg_show"], tclshot("safe", 0.3)))
    # スコアボード（3 回目）と試合の終わり（引数 A = 1）
    tcl.append('set ::n 0 ; debug set_bp %d {} {incr ::n ; if {[reg a] == 1} { %s } elseif {$::n == 3} { %s }}'
               % (0xDD03, tclshot("gameset", 1.5), tclshot("board", 1.5)))
    steps = [("wait", 8)] + [("tcl", t) for t in tcl] + [("wait", 2400)]
    emu.run(steps, tag="dem", timeout=4000)
    names = ["field1", "field2", "throw", "homerun", "homerun2", "so_strike", "so_out", "foul", "pitch1", "pitch2",
             "board", "gameset", "safe"] + ["contact_%d" % k for k in range(12)]
    crop_all("dem", names)


if __name__ == "__main__":
    what = sys.argv[1:] or ["menus", "demo"]
    if "menus" in what:
        menus()
    if "demo" in what:
        demo()
    if "bunt" in what:
        bunt()
    if "edit" in what:
        edit()
    if "tour" in what:
        tour()
    if "rundown" in what:
        rundown()
    print("ok")
