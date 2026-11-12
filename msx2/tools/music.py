# -*- coding: utf-8 -*-
"""曲（すべて自作）と効果音 → C の配列
MML: c d e f g a b（+ - で半音）, r 休符, o 音階, < > 上下, l 長さ, 数字 = 長さ（4 = 4 分）, . 付点
V 音量, D 減衰の間隔, F 下限, [ ループの始め"""

NOTE = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}


def mml(src, whole):
    """whole = 全音符のフレーム数"""
    out = []
    o, L = 4, 8
    i = 0
    s = src.replace('|', ' ')
    carry = 0.0

    def num():
        nonlocal i
        j = i
        while i < len(s) and s[i].isdigit():
            i += 1
        return int(s[j:i]) if i > j else None

    def length():
        nonlocal i, carry
        n = num()
        ln = whole / (n if n else L)
        d = ln
        while i < len(s) and s[i] == '.':
            d /= 2
            ln += d
            i += 1
        ln += carry
        f = int(round(ln))
        carry = ln - f
        return max(1, f)
    while i < len(s):
        c = s[i]
        i += 1
        if c in ' \n\t':
            continue
        if c == 'o':
            o = num()
        elif c == '<':
            o -= 1
        elif c == '>':
            o += 1
        elif c == 'l':
            L = num()
        elif c == 'V':
            out += [0xF0, num()]
        elif c == 'D':
            out += [0xF1, num()]
        elif c == 'F':
            out += [0xF2, num()]
        elif c == '[':
            out += [0xFD]
        elif c == 'r':
            f = length()
            while f > 250:
                out += [0x60, 250]
                f -= 250
            out += [0x60, f]
        elif c in NOTE:
            n = NOTE[c]
            while i < len(s) and s[i] in '+-':
                n += 1 if s[i] == '+' else -1
                i += 1
            f = length()
            idx = o * 12 + n
            assert 0 <= idx < 96, (src, idx)
            out += [idx, min(f, 250)]
        else:
            raise ValueError("bad mml char %r in %r" % (c, src[:40]))
    return out


# 1 小節 = 4 拍。whole = 全音符のフレーム数
TRACKS = {
    "TITLE": dict(whole=96, loop=True, ch=[
        "V13 D6 F9 [ o5 l8 c4 c e g4 g >c< | b4 a g a2 | f4 f a >c4 c< a | g2 r2 |"
        " e4 e g >c4 c e | d4 c< b >c2< | a4 >c< a g4 e d | c2 r2",
        "V11 D4 F6 [ o3 l8 c g e g c g e g | g >d< b >d< g >d< b >d< | f >c< a >c< f >c< a >c< | g >d< b >d< g4 r4 |"
        " c g e g c g e g | g >d< b >d< c g e g | f >c< a >c< g >d< b >d< | c g e g c4 r4",
        "V9 D8 F5 [ o4 l4 e e d d | d d e e | a a a a | b b g r | e e e e | f f e e | f f f f | e e e r",
    ]),
    "ATBAT": dict(whole=88, loop=True, ch=[
        "V13 D5 F8 [ o5 l8 g4 e g a4 g e | f4 d f g4 f d | e g >c< b a g f e | d2 r4 g4 |"
        " g4 e g a4 g e | f4 d f a4 >c< b | >c< g e c d e f d | c2. r4",
        "V12 D3 F6 [ o3 l8 c c g g c c g g | d d a a d d a a | c c e e f f g g | g g b b g g b b |"
        " c c g g c c g g | d d a a f f a a | e e g g f f g g | c c g g c4 r4",
        "V9 D3 F4 [ o4 l8 r e r e r e r e | r f r f r f r f | r g r g r a r a | r b r b r b r b |"
        " r e r e r e r e | r f r f r a r a | r g r g r a r b | r e r g >c4< r4",
    ]),
    "ATBAT2": dict(whole=88, loop=True, ch=[
        "V13 D5 F8 [ o5 l8 c4 < a4 f4 a4 | b-4 g4 e4 g4 | a f c f a >c< a f | g2 r4 >c4 |"
        " c4 < a4 f4 a4 | b-4 >d4 c4< b-4 | a g f e g f e d | c2 f4 r4",
        "V12 D3 F6 [ o3 l8 f f >c c< f f >c c< | c c g g c c g g | f f a a f f a a | c c e e g g e e |"
        " f f >c c< f f >c c< | b- b- >d d< b- b- >d d< | c c e e c c e e | f f c c f4 r4",
        "V9 D3 F4 [ o4 l8 r a r a r a r a | r g r g r g r g | r a r a r a r a | r e r e r g r g |"
        " r a r a r a r a | r f r f r f r f | r g r g r e r e | r a r a f4 r4",
    ]),
    "HOMERUN": dict(whole=80, loop=False, ch=[
        "V14 D8 F10 o5 l16 g g g8 >c4. r8 < a8 >c8 e8 g4. f8 e8 d8 c2",
        "V12 D8 F8 o5 l16 e e e8 g4. r8 f8 a8 >c8 e4. d8 c8 < b8 >c2",
        "V11 D4 F6 o3 l8 c c c c f f f f g g g g c2",
    ]),
    "CHANGE": dict(whole=72, loop=False, ch=[
        "V13 D5 F8 o5 l8 c e g >c< g e c4 r4",
        "V11 D5 F6 o4 l8 e g >c e c< g e4 r4",
        "V10 D4 F5 o3 l4 c g c r",
    ]),
    "GAMESET": dict(whole=120, loop=False, ch=[
        "V13 D10 F9 o5 l4 c e g >c2< b a g2 f e d c1",
        "V11 D10 F7 o4 l4 e g >c e2 d c< b2 a g f e1",
        "V10 D8 F6 o3 l2 c e f g f g c1",
    ]),
    "PLAYBALL": dict(whole=72, loop=False, ch=[
        "V13 D6 F9 o5 l16 g >c e g4 r8 e8 g2",
        "V11 D6 F7 o4 l16 e g >c e4 r8 c8 e2",
        "V10 D6 F5 o3 l8 c g c4 r8 g8 c2",
    ]),
}
ORDER = ["TITLE", "ATBAT", "HOMERUN", "CHANGE", "GAMESET", "PLAYBALL", "ATBAT2"]


def tone(freq):
    return int(round(111860.8 / freq))


# 効果音：1 フレーム = (mode, 音程, ノイズ周期, 音量)。mode bit0 = 音, bit1 = ノイズ
# ROM に入れるときは「同じ増え方が続く区間」にまとめる（区間 = フレーム数・mode・音程・音程の増分・ノイズ・増分・音量・増分）
def sweep(f0, f1, n, v0, v1, mode=1, noise=0):
    """音程（周期）と音量を直線で変える"""
    p0, p1 = tone(f0), tone(f1)
    out = []
    for k in range(n):
        t = k / max(1, n - 1)
        out.append((mode, int(round(p0 + (p1 - p0) * t)), noise, int(round(v0 + (v1 - v0) * t))))
    return out


def lin(n, mode, p0, dp, nz0, dnz, v0, dv):
    """区間をそのまま書く（増分は 1 フレームごと）"""
    return [(mode, p0 + dp * k, nz0 + dnz * k, v0 + dv * k) for k in range(n)]


def segments(frames):
    """フレームの並び → 区間 [(n, mode, p, dp, nz, dnz, v, dv)]（増分が同じあいだを 1 つにまとめる）"""
    segs = []
    i = 0
    while i < len(frames):
        m, p, nz, v = frames[i]
        j = i + 1
        d = None
        while j < len(frames) and j - i < 255:
            m2, p2, nz2, v2 = frames[j]
            dd = (p2 - frames[j - 1][1], nz2 - frames[j - 1][2], v2 - frames[j - 1][3])
            if m2 != m or (d is not None and dd != d) or not all(-128 <= x < 128 for x in dd):
                break
            d = dd
            j += 1
        d = d or (0, 0, 0)
        segs.append((j - i, m, p, d[0], nz, d[1], v, d[2]))
        i = j
    return segs


SFX = {
    "HIT": [(3, tone(900), 2, 15), (3, tone(700), 3, 14), (2, 0, 5, 13), (2, 0, 7, 11), (2, 0, 9, 9),
            (2, 0, 11, 7), (2, 0, 13, 5), (2, 0, 15, 3)],
    "CATCH": [(2, 0, 20, 13), (2, 0, 24, 10), (2, 0, 28, 6), (2, 0, 31, 3)],
    "THROW": sweep(500, 300, 6, 10, 4),
    "STRIKE": [(1, tone(880), 0, 12)] * 4 + [(1, tone(660), 0, 11)] * 6,
    "OUT": [(1, tone(523), 0, 13)] * 5 + [(1, tone(392), 0, 12)] * 8,
    "CURSOR": [(1, tone(1320), 0, 11)] * 3,
    "PITCH": [(2, 0, 4, 8), (2, 0, 6, 7), (2, 0, 8, 5), (2, 0, 10, 3)],
    "FOUL": sweep(700, 300, 10, 12, 6),
    "BOUND": sweep(150, 90, 6, 13, 4),          # 弾んだ瞬間：低い音が 0.1 秒（150→90Hz、だんだん小さく）
    "BOUND2": sweep(140, 100, 4, 9, 3),        # 3 回目からの小さな弾み：小さく短く
    "SAFE": [(1, tone(784), 0, 12)] * 4 + [(1, tone(1046), 0, 12)] * 6,
    # 速球（140km 以上）：「ひゅん！」高い音が息のように鳴って、すっと下がって消える（0.5 秒）
    "FAST": lin(8, 3, 34, 3, 1, 0, 14, 0) + lin(12, 1, 60, 3, 0, 0, 13, -1) + lin(10, 1, 96, 4, 0, 0, 1, 0),
}
SFX_ORDER = ["HIT", "CATCH", "THROW", "STRIKE", "OUT", "CURSOR", "PITCH", "FOUL", "BOUND", "SAFE", "FAST", "BOUND2"]


def build():
    C = []
    H = []
    # 音程：いちばん低いオクターブの 12 音だけ持ち、オクターブごとに半分にする（sound.c）
    base = [tone(440.0 * 2 ** ((n - 57) / 12)) for n in range(12)]
    C.append("const u16 note_base[12] = {" + ",".join(str(p) for p in base) + "};\n")
    H.append("extern const u16 note_base[12];")
    songs = []
    ofs = []
    for name in ORDER:
        t = TRACKS[name]
        blob = []
        for ci, ch in enumerate(t["ch"]):
            data = mml(ch, t["whole"])
            data += [0xFE] if t["loop"] else [0xFF]
            ofs.append(len(blob))
            blob += data
        songs.append((name, bytes(blob), t["loop"]))
    loop_max = max(len(b) for _, b, lp in songs if lp)
    jin_max = max(len(b) for _, b, lp in songs if not lp)
    C.append("const u8 bgm_ofs[] = {" + ",".join(str(o) for o in ofs) + "};\n")
    C.append("const u8 bgm_loop[] = {" + ",".join("1" if TRACKS[n]["loop"] else "0" for n in ORDER) + "};\n")
    H.append("extern const u8 bgm_ofs[];\nextern const u8 bgm_loop[];")
    H.append(f"#define BGM_LOOP_MAX {loop_max}\n#define BGM_JIN_MAX {jin_max}")
    H.append("#define BGM_TABLE " + ",".join("{A_BGM_%s}" % n for n in ORDER))
    sn = []
    for name in SFX_ORDER:
        b = []
        for n, mode, p, dp, nz, dnz, v, dv in segments(SFX[name]):
            assert 0 <= v <= 15 and 0 <= v + dv * (n - 1) <= 15, name
            b += [n, mode, p & 255, p >> 8, dp & 255, nz, dnz & 255, v, dv & 255]
        b += [0]
        nm = f"sfx_{name}"
        C.append(f"static const u8 {nm}[] = {{" + ",".join(str(x) for x in b) + "};\n")
        sn.append(nm)
    C.append("const u8* const sfx_tab[] = {" + ",".join(sn) + "};\n")
    H.append("extern const u8* const sfx_tab[];")
    return "".join(C), H, songs


if __name__ == "__main__":
    c, h = build()
    print(len(c), "chars")
    for name in ORDER:
        t = TRACKS[name]
        for ch in t["ch"]:
            d = mml(ch, t["whole"])
            tot = 0
            k = 0
            while k < len(d):
                if d[k] < 0x61:
                    tot += d[k + 1]
                    k += 2
                elif d[k] in (0xF0, 0xF1, 0xF2):
                    k += 2
                else:
                    k += 1
            print(name, tot)
