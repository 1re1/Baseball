# -*- coding: utf-8 -*-
"""マニュアルの挿絵（すべて自作の図形で描く）。
・ボールくん：野球のボールの顔をした案内役
・キャップちゃん / キャップくん：ちびキャラの選手（いろいろなポーズ）
座標は reportlab（y は上向き）。各関数の (x, y) は足もと（ボールくんは中心）。"""
import math
from reportlab.lib.colors import Color, white, black

SKIN = Color(1.0, 0.82, 0.66)
SKIN_D = Color(0.92, 0.66, 0.50)
HAIR = Color(0.22, 0.16, 0.14)
CHEEK = Color(1.0, 0.55, 0.60)
RED = Color(0.88, 0.16, 0.20)
NAVY = Color(0.12, 0.20, 0.48)
WOOD = Color(0.93, 0.78, 0.45)
WOOD_D = Color(0.70, 0.52, 0.25)
GLOVE = Color(0.62, 0.36, 0.16)
SHOE = Color(0.20, 0.20, 0.24)
OUT = Color(0.18, 0.14, 0.14)


def _stroke(c, col=OUT, w=1.2):
    c.setStrokeColor(col)
    c.setLineWidth(w)
    c.setLineCap(1)
    c.setLineJoin(1)


def _circle(c, x, y, r, fill, line=True, lw=1.2):
    c.setFillColor(fill)
    _stroke(c, OUT, lw)
    c.circle(x, y, r, stroke=1 if line else 0, fill=1)


def _ellipse(c, x, y, rx, ry, fill, line=True, lw=1.2):
    c.setFillColor(fill)
    _stroke(c, OUT, lw)
    c.ellipse(x - rx, y - ry, x + rx, y + ry, stroke=1 if line else 0, fill=1)


def _limb(c, x0, y0, x1, y1, w, col, lw=1.2):
    """太い腕・足（輪郭つき）"""
    c.setLineCap(1)
    c.setStrokeColor(OUT)
    c.setLineWidth(w + lw * 2)
    c.line(x0, y0, x1, y1)
    c.setStrokeColor(col)
    c.setLineWidth(w)
    c.line(x0, y0, x1, y1)


def _rrect(c, x, y, w, h, r, fill, line=True, lw=1.2):
    c.setFillColor(fill)
    _stroke(c, OUT, lw)
    c.roundRect(x, y, w, h, r, stroke=1 if line else 0, fill=1)


def bat(c, x0, y0, x1, y1, u):
    """手元 (x0,y0) → 先 (x1,y1) のバット（先が太い）"""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    w0, w1 = 1.6 * u, 3.6 * u
    p = c.beginPath()
    p.moveTo(x0 + nx * w0, y0 + ny * w0)
    p.lineTo(x1 + nx * w1, y1 + ny * w1)
    p.lineTo(x1 - nx * w1, y1 - ny * w1)
    p.lineTo(x0 - nx * w0, y0 - ny * w0)
    p.close()
    c.setFillColor(WOOD)
    _stroke(c, OUT, 1.0)
    c.drawPath(p, stroke=1, fill=1)
    _circle(c, x1, y1, w1, WOOD, lw=1.0)
    _circle(c, x0, y0, w0 * 1.4, WOOD_D, lw=1.0)


def ball(c, x, y, r):
    _circle(c, x, y, r, white, lw=1.0)
    c.setStrokeColor(RED)
    c.setLineWidth(max(0.6, r * 0.18))
    c.arc(x - r * 1.55, y - r * 0.9, x - r * 0.25, y + r * 0.9, -40, 80)
    c.arc(x + r * 0.25, y - r * 0.9, x + r * 1.55, y + r * 0.9, 140, 80)


def face(c, x, y, u, mood="smile", look=0.0):
    """顔（目・ほっぺ・口）。(x,y) = 顔の中心"""
    ex = 6.5 * u
    for sx in (-1, 1):
        _ellipse(c, x + sx * ex + look * u, y + 1.5 * u, 2.4 * u, 3.4 * u, OUT, line=False)
        _circle(c, x + sx * ex + look * u + 0.8 * u, y + 2.8 * u, 0.9 * u, white, line=False)
        _ellipse(c, x + sx * 10.5 * u, y - 3.5 * u, 2.8 * u, 1.8 * u, CHEEK, line=False)
    _stroke(c, OUT, 1.1)
    if mood == "smile":
        c.arc(x - 3.2 * u, y - 7.0 * u, x + 3.2 * u, y - 2.0 * u, 200, 140)
    elif mood == "open":
        _ellipse(c, x, y - 5.0 * u, 2.6 * u, 2.4 * u, Color(0.85, 0.25, 0.3), lw=1.0)
    elif mood == "o":
        _ellipse(c, x, y - 5.0 * u, 1.6 * u, 1.9 * u, Color(0.85, 0.25, 0.3), lw=1.0)
    elif mood == "flat":
        c.line(x - 2.5 * u, y - 4.8 * u, x + 2.5 * u, y - 4.8 * u)


def head(c, x, y, u, cap, mood="smile", back=False, look=0.0, helmet=False):
    """頭（帽子つき）。(x,y) = 頭の中心。半径 18u"""
    r = 18 * u
    # 後ろ髪
    _circle(c, x, y, r, HAIR if back else SKIN)
    if not back:
        # 横の髪
        c.setFillColor(HAIR)
        c.setStrokeColor(HAIR)
        c.wedge(x - r, y - r, x + r, y + r, 120, 50, stroke=0, fill=1)
        c.wedge(x - r, y - r, x + r, y + r, 10, 50, stroke=0, fill=1)
        _stroke(c)
        c.setFillColor(SKIN)
        c.circle(x, y - 2 * u, r * 0.86, stroke=0, fill=1)
        c.setFillColor(Color(0, 0, 0, 0))
        _stroke(c)
        c.circle(x, y, r, stroke=1, fill=0)
        face(c, x, y - 3 * u, u, mood, look)
    # 帽子（つばは前）
    c.setFillColor(cap)
    _stroke(c)
    p = c.beginPath()
    p.arc(x - r * 1.02, y - r * 0.55, x + r * 1.02, y + r * 1.12, 0, 180)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    if helmet:
        _ellipse(c, x - 12 * u, y + 2 * u, 5 * u, 6 * u, cap)
    if not back:
        _ellipse(c, x + 4 * u, y + 4.5 * u, 20 * u, 4.2 * u, cap)
        # 帽子のマーク
        _circle(c, x, y + 13 * u, 3.4 * u, white, lw=0.8)


def player(c, x, y, h, pose="stand", cap=NAVY, uni=white, line=None, mood="smile", flip=False, back=False):
    """ちびキャラの選手。h = 背の高さ（ポイント）。line = ユニフォームの線（なければ帽子の色）"""
    u = h / 100.0
    line = line or cap
    c.saveState()
    c.translate(x, y)
    if flip:
        c.scale(-1, 1)
    # ポーズごとの手足の位置（足もと = 0,0）
    hipL, hipR = (-6 * u, 30 * u), (6 * u, 30 * u)
    footL, footR = (-8 * u, 4 * u), (8 * u, 4 * u)
    shL, shR = (-13 * u, 50 * u), (13 * u, 50 * u)
    handL, handR = (-17 * u, 31 * u), (17 * u, 31 * u)
    extra = []
    hy = 74 * u
    if pose == "wave":
        handR = (26 * u, 70 * u)
    elif pose == "cheer":
        handL, handR = (-24 * u, 76 * u), (24 * u, 76 * u)
        footL, footR = (-12 * u, 5 * u), (12 * u, 5 * u)
    elif pose == "point":
        handR = (34 * u, 52 * u)
    elif pose == "think":
        handR = (6 * u, 58 * u)
    elif pose == "run":
        footL, footR = (-20 * u, 10 * u), (16 * u, 3 * u)
        handL, handR = (-22 * u, 52 * u), (20 * u, 38 * u)
    elif pose == "bat":            # 構え：バットを立てる
        handL, handR = (10 * u, 55 * u), (13 * u, 58 * u)
        footL, footR = (-12 * u, 4 * u), (12 * u, 4 * u)
        extra.append(("bat", (12 * u, 57 * u), (-8 * u, 102 * u)))
    elif pose == "swing":          # 振り抜く：バットは水平
        handL, handR = (22 * u, 42 * u), (25 * u, 44 * u)
        footL, footR = (-14 * u, 4 * u), (14 * u, 4 * u)
        extra.append(("bat", (24 * u, 43 * u), (72 * u, 46 * u)))
    elif pose == "bunt":
        handL, handR = (16 * u, 46 * u), (30 * u, 48 * u)
        footL, footR = (-10 * u, 4 * u), (12 * u, 4 * u)
        extra.append(("bat", (16 * u, 46 * u), (46 * u, 50 * u)))
    elif pose == "pitch":          # 振りかぶって投げる直前
        handR = (-26 * u, 80 * u)
        handL = (22 * u, 50 * u)
        footR = (16 * u, 22 * u)
        extra.append(("ball", (-26 * u, 84 * u)))
    elif pose == "throw":
        handR = (34 * u, 62 * u)
        handL = (-22 * u, 44 * u)
        footL, footR = (-16 * u, 4 * u), (18 * u, 4 * u)
        extra.append(("ball", (39 * u, 64 * u)))
    elif pose == "catch":          # グラブを上げる
        handL = (-18 * u, 86 * u)
        handR = (16 * u, 36 * u)
        extra.append(("glove", (-18 * u, 92 * u)))
    elif pose == "ready":          # 守備の構え
        handL, handR = (-12 * u, 24 * u), (12 * u, 24 * u)
        footL, footR = (-15 * u, 4 * u), (15 * u, 4 * u)
        hy = 70 * u
        extra.append(("glove", (-12 * u, 22 * u)))
    elif pose == "slide":
        pass
    if pose == "slide":
        # すべり込み（横向きに寝た形）
        c.saveState()
        c.translate(0, 14 * u)
        c.rotate(-72)
        player(c, 0, -10 * u, h, "cheer", cap, uni, line, mood)
        c.restoreState()
        c.restoreState()
        return
    # 足
    for hp, ft in ((hipL, footL), (hipR, footR)):
        _limb(c, hp[0], hp[1], ft[0], ft[1] + 5 * u, 8 * u, uni)
        _limb(c, ft[0], ft[1] + 9 * u, ft[0], ft[1] + 4 * u, 7.4 * u, line)   # ソックス
        _ellipse(c, ft[0] + 2 * u, ft[1], 6.5 * u, 3.6 * u, SHOE)
    # 胴
    _rrect(c, -14 * u, 27 * u, 28 * u, 27 * u, 7 * u, uni)
    c.setFillColor(line)
    c.rect(-13.4 * u, 29 * u, 26.8 * u, 3.4 * u, stroke=0, fill=1)        # ベルト
    c.setStrokeColor(line)
    c.setLineWidth(1.4 * u)
    c.line(0, 34 * u, 0, 52 * u)                                          # 前立て
    # 腕（袖 → 手）
    for sh, hd in ((shL, handL), (shR, handR)):
        mx, my = sh[0] + (hd[0] - sh[0]) * 0.45, sh[1] + (hd[1] - sh[1]) * 0.45
        _limb(c, sh[0], sh[1], mx, my, 8 * u, uni)
        _limb(c, mx, my, hd[0], hd[1], 5.5 * u, SKIN)
        _circle(c, hd[0], hd[1], 3.6 * u, SKIN, lw=1.0)
    for e in extra:
        if e[0] == "bat":
            bat(c, e[1][0], e[1][1], e[2][0], e[2][1], u)
            _circle(c, e[1][0], e[1][1], 3.6 * u, SKIN, lw=1.0)
        elif e[0] == "ball":
            ball(c, e[1][0], e[1][1], 4.5 * u)
        elif e[0] == "glove":
            _ellipse(c, e[1][0], e[1][1], 7.5 * u, 8.5 * u, GLOVE)
            c.setStrokeColor(Color(0.45, 0.25, 0.1))
            c.setLineWidth(0.8)
            for k in (-3, 0, 3):
                c.line(e[1][0] + k * u, e[1][1] - 3 * u, e[1][0] + k * u, e[1][1] + 5 * u)
    head(c, 0, hy, u, cap, mood, back=back)
    c.restoreState()


def ballkun(c, x, y, r, mood="smile", arms="wave"):
    """案内役のボールくん（(x,y) = 体の中心）"""
    u = r / 20.0
    # 足
    for sx in (-1, 1):
        _limb(c, x + sx * 7 * u, y - 16 * u, x + sx * 9 * u, y - 25 * u, 3.4 * u, white, lw=1.0)
        _ellipse(c, x + sx * 10 * u, y - 26 * u, 5 * u, 3 * u, RED)
    # 腕
    if arms == "wave":
        hands = [(-27 * u, -6 * u), (26 * u, 18 * u)]
    elif arms == "up":
        hands = [(-26 * u, 18 * u), (26 * u, 18 * u)]
    elif arms == "point":
        hands = [(-26 * u, -6 * u), (32 * u, 4 * u)]
    else:
        hands = [(-25 * u, -8 * u), (25 * u, -8 * u)]
    for sx, (hx, hy) in zip((-1, 1), hands):
        _limb(c, x + sx * 17 * u, y + 2 * u, x + hx, y + hy, 3.4 * u, white, lw=1.0)
        _circle(c, x + hx, y + hy, 3.6 * u, white, lw=1.0)
    _circle(c, x, y, r, white, lw=1.4)
    c.setStrokeColor(RED)
    c.setLineWidth(1.6 * u)
    c.arc(x - r * 1.7, y - r * 1.0, x - r * 0.45, y + r * 1.0, -42, 84)
    c.arc(x + r * 0.45, y - r * 1.0, x + r * 1.7, y + r * 1.0, 138, 84)
    # 縫い目の印
    for k in range(-3, 4):
        a = math.radians(k * 11)
        for sx in (-1, 1):
            cx0 = x + sx * (r * 1.075 - r * 0.625 * math.cos(a))
            cy0 = y + r * 0.92 * math.sin(a)
            c.line(cx0 - 1.2 * u, cy0, cx0 + 1.2 * u, cy0)
    face(c, x, y + 1 * u, u * 0.95, mood)


def bubble(c, x, y, w, h, tail=(0, 0), fill=white, edge=OUT):
    """吹き出し（左下が x,y）。tail = しっぽの先の位置（絶対座標）"""
    c.setFillColor(fill)
    _stroke(c, edge, 1.3)
    c.roundRect(x, y, w, h, 10, stroke=1, fill=1)
    tx, ty = tail
    if tx or ty:
        bx = min(max(tx, x + 16), x + w - 16)
        by = y if ty < y else y + h
        p = c.beginPath()
        p.moveTo(bx - 7, by)
        p.lineTo(tx, ty)
        p.lineTo(bx + 7, by)
        c.drawPath(p, stroke=1, fill=1)
        c.setStrokeColor(fill)
        c.setLineWidth(2.6)
        c.line(bx - 5.5, by, bx + 5.5, by)


def star(c, x, y, r, col):
    p = c.beginPath()
    for k in range(10):
        a = math.radians(90 + k * 36)
        rr = r if k % 2 == 0 else r * 0.45
        if k == 0:
            p.moveTo(x + rr * math.cos(a), y + rr * math.sin(a))
        else:
            p.lineTo(x + rr * math.cos(a), y + rr * math.sin(a))
    p.close()
    c.setFillColor(col)
    _stroke(c, OUT, 0.8)
    c.drawPath(p, stroke=1, fill=1)
