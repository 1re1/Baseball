# -*- coding: utf-8 -*-
"""スプライト（自作のドット絵）。
記号: P=チーム主色 U=ユニフォーム s=肌 k=黒 w=白 d=バット .=透明
1 ラインに使える色は 2 色（2 枚重ね）。同じ「家族」のコマは行ごとの色の組（ZONE）を共有する。
ZONE の 1 つめが主な色：混んだラインで 1 枚に減らすときはこの色だけ残る。

体つき：頭は帽子 2 行＋顔 3 行（5 行）、全体で 15 行・横 8 ドット（約 3 頭身）。
腕と手はどのコマにも描く。"""

SYM2COLOR_FIXED = {'s': 6, 'k': 1, 'w': 7, 'd': 15}

# ---------------- ちびキャラ 16x16（守備・走者） ----------------
ZONE_CHIBI = [
    ('P', 's'),   # 0 帽子・上げた手
    ('P', 's'),   # 1 帽子
    ('P', 's'),   # 2 帽子のつば
    ('s', 'k'),   # 3 顔・髪
    ('s', 'k'),   # 4 目
    ('s', 'k'),   # 5 あご
    ('U', 's'),   # 6 肩
    ('U', 's'),   # 7 胴・袖
    ('U', 's'),   # 8 胴・腕
    ('U', 's'),   # 9 手
    ('P', 's'),   # 10 ベルト
    ('U', 'k'),   # 11 足
    ('U', 'k'),   # 12 足
    ('U', 'k'),   # 13 足（上げた靴）
    ('P', 'k'),   # 14 ソックス
    ('k', 'P'),   # 15 靴
]

# 正面（下向き）の頭・背中（上向き）の頭・横（左向き）の頭
HEAD_D = [
    "................",
    "......PPPP......",
    ".....PPPPPP.....",
    ".....kssssk.....",
    ".....skssks.....",
    "......ssss......",
]
HEAD_U = [
    "................",
    "......PPPP......",
    ".....PPPPPP.....",
    ".....kkkkkk.....",
    ".....kkkkkk.....",
    "......kssk......",
]
HEAD_L = [
    "................",
    "......PPPP......",
    "....PPPPPP......",
    "......sskk......",
    ".....skskk......",
    "......sss.......",
]
LEGS_STAND = [
    ".....PPPPPP.....",
    ".....UU..UU.....",
    ".....UU..UU.....",
    ".....UU..UU.....",
    ".....PP..PP.....",
    "....kkk..kkk....",
]

CHIBI = {}
CHIBI['STAND_D'] = HEAD_D + [
    ".....UUUUUU.....",
    "....UUUUUUUU....",
    "....sUUUUUUs....",
    "....sUUUUUUs....",
] + LEGS_STAND
# 走る（正面）：右手が前なら左足が前。上げた足は靴が高い
CHIBI['RUN_D1'] = HEAD_D + [
    ".....UUUUUU.....",
    "....sUUUUUUU....",
    ".....UUUUUUs....",
    ".....UUUUUUs....",
    ".....PPPPPP.....",
    ".....UU..UU.....",
    ".....UU..UU.....",
    ".....UU..kkk....",
    ".....PP.........",
    "....kkk.........",
]
CHIBI['RUN_D2'] = HEAD_D + [
    ".....UUUUUU.....",
    "....UUUUUUUs....",
    "....sUUUUUU.....",
    "....sUUUUUU.....",
    ".....PPPPPP.....",
    ".....UU..UU.....",
    ".....UU..UU.....",
    "....kkk..UU.....",
    ".........PP.....",
    ".........kkk....",
]
CHIBI['STAND_U'] = HEAD_U + [
    ".....UUUUUU.....",
    "....UUUUUUUU....",
    "....sUUUUUUs....",
    "....sUUUUUUs....",
] + LEGS_STAND
CHIBI['RUN_U1'] = HEAD_U + CHIBI['RUN_D1'][6:]
CHIBI['RUN_U2'] = HEAD_U + CHIBI['RUN_D2'][6:]
# 横（左向き）
CHIBI['STAND_L'] = HEAD_L + [
    "......UUU.......",
    ".....UUUUU......",
    ".....UsUUU......",
    ".....UsUUU......",
    ".....PPPPP......",
    "......UUU.......",
    "......UUU.......",
    "......UU........",
    "......PP........",
    ".....kkk........",
]
# 走る（横）：1 = 足を前後に大きく開く、2 = 足をそろえて膝を上げる
CHIBI['RUN_L1'] = HEAD_L + [
    "......UUU.......",
    "....sUUUUU......",
    ".....UUUUUs.....",
    "......UUU.s.....",
    "......PPPP......",
    ".....UU.UU......",
    "....UU...UU.....",
    "...UU.....UUk...",
    "...PP...........",
    "..kkk...........",
]
CHIBI['RUN_L2'] = HEAD_L + [
    "......UUU.......",
    ".....UUUUU......",
    ".....UUsUU......",
    "......UsU.......",
    ".....PPPP.......",
    "....UUUUU.......",
    "....UU.UU.......",
    "...kk..UU.......",
    ".......PP.......",
    "......kkk.......",
]
# 投げる（左へ）：投げる腕を前へ伸ばし、足を踏み出す
CHIBI['THROW_L'] = HEAD_L + [
    "..ssUUUU........",
    "......UUUUs.....",
    "......UUUU......",
    "......UUUU......",
    "......PPPP......",
    ".....UU..UU.....",
    "....UU....UU....",
    "...UU......UU...",
    "...PP......PP...",
    "..kkk.......kk..",
]
# 捕る：両手を頭の上に上げる
CHIBI['CATCH'] = [
    "....ss....ss....",
    ".....sPPPPs.....",
    ".....PPPPPP.....",
    "....kkssssk.....",
    "....sskssks.....",
    "....s.ssss.s....",
    "....sUUUUUUs....",
    ".....UUUUUU.....",
    ".....UUUUUU.....",
    ".....UUUUUU.....",
] + LEGS_STAND
# 構える（内野・正面）：足を開いて膝に手
CHIBI['READY_D'] = HEAD_D + [
    ".....UUUUUU.....",
    "....UUUUUUUU....",
    "....UUUUUUUU....",
    "....sUUUUUUs....",
    "....sPPPPPPs....",
    "....UUU..UUU....",
    "...UU......UU...",
    "...UU......UU...",
    "...PP......PP...",
    "..kkk......kkk..",
]
# 捕手（後ろから・しゃがむ）
CHIBI['CROUCH_B'] = [
    "................",
    "......PPPP......",
    ".....PPPPPP.....",
    ".....kkkkkk.....",
    ".....kkkkkk.....",
    "......ssss......",
    "....UUUUUUUU....",
    "...sUUUUUUUUs...",
    "...sUUUUUUUUs...",
    "....UUUUUUUU....",
    "....PPPPPPPP....",
    "...UUUU..UUUU...",
    "..UUU......UUU..",
    "..UUU......UUU..",
    "...PP......PP...",
    "..kkk......kkk..",
]
# すべり込む（左へ・足から）
CHIBI['SLIDE_L'] = [
    "................",
    "................",
    "................",
    "..........kkk...",
    ".........skkk...",
    ".........sss....",
    "........UUUU....",
    ".......sUUUUs...",
    "......UUUUU.....",
    "......UUUU......",
    ".....PPPP.......",
    "..UUUUUU........",
    ".kUUUU..........",
    "kk..............",
    "................",
    "................",
]


import chars_art as _CA      # 描き直したドット絵
CHIBI.update(_CA.CHIBI)


def mirror(rows):
    return [r[::-1] for r in rows]


for name in ['STAND_L', 'RUN_L1', 'RUN_L2', 'THROW_L', 'SLIDE_L', 'LEAD_L1', 'LEAD_L2']:
    CHIBI[name.replace('_L', '_R')] = mirror(CHIBI[name])

CHIBI_ORDER = ['STAND_D', 'RUN_D1', 'RUN_D2', 'STAND_U', 'RUN_U1', 'RUN_U2',
               'STAND_L', 'RUN_L1', 'RUN_L2', 'STAND_R', 'RUN_R1', 'RUN_R2',
               'THROW_L', 'THROW_R', 'CATCH', 'READY_D', 'CROUCH_B', 'SLIDE_L', 'SLIDE_R',
               'LEAD_L1', 'LEAD_L2', 'LEAD_R1', 'LEAD_R2']

# ---------------- 打者 16x24（右打ち・右向き。最下行 = bat_y） ----------------
# 足（靴）は 3..12 列に収める：バッターボックスの中（16 ドット）からはみ出さない
ZONE_BATTER = [('.', '.')] * 6 + [
    ('P', 's'),   # 6 ヘルメット・上げた手
    ('P', 's'),   # 7
    ('P', 's'),   # 8 つば
    ('s', 'k'),   # 9 顔
    ('s', 'k'),   # 10 目
    ('s', 'k'),   # 11 あご
    ('U', 's'),   # 12 肩・手
    ('U', 's'),   # 13
    ('U', 's'),   # 14 振り出した手
    ('U', 's'),   # 15
    ('P', 's'),   # 16 ベルト
    ('U', 'k'),   # 17
    ('U', 'k'),   # 18
    ('U', 'k'),   # 19
    ('U', 'k'),   # 20
    ('P', 'k'),   # 21 ソックス
    ('k', 'P'),   # 22 靴
    ('k', 'P'),   # 23 靴
]
B_HEAD = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "......PPPP......",
    ".....PPPPPP.....",
    ".....PPPPPPPP...",
    ".....kkssss.....",
    ".....ksssks.....",
    "......kssss.....",
]
BATTER = {}
# 7 コマ：構え → 踏み込み → 引き → 振り出し → 当たる瞬間 → 振り抜き → 振り終わり
# 足（靴）は 3..12 列（バッターボックスの中）。手の位置は BAT_LINE の手元と同じ
_H = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
]
_FACE = [
    ".....kkssss.....",
    ".....ksssks.....",
    "......kssss.....",
]
_LEGS_STANCE = [
    ".....PPPPP......",
    ".....UUUUUU.....",
    "....UU...UU.....",
    "....UU....UU....",
    "....UU....UU....",
    "....PP....PP....",
    "...kkk....kkk...",
    "................",
]
_LEGS_OPEN = [
    ".....PPPPP......",
    "......UUUUU.....",
    ".....UU..UU.....",
    "....UU....UU....",
    "....kk....UU....",
    "..........PP....",
    "..........kkk...",
    "................",
]
BATTER['STANCE'] = _H + [
    "......PPPP......",
    "....ssPPPPP.....",
    "....ssPPPPPPP...",
] + _FACE + [
    ".....UUUUU......",
    "....UUUUUU......",
    ".....UUUUU......",
    ".....UUUUU......",
] + _LEGS_STANCE
BATTER['STRIDE'] = _H + [
    "......PPPP......",
    "...ssPPPPPP.....",
    "...ss.PPPPPPP...",
] + _FACE + [
    ".....UUUUU......",
    "....UUUUUU......",
    ".....UUUUU......",
    ".....UUUUU......",
    ".....PPPPP......",
    ".....UUUUUUU....",
    "....UU...UUU....",
    "....UU.....kk...",
    "....UU..........",
    "....PP..........",
    "...kkk..........",
    "................",
]
BATTER['LOAD'] = _H + [
    "......PPPP......",
    ".....PPPPPP.....",
    ".....PPPPPPPP...",
    "...sskkssss.....",
    "...ssksssks.....",
    "......kssss.....",
    "....UUUUUU......",
    "....UUUUUU......",
    ".....UUUUU......",
    ".....UUUUU......",
    ".....PPPPP......",
    ".....UUUUUU.....",
    "....UU....UU....",
    "...UU......UU...",
    "...UU.....UU....",
    "...PP.....PP....",
    "...kk.....kkk...",
    "................",
]
BATTER['SWING1'] = _H + [
    "......PPPP......",
    ".....PPPPPP.....",
    ".....PPPPPPPP...",
] + _FACE + [
    ".....UUUUU......",
    "....UUUUUUss....",
    ".....UUUUUU.....",
    ".....UUUUU......",
] + _LEGS_STANCE
BATTER['CONTACT'] = _H + [
    "......PPPP......",
    ".....PPPPPP.....",
    ".....PPPPPPPP...",
] + _FACE + [
    ".....UUUUU......",
    "....UUUUUUUU....",
    ".....UUUUUUUss..",
    ".....UUUUU......",
] + _LEGS_OPEN
BATTER['FOLLOW1'] = _H + [
    "......PPPP......",
    ".....PPPPPP.....",
    ".....PPPPPPPP...",
    ".....kkssss.....",
    ".....ksssks.....",
    "......kssssss...",
    ".....UUUUUUU....",
    "....UUUUUUU.....",
    ".....UUUUU......",
    ".....UUUUU......",
] + _LEGS_OPEN
BATTER['FOLLOW2'] = _H + [
    "......PPPP.ss...",
    ".....PPPPPPss...",
    ".....PPPPPPPP...",
] + _FACE + [
    ".....UUUUUU.....",
    "....UUUUUUU.....",
    ".....UUUUU......",
    ".....UUUUU......",
] + _LEGS_OPEN
# バントの構え：投手へ体を向け（顔は投手のほう）、腰を落としてひざを曲げ、足は肩幅より広く。
# 両腕を前へのばし、胸の高さでバットを水平に持つ（下の手 = グリップ、上の手 = バットの中ほど）
BATTER['BUNT'] = _H + [
    "......PPPP......",
    ".....PPPPPP.....",
    ".....PPPPPPPP...",
] + _FACE + [
    ".....UUUUUUss.ss",
    ".....UUUUUUU....",
    "......UUUUU.....",
    "......UUUUU.....",
    "......PPPPP.....",
    ".....UUUUUUU....",
    "....UU.....UU...",
    "...UU.......UU..",
    "....UU.....UU...",
    "....PP.....PP...",
    "...kkk.....kkk..",
    "................",
]
BATTER.update(_CA.BATTER)
BATTER_ORDER = ['STANCE', 'STRIDE', 'LOAD', 'SWING1', 'CONTACT', 'FOLLOW1', 'FOLLOW2', 'BUNT']

# ---------------- 投手 16x24（正面・最下行 = 足もと） ----------------
ZONE_PITCHER = [('.', '.')] * 6 + [
    ('P', 's'),   # 6 帽子・上げた手
    ('P', 's'),   # 7
    ('P', 's'),   # 8
    ('s', 'k'),   # 9 顔
    ('s', 'k'),   # 10
    ('s', 'k'),   # 11
    ('U', 's'),   # 12
    ('U', 's'),   # 13
    ('U', 's'),   # 14
    ('U', 's'),   # 15
    ('P', 's'),   # 16 ベルト
    ('U', 'k'),   # 17
    ('U', 'k'),   # 18
    ('U', 'k'),   # 19 上げた足の靴
    ('U', 'k'),   # 20
    ('P', 'k'),   # 21
    ('k', 'P'),   # 22
    ('k', 'P'),   # 23
]
P_HEAD = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "......PPPP......",
    ".....PPPPPP.....",
    ".....kssssk.....",
    ".....skssks.....",
    "......ssss......",
]
PITCHER = {}
# セット：両手を胸の前で合わせる
PITCHER['SET'] = P_HEAD + [
    ".....UUUUUU.....",
    "....UUUssUUU....",
    "....UUUssUUU....",
    ".....UUUUUU.....",
    ".....PPPPPP.....",
    ".....UU..UU.....",
    ".....UU..UU.....",
    ".....UU..UU.....",
    ".....UU..UU.....",
    ".....PP..PP.....",
    "....kkk..kkk....",
    "................",
]
# 振りかぶる：両手を頭の上へ、左足を上げる
PITCHER['WINDUP'] = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    ".......ss.......",
    "......sPPs......",
    ".....PPPPPP.....",
    ".....kssssk.....",
    ".....skssks.....",
    "......ssss......",
    ".....UUUUUU.....",
    ".....UUUUUU.....",
    ".....UUUUUU.....",
    ".....UUUUUU.....",
    ".....PPPPPP.....",
    ".....UU.UUUU....",
    ".....UU...UU....",
    ".....UU...kk....",
    ".....UU.........",
    ".....PP.........",
    "....kkk.........",
    "................",
]
# 投げる：右腕を前へ振り下ろし、足を踏み出す
PITCHER['RELEASE'] = P_HEAD + [
    ".....UUUUUU.....",
    "...sUUUUUUU.....",
    "....UUUUUUUs....",
    ".....UUUUUUs....",
    ".....PPPPPP.....",
    "....UU...UU.....",
    "...UU.....UU....",
    "...UU......UU...",
    "...UU......UU...",
    "...PP......PP...",
    "..kkk......kkk..",
    "................",
]
PITCHER.update(_CA.PITCHER)
PITCHER_ORDER = ['SET', 'WINDUP', 'RELEASE']

# ---------------- バット（右打ち・1 色・32x16 = 2 枚並べ） ----------------
# 長さは約 14 ドット（打者の背の約半分。実物のバット 84cm／身長 180cm と同じくらいの比）。打者の各コマの手元 → 先 の線から描く（座標は打者の絵の列・行）。
# 先の半分は太く（2 ドット）。各コマの絵の左上は、打者の絵の左上（bat_x-8, bat_y-23）から BAT_OFS だけずらした所。
# 当たる瞬間（CONTACT）は手元 bat_x+5 から先 bat_x+19、高さは当たる線 bat_y-8。芯 = bat_x+BAT_REACH（先から 4 ドット）
BAT_REACH = 15
BAT_LINE = {
    'STANCE': ((5, 8), (3, -5)),
    'STRIDE': ((4, 8), (-6, -2)),
    'LOAD': ((4, 10), (-9, 5)),
    'SWING1': ((10, 13), (-2, 19)),
    'CONTACT': ((13, 14), (27, 15)),
    'FOLLOW1': ((12, 11), (21, 0)),
    'FOLLOW2': ((12, 7), (-1, 4)),
    'BUNT': ((10, 12), (24, 12)),           # 胸の高さで水平。手元 bat_x+2 → 先 bat_x+16
}
BAT_ORDER = BATTER_ORDER


def _bat_pixels(k):
    (x0, y0), (x1, y1) = BAT_LINE[k]
    n = max(abs(x1 - x0), abs(y1 - y0)) * 2
    pts = set()
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        pts.add((round(x), round(y)))
        if t > 0.45:                        # 先の半分は太く
            if abs(x1 - x0) >= abs(y1 - y0):
                pts.add((round(x), round(y) + 1))
            else:
                pts.add((round(x) + 1, round(y)))
    return pts


BAT = {}
BAT_OFS = {}
for _k in BAT_ORDER:
    _p = _bat_pixels(_k)
    _ox = min(x for x, _ in _p)
    _oy = min(y for _, y in _p)
    assert max(x for x, _ in _p) - _ox < 32 and max(y for _, y in _p) - _oy < 16, _k
    BAT_OFS[_k] = (_ox, _oy)
    BAT[_k] = ["".join('d' if (x + _ox, y + _oy) in _p else '.' for x in range(32)) for y in range(16)]


# ---------------- 審判 16x16（1 枚・色は行ごと：帽子 黒／顔 肌（球審はマスクで黒）／上着 黒／ズボン 灰／靴 黒） ----------------
# 上着は黒（1）。紺（13）はホームランでフェンスを光らせる色なので使わない（審判がいっしょに点滅しないように）
UMP_ROWCOL = [1, 1, 1, 6, 6, 6, 1, 1, 1, 1, 1, 14, 14, 14, 14, 1]
UMP_ROWCOL_PLATE = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 14, 14, 14, 14, 1]
UMPIRE = {}
UMPIRE['STAND'] = [
    "................",
    "......####......",
    ".....######.....",
    ".....######.....",
    ".....######.....",
    "......####......",
    ".....######.....",
    "....########....",
    "....########....",
    "....##.##.##....",
    ".....######.....",
    ".....##..##.....",
    ".....##..##.....",
    ".....##..##.....",
    ".....##..##.....",
    "....###..###....",
]
# ストライク・アウト：右のこぶしを高く上げる
UMPIRE['PUNCH'] = [
    "...##...........",
    "...##.####......",
    "....#######.....",
    "....#######.....",
    "....#######.....",
    "....#.####......",
    "....#######.....",
    ".....#######....",
    ".....#######....",
    ".....######.#...",
    ".....######.....",
    ".....##..##.....",
    ".....##...##....",
    "....##....##....",
    "....##....##....",
    "...###....###...",
]
# セーフ：両手を横に大きく広げる
UMPIRE['SAFE'] = [
    "................",
    "......####......",
    ".....######.....",
    ".....######.....",
    ".....######.....",
    "......####......",
    ".....######.....",
    "################",
    "################",
    ".....######.....",
    ".....######.....",
    "....##....##....",
    "....##....##....",
    "...##......##...",
    "...##......##...",
    "..###......###..",
]
# ファウル・タイム：両手を上げる
UMPIRE['FOUL'] = [
    "...##......##...",
    "...##.####.##...",
    "....########....",
    "....########....",
    "....########....",
    "....#.####.#....",
    ".....######.....",
    ".....######.....",
    ".....######.....",
    ".....######.....",
    ".....######.....",
    ".....##..##.....",
    ".....##..##.....",
    ".....##..##.....",
    ".....##..##.....",
    "....###..###....",
]
UMPIRE.update(_CA.UMPIRE)
UMP_ORDER = ['STAND', 'PUNCH', 'SAFE', 'FOUL']

# ボール・影
BALLS = {}
BALLS['BALL_S'] = ["." * 16] * 7 + [".......ww......."] * 2 + ["." * 16] * 7
BALLS['BALL_M'] = ["." * 16] * 6 + [".......ww.......", "......wwww......", "......wwww......", ".......ww......."] + ["." * 16] * 6
BALLS['BALL_L'] = ["." * 16] * 5 + ["......wwww......", ".....wwwwww.....", ".....wwwwww.....",
                                    ".....wwwwww.....", ".....wwwwww.....", "......wwww......"] + ["." * 16] * 5
BALLS['SHADOW'] = ["." * 16] * 7 + ["......kkkk......", ".......kk......."] + ["." * 16] * 7
BALL_ORDER = ['BALL_S', 'BALL_M', 'BALL_L', 'SHADOW']


def check(rows, h, name, w=16):
    assert len(rows) == h, (name, len(rows))
    for r in rows:
        assert len(r) == w, (name, r, len(r))


def family_zones(frames, h, name, zones=None):
    """各行の記号の組（最大 2 つ）。zones があればそれに合っているか確かめて返す"""
    if zones is not None:
        assert len(zones) == h, name
        for k, f in frames.items():
            for y in range(h):
                for c in f[y]:
                    if c != '.' and c not in zones[y]:
                        raise ValueError(f"{name}:{k} row {y} uses {c!r}, zone {zones[y]}: {f[y]}")
        return [tuple(z) for z in zones]
    out = []
    for y in range(h):
        syms = []
        for f in frames.values():
            for c in f[y]:
                if c != '.' and c not in syms:
                    syms.append(c)
        if len(syms) > 2:
            raise ValueError(f"{name}: row {y} uses {syms}")
        while len(syms) < 2:
            syms.append('.')
        out.append(tuple(syms))
    return out


def pat16(rows16, sym, x0=0):
    """16x16 の 1 色分の柄（MSX の並び：左上・左下・右上・右下）。x0 = 切り出す左端の列"""
    out = []
    for half in (0, 8):
        for y in range(16):
            b = 0
            for x in range(8):
                if rows16[y][x0 + half + x] == sym:
                    b |= 0x80 >> x
            out.append(b)
    return out


def layered(frames, order, h, name, zones=None):
    for k in order:
        check(frames[k], h, name + ':' + k)
    zones = family_zones({k: frames[k] for k in order}, h, name, zones)
    pats = []   # 各コマ: [B 層の柄..., A 層の柄...]（上から 16 行ずつ）
    for k in order:
        rows = frames[k] + ["." * 16] * ((-h) % 16)
        layers = []
        for layer in (1, 0):   # B（上に重なる）→ A
            parts = []
            for top in range(0, len(rows), 16):
                blk = rows[top:top + 16]
                zrow = [zones[top + y][layer] if top + y < h else '.' for y in range(16)]
                sel = [''.join(c if (c != '.' and c == zrow[y]) else '.' for c in blk[y]) for y in range(16)]
                parts.append(pat16([s.replace(zrow[y], '#') if zrow[y] != '.' else s for y, s in enumerate(sel)], '#'))
            layers.append(parts)
        pats.append(layers)
    return zones, pats


def bat_patterns(mirror_it=False):
    """バット 7 コマ × 2 枚（左・右）の柄"""
    out = bytearray()
    for k in BAT_ORDER:
        rows = BAT[k]
        check(rows, 16, 'bat:' + k, 32)
        if mirror_it:
            rows = mirror(rows)
        for x0 in (0, 16):
            out += bytes(pat16([r.replace('d', '#') for r in rows], '#', x0))
    return out


def preview(path, team=None, scale=6):
    from PIL import Image
    from common import rgb8
    team = team or {'P': (1, 2, 6), 'U': (7, 7, 7)}

    def col(sym):
        if sym in team:
            r, g, b = team[sym]
            return (r * 36, g * 36, b * 36)
        return rgb8(SYM2COLOR_FIXED[sym])
    groups = [(CHIBI, CHIBI_ORDER, 16, 16), (BATTER, BATTER_ORDER, 24, 16), (PITCHER, PITCHER_ORDER, 24, 16),
              (BAT, BAT_ORDER, 16, 32), (BALLS, BALL_ORDER, 16, 16), (UMPIRE, UMP_ORDER, 16, 16)]
    W = 24 * 18
    im = Image.new("RGB", (W, 6 * 28), (40, 140, 40))
    px = im.load()
    for gi, (fr, order, h, w) in enumerate(groups):
        x = 1
        for k in order:
            for y in range(h):
                for c in range(w):
                    s = fr[k][y][c]
                    if s == '#':
                        px[x + c, gi * 28 + y + 2] = rgb8(UMP_ROWCOL[y])
                    elif s != '.':
                        px[x + c, gi * 28 + y + 2] = col(s)
            x += w + 2
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(path)


def preview_batter(path, scale=8):
    """打者とバットを重ねて、バッターボックスとホームベースと一緒に描く（右打ち・左打ち）"""
    from PIL import Image
    from common import rgb8
    team = {'P': (6, 1, 1), 'U': (7, 7, 7)}

    def col(sym):
        if sym in team:
            r, g, b = team[sym]
            return (r * 36, g * 36, b * 36)
        return rgb8(SYM2COLOR_FIXED[sym])
    W, H = len(BATTER_ORDER) * 72, 2 * 40
    im = Image.new("RGB", (W, H), rgb8(4))
    px = im.load()
    for row, left in enumerate((False, True)):
        for i, (bk, fk) in enumerate(zip(BAT_ORDER, BATTER_ORDER)):
            bx = i * 72 + (30 if not left else 42)      # bat_x
            by = row * 40 + 34                            # bat_y
            # 箱（右打ちは左の箱 bat_x-9..bat_x+8）
            x0 = bx - 9 if not left else bx - 8
            for x in range(x0, x0 + 18):
                px[x, by - 23 + 1] = px[x, by + 1] = (255, 255, 255)
            for y in range(by - 23 + 1, by + 2):
                px[x0, y] = px[x0 + 17, y] = (255, 255, 255)
            hp = bx + 23 if not left else bx - 23          # ホームベースの中心
            for x in range(hp - 5, hp + 5):
                for y in range(by - 6, by):
                    px[x, y] = (255, 255, 255)
            rows = BAT[bk] if not left else mirror(BAT[bk])
            ox, oy = BAT_OFS[bk]
            if left:
                ox = -16 - ox
            for y in range(16):
                for x in range(32):
                    if rows[y][x] == 'd':
                        px[bx - 8 + ox + x, by - 23 + oy + y] = col('d')
            fr = BATTER[fk] if not left else mirror(BATTER[fk])
            for y in range(24):
                for x in range(16):
                    if fr[y][x] != '.':
                        px[bx - 8 + x, by - 23 + y] = col(fr[y][x])
            # 当たる線（bat_y-8）と芯
            sx = bx + BAT_REACH if not left else bx - BAT_REACH
            px[sx, by - 8] = (255, 0, 255)
    im.resize((W * scale, H * scale), Image.NEAREST).save(path)


if __name__ == "__main__":
    for fr, order, h, nm, z in [(CHIBI, CHIBI_ORDER, 16, 'chibi', ZONE_CHIBI), (BATTER, BATTER_ORDER, 24, 'batter', ZONE_BATTER),
                                (PITCHER, PITCHER_ORDER, 24, 'pitcher', ZONE_PITCHER)]:
        layered(fr, order, h, nm, z)
    bat_patterns()
    preview("../build/sprites_preview.png")
    preview_batter("../build/batter_preview.png")
    print("ok")
