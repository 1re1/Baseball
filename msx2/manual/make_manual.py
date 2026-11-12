# -*- coding: utf-8 -*-
"""MSX STADIUM プレイングマニュアル（PDF）を作る。
画面写真は manual/img（shots.py で撮る）、挿絵は art.py、ドット絵・字はゲームの素材から描く。
出力：MSXSTADIUM_manual.pdf（msx2 の直下）"""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import Color, white, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from PIL import Image
import art
import gfx_font
import gfx_sprites as SP
import teams as TM
from common import rgb8, PALETTE

FONT_DIR = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("G", os.path.join(FONT_DIR, "BIZ-UDGothicR.ttc"), subfontIndex=0))
pdfmetrics.registerFont(TTFont("GB", os.path.join(FONT_DIR, "BIZ-UDGothicB.ttc"), subfontIndex=0))

W, H = A4
M = 42                      # 左右の余白
IMG = os.path.join(HERE, "img")
CACHE = os.path.join(ROOT, "build", "manual_cache")
OUTPDF = os.path.join(ROOT, "MSXSTADIUM_manual.pdf")

GREEN = Color(0.16, 0.62, 0.26)
GREEN_L = Color(0.88, 0.96, 0.88)
NAVY = Color(0.12, 0.20, 0.48)
NAVY_L = Color(0.90, 0.92, 0.98)
YELLOW = Color(1.0, 0.84, 0.18)
YELLOW_L = Color(1.0, 0.97, 0.84)
RED = Color(0.86, 0.18, 0.20)
RED_L = Color(1.0, 0.92, 0.92)
GRAY = Color(0.45, 0.45, 0.48)
INK = Color(0.15, 0.15, 0.18)
DIRT = Color(0.86, 0.60, 0.34)

CHAPTERS = {
    0: ("はじめに", GREEN), 1: ("じゅんび", NAVY), 2: ("打つ", RED), 3: ("投げる", Color(0.13, 0.45, 0.75)),
    4: ("守る", GREEN), 5: ("走る", Color(0.85, 0.45, 0.10)), 6: ("試合", NAVY), 7: ("チーム", Color(0.55, 0.25, 0.65)),
    8: ("ふろく", GRAY), 9: ("モード", Color(0.08, 0.52, 0.55)),
}


def style(size=11.0, leading=None, font="G", color=INK, align=0):
    return ParagraphStyle("s", fontName=font, fontSize=size, leading=leading or size * 1.7, textColor=color,
                          wordWrap="CJK", alignment=align)


# ---------------------------------------------------------------- 画像
def big(name, scale=4):
    """画面写真を整数倍に拡大（ドットがぼやけないように）"""
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, f"{name}_x{scale}.png")
    if not os.path.exists(out):
        im = Image.open(os.path.join(IMG, name + ".png")).convert("RGB")
        im.resize((im.width * scale, im.height * scale), Image.NEAREST).save(out)
    return out


def crop_big(name, box, scale=6, tag=None):
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, f"{name}_{tag or '_'.join(map(str, box))}_x{scale}.png")
    if not os.path.exists(out):
        im = Image.open(os.path.join(IMG, name + ".png")).convert("RGB").crop(box)
        im.resize((im.width * scale, im.height * scale), Image.NEAREST).save(out)
    return out


def sprite_sheet(frames, order, h, team, scale=10, gap=4, bg=(76, 175, 80), w=16):
    """ゲームのドット絵を大きく描いた画像"""
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, "spr_%s_%d.png" % ("_".join(order), scale))
    if os.path.exists(out):
        return out

    def col(sym):
        if sym in team:
            r, g, b = team[sym]
            return (r * 36, g * 36, b * 36)
        return rgb8(SP.SYM2COLOR_FIXED[sym])
    n = len(order)
    im = Image.new("RGB", ((w + gap) * n + gap, h + gap * 2), bg)
    px = im.load()
    for i, k in enumerate(order):
        for y in range(h):
            for x in range(w):
                s = frames[k][y][x]
                if s != '.':
                    px[gap + i * (w + gap) + x, gap + y] = col(s)
    im.resize((im.width * scale, im.height * scale), Image.NEAREST).save(out)
    return out


def batter_bat(keys, scale=10, gap=6, bg=(206, 150, 86)):
    """打者のコマにバットを重ねた絵（ゲームと同じ位置関係）。土の色の上に並べる"""
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, "bb_%s_%d.png" % ("_".join(keys), scale))
    team = {'P': (6, 1, 1), 'U': (7, 7, 7)}

    def col(sym):
        if sym in team:
            r, g, b = team[sym]
            return (r * 36, g * 36, b * 36)
        return rgb8(SP.SYM2COLOR_FIXED[sym])
    cw, ch = 40, 26
    im = Image.new("RGB", ((cw + gap) * len(keys) + gap, ch + gap * 2), bg)
    px = im.load()
    for i, k in enumerate(keys):
        bx0, by0 = gap + i * (cw + gap) + 6, gap
        for y in range(24):
            for x in range(16):
                sym = SP.BATTER[k][y][x]
                if sym != '.':
                    px[bx0 + x, by0 + y] = col(sym)
        ox, oy = SP.BAT_OFS[k]
        for y in range(16):
            for x in range(32):
                if SP.BAT[k][y][x] != '.':
                    xx, yy = bx0 + ox + x, by0 + oy + y
                    if 0 <= xx < im.width and 0 <= yy < im.height and SP.BATTER[k][min(23, max(0, oy + y))][min(15, max(0, ox + x))] not in 'sS':
                        px[xx, yy] = (240, 220, 60)
    im.resize((im.width * scale, im.height * scale), Image.NEAREST).save(out)
    return out


def ump_sheet(scale=9, gap=4, bg=(76, 175, 80)):
    """審判のドット絵（色は行ごと：帽子 黒・顔 肌・上着 紺・ズボン 灰・靴 黒）"""
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, "ump_%d.png" % scale)
    n = len(SP.UMP_ORDER)
    im = Image.new("RGB", ((16 + gap) * n + gap, 16 + gap * 2), bg)
    px = im.load()
    for i, k in enumerate(SP.UMP_ORDER):
        for y in range(16):
            for x in range(16):
                if SP.UMPIRE[k][y][x] != '.':
                    px[gap + i * (16 + gap) + x, gap + y] = rgb8(SP.UMP_ROWCOL[y])
    im.resize((im.width * scale, im.height * scale), Image.NEAREST).save(out)
    return out


def msg_image(text, scale=6):
    """ゲームの判定メッセージ（縦 2 倍の字・上から白→黄→赤）"""
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, "msg_%s.png" % "".join("%04x" % ord(c) for c in text))
    if os.path.exists(out):
        return out
    im = Image.new("RGB", (8 * len(text) + 4, 20), (20, 24, 40))
    px = im.load()
    rowcol = [rgb8(7)] * 3 + [rgb8(15)] * 9 + [rgb8(12)] * 4
    for i, ch in enumerate(text):
        g = gfx_font.glyph(ch)
        for r in range(16):
            row = g[r // 2]
            for x in range(8):
                if row[x] == '#':
                    px[2 + i * 8 + x, 2 + r] = rowcol[r]
    im.resize((im.width * scale, im.height * scale), Image.NEAREST).save(out)
    return out


def font_text_image(text, fg=(255, 255, 255), bg=(0, 0, 0), scale=6):
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, "ft_%s_%d.png" % ("".join("%04x" % ord(c) for c in text), fg[0]))
    if os.path.exists(out):
        return out
    im = Image.new("RGB", (8 * len(text), 8), bg)
    px = im.load()
    for i, ch in enumerate(text):
        for r, row in enumerate(gfx_font.glyph(ch)):
            for x in range(8):
                if row[x] == '#':
                    px[i * 8 + x, r] = fg
    im.resize((im.width * scale, im.height * scale), Image.NEAREST).save(out)
    return out


# ---------------------------------------------------------------- ページの部品
class Book:
    def __init__(self, path):
        self.c = canvas.Canvas(path, pagesize=A4)
        self.c.setTitle("MSX STADIUM プレイングマニュアル")
        self.c.setAuthor("MSX STADIUM (fan made)")
        self.c.setSubject("MSX2 用 野球ゲームの操作説明書")
        self.page = 0
        self.toc = []

    # --- ページ
    def begin(self, chap, title, sub=None):
        c = self.c
        self.page += 1
        name, col = CHAPTERS[chap]
        self.col = col
        self.toc.append((self.page, chap, title))
        c.setFillColor(white)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        # 見出しの帯
        c.setFillColor(col)
        c.roundRect(M - 12, H - 92, W - 2 * M + 24, 58, 14, stroke=0, fill=1)
        c.setFillColor(white)
        c.roundRect(M, H - 80, 74, 34, 10, stroke=0, fill=1)
        c.setFillColor(col)
        c.setFont("GB", 15)
        c.drawCentredString(M + 37, H - 69, name)
        c.setFillColor(white)
        c.setFont("GB", 22)
        c.drawString(M + 90, H - 72, title)
        if sub:
            c.setFont("G", 10)
            c.drawRightString(W - M, H - 48, sub)
        art.ball(c, W - M - 6, H - 72, 9)
        # 下の線とページ番号
        c.setStrokeColor(col)
        c.setLineWidth(1.2)
        c.line(M, 44, W - M, 44)
        c.setFillColor(GRAY)
        c.setFont("G", 9)
        c.drawString(M, 30, "MSX STADIUM プレイングマニュアル")
        art.ball(c, W - M - 16, 32, 11)
        c.setFillColor(INK)
        c.setFont("GB", 9)
        c.drawCentredString(W - M - 16, 29, str(self.page))
        self.y = H - 112

    def end(self):
        self.c.showPage()

    # --- 文字
    def para(self, html, x=None, w=None, size=11.0, font="G", color=INK, gap=8, y=None, align=0, leading=None):
        x = M if x is None else x
        w = (W - 2 * M) if w is None else w
        y = self.y if y is None else y
        p = Paragraph(html, style(size, leading, font, color, align))
        _, h = p.wrap(w, 10000)
        p.drawOn(self.c, x, y - h)
        self.y = y - h - gap
        return h

    def head(self, text, color=None, size=14, x=None, w=None):
        c = self.c
        x = M if x is None else x
        col = color or self.col
        c.setFillColor(col)
        c.circle(x + 7, self.y - 8, 6, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("GB", size)
        c.drawString(x + 20, self.y - 13, text)
        c.setStrokeColor(col)
        c.setLineWidth(0.8)
        c.line(x + 20, self.y - 18, x + (w or (W - 2 * M)), self.y - 18)
        self.y -= 30

    def bullets(self, items, x=None, w=None, size=11, mark="●", color=None):
        x = M if x is None else x
        w = (W - 2 * M) if w is None else w
        for it in items:
            c = self.c
            c.setFillColor(color or self.col)
            c.setFont("GB", size * 0.8)
            c.drawString(x + 2, self.y - size * 1.05, mark)
            self.para(it, x + size * 1.3, w - size * 1.3, size=size, gap=4)
        self.y -= 4

    def box(self, x, ytop, w, h, fill, edge=None, r=12):
        c = self.c
        c.setFillColor(fill)
        if edge:
            c.setStrokeColor(edge)
            c.setLineWidth(1.4)
        c.roundRect(x, ytop - h, w, h, r, stroke=1 if edge else 0, fill=1)

    def note(self, html, title="ポイント", fill=YELLOW_L, edge=YELLOW, x=None, w=None, size=10.5):
        """囲みの説明"""
        x = M if x is None else x
        w = (W - 2 * M) if w is None else w
        p = Paragraph(html, style(size))
        _, h = p.wrap(w - 28, 10000)
        hh = h + 34
        self.box(x, self.y, w, hh, fill, edge)
        c = self.c
        c.setFillColor(edge)
        c.roundRect(x + 12, self.y - 9, 70, 18, 8, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("GB", 10)
        c.drawCentredString(x + 47, self.y - 4, title)
        p.drawOn(c, x + 14, self.y - 22 - h)
        self.y -= hh + 12

    def tip(self, html, who="ball", x=None, w=None, mood="smile", size=10.5):
        """キャラクターのひとこと（吹き出し）"""
        x = M if x is None else x
        w = (W - 2 * M) if w is None else w
        p = Paragraph(html, style(size))
        bw = w - 90
        _, h = p.wrap(bw - 26, 10000)
        hh = max(h + 24, 62)
        c = self.c
        cy = self.y - hh / 2
        if who == "ball":
            art.ballkun(c, x + 34, cy - 2, 20, mood, "point")
        else:
            art.player(c, x + 34, cy - 34, 68, "point", cap=RED if who == "chan" else NAVY)
        art.bubble(c, x + 84, self.y - hh, bw, hh, tail=(x + 66, cy + 4))
        p.drawOn(c, x + 97, self.y - hh / 2 - h / 2)
        self.y -= hh + 12

    def shot(self, name, x, ytop, w, caption=None, scale=4):
        """画面写真（黒いふちつき）。高さを返す"""
        c = self.c
        h = w * 212 / 256
        c.setFillColor(INK)
        c.roundRect(x - 5, ytop - h - 5, w + 10, h + 10, 6, stroke=0, fill=1)
        c.drawImage(big(name, scale), x, ytop - h, w, h)
        if caption:
            c.setFillColor(GRAY)
            c.setFont("G", 9)
            c.drawCentredString(x + w / 2, ytop - h - 18, caption)
            return h + 26
        return h + 12

    def image(self, path, x, ytop, w, h=None, frame=False):
        im = Image.open(path)
        h = h or w * im.height / im.width
        if frame:
            self.c.setFillColor(INK)
            self.c.roundRect(x - 4, ytop - h - 4, w + 8, h + 8, 5, stroke=0, fill=1)
        self.c.drawImage(path, x, ytop - h, w, h, mask='auto')
        return h

    def badge(self, n, x, y, col=RED, r=9):
        c = self.c
        c.setFillColor(col)
        c.setStrokeColor(white)
        c.setLineWidth(1.5)
        c.circle(x, y, r, stroke=1, fill=1)
        c.setFillColor(white)
        c.setFont("GB", r * 1.15)
        c.drawCentredString(x, y - r * 0.4, str(n))

    def keycap(self, x, y, w, h, label, sub=None, col=None, size=10):
        c = self.c
        c.setFillColor(Color(0.82, 0.82, 0.86))
        c.roundRect(x, y - 3, w, h, 5, stroke=0, fill=1)
        c.setFillColor(col or white)
        c.setStrokeColor(GRAY)
        c.setLineWidth(1)
        c.roundRect(x, y, w, h, 5, stroke=1, fill=1)
        c.setFillColor(INK)
        c.setFont("GB", size)
        c.drawCentredString(x + w / 2, y + h / 2 - size * 0.35 + (4 if sub else 0), label)
        if sub:
            c.setFont("G", 7)
            c.drawCentredString(x + w / 2, y + 4, sub)

    def table(self, data, widths, x=None, size=10, head_col=None, zebra=True, align_right=()):
        x = M if x is None else x
        cells = []
        for r, row in enumerate(data):
            cells.append([Paragraph(str(v), style(size, size * 1.35, "GB" if r == 0 else "G",
                                                  white if r == 0 else INK, 2 if (ci in align_right and r) else 0))
                          for ci, v in enumerate(row)])
        t = Table(cells, colWidths=widths)
        st = [("BACKGROUND", (0, 0), (-1, 0), head_col or self.col),
              ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
              ("LINEBELOW", (0, 0), (-1, -1), 0.4, Color(0.8, 0.8, 0.84)),
              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        if zebra:
            for r in range(2, len(data), 2):
                st.append(("BACKGROUND", (0, r), (-1, r), Color(0.95, 0.96, 0.98)))
        t.setStyle(TableStyle(st))
        _, h = t.wrap(sum(widths), 10000)
        t.drawOn(self.c, x, self.y - h)
        self.y -= h + 12
        return h

    def arrow(self, x0, y0, x1, y1, col=RED, w=2.2):
        import math
        c = self.c
        c.setStrokeColor(col)
        c.setFillColor(col)
        c.setLineWidth(w)
        c.setLineCap(1)
        a = math.atan2(y1 - y0, x1 - x0)
        hx, hy = x1 - 9 * math.cos(a), y1 - 9 * math.sin(a)
        c.line(x0, y0, hx, hy)
        p = c.beginPath()
        p.moveTo(x1, y1)
        p.lineTo(hx + 5 * math.sin(a), hy - 5 * math.cos(a))
        p.lineTo(hx - 5 * math.sin(a), hy + 5 * math.cos(a))
        p.close()
        c.drawPath(p, stroke=0, fill=1)


# ---------------------------------------------------------------- 図
def diamond(b, cx, cy, s, labels=True, throws=False, runs=False):
    """ダイヤモンド（ホームが下）。s = ホームから二塁までの半分"""
    c = b.c
    home, first, second, third = (cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)
    c.setFillColor(GREEN_L)
    c.setStrokeColor(GREEN)
    c.setLineWidth(1)
    c.circle(cx, cy, s * 1.55, stroke=1, fill=1)
    p = c.beginPath()
    p.moveTo(*home)
    p.lineTo(*first)
    p.lineTo(*second)
    p.lineTo(*third)
    p.close()
    c.setFillColor(Color(0.93, 0.80, 0.62))
    c.setStrokeColor(white)
    c.setLineWidth(3)
    c.drawPath(p, stroke=1, fill=1)
    c.setFillColor(Color(0.86, 0.72, 0.52))
    c.circle(cx, cy - s * 0.12, s * 0.16, stroke=0, fill=1)
    for (bx, by), nm in ((home, "本塁"), (first, "一塁"), (second, "二塁"), (third, "三塁")):
        c.setFillColor(white)
        c.setStrokeColor(GRAY)
        c.setLineWidth(1)
        c.rect(bx - 6, by - 6, 12, 12, stroke=1, fill=1)
        if labels:
            c.setFillColor(INK)
            c.setFont("GB", 10)
            dx = {"一塁": 26, "三塁": -26}.get(nm, 0)
            dy = {"本塁": -22, "二塁": 14}.get(nm, -4)
            c.drawCentredString(bx + dx, by + dy, nm)
    return home, first, second, third


def keypad(b, x, y, s, labels=("↑", "↓", "←", "→")):
    """十字キー"""
    c = b.c
    c.setFillColor(Color(0.25, 0.25, 0.3))
    c.roundRect(x - s * 0.5, y - s * 1.5, s, s * 3, 4, stroke=0, fill=1)
    c.roundRect(x - s * 1.5, y - s * 0.5, s * 3, s, 4, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("GB", s * 0.55)
    c.drawCentredString(x, y + s * 0.85, labels[0])
    c.drawCentredString(x, y - s * 1.2, labels[1])
    c.drawCentredString(x - s * 1.05, y - s * 0.18, labels[2])
    c.drawCentredString(x + s * 1.05, y - s * 0.18, labels[3])


def flow_box(b, x, y, w, h, text, col, size=10):
    c = b.c
    c.setFillColor(col)
    c.roundRect(x, y, w, h, 8, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("GB", size)
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        c.drawCentredString(x + w / 2, y + h / 2 + (len(lines) / 2 - i - 0.75) * size * 1.25, ln)


# ================================================================ 各ページ
def p_cover(b):
    c = b.c
    b.page += 1
    b.toc.append((b.page, 0, "表紙"))
    # 夜空と球場
    c.setFillColor(Color(0.07, 0.10, 0.28))
    c.rect(0, 0, W, H, stroke=0, fill=1)
    import random
    rnd = random.Random(7)
    for _ in range(70):
        art.star(c, rnd.uniform(20, W - 20), rnd.uniform(H * 0.45, H - 20), rnd.uniform(1.5, 4), Color(1, 1, 0.8))
    c.setFillColor(GREEN)
    c.ellipse(-120, -260, W + 120, 360, stroke=0, fill=1)
    c.setFillColor(DIRT)
    p = c.beginPath()
    p.moveTo(W / 2, 40)
    p.lineTo(W / 2 + 190, 190)
    p.lineTo(W / 2, 320)
    p.lineTo(W / 2 - 190, 190)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(GREEN)
    p = c.beginPath()
    p.moveTo(W / 2, 90)
    p.lineTo(W / 2 + 120, 190)
    p.lineTo(W / 2, 280)
    p.lineTo(W / 2 - 120, 190)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    # タイトル（ゲームの字）
    b.image(font_text_image("MSX", (255, 230, 60), (18, 26, 72), 12), W / 2 - 108, H - 120, 216)
    b.image(font_text_image("STADIUM", (255, 255, 255), (18, 26, 72), 12), W / 2 - 252, H - 230, 504)
    c.setFillColor(RED)
    c.roundRect(W / 2 - 170, H - 300, 340, 40, 20, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("GB", 22)
    c.drawCentredString(W / 2, H - 288, "プレイングマニュアル")
    c.setFont("G", 12)
    c.setFillColor(Color(0.85, 0.88, 1))
    c.drawCentredString(W / 2, H - 326, "MSX2 用 野球ゲーム ／ 操作説明書")
    # キャラクター
    art.player(c, W / 2 - 170, 120, 170, "bat", cap=RED)
    art.player(c, W / 2 + 165, 120, 170, "pitch", cap=NAVY, flip=True)
    art.player(c, W / 2, 210, 130, "catch", cap=Color(0.95, 0.55, 0.1))
    art.ballkun(c, W / 2 + 40, 470, 36, "open", "up")
    c.setFillColor(white)
    c.setFont("G", 9)
    c.drawCentredString(W / 2, 22, "ファンメイド作品（オリジナルの絵・曲・チーム）")
    c.showPage()


def p_toc(b, entries):
    b.begin(0, "もくじ")
    c = b.c
    col_x = [M, W / 2 + 8]
    y0 = b.y
    per = (len(entries) + 1) // 2
    step = min(22.5, (y0 - 60) / per)
    for i, (pg, chap, title) in enumerate(entries):
        x = col_x[i // per]
        y = y0 - (i % per) * step
        name, colr = CHAPTERS[chap]
        c.setFillColor(colr)
        c.roundRect(x, y - 13, 52, 16, 6, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("GB", 8.5)
        c.drawCentredString(x + 26, y - 9, name)
        c.setFillColor(INK)
        c.setFont("G", 10.5)
        c.drawString(x + 58, y - 9.5, title)
        c.setFont("GB", 10.5)
        c.drawRightString(x + W / 2 - M - 14, y - 9.5, str(pg))
        c.setStrokeColor(Color(0.8, 0.8, 0.84))
        c.setDash(1, 2)
        tw = c.stringWidth(title, "G", 10.5)
        c.line(x + 62 + tw, y - 9, x + W / 2 - M - 32, y - 9)
        c.setDash()
    b.end()


PAGEREF = {}                    # 1 回目に数えたページ番号（見出し → ページ）


def pg(title):
    """見出しのページ番号（1 回目はまだわからないので 99）"""
    if title.startswith("TEAM"):
        teams = [p for p, ch, t in PAGEREF.get("_all", []) if ch == 7]
        return str(min(teams)) if teams else "99"
    return str(PAGEREF.get(title, 99))


def p_intro(b):
    b.begin(0, "このゲームについて")
    b.shot("title", W - M - 230, b.y, 230, "タイトル画面")
    b.para("「<b>MSX STADIUM</b>」は、MSX2 で遊べる野球ゲームです。打って、投げて、守って、走る。"
           "ファミコン時代の野球ゲームのような、手軽でテンポのよい遊び心地をめざして作りました。", w=W - 2 * M - 250, size=12)
    b.para("絵・曲・チーム・選手は、すべてこのゲームのために作ったオリジナルです。", w=W - 2 * M - 250)
    b.y = H - 112 - 230 * 212 / 256 - 40
    b.head("このゲームの特ちょう")
    b.bullets(["8 つのチーム。それぞれ打撃や投手に「くせ」があります（" + pg("TEAM") + " ページから）",
               "1 人で COM と対戦、2 人で対戦、COM 同士の試合の観戦ができます",
               "3 回・6 回・9 回の試合。同点なら延長戦（最大 3 回）",
               "打つときはタイミングとバットの芯、投げるときは球の速さと変化で勝負",
               "守備は自動で追いかけ、送球や走塁は自分で決められます",
               "代打・リリーフで作戦を立てられます。バントもできます",
               "4 人の審判が、ストライク・アウト・セーフ・ファウルを身ぶりで伝えます",
               "タイトル画面の SPEED で、試合ぜんたいの速さを 5 段階に変えられます",
               "EDIT でチーム・選手を書きかえ、6 チームのトーナメントも。フロッピーディスクに保存して続きから遊べます",
               "COM は挟殺プレー（ランダウン）も、実際の野球の定石どおりに"])
    b.tip("こんにちは！ボクは案内役の<b>ボールくん</b>。このマニュアルでは、はじめての人でも遊べるように、"
          "1 つずつ順番に説明するよ。ページの下の番号を見ながら読んでね。")
    b.end()


def p_friends(b):
    b.begin(0, "なかまたち")
    c = b.c
    y = b.y
    art.ballkun(c, M + 60, y - 70, 34, "smile", "wave")
    art.player(c, M + 210, y - 140, 120, "wave", cap=NAVY)
    art.player(c, M + 350, y - 140, 120, "cheer", cap=RED)
    art.player(c, M + 470, y - 140, 120, "ready", cap=Color(0.95, 0.55, 0.1))
    for x, nm in ((M + 60, "ボールくん"), (M + 210, "キャップくん"), (M + 350, "キャップちゃん"), (M + 470, "グラブくん")):
        c.setFillColor(INK)
        c.setFont("GB", 11)
        c.drawCentredString(x, y - 162, nm)
    b.y = y - 180
    b.para("<b>ボールくん</b>：このマニュアルの案内役。大事なところで「ひとこと」を言います。<br/>"
           "<b>キャップくん・キャップちゃん</b>：打つこと・投げることのコツを教えてくれます。<br/>"
           "<b>グラブくん</b>：守備が大好き。ゴロもフライもおまかせ。", size=11)
    b.head("ゲームの中の選手たち（ドット絵）")
    team = {'P': (6, 1, 1), 'U': (7, 7, 7)}
    p1 = sprite_sheet(SP.CHIBI, ['STAND_D', 'RUN_D1', 'RUN_D2', 'STAND_L', 'RUN_L1', 'RUN_L2', 'THROW_L', 'CATCH', 'READY_D', 'CROUCH_B', 'SLIDE_L'],
                      16, team, scale=8)
    h = b.image(p1, M, b.y, W - 2 * M, frame=True)
    b.y -= h + 16
    p2 = sprite_sheet(SP.BATTER, SP.BATTER_ORDER[:7], 24, team, scale=8)
    p3 = sprite_sheet(SP.PITCHER, SP.PITCHER_ORDER, 24, {'P': (1, 2, 6), 'U': (7, 7, 7)}, scale=8)
    h2 = b.image(p2, M, b.y, 270, frame=True)
    h3 = b.image(p3, M + 290, b.y, 205, frame=True)
    b.y -= max(h2, h3) + 14
    b.para("上：守備・走者（正面・横・投げる・捕る・構える・捕手・すべり込み）。下：打者（構え→踏み込み→引き→振り出し→当たる瞬間→振り抜き→振り終わり）と投手"
           "（セット→足を上げる→踏み出して投げる）。帽子と 2 色のユニフォームはチームの色になります。", size=10, color=GRAY)
    b.end()


def p_need(b):
    b.begin(1, "用意するもの")
    b.head("動く機種")
    b.table([["機種", "遊べる？", "メモ"],
              ["MSX2 / MSX2+ / MSX turbo R", "○", "RAM 64KB 以上"],
              ["MSX（MSX1）", "×", "「MSX2 専用」と出て止まります"],
              ["エミュレーター（openMSX・WebMSX・blueMSX）", "○", "MSX2 の機種を選んでください"]],
             [230, 60, 221])
    b.head("ROM ファイル")
    b.para("ゲームは <b>MSXSTADIUM.ROM</b>（512KB = 4M ビット）という 1 つのファイルです。"
           "「メガROM」という大きなカートリッジの形式（<b>ASCII16</b>）で作ってありますが、"
           "ASCII8 として読み込まれても、起動したときに自分で見分けて動きます。")
    b.para("<b>フロッピーディスクドライブ</b>のある機種では、EDIT したチームとトーナメントの途中経過をディスクに保存できます"
           "（" + pg("続きから・セーブについて") + " ページ）。ドライブがなくても試合とトーナメントは遊べます（カートリッジの SRAM には対応していません）。")
    b.note("ROM ファイルの名前は変えても動きます。ただし中身を書き換えると動かなくなることがあります。", "ちゅうい", RED_L, RED)
    b.head("確認した環境")
    b.bullets(["openMSX：C-BIOS MSX2、Panasonic FS-A1 / FS-A1GT、Sony HB-F1XD / HB-F1XV、Philips NMS 8245",
               "WebMSX 6.0"])
    b.tip("どの機種でも同じように遊べるよう、画面の書き換えの速さまで実機に合わせて確かめてあるよ。", mood="smile")
    b.end()


def p_emu(b):
    b.begin(1, "エミュレーターで遊ぶ")
    b.head("openMSX")
    b.para("コマンドで起動するときは、次のように打ちます（機種は MSX2 以上なら何でも）。")
    b.box(M, b.y, W - 2 * M, 30, Color(0.12, 0.13, 0.16))
    b.c.setFillColor(Color(0.6, 1, 0.6))
    b.c.setFont("G", 11)
    b.c.drawString(M + 14, b.y - 19, "openmsx -machine Sony_HB-F1XD -cart MSXSTADIUM.ROM -diska save")
    b.y -= 44
    b.para("ディスクドライブのある機種（HB-F1XD など）で <b>-diska フォルダ名</b>（か .dsk ファイル）を付けると、そこがフロッピーディスクになり、"
           "EDIT とトーナメントを保存できます（付けなくても遊べます）。")
    b.head("WebMSX（ブラウザー）")
    b.bullets(["GitHub のリポジトリ（github.com/1re1/Baseball）の README にある「WebMSX（C-BIOS 版）で MSX STADIUM を遊ぶ」のリンクを開くと、"
               "WebMSX の C-BIOS 版（webmsx.org/cbios/）が ROM を読み込んですぐ始まります（C-BIOS 版はディスクがないので保存できません）",
               "保存もしたいときは「ディスク付きで遊ぶ」のリンクで、ROM と保存用の空のディスクを読み込みます",
               "ROM ファイルを WebMSX の画面にドラッグ＆ドロップしても遊べます",
               "WebMSX は ASCII8 と判定しますが、そのまま動きます",
               "ドラッグ＆ドロップで始めたときは、保存する前に画面下のディスクのアイコン（Drive A）から空のディスクを入れてください",
               "保存した中身はブラウザーの中のディスクだけにあります。続きを残すときは、ディスクのメニューからディスクイメージを保存してください"], size=10)
    b.head("blueMSX")
    b.bullets(["メニューの「ファイル」→「カートリッジスロット 1」→ ROM を選ぶ",
               "うまく動かないときは、マッパーの種類を「ASCII16」にしてください"])
    b.head("実機で遊ぶ")
    b.para("Carnivore2・MegaFlashROM など、メガROM が使えるカートリッジに <b>ASCII16</b> として書き込みます。"
           "書き込み方は、それぞれのカートリッジの説明書を見てください。")
    b.tip("エミュレーターでは「速度 100%」で遊ぶのがおすすめ。速すぎると打つタイミングが合わなくなるよ。", size=10)
    b.end()


def p_keys1(b):
    b.begin(1, "キーとジョイスティック（1P）")
    c = b.c
    y = b.y
    # キーボードの絵
    b.box(M, y, W - 2 * M, 190, Color(0.93, 0.93, 0.95), Color(0.75, 0.75, 0.8))
    kx, ky = M + 22, y - 60
    b.keycap(kx, ky, 46, 30, "F1", "SELECT", YELLOW_L)
    b.keycap(kx + 360, ky, 70, 30, "RETURN", "START", YELLOW_L)
    b.keycap(kx + 60, ky - 52, 34, 30, "Z", "A", GREEN_L)
    b.keycap(kx + 98, ky - 52, 34, 30, "X", "B", RED_L)
    b.keycap(kx + 188, ky - 52, 34, 30, "B", "B", RED_L)
    b.keycap(kx + 230, ky - 52, 34, 30, "M", "B", RED_L)
    b.keycap(kx + 40, ky - 100, 220, 30, "スペース", "A", GREEN_L)
    keypad(b, kx + 405, ky - 75, 26)
    c.setFillColor(INK)
    c.setFont("GB", 10)
    c.drawCentredString(kx + 405, ky - 128, "カーソルキー")
    b.y = y - 204
    b.table([["ボタン", "キーボード", "ジョイスティック", "おもな使い方"],
             ["十字", "カーソルキー", "スティック", "打者・選手・カーソルを動かす"],
             ["A", "スペース・Z", "トリガ A", "打つ・投げる・送球・決定"],
             ["B", "B・X・M", "トリガ B", "バントの構え・走る（進塁・盗塁）・ボールを持って走る"],
             ["SELECT", "F1", "（SELECT）", "代打・リリーフ"],
             ["START", "RETURN", "—", "一時停止・もう一度で再開"]],
            [62, 96, 92, 261])
    b.tip("この先は、ボタンの名前を <b>A</b>・<b>B</b> と書くよ。キーボードならスペースが A、B キー（X・M でも）が B だね。")
    b.end()


def p_keys2(b):
    b.begin(1, "2P のキー・一時停止")
    b.head("2P（1P VS 2P のとき）")
    c = b.c
    y = b.y
    b.box(M, y, W - 2 * M, 120, Color(0.93, 0.93, 0.95), Color(0.75, 0.75, 0.8))
    keypad(b, M + 70, y - 60, 24, ("W", "S", "A", "D"))
    b.keycap(M + 170, y - 50, 34, 30, "G", "A", GREEN_L)
    b.keycap(M + 210, y - 50, 34, 30, "H", "B", RED_L)
    b.keycap(M + 280, y - 50, 46, 30, "F2", "SELECT", YELLOW_L)
    b.keycap(M + 340, y - 50, 50, 30, "TAB", "START", YELLOW_L)
    c.setFillColor(INK)
    c.setFont("G", 10)
    c.drawString(M + 170, y - 92, "ジョイスティック 2 も使えます（十字・トリガ A・B）")
    b.y = y - 134
    b.table([["ボタン", "キーボード", "ジョイスティック"],
             ["十字", "W（↑）・S（↓）・A（←）・D（→）", "スティック 2"],
             ["A", "G", "トリガ A"], ["B", "H", "トリガ B"], ["SELECT", "F2", "—"], ["START", "TAB", "—"]],
            [80, 260, 171])
    b.head("一時停止")
    b.para("試合中に <b>START</b>（RETURN）を押すと一時停止。もう一度押すと続きから始まります。")
    b.head("COM 同士の試合（デモ）を止める")
    b.para("観戦中やデモ試合のときは、<b>A</b> か <b>START</b> でタイトル画面に戻ります。")
    b.tip("2 人で遊ぶときは、1 つのキーボードを 2 人で使えるよう、左側に 2P のキーがまとまっているよ。")
    b.end()


def p_title(b):
    b.begin(1, "タイトル画面")
    b.shot("title_mode", M, b.y, 250, "↑↓ で行を選ぶ（● が選んだモード）")
    b.shot("title_speed", W - M - 250, b.y, 250, "SPEED の行で ←→")
    b.y -= 250 * 212 / 256 + 36
    b.head("STEP 1　モードを選ぶ（↑↓）")
    b.table([["モード", "内容"],
             ["1P VS COM", "1P が先攻、COM が後攻。両方のチームを 1P が選びます"],
             ["1P VS 2P", "1P が先攻、2P が後攻。それぞれ自分のチームを選びます"],
             ["COM VS COM", "COM 同士の試合を観戦します"],
             ["EDIT", "チーム・選手を書きかえて保存（" + pg("EDIT モード") + " ページ）"],
             ["TOURNAMENT", "6 チームのトーナメント（" + pg("トーナメント（選ぶ・組み合わせ）") + " ページ）"],
             ["CONTINUE", "保存したトーナメントの続きから（" + pg("続きから・セーブについて") + " ページ）"]], [110, 401], size=9.5)
    b.head("STEP 2　イニング数・SPEED を選ぶ（←→）")
    b.para("イニングは 3 回・6 回・9 回。<b>SPEED</b> は試合ぜんたいの動きの速さで 1〜5"
           "（1 = 60%・2 = 70%・<b>3 = 80%（はじめ）</b>・4 = 90%・5 = 100%）。投球・打球・送球・走者・守備が同じ割合で速く／遅くなります。",
           size=10.5)
    b.head("STEP 3　スペース（A）で決定")
    b.note("タイトルで 10 秒ほど何もしないと、COM 同士の<b>デモ試合</b>が始まります。A か START でタイトルに戻ります。", "メモ", NAVY_L, NAVY)
    b.end()


def p_select(b):
    b.begin(1, "チームセレクト")
    b.shot("select2", M, b.y, 240, "先攻（センコウ）のチームを選ぶ")
    b.shot("select3", W - M - 240, b.y, 240, "後攻（コウコウ）のチームを選ぶ")
    b.y -= 240 * 212 / 256 + 36
    b.head("選び方")
    b.bullets(["<b>↑↓</b> でチームを選ぶ（左の ＞ が先攻、右の ＜ が後攻）",
               "<b>A</b> で決定。先攻 → 後攻の順に選びます",
               "後攻を選んでいるときに <b>B</b> を押すと、先攻を選び直せます",
               "画面の下に、選んだチームのユニフォームの選手が出ます"])
    b.head("8 つのチーム")
    b.table([["略称", "チーム", "とくちょう"],
             ["DOL", "ドルフィンズ", "よく当てる打線・速球派"], ["FAL", "ファルコンズ", "長打の打線"],
             ["THU", "サンダース", "長打・技巧派の投手"], ["COM", "コメッツ", "足が速い"],
             ["WOL", "ウルブズ", "バランス・速球派"], ["ROC", "ロケッツ", "長打の打線"],
             ["SHA", "シャークス", "足が速い・技巧派"], ["STA", "スターズ", "強打の特別チーム"]],
            [60, 130, 321])
    b.end()


def p_lineup(b):
    b.begin(1, "スターティングオーダー")
    b.shot("lineup", M + 40, b.y, 430)
    b.y -= 430 * 212 / 256 + 24
    b.para("両チームの打順（1〜9 番）が出ます。名前の右は<b>打率</b>、<b>L</b> は左打ち。"
           "9 番は投手で、<b>P</b> の右は投手の<b>球速（km/h）</b>です。")
    b.bullets(["スペース（A）で試合が始まります（「プレイボール」）",
               "打率が高い打者ほど、バットにボールが当たる範囲が少し広くなります"])
    b.end()


def p_flow(b):
    b.begin(1, "試合の流れ")
    c = b.c
    steps = [("タイトル", GRAY), ("チームセレクト", GRAY), ("オーダー", GRAY), ("プレイボール", GREEN),
             ("打席\n（投げる・打つ）", RED), ("打球を追う\n（守る・走る）", Color(0.13, 0.45, 0.75)),
             ("3 アウトで\nチェンジ", NAVY), ("スコアボード", NAVY), ("ゲームセット", Color(0.55, 0.25, 0.65))]
    x0, y = M + 40, b.y - 10
    for i, (t, col) in enumerate(steps):
        yy = y - i * 58
        flow_box(b, x0, yy - 40, 180, 40, t, col, 11)
        if i < len(steps) - 1:
            b.arrow(x0 + 90, yy - 42, x0 + 90, yy - 56, GRAY, 2)
    # くり返し
    b.arrow(x0 + 184, y - 5 * 58 - 20, x0 + 230, y - 5 * 58 - 20, RED, 1.6)
    b.arrow(x0 + 230, y - 5 * 58 - 20, x0 + 230, y - 4 * 58 - 20, RED, 1.6)
    b.arrow(x0 + 230, y - 4 * 58 - 20, x0 + 184, y - 4 * 58 - 20, RED, 1.6)
    c.setFillColor(RED)
    c.setFont("GB", 10)
    c.drawString(x0 + 238, y - 4.5 * 58 - 24, "アウトが 3 つになるまでくり返し")
    b.arrow(x0 + 184, y - 7 * 58 - 20, x0 + 270, y - 7 * 58 - 20, NAVY, 1.6)
    b.arrow(x0 + 270, y - 7 * 58 - 20, x0 + 270, y - 4 * 58 - 10, NAVY, 1.6)
    c.setFillColor(NAVY)
    c.drawString(x0 + 278, y - 6 * 58 - 10, "次の回へ（表 → 裏 → 次の回の表）")
    art.player(c, W - M - 70, y - 520, 110, "cheer", cap=RED)
    b.y = y - 9 * 58 - 10
    b.para("1 回の表は先攻チームの攻撃、裏は後攻チームの攻撃です。最後の回が終わって点の多いチームの勝ち。"
           "後攻が最後の回の表の終わりでリードしていれば、そこで試合終了です。", size=10.5)
    b.end()


def p_screen(b):
    b.begin(1, "打席の画面の見かた")
    x, w = M + 20, 470
    top = b.y
    hh = b.shot("atbat1p", x, top, w)
    s = w / 256.0
    for n, (px, py) in enumerate([(20, 10), (236, 10), (24, 204), (240, 204), (128, 136), (128, 186), (128, 60)], 1):
        b.badge(n, x + px * s, top - py * s, RED, 10)
    b.y = top - hh - 8
    b.table([["番号", "場所", "わかること"],
             ["1", "左上", "両チームの略称と得点、いまの回（例：1回表）"],
             ["2", "右上", "投手の名前、球速（km/h）、スタミナ（ST）"],
             ["3", "左下", "打順と打者の名前、打率と本塁打の数"],
             ["4", "右下", "ボール（B）・ストライク（S）・アウト（O）のランプ"],
             ["5", "マウンド", "投手。ここから投げます"],
             ["6", "本塁", "打者（バッターボックスの中）と捕手"],
             ["7", "内野", "一塁手・二塁手・遊撃手・三塁手（構えて待つ）"]],
            [38, 70, 403])
    b.para("黒い上着の人は<b>審判</b>（球審・一塁・二塁・三塁の 4 人）。一塁・三塁の審判は、内野の画面の右はし・左はしに見えます。", size=10, color=GRAY)
    b.end()


def p_hud1(b):
    b.begin(1, "画面の四すみ ①")
    b.head("左上：得点と回")
    h = b.image(crop_big("atbat1p", (0, 0, 40, 24), 8, "tl"), M, b.y, 200, frame=True)
    b.para("1 行目が先攻、2 行目が後攻のチーム（略称と得点）。<br/>3 行目は回です。"
           "「<b>1回表</b>」は 1 回の表（先攻の攻撃）、「<b>1回裏</b>」は 1 回の裏（後攻の攻撃）。",
           x=M + 220, w=W - 2 * M - 220, y=b.y)
    b.y = min(b.y, H - 112 - h - 70)
    b.head("右上：投手")
    h = b.image(crop_big("atbat1p", (216, 0, 256, 24), 8, "tr"), M, b.y, 200, frame=True)
    b.para("1 行目：投手の名前<br/>2 行目：いま投げた球の<b>速さ</b>（km/h）<br/>3 行目：<b>スタミナ</b>（ST、0〜99）。"
           "投げるたびに減り、30 より少なくなると球が遅くなります。",
           x=M + 220, w=W - 2 * M - 220, y=b.y)
    b.y = min(b.y, H - 112 - 2 * h - 160)
    b.tip("どちらも、必要な文字だけを四すみに小さくまとめてあるから、球場がひろく見えるよ。")
    b.end()


def p_hud2(b):
    b.begin(1, "画面の四すみ ②")
    b.head("左下：打者（いつも 7 文字の幅）")
    h = b.image(crop_big("atbat1p", (0, 196, 56, 212), 8, "bl"), M, b.y, 220, frame=True)
    b.para("1 行目：<b>打順</b>と<b>名前</b>（例：1フジタ）<br/>2 行目：<b>打率</b>と<b>本塁打</b>（例：.266H 3 → 打率 2 割 6 分 6 厘、本塁打 3 本）。"
           "本塁打が 10 本以上なら「.123H12」のように出ます。",
           x=M + 240, w=W - 2 * M - 240, y=b.y)
    b.y = min(b.y, H - 112 - h - 80)
    b.head("右下：カウント（B・S・O）")
    h = b.image(crop_big("so_strike", (224, 188, 256, 212), 8, "br"), M, b.y, 150, frame=True)
    b.para("<b>B</b>（緑）ボール 3 つまで。4 つでフォアボール。<br/>"
           "<b>S</b>（黄）ストライク 2 つまで。3 つで三振（アウト）。<br/>"
           "<b>O</b>（赤）アウト 2 つまで。3 つでチェンジ。",
           x=M + 170, w=W - 2 * M - 170, y=b.y)
    b.y = min(b.y, H - 112 - h - 160)
    b.note("ファウルはストライクに数えますが、2 ストライクからはいくらファウルしても三振にはなりません。")
    b.end()


# ---------------------------------------------------------------- 打つ
def p_bat_box(b):
    b.begin(2, "打者の構えと動き方")
    art.player(b.c, W - M - 70, b.y - 190, 150, "bat", cap=RED)
    b.para("打席では、<b>十字キー</b>で打者を動かせます。動けるのは<b>バッターボックスの中</b>だけ。"
           "足はボックスの中か、白い線の上まで（はみ出しません）。", w=W - 2 * M - 150, size=12)
    b.bullets(["<b>←→</b>：ホームベースに近づく・はなれる",
               "<b>↑↓</b>：前（投手のほう）・後ろ（捕手のほう）"], w=W - 2 * M - 150)
    b.y -= 10
    h = b.image(crop_big("atbat1p", (100, 156, 160, 200), 7, "box"), M, b.y, 300, frame=True)
    b.para("ホームベースに近づくと<b>外角</b>（遠い球）に、はなれると<b>内角</b>（近い球）にバットの芯が合います。"
           "前に出ると、早めのタイミングで打つことになります。", x=M + 320, w=W - 2 * M - 320, y=b.y)
    b.y = min(b.y, H - 112 - 200 - h)
    b.note("左打ちの打者は、右のバッターボックスに立ちます（オーダーで <b>L</b> がついている打者）。", "メモ", NAVY_L, NAVY)
    b.tip("投手が投げる前に立つ場所を決めておこう。投げたあとでも少しなら動けるよ。", who="kun")
    b.end()


def p_swing(b):
    b.begin(2, "スイングのタイミング")
    b.para("<b>A</b> を押すとバットを振ります。ボールが打者の前に来たときに当たれば打球になります。", size=12)
    c = b.c
    y = b.y - 10
    # タイミングの図
    labels = [("はやい", "引っぱり", "右打ちならレフト方向"), ("ちょうど", "センター", "まっすぐ前へ"), ("おそい", "流し打ち", "右打ちならライト方向")]
    for i, (t, d, e) in enumerate(labels):
        x = M + i * 172
        b.box(x, y, 160, 120, [RED_L, YELLOW_L, NAVY_L][i], [RED, YELLOW, NAVY][i])
        c.setFillColor(INK)
        c.setFont("GB", 15)
        c.drawCentredString(x + 80, y - 30, t)
        c.setFont("GB", 12)
        c.drawCentredString(x + 80, y - 60, "→ " + d)
        c.setFont("G", 10)
        c.drawCentredString(x + 80, y - 86, e)
    b.y = y - 140
    b.head("振る絵の順番（7 コマ）")
    b.para("スイングは必ず <b>構え → 踏み込み → 引き → 振り出し → 当たる瞬間 → 振り抜き → 振り終わり</b> の順に、なめらかに動きます。"
           "バットの長さは打者の背の約半分（本物と同じくらいの比）。当たった瞬間は、バットとボールが合わさった絵が少し止まって見えます。")
    p2 = batter_bat(SP.BATTER_ORDER[:7], scale=6)
    h = b.image(p2, M, b.y, W - 2 * M, frame=True)
    b.y -= h + 16
    b.tip("タイミングは「ボールがバッターボックスの少し前に来たら」。最初は真ん中を打ち返すつもりで！", who="chan")
    b.end()


def p_sweet(b):
    b.begin(2, "バットの芯と打球の種類")
    c = b.c
    y = b.y - 20
    # バットの図
    x0, x1 = M + 40, W - M - 40
    zones = [(0.0, 0.22, Color(0.6, 0.6, 0.65), "根っこ", "弱いゴロ"), (0.22, 0.48, Color(0.35, 0.6, 0.85), "手元寄り", "ゴロ"),
             (0.48, 0.78, RED, "芯", "ライナー・ホームラン"), (0.78, 1.0, Color(0.95, 0.6, 0.15), "先", "フライ")]
    for a0, a1, col, nm, res in zones:
        xa, xb = x0 + (x1 - x0) * a0, x0 + (x1 - x0) * a1
        c.setFillColor(col)
        c.rect(xa, y - 56, xb - xa, 22, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("GB", 12)
        c.drawCentredString((xa + xb) / 2, y - 80, nm)
        c.setFont("G", 10)
        c.drawCentredString((xa + xb) / 2, y - 96, res)
    art.bat(c, x0, y - 22, x1, y - 22, 7)
    c.setFillColor(GRAY)
    c.setFont("G", 9)
    c.drawString(x0 - 10, y - 4, "手元（打者の手）")
    c.drawRightString(x1 + 10, y - 4, "先")
    b.y = y - 116
    b.para("ボールがバットのどこに当たったかで、打球が変わります。芯の真ん中に当たると、たまに"
           "<b>会心の当たり</b>（大きなフライ）になり、ホームランが出やすくなります。パワーのある打者ほど起こりやすい。")
    b.head("打球の向き")
    b.para("左右の向きは<b>バットの角度</b>で決まります。振り始めてから長いほど（バットが前に出ているほど）、"
           "またボールを前でとらえるほど引っぱりに、振り遅れると流し打ちになります。")
    b.head("当たる瞬間のキー")
    b.table([["当たる瞬間に押す", "打球"],
             ["↓", "打ち上げる（ほとんどフライになり、高く上がる。犠牲フライに）"],
             ["↑", "たたきつける（ライナー・ゴロが多くなる）"],
             ["→ ／ ←", "少し右方向 ／ 左方向へ（バットの角度のほうが大きく効きます）"]], [150, 361], size=10)
    b.head("打球の強さ")
    b.bullets(["芯に近いほど強い打球（遠いと弱くなる）",
               "打者の<b>パワー</b>が大きいほど強い",
               "<b>速い球</b>を打ち返すと打球も少し速くなる。ただし非力な打者は速い球に<b>押されて</b>弱くなり、↓ だとポップフライになりやすい"])
    b.tip("外角の球はベースに近づいて、内角の球ははなれて、芯でとらえよう！ ランナー三塁なら ↓ で外野フライ！", who="kun")
    b.end()


def p_contact(b):
    b.begin(2, "当たった瞬間（連続写真）")
    b.para("打ったときの画面を 1 フレーム（1/60 秒）ごとに並べました。踏み込み → 水平に振る（当たった瞬間は少し止まる）→ 打球が飛ぶ画面へ。", size=11)
    c = b.c
    names = ["contact_%d" % k for k in range(12)]
    cw = (W - 2 * M - 30) / 4
    y = b.y
    for i, nm in enumerate(names):
        x = M + (i % 4) * (cw + 10)
        yy = y - (i // 4) * (cw * 0.75 + 22)
        path = crop_big(nm, (88, 140, 168, 200), 5, "ct")
        b.image(path, x, yy, cw, cw * 0.75, frame=True)
        c.setFillColor(GRAY)
        c.setFont("G", 8.5)
        c.drawCentredString(x + cw / 2, yy - cw * 0.75 - 12, "%d" % (i + 1))
    b.y = y - 3 * (cw * 0.75 + 22) - 6
    b.note("バットの絵の長さと、ボールに当たる範囲は同じです。バットに重なって見えたのに空振り、ということはありません。")
    b.end()


def p_bunt(b):
    b.begin(2, "バント")
    art.player(b.c, W - M - 90, b.y - 170, 140, "bunt", cap=NAVY)
    b.para("<b>B を押している間</b>、バントの構えになります（人が打つときだけ。キーボードは B・X・M キー、ジョイパッドは B ボタン）。"
           "ボールがバットに当たると、ころころと転がるゴロになります。", w=W - 2 * M - 170, size=12)
    b.para("構えは本物のバントと同じ形：投手のほうへ体を向けて腰を落とし、ひざを曲げて足を広げ、"
           "<b>バットを両手で持って胸の高さで水平に</b>前へ出します（下の手はグリップ、上の手はバットの中ほど）。", w=W - 2 * M - 170, size=10.5)
    h = b.image(batter_bat(["STANCE", "BUNT"], scale=7), M, b.y, 260, frame=True)
    b.para("左：ふつうの構え<br/>右：バントの構え", x=M + 280, w=150, y=b.y - 20, size=10.5)
    b.y -= h + 14
    b.bullets(["当たる瞬間の <b>←→</b> で、三塁側・一塁側へ転がせます",
               "使いどころ：ランナーを次の塁へ進めたいとき（送りバント）、足の速い打者で内野安打をねらうとき"])
    b.head("ちゅうい")
    b.bullets(["構えたままボールが来たら、当たらなくてもストライク。<b>B をはなしてバットを引けば</b>見のがしと同じ判定（ベースを外れればボール）",
               "2 ストライクからのバントのファウルは三振です（スリーバント失敗）",
               "方向キーを押しながらの B は盗塁です（「盗塁」のページ）"])
    b.tip("バントは打球が弱いぶん、守備がすぐに捕りに来るよ。足の速いランナーのときに使おう。", who="kun")
    b.end()


def p_eye(b):
    b.begin(2, "ストライクとボールの見きわめ")
    b.para("振らなかった球は、捕手が捕ったときに判定されます。", size=12)
    strike_diagram(b)
    b.bullets(["ボールが<b>ホームベースに 1 ドットでもかかれば ストライク</b>",
               "かからなければ <b>ボール</b>。4 つでフォアボール（一塁へ）",
               "振ったら、どこを通っても ストライク（空振り）",
               "打者の体に当たったら デッドボール（一塁へ）"])
    b.tip("ストライクは少しせまめ。ベースの外の球は見のがして、フォアボールをねらうのも作戦だよ。")
    b.end()


def strike_diagram(b):
    c = b.c
    y = b.y - 10
    cx = W / 2
    s = 14
    # ホームベース（五角形）
    p = c.beginPath()
    p.moveTo(cx - 5 * s, y - 20)
    p.lineTo(cx + 5 * s, y - 20)
    p.lineTo(cx + 5 * s, y - 20 - 4 * s)
    p.lineTo(cx, y - 20 - 7 * s)
    p.lineTo(cx - 5 * s, y - 20 - 4 * s)
    p.close()
    c.setFillColor(white)
    c.setStrokeColor(INK)
    c.setLineWidth(2)
    c.drawPath(p, stroke=1, fill=1)
    for bx, ok in ((cx - 2 * s, True), (cx + 6 * s, True), (cx - 7.5 * s, False), (cx + 8.2 * s, False)):
        art.ball(c, bx, y - 20 - 2 * s, 2 * s)
        c.setFillColor(RED if ok else NAVY)
        c.setFont("GB", 12)
        c.drawCentredString(bx, y - 20 - 4.8 * s, "ストライク" if ok else "ボール")
    c.setFillColor(GRAY)
    c.setFont("G", 9)
    c.drawCentredString(cx, y - 6, "（上から見たホームベース。ボールが少しでも重なればストライク）")
    b.y = y - 20 - 7 * s - 20


def p_bat_tips(b):
    b.begin(2, "打撃のコツ Q&A")
    qa = [("ぜんぜん当たりません", "ボールが打者の前に来る少し前に A を押してみましょう。早すぎ・遅すぎは空振りになります。"
                                     "まずは真ん中の球だけ振るようにすると、タイミングがつかめます。"),
          ("ゴロばかりになります", "バットの手元（根っこ）に当たっています。ベースに少し近づいて、芯で当たるようにしましょう。"),
          ("フライばかりになります", "バットの先に当たっています。ベースから少しはなれましょう。"),
          ("速い球が打てません", "ふだんより少し早めに振りましょう。前（↑）に出て構えるのも手です。"),
          ("遅い球で空振りします", "速い球のつもりで振ると早すぎます。球速の表示（右上）を見て、遅い球ならひと呼吸待ちましょう。"),
          ("ホームランを打ちたい", "パワーのある打者で、芯でとらえること。当たる瞬間に ↓ で打ち上げると、会心の当たりが大きく飛びます。")]
    for q, a in qa:
        b.box(M, b.y, W - 2 * M, 22, RED_L)
        b.c.setFillColor(RED)
        b.c.setFont("GB", 11)
        b.c.drawString(M + 10, b.y - 15, "Q. " + q)
        b.y -= 28
        b.para("A. " + a, x=M + 10, w=W - 2 * M - 20, size=10.5, gap=12)
    b.end()


# ---------------------------------------------------------------- 投げる
def p_plate(b):
    b.begin(3, "プレートの位置")
    art.player(b.c, W - M - 80, b.y - 190, 150, "pitch", cap=NAVY, flip=True)
    b.para("投げる前（打席の画面）に <b>←→</b> を押すと、投手がプレートの上で左右に動きます。"
           "投げる位置を変えると、ボールの通る道すじが変わります。", w=W - 2 * M - 170, size=12)
    b.bullets(["右に寄って投げる → 左打者の内角・右打者の外角へ行きやすい",
               "左に寄って投げる → その反対"], w=W - 2 * M - 170)
    b.y -= 20
    b.shot("pitch1", M, b.y, 250, "投げた直後")
    b.shot("pitch2", W - M - 250, b.y, 250, "ホームベースに向かうボール")
    b.y -= 250 * 212 / 256 + 36
    b.head("投げる")
    b.para("<b>A</b> を押すと振りかぶって投げます（約 0.4 秒後にボールがはなれます）。")
    b.tip("投げる位置を毎回変えると、打者はタイミングを合わせにくくなるよ。", who="chan")
    b.end()


def p_speed(b):
    b.begin(3, "球の速さ（↓ 速球・↑ 遅い球）")
    c = b.c
    b.para("投げるときに十字キーの <b>↓</b> か <b>↑</b> を押しておくと、球の速さを変えられます。"
           "A を押すときに押していても、振りかぶっている間に押してもかまいません。", size=12)
    rows = [("↓ を押しながら", "速球", 1.0, RED), ("何も押さない", "ふつう", 0.86, YELLOW), ("↑ を押しながら", "遅い球", 0.62, NAVY)]
    y = b.y - 6
    for i, (k, t, v, col) in enumerate(rows):
        yy = y - i * 58
        b.box(M, yy, 150, 44, white, col)
        c.setFillColor(INK)
        c.setFont("GB", 13)
        c.drawCentredString(M + 75, yy - 27, k)
        c.setFillColor(col)
        c.roundRect(M + 170, yy - 38, 300 * v, 32, 8, stroke=0, fill=1)
        c.setFillColor(white if col != YELLOW else INK)
        c.setFont("GB", 14)
        c.drawString(M + 182, yy - 27, t)
    b.y = y - 3 * 58 - 6
    b.table([["", "球速（例：最高 146km/h・最低 110km/h の投手）", "とくちょう"],
             ["速球（↓）", "146 km/h（最高球速）", "打者が振り遅れやすい"],
             ["ふつう", "138 km/h（最高 − 8。最低より遅くはならない）", "コントロールしやすい"],
             ["遅い球（↑）", "110 km/h（最低球速）", "早く振らせて空振りをさそう"]], [80, 250, 181])
    b.note("右上の 2 行目に、投げた球の速さが出ます。最高・最低の球速は投手ごとにちがい、EDIT モードで変えられます。"
           "スタミナが 30 より少ないと、最高も最低も下がります。"
           "<b>140km 以上</b>の速球は、見た目もひと回り速く飛び、「ひゅん！」と高い音が鳴ります。")
    b.end()


def p_curve(b):
    b.begin(3, "変化球")
    b.para("投げる前に<b>同じ方向をすばやく 2 回</b>押してから A を押すと、変化球を投げます。", size=12)
    b.table([["コマンド", "球種", "動き"],
             ["↓↓ ＋ A", "フォーク", "まっすぐ来て、打者の手前でストンと落ちる。当てにくい（−8km）"],
             ["←← か →→ ＋ A", "カーブ", "利き腕と反対へ。浮いてから落ちる山なりで、だんだん大きく曲がる（−16km）"],
             ["←← か →→ ＋ A", "シュート", "利き腕の側へ。打者の手元で鋭く曲がる（−5km）"]], [110, 70, 331], size=9.5)
    b.para("右投手なら →→ でカーブ（一塁側へ）、←← でシュート（三塁側へ）。左投手は逆です。曲がる幅は投手の<b>変化</b>の値で決まります。"
           "ボールが手をはなれたあとも、十字キーで少し動かせます。", size=10)
    c = b.c
    y = b.y - 10
    # 図：まっすぐ・曲がる
    for i, (lab, dx) in enumerate([("←：左へ曲がる", -1), ("まっすぐ", 0), ("→：右へ曲がる", 1)]):
        x = M + 80 + i * 170
        c.setStrokeColor(GRAY)
        c.setDash(3, 3)
        c.setLineWidth(1.2)
        c.line(x, y - 10, x, y - 150)
        c.setDash()
        c.setStrokeColor(RED)
        c.setLineWidth(2.5)
        p = c.beginPath()
        p.moveTo(x, y - 10)
        p.curveTo(x, y - 60, x + dx * 10, y - 110, x + dx * 40, y - 150)
        c.drawPath(p, stroke=1, fill=0)
        art.ball(c, x + dx * 40, y - 150, 7)
        c.setFillColor(INK)
        c.setFont("GB", 11)
        c.drawCentredString(x, y - 176, lab)
    b.y = y - 196
    b.bullets(["投げたあとの <b>←→</b>：押している間、ボールが左右に曲がる（打者の近くで大きく）。変化球にも足せる",
               "投げたあとの <b>↓</b>：フォークのように落とす　／　<b>↑</b>：<b>チェンジアップ</b>（ゆっくりになる）",
               "COM の投手も変化球を投げてきます（「変化」の高い投手ほど多く、2 ストライクからはフォークが増える）",
               "捕手は捕った球を山なりに投手へ返します"], size=10)
    b.y -= 12
    b.note("曲げすぎるとホームベースから外れてボールになります。ストライクは「ベースに 1 ドットでもかかる」とき。", "ちゅうい", RED_L, RED)
    b.tip("内角いっぱいに投げて、最後に外へ逃げる！なんて投球もできるよ。", who="chan")
    b.end()


def p_zone(b):
    b.begin(3, "ストライクの判定")
    b.para("見のがした球は、ボールの影がホームベースを通ったかどうかで決まります。", size=12)
    strike_diagram(b)
    b.shot("so_strike", M, b.y, 240, "3 つめのストライク")
    b.shot("so_out", W - M - 240, b.y, 240, "1 秒後に「アウト」")
    b.y -= 240 * 212 / 256 + 36
    b.para("三振のときは、まず「<b>ストライク</b>」が出て、<b>1 秒後</b>に「<b>アウト</b>」が出ます。"
           "右下の O のランプも、アウトが出たときに点きます。")
    b.end()


def p_stamina(b):
    b.begin(3, "スタミナとリリーフ")
    b.para("投手のスタミナ（右上の <b>ST</b>）は 1 球投げるごとに 1 減ります。", size=12)
    b.bullets(["30 より少なくなると、球が遅くなります（少ないほど遅い）",
               "先発投手ほどスタミナが多く、リリーフ投手は少なめです"])
    b.head("リリーフの出し方")
    b.para("守備側のプレーヤーが、<b>打席の始まり（投げる前）</b>に <b>SELECT</b>（F1 / 2P は F2）を押すと、"
           "リリーフ投手のリストが出ます。くわしくは " + pg("代打・リリーフのしかた") + " ページ。")
    b.y -= 6
    art.player(b.c, M + 80, b.y - 170, 140, "throw", cap=NAVY)
    art.ballkun(b.c, W - M - 120, b.y - 90, 30, "o", "point")
    art.bubble(b.c, M + 170, b.y - 120, 220, 70, tail=(W - M - 150, b.y - 90))
    b.para("ST が 30 を切ったら<br/>交代のサイン！", x=M + 186, w=200, y=b.y - 66, size=12, font="GB")
    b.end()


def p_pickoff(b):
    b.begin(3, "牽制球（けんせい）")
    y0 = b.y
    b.shot("lead", W - M - 236, b.y, 236, "一塁の走者はリードの構え（一塁手は定位置）")
    w = W - 2 * M - 256
    b.para("投げる前に <b>B ＋ 塁の方向</b>を押すと、その塁へ牽制球を投げます。", w=w, size=12)
    b.table([["操作", "投げる先"], ["B ＋ →", "一塁"], ["B ＋ ↑", "二塁"], ["B ＋ ←", "三塁"]], [90, w - 90], size=10.5)
    b.y = min(b.y, y0 - 236 * 212 / 256 - 34)
    b.bullets(["方向は、投手から見た塁の向きです（画面の向きと同じ）",
               "走者のいない塁の方向では投げません。走者が 1 人もいなければ、<b>B でも投球</b>します",
               "走者はふだんすぐに塁へ戻りますが、ときどき逆を突かれて戻るのが遅れます。ボールが先にベースへ届けばタッチアウト",
               "一塁・三塁に走者がいても一塁手・三塁手は定位置で守り、牽制球のときはベースへ走って入って受けます。二塁に走者がいると遊撃手が二塁ベースに近づきます",
               "COM の投手も、一塁の足の速い走者にときどき牽制します"], size=10.5)
    b.y -= 14
    b.note("自分が走者のときは、牽制球が来たら <b>A</b> を押すとすぐ塁へ戻れます（押さなくても自動で戻ります）。", "走者のとき", NAVY_L, NAVY, size=10)
    b.end()


def p_pitch_tips(b):
    b.begin(3, "投球のコツ")
    tips = [("速球と遅い球をまぜる", "打者は球の速さに合わせて振ります。同じ速さばかりだと打たれやすくなります。"),
            ("コースを散らす", "プレートの位置と変化球で、内角・外角に投げ分けましょう。"),
            ("2 ストライクからは外へ", "追い込んだら、ベースのはしをかすめる球や、外へ逃げる球で空振りをさそいます。"),
            ("ボールが先行したら真ん中寄り", "3 ボールになったら、フォアボールを出さないようにストライクを取りにいきます。"),
            ("スタミナに注意", "球が遅くなってきたら（ST 30 未満）、リリーフを考えましょう。")]
    for i, (t, d) in enumerate(tips):
        b.box(M, b.y, W - 2 * M, 60, NAVY_L)
        b.badge(i + 1, M + 22, b.y - 30, Color(0.13, 0.45, 0.75), 13)
        b.c.setFillColor(INK)
        b.c.setFont("GB", 12.5)
        b.c.drawString(M + 46, b.y - 22, t)
        b.para(d, x=M + 46, w=W - 2 * M - 60, y=b.y - 28, size=10.5, gap=0)
        b.y -= 70 - 0
        b.y = min(b.y, b.y)
    b.tip("COM の打者は、ストライクの球はよく振るけど、ボール球には手を出しにくいよ。", who="chan")
    b.end()


# ---------------------------------------------------------------- 守る
def p_field(b):
    b.begin(4, "守備の画面")
    b.shot("field1", M, b.y, 250, "打球を追う守備")
    b.shot("field2", W - M - 250, b.y, 250, "画面はボールについて動く")
    b.y -= 250 * 212 / 256 + 36
    b.para("打球が飛ぶと、画面が球場全体を見わたす<b>守備の画面</b>に切りかわります。"
           "画面はボールについてなめらかにスクロールします。", size=12)
    b.bullets(["打球にいちばん早く追いつける選手が、自動で追いかけます",
               "ほかの選手は、ベースに入ったり、ボールのほうへ寄ったりします",
               "ボールを捕ったら、送球（A）か、ボールを持って走る（B）"])
    b.tip("フライのときは、落ちてくる場所に先回りするよ。ゴロは、転がっていく先で待ちかまえるんだ。", who="kun")
    b.end()


def p_field_manual(b):
    b.begin(4, "自動で追う・自分で動かす")
    art.player(b.c, W - M - 70, b.y - 190, 150, "catch", cap=Color(0.95, 0.55, 0.1))
    b.para("守備側のプレーヤーは、打球を追う選手を<b>十字キー</b>で動かせます。", w=W - 2 * M - 150, size=12)
    b.bullets(["十字キーを<b>押している間</b>：自分で動かす", "十字キーを<b>はなすと</b>：また自動で追いかける",
               "<b>B</b>：操作する野手を切り替える（画面の中心に近い順。替わった野手は少し点滅）"], w=W - 2 * M - 150)
    b.y -= 20
    b.head("動かす選手")
    b.para("動かせるのは、いまボールを追っている選手（ボールにいちばん近い選手）です。"
           "ボールが送球されたら受ける選手、捕ったらその選手に替わります。"
           "はっきり外野（外野手の定位置のあたり）へ飛んだ打球は、内野手は追わずに外野手が追います。")
    b.head("捕る")
    b.para("選手がボールに重なれば、自動で捕ります。フライを地面に落ちる前に捕れば<b>アウト</b>（フライアウト）。")
    b.note("ゴロは自動で追うのがいちばん速いことが多いです。自分で動かすのは、打球が壁にはね返ったときなどに。")
    b.end()


def p_throw(b):
    b.begin(4, "送球（どの塁へ投げるか）")
    b.para("ボールを持った選手で、<b>A ＋ 方向</b>を押すと、その塁へ投げます。", size=12)
    home, first, second, third = diamond(b, W / 2, b.y - 190, 120)
    c = b.c
    for (bx, by), lab, (dx, dy) in ((first, "A ＋ →", (40, -30)), (second, "A ＋ ↑", (0, 34)), (third, "A ＋ ←", (-40, -30)), (home, "A ＋ ↓", (0, -40))):
        c.setFillColor(RED)
        c.roundRect(bx + dx - 34, by + dy - 10, 68, 22, 8, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("GB", 11)
        c.drawCentredString(bx + dx, by + dy - 3, lab)
    b.arrow(W / 2 - 10, b.y - 170, first[0] - 12, first[1] + 4)
    b.y -= 360
    b.bullets(["方向を押さずに <b>A</b> だけ → <b>一塁</b>へ", "投げた先の塁には、ベースに入った選手が受けます"])
    b.shot("throw", W / 2 - 120, b.y, 240, "一塁への送球")
    b.y -= 240 * 212 / 256 + 30
    b.end()


def p_runball(b):
    b.begin(4, "ボールを持って走る")
    b.para("ボールを持った選手で、<b>B ＋ 方向</b>を押すと、その塁へボールを持ったまま走ります（↑二塁・→一塁・←三塁・↓本塁）。", size=12)
    art.player(b.c, W - M - 70, b.y - 180, 140, "run", cap=Color(0.95, 0.55, 0.1))
    b.head("フォースアウト", w=W - 2 * M - 150)
    b.para("ランナーが次の塁へ進まなければいけないとき（押し出されるとき）は、ボールを持ってその塁を<b>踏めばアウト</b>。",
           w=W - 2 * M - 150)
    b.head("タッチアウト", w=W - 2 * M - 150)
    b.para("塁と塁の間にいるランナーに、ボールを持った選手が<b>触ればアウト</b>。", w=W - 2 * M - 150)
    b.y -= 10
    b.note("近くの塁なら、投げるより走ったほうが早いことがあります。", "ポイント")
    b.tip("ボールを持っているときに十字キーだけ押すと、その方向に歩けるよ。", who="kun")
    b.end()


def p_fly(b):
    b.begin(4, "フライ・ゴロ・ダブルプレー")
    b.head("フライ")
    b.para("地面に落ちる前に捕ればアウト。ランナーは捕られたら元の塁に戻らなければいけません（タッチアップ：" + pg("タッチアップ") + " ページ）。"
           "捕れるのは、ボールの絵が野手の体に重なったときだけ（見た目どおり）。一度でもフェアグラウンドで弾めば（<b>弾む音</b>が鳴れば）フライアウトになりません。", size=10.5)
    b.head("ゴロ")
    b.para("捕ったら、一塁などへ送球してランナーより早く届けばアウト（塁まで残り 4.5 ドット未満のランナーは足がかかっているのでセーフ）。"
           "打球を追う野手の代わりに、その塁に近い手の空いた内野手が<b>ベースカバー</b>に入ります。"
           "芯の近くでとらえた強いゴロは、ときどき何度も弾みながら速く転がり（<b>痛烈なゴロ</b>）、内野を抜けると外野の壁まで届きます。", size=10.5)
    b.head("ダブルプレー（ゲッツー）")
    b.para("一塁にランナーがいるときのゴロは、まず<b>二塁</b>（A ＋ ↑）へ投げてフォースアウト、"
           "受けた選手ですぐに<b>一塁</b>（A ＋ →）へ投げれば 2 つアウトが取れます。")
    b.y -= 6
    home, first, second, third = diamond(b, W / 2, b.y - 150, 95, labels=True)
    b.arrow(W / 2 - 50, b.y - 150 + 20, second[0] - 6, second[1] - 8, RED)
    b.arrow(second[0] + 8, second[1] - 6, first[0] - 8, first[1] + 6, NAVY)
    b.c.setFillColor(RED)
    b.c.setFont("GB", 11)
    b.c.drawString(W / 2 - 130, b.y - 120, "① 二塁へ")
    b.c.setFillColor(NAVY)
    b.c.drawString(W / 2 + 80, b.y - 100, "② 一塁へ")
    b.y -= 300
    b.end()


def p_def_tips(b):
    b.begin(4, "守備のコツ")
    tips = [("自動にまかせる", "打球を追うのは自動がいちばん正確。十字キーは必要なときだけ。"),
            ("投げる塁を早めに決める", "捕る前に、ランナーの位置を見ておきましょう。"),
            ("先頭のランナーをねらう", "点を取られそうなときは、本塁（A ＋ ↓）や三塁へ。"),
            ("外野からは中継", "外野から本塁は遠いので、二塁や三塁に返して、ランナーを止めましょう。"),
            ("壁ぎわの打球", "外野のフェンスではね返った打球は、追いかけ方が変わります。十字キーで手伝いましょう。")]
    for i, (t, d) in enumerate(tips):
        b.box(M, b.y, W - 2 * M, 60, GREEN_L)
        b.badge(i + 1, M + 22, b.y - 30, GREEN, 13)
        b.c.setFillColor(INK)
        b.c.setFont("GB", 12.5)
        b.c.drawString(M + 46, b.y - 22, t)
        b.para(d, x=M + 46, w=W - 2 * M - 60, y=b.y - 28, size=10.5, gap=0)
        b.y -= 70
    b.tip("COM も同じルールで守っているよ。いいプレーを見て、まねしてみよう。", who="kun")
    b.end()


# ---------------------------------------------------------------- 走る
def p_run(b):
    b.begin(5, "進塁と帰塁")
    b.para("攻撃側のプレーヤーは、打球が飛んでいる間にランナーを動かせます。", size=12)
    b.table([["操作", "動き"],
             ["B", "全員が次の塁へ走る"],
             ["B ＋ 方向", "その塁をめざすランナーだけ走る（→一塁・↑二塁・←三塁・↓本塁）"],
             ["A", "全員が前の塁へ戻る"],
             ["A ＋ 方向", "そのランナーだけ戻る"]], [110, 401])
    home, first, second, third = diamond(b, W / 2, b.y - 150, 100)
    b.arrow(first[0] - 8, first[1] + 10, second[0] + 10, second[1] - 8, Color(0.85, 0.45, 0.1))
    b.c.setFillColor(Color(0.85, 0.45, 0.1))
    b.c.setFont("GB", 11)
    b.c.drawString(W / 2 + 70, b.y - 80, "B ＋ ↑：二塁をめざす")
    b.y -= 300
    b.note("打者は打つと自動で一塁へ走ります。押し出されるランナー（一塁が埋まっているとき）も自動で次の塁へ。", "メモ", NAVY_L, NAVY)
    b.end()


def p_steal(b):
    b.begin(5, "盗塁")
    art.player(b.c, W - M - 80, b.y - 170, 140, "run", cap=RED)
    b.para("投手が投げる動作に入ったら、<b>B ＋ 目指す塁の方向</b>でランナーが走り出します（盗塁）。", w=W - 2 * M - 170, size=12)
    b.table([["操作", "走るランナー"], ["B ＋ ↑", "一塁のランナーが二塁へ"], ["B ＋ ←", "二塁のランナーが三塁へ"],
             ["B ＋ →（盗塁中）", "一塁へ戻る"], ["B ＋ ↑（二塁から盗塁中）", "二塁へ戻る"]], [150, 190], size=10)
    b.bullets(["方向なしの B は<b>バントの構え</b>です", "塁の上のランナーはリードの構えをとっていて、<b>リードの位置から走り出します</b>",
               "前の塁にランナーがいるときは走れません", "足の速いランナーほど成功しやすい",
               "<b>盗塁中も B ＋ 元の塁の方向で戻り、また B ＋ 次の塁の方向で進み直せる</b>（何度でも）",
               "捕手が投げたボールより早く塁に着けば セーフ"], w=W - 2 * M - 170, size=10)
    b.y -= 10
    b.note("COM のランナーも、足が速いと盗塁してきます。塁を離れたランナーには、ボールを持った守備が距離を見て追いかけ、重なってタッチします。")
    b.tip("投手が振りかぶった瞬間がスタートの合図！遅れると刺されるよ。", who="chan")
    b.end()


def p_tagup(b):
    b.begin(5, "タッチアップ")
    b.para("フライが捕られたら、ランナーは<b>元の塁に戻ってから</b>でないと次の塁へ進めません。", size=12)
    b.bullets(["フライが捕られると、ランナーは自動で元の塁に戻ります",
               "捕った瞬間に塁にいた・戻って塁を踏み直したランナーは、<b>B</b> で次の塁へ走れます（タッチアップ）",
               "フライが上がっている間は、押し出されたランナーも <b>A</b> で戻れます",
               "三塁ランナーがタッチアップで本塁に帰れば 1 点（犠牲フライ）",
               "COM のランナー：外野フライなら二・三塁のランナーは塁に戻って備え、一塁はハーフウェイで待つ。"
               "送球より先に着けそうなら走る",
               "フライを捕った外野手は、足を止めてから投げます"], size=10)
    home, first, second, third = diamond(b, W / 2, b.y - 130, 80)
    b.arrow(third[0] + 10, third[1] - 10, home[0] - 10, home[1] + 10, Color(0.85, 0.45, 0.1))
    b.c.setFillColor(Color(0.85, 0.45, 0.1))
    b.c.setFont("GB", 11)
    b.c.drawString(M + 20, b.y - 180, "戻ってから B で本塁へ！")
    b.y -= 290
    b.note("戻る前に走り出したまま捕られると、ボールを持った守備が元の塁を踏めばアウトです。", "ちゅうい", RED_L, RED)
    b.end()


def p_rundown(b):
    b.begin(5, "挟まれたとき（挟殺プレー）")
    y0 = b.y
    b.shot("rundown1", M, b.y, 236, "COM の挟殺：塁の間の走者を両側から詰める")
    x2 = M + 256
    b.para("塁と塁の間で、走者が前と後ろの守備に<b>挟まれる</b>ことがあります（挟殺・ランダウンプレー）。"
           "COM は実際の野球の定石どおりに動きます。", x=x2, w=W - M - x2, size=10.5)
    b.para("いちばん大事なのは「<b>先の塁を与えない</b>」こと。だから走者は元の塁のほうへ追い返し、"
           "送球はできるだけ少なく（1 回でタッチできるのが理想）します。", x=x2, w=W - M - x2, size=10.5)
    b.y = y0 - 236 * 212 / 256 - 38
    b.head("COM の守り")
    b.bullets(["<b>フォースプレーが先</b>：押し出された走者（打者走者など）がまだ走っている間は、ふつうに一塁などへ投げてアウトを取る",
               "走者が向かう塁へ、送球のほうが早ければ<b>先回りして送球</b>する",
               "挟まれた走者・盗塁中に戻った走者には、ボールを持った守備が距離を見て向かっていき、重なってタッチ。<b>元の塁のほうへ追い返す</b>（逃げられても先の塁を与えない）",
               "走者が反対側の塁（味方が入っている）の近くまで来たら、そこへ投げる。受けた味方が走者に向かって<b>タッチ</b>",
               "投げた守備は自分の塁へ戻るので、何度往復しても両側から詰まっていく"], size=10)
    b.head("COM のランナー")
    b.bullets(["塁から 8 ドット（1 人分）以上離れたところで、<b>元の塁にボールを持った守備が入ったら、戻らずに次の塁へ</b>",
               "ボールを持った守備が<b>次の塁</b>にいたら、元の塁へ戻る",
               "追いかけられたら、その守備から遠いほうの塁へ逃げる"], size=10)
    b.tip("自分が守るときも同じ。B ＋ 方向でボールを持って走者に向かい、走者が反対の塁に近づいたら A ＋ 方向で送球しよう。", who="kun", size=10)
    b.end()


def p_run_tips(b):
    b.begin(5, "走塁のコツ")
    tips = [("打球の行き先を見る", "外野の間を抜けたら次の塁をねらい、内野に止まったら無理をしない。"),
            ("ボールの位置を見る", "守備がボールを捕って投げようとしていたら、戻るほうが安全です。"),
            ("足の速さを知る", "チーム紹介のページで、走力（★）の多い選手を確かめましょう。"),
            ("2 アウトなら思い切って", "2 アウトでは打った瞬間からランナーは全力で走ってかまいません。")]
    for i, (t, d) in enumerate(tips):
        b.box(M, b.y, W - 2 * M, 60, Color(1.0, 0.94, 0.86))
        b.badge(i + 1, M + 22, b.y - 30, Color(0.85, 0.45, 0.1), 13)
        b.c.setFillColor(INK)
        b.c.setFont("GB", 12.5)
        b.c.drawString(M + 46, b.y - 22, t)
        b.para(d, x=M + 46, w=W - 2 * M - 60, y=b.y - 28, size=10.5, gap=0)
        b.y -= 70
    art.player(b.c, M + 90, b.y - 150, 120, "run", cap=Color(0.95, 0.55, 0.1))
    art.player(b.c, M + 250, b.y - 150, 120, "cheer", cap=RED)
    art.ballkun(b.c, M + 410, b.y - 80, 30, "open", "up")
    b.end()


# ---------------------------------------------------------------- 試合
def p_messages(b):
    b.begin(6, "判定メッセージ一覧")
    msgs = [("ストライク", "ストライク（見のがし・空振り・ファウル）"), ("ボール", "ボール"), ("アウト", "アウト"),
            ("セーフ", "セーフ"), ("ファウル", "ファウル"), ("ホームラン", "ホームラン"), ("フォアボール", "四球（一塁へ）"),
            ("デッドボール", "死球（一塁へ）"), ("チェンジ", "3 アウトで攻守交代"), ("ゲームセット", "試合終了"),
            ("プレイボール", "試合開始"), ("ヒット", "安打"), ("ツーベース", "二塁打（エンタイトルを含む）"),
            ("スリーベース", "三塁打"), ("サヨナラ", "最後の回の裏で勝ち越し"), ("ダブルプレー", "併殺")]
    c = b.c
    y = b.y
    for i, (m, d) in enumerate(msgs):
        x = M + (i % 2) * 262
        yy = y - (i // 2) * 74
        path = msg_image(m, 4)
        im = Image.open(path)
        w = min(200, im.width * 0.5)
        h = w * im.height / im.width
        b.image(path, x, yy, w, h)
        c.setFillColor(INK)
        c.setFont("G", 10)
        c.drawString(x, yy - h - 14, d)
    b.y = y - 8 * 74 - 4
    b.para("メッセージは<b>画面の真ん中</b>に、上から白・黄・赤の字で出ます。", size=10, color=GRAY)
    b.end()


def p_umpire(b):
    b.begin(6, "審判と球場")
    b.shot("safe", W - M - 250, b.y, 250, "セーフ（塁審が両手を広げる）")
    b.para("審判は 4 人。<b>球審</b>（捕手の後ろ）と、<b>一塁・二塁・三塁</b>の塁審です。"
           "判定は文字といっしょに身ぶりでも伝えます。", w=W - 2 * M - 270, size=12)
    b.y = min(b.y, H - 112 - 250 * 212 / 256 - 40)
    pu = ump_sheet(scale=9)
    h = b.image(pu, M, b.y, 300, frame=True)
    b.para("左から：ふつう／ストライク・アウト（こぶしを上げる）／セーフ（両手を広げる）／ファウル（両手を上げる）",
           x=M + 320, w=W - 2 * M - 320, y=b.y, size=10)
    b.y -= h + 14
    b.bullets(["審判はボールや選手に当たりません。止まりかけたボールが近くに来ると、2 人分くらい離れてよけます",
               "セーフ・アウトは、走者がいちばん近い塁の審判が判定します",
               "一塁・三塁の後ろのファウルゾーンには<b>屋根つきのベンチ</b>があります（左右対称）",
               "ファウルラインの近くで止まったボールは、白線と見分けやすいように<b>灰色と白で点滅</b>します"])
    b.end()


def p_homerun(b):
    b.begin(6, "ホームラン・ファウル")
    b.shot("homerun", M, b.y, 250, "ホームラン（フェンスが光る）")
    b.shot("foul", W - M - 250, b.y, 250, "ファウル")
    b.y -= 250 * 212 / 256 + 36
    b.head("ホームラン")
    b.para("フライがそのままフェンスを越えればホームラン。フェンスが黄色く光り、ランナー全員がホームに帰ります"
           "（<b>A か B を押している間は 3 倍の速さ</b>で走ります）。"
           "ファンファーレといっしょに、スタンドから「ワーッ」と<b>歓声</b>が上がります。")
    b.head("ホームラン・得点の演出")
    b.bullets(["ホームラン：外野フェンス・ファウルゾーンの壁の線（ベンチの前も）・バックネットがすべて黄色に点滅",
               "点が入ると、次の投球まで観客が 0.3 秒ごとに跳びはねて手を上げる"])
    b.head("球場の音")
    b.bullets(["<b>歓声</b>（約 3 秒）：外野へのヒット・点が入った瞬間・ホームランの瞬間。曲は鳴ったまま",
               "<b>フライの軌道音</b>：「ぴ〜〜」。高く上がるほど高い音、落ちてくると低い音",
               "<b>弾む音</b>：ボールが地面で弾むたびに必ず鳴る（3 回目からは小さく短い音）"])
    b.head("エンタイトルツーベース")
    b.para("一度地面にはずんでからフェンスを越えたときは、ランナー全員が 2 つ先の塁まで進みます（「ツーベース」）。")
    b.head("ファウル")
    b.para("打球が一塁線・三塁線の外に出たらファウル。2 ストライクまではストライクに数えます。"
           "フェアと決まる前に壁やベンチの屋根に当たった打球もファウルです。")
    b.end()


def p_sub(b):
    b.begin(6, "代打・リリーフのしかた")
    b.shot("pinch", M, b.y, 250, "代打（ダイダ）のリスト")
    b.shot("after_pinch", W - M - 250, b.y, 250, "代打が打席に入った")
    b.y -= 250 * 212 / 256 + 36
    b.bullets(["打席の始まり（投手が投げる前）に <b>SELECT</b> を押す（1P は F1、2P は F2）",
               "攻撃側なら<b>代打</b>、守備側なら<b>リリーフ</b>のリストが出ます",
               "<b>↑↓</b> で選んで <b>A</b> で決定。やめるときは「キャンセル」を選びます",
               "名前の右は、代打なら打率、リリーフなら球速"])
    b.note("一度交代した選手は、その試合ではもう出られません。控えは打者 4 人・投手 4 人です。", "ちゅうい", RED_L, RED)
    b.end()


def p_board(b):
    b.begin(6, "スコアボード")
    b.shot("board", M + 40, b.y, 430)
    b.y -= 430 * 212 / 256 + 24
    b.para("イニングの表・裏が終わるたびに、プロ野球の球場のセンター後方（<b>バックスクリーン</b>）の電光スコアボードが出ます。"
           "まわりは夜空・照明塔・時計・両チームの色の旗・屋根つきのスタンド・黒いバックスクリーン・外野フェンスの広告と「122m」の表示。", size=11)
    b.bullets(["左はしの色の帯はチームの色。上が先攻、下が後攻",
               "黄色い数字は回。回のマスは 1 つおきに色を変えてあるので、すき間なしでも読みやすい",
               "<b>R</b>（黄）は得点の合計、<b>H</b> は安打の数",
               "下の段に「○回表 シュウリョウ」",
               "A か START で次へ。何もしなくても数秒で進みます"])
    b.end()


def p_gameend(b):
    b.begin(6, "試合の終わり")
    b.shot("gameset", W - M - 250, b.y, 250, "ゲームセット")
    b.para("最後の回が終わったら試合終了。勝ったチームの略称と「WIN!」が出ます。", w=W - 2 * M - 270, size=12)
    b.bullets(["後攻が最後の回の表の終わりでリードしていれば、裏はしません",
               "最後の回の裏で後攻が勝ち越したら<b>サヨナラ</b>",
               "同点なら<b>延長戦</b>。3 回まで延長して、それでも同点なら<b>引き分け</b>（ヒキワケ）"],
              w=W - 2 * M - 270)
    b.y = min(b.y, H - 112 - 250 * 212 / 256 - 40)
    b.head("COM VS COM（観戦）とデモ")
    b.para("COM VS COM を選ぶと、COM 同士の試合を最後まで観戦できます。タイトルで 10 秒待つと始まるデモ試合も同じです。"
           "A か START でいつでもタイトルに戻れます。")
    b.tip("COM のプレーを見ると、走塁や送球のコツがよくわかるよ。", mood="open")
    b.end()


# ---------------------------------------------------------------- モード
def p_edit1(b):
    b.begin(9, "EDIT モード")
    b.shot("edit_list", M, b.y, 236, "チームを選ぶ（↑↓ と A）")
    b.shot("edit_team", W - M - 236, b.y, 236, "チームの画面（▶ がカーソル）")
    b.y -= 236 * 212 / 256 + 36
    b.para("タイトルで <b>EDIT</b> を選ぶと、チーム名・選手名・打順・能力を書きかえて、<b>フロッピーディスク</b>に"
           "保存できます（ドライブのある機種）。ドライブがないと「ディスク ドライブ ガ アリマセン」と出て戻ります。", size=10.5)
    b.table([["行", "書きかえられるもの"],
             ["いちばん上", "略称（リャク・3 文字）、チーム名（チームメイ・6 文字）"],
             ["打者 12 人", "名前（5 文字）・打率（.100〜.355）・パワー（1〜9）・走力（1〜9）。上の 8 人がスタメン（打順どおり）、下の 4 人が控え"],
             ["投手 5 人", "名前（5 文字）・最高球速（100〜165km）・最低球速（70km〜最高）・変化（1〜9）・スタミナ（1〜9）。いちばん上が先発"]],
            [80, 431], size=9.5)
    b.table([["ボタン", "チームの画面での動き"],
             ["十字キー", "カーソルを動かす（↑↓ で行、←→ で項目）"],
             ["A", "書きかえる（名前は字の表、数は ↑↓←→）"],
             ["B", "2 つの行で押すと、その 2 人を入れかえる"],
             ["START", "ディスクに保存して、チームの一覧へ戻る"]], [80, 431], size=9.5)
    b.end()


def p_edit2(b):
    b.begin(9, "EDIT：数・名前・入れかえ")
    b.shot("edit_num", M, b.y, 236, "打率を書きかえているところ")
    b.shot("edit_name", W - M - 236, b.y, 236, "名前を書く（字の表から選ぶ）")
    b.y -= 236 * 212 / 256 + 36
    b.head("数を変える")
    b.para("<b>↑↓</b> で 1 ずつ、<b>←→</b> で 10 ずつ変わります。<b>A</b> か <b>B</b> で決定。", size=10.5)
    b.head("名前を書く")
    b.para("十字キーで字を選んで <b>A</b> で入れる、<b>B</b> で 1 文字消す、<b>START</b> で終わり。"
           "使える字は、英大文字・数字・「.」「-」・空白と、カタカナ 71 字です"
           "（ゥ ェ ォ ゼ ゾ ヂ ヅ ヌ プ ヲ は、フォントに空きがないので使えません）。", size=10.5)
    b.head("打順・控え・先発を入れかえる")
    b.para("<b>B</b> を 2 つの行で押すと、その 2 人が入れかわります（打者どうし・投手どうし）。"
           "スタメンと控えを入れかえれば控えの選手がスタメンに、投手を入れかえれば先発が変わります。", size=10.5)
    b.note("保存したチームは、1P VS COM などのふつうの試合とトーナメントで使われます。"
           "元に戻す機能はありません（ディスクの MSXSTAD.DAT を消すと、最初のチームに戻ります）。", "メモ", NAVY_L, NAVY, size=10)
    b.end()


def p_tour1(b):
    b.begin(9, "トーナメント（選ぶ・組み合わせ）")
    b.shot("tour_pick", M, b.y, 236, "6 チームを選ぶ（● が選んだチーム）")
    b.shot("tour_arrange", W - M - 236, b.y, 236, "組み合わせ（上と下の 2 チームがシード）")
    b.y -= 236 * 212 / 256 + 36
    b.para("タイトルで <b>TOURNAMENT</b> を選ぶと始まります。タイトルの<b>イニング</b>が、全試合のイニング数になります。", size=10.5)
    b.head("STEP 1　6 チームを選ぶ")
    b.para("全 8 球団から、<b>↑↓</b> と <b>A</b> で 6 つに ● を付けて <b>START</b>。", size=10.5)
    b.head("STEP 2　組み合わせを決める")
    b.bullets(["画面いっぱいにトーナメント表が出ます。<b>いちばん上といちばん下</b>の 2 チームが<b>シード</b>（2 回戦から）",
               "<b>A</b> を 2 か所で押すと、その 2 チームが入れかわります（組み合わせを自由に決められます）",
               "<b>B</b> で 1P が操作するチームを決めます（▶ が 1P。もう一度押すと「1P なし」）",
               "<b>START</b> で開始",
               "<b>ESC</b> を押すと、いつでもタイトルへ戻ります（トーナメント表の画面でも。始めた後なら、そこまでの結果は保存済み）"], size=10.5)
    b.y -= 10
    b.note("1 回戦は 2 試合（2 番目と 3 番目、4 番目と 5 番目のチーム）。シードの 2 チームは 2 回戦から出て、"
           "勝ち残った 2 チームが決勝で戦います。全部で 5 試合です。", "しくみ", NAVY_L, NAVY, size=10)
    b.tip("1P のチームをシードの位置に入れかえると、試合が 1 つ少なくて済むよ。どこに入れるかも作戦だね。", who="chan", size=10)
    b.end()


def p_tour2(b):
    b.begin(9, "トーナメント（試合と結果）")
    b.shot("tour_sim", M, b.y, 236, "COM 同士の試合は結果だけ（勝った線が黄色）")
    b.shot("tour_play", W - M - 236, b.y, 236, "1P のチームの試合（A ボタンで試合へ）")
    b.y -= 236 * 212 / 256 + 36
    b.bullets(["1P のチームの試合は <b>1P VS COM</b> で遊びます（表の上の側が先攻）",
               "COM 同士の試合は、チームの打率・パワーと投手の力から<b>結果だけ</b>決まります",
               "1P のチームを「なし」にすると、全試合を <b>COM VS COM</b> で観戦できます",
               "勝ったほうの線が<b>黄色</b>になり、点数が表に書かれます",
               "引き分けは安打の多いほうの勝ち。それも同じならくじ",
               "決勝に勝つと「<b>ユウショウ</b>」"], size=10.5)
    b.note("組み合わせと結果は、<b>1 試合終わるごとにディスクに保存</b>されます。電源を切っても、タイトルの CONTINUE で続きから遊べます。",
           "セーブ", YELLOW_L, YELLOW, size=10)
    b.tip("COM 同士の試合も見たいときは、1P のチームを「なし」にしてみよう。全部の試合を観戦できるよ。", who="kun", size=10)
    b.end()


def p_save(b):
    b.begin(9, "続きから・セーブについて")
    y0 = b.y
    b.shot("tour_cont", M, b.y, 236, "CONTINUE：次の試合から")
    x2 = M + 256
    b.para("タイトルで <b>CONTINUE</b> を選ぶと、保存したトーナメントの<b>次の試合</b>から始まります。"
           "1 試合終わるごとに、また保存されます。", x=x2, w=W - M - x2, size=10.5)
    b.para("トーナメントが終わっていると「セーブ ガ アリマセン」、ディスクドライブがないと「ディスク ドライブ ガ アリマセン」と出ます。",
           x=x2, w=W - M - x2, size=10.5)
    b.y = y0 - 236 * 212 / 256 - 38
    b.head("保存するもの")
    b.table([["保存するもの", "いつ"],
             ["EDIT したチーム（8 チーム分）", "チームの画面で START を押したとき"],
             ["トーナメントの組み合わせ・結果", "トーナメントを始めたとき・1 試合終わるごと"]], [230, 281], size=9.5)
    b.head("フロッピーディスク（ドライブのある機種）")
    b.para("ディスクの <b>MSXSTAD.DAT</b>（1536 バイト）に保存します。起動のときに読み、保存のたびに書きます（1〜2 秒、その間は音が止まります）。"
           "ファイルがなければ最初のチームから始まります。ディスクが入っていない・書き込み禁止のときは「ディスク ニ セーブ デキマセン」と出て、"
           "そのまま続けられます（openMSX は <b>-diska フォルダ名</b> でフォルダをディスクにできます）。", size=10)
    b.head("ドライブのない機種")
    b.para("試合とトーナメントは遊べますが、保存はできません（EDIT・CONTINUE は使えません）。カートリッジの SRAM には対応していません。", size=10)
    b.end()


# ---------------------------------------------------------------- チーム
STYLE_B = {"avg": "よく当てる打線", "power": "長打の打線", "speed": "足が速い打線", "even": "バランスのよい打線", "star": "強打の特別チーム"}
STYLE_P = {"fast": "速球派の投手陣", "even": "バランス型の投手陣", "slow": "変化球の投手陣", "star": "球が速くよく曲がる"}


def stars(n):
    return "★" * n + "<font color='#cccccc'>" + "★" * (9 - n) + "</font>"


def p_team(b, t, info):
    name, abbr, pc, uc, bs, ps = info
    b.begin(7, "%s（%s）" % (t["name"], abbr))
    c = b.c
    col = Color(pc[0] / 7, pc[1] / 7, pc[2] / 7)
    ucol = Color(uc[0] / 7, uc[1] / 7, uc[2] / 7)
    art.player(c, W - M - 60, b.y - 120, 105, "wave", cap=col, uni=ucol, line=col)
    b.para("<b>%s</b>／%s" % (STYLE_B[bs], STYLE_P[ps]), w=W - 2 * M - 120, size=12.5)
    c.setFillColor(col)
    c.roundRect(M, b.y - 18, 60, 18, 6, stroke=0, fill=1)
    c.setFillColor(ucol)
    c.setStrokeColor(GRAY)
    c.roundRect(M + 66, b.y - 18, 60, 18, 6, stroke=1, fill=1)
    c.setFillColor(GRAY)
    c.setFont("G", 9)
    c.drawString(M + 134, b.y - 13, "チームの色（帽子・ソックス／ユニフォーム）")
    b.y -= 36
    rows = [["打順", "名前", "打率", "本塁打", "パワー", "走力", "打"]]
    for i in range(8):
        bt = t["batters"][i]
        rows.append([str(i + 1), bt["name"][:5], ".%03d" % bt["avg"], str(bt["hr"]), stars(bt["pow"]), stars(bt["spd"]), "左" if bt["left"] else "右"])
    p0 = t["pitchers"][0]
    rows.append(["9", p0["name"][:5] + "（投）", "—", "—", "—", "—", "左" if p0["left"] else "右"])
    b.table(rows, [34, 92, 48, 46, 118, 118, 30], size=9.5, head_col=col if sum(pc) < 14 else NAVY)
    rows = [["控え", "打率", "本塁打", "パワー", "走力", "打"]]
    for bt in t["batters"][8:12]:
        rows.append([bt["name"][:5], ".%03d" % bt["avg"], str(bt["hr"]), stars(bt["pow"]), stars(bt["spd"]), "左" if bt["left"] else "右"])
    b.table(rows, [92, 48, 46, 118, 118, 30], x=M + 34, size=9.5, head_col=GRAY)
    rows = [["投手", "役", "最高球速", "最低球速", "変化", "スタミナ", "投"]]
    for i, p in enumerate(t["pitchers"]):
        rows.append([p["name"][:5], "先発" if i == 0 else "リリーフ", "%dkm" % p["kmh"], "%dkm" % ((p["kmh"] * 3 + 2) // 4),
                     stars(p["cv"]), stars(min(9, p["st"])), "左" if p["left"] else "右"])
    b.table(rows, [76, 52, 56, 56, 108, 108, 30], size=9.5, head_col=Color(0.13, 0.45, 0.75))
    b.end()


# ---------------------------------------------------------------- ふろく
def p_trouble(b):
    b.begin(8, "困ったときは")
    qa = [("画面が出ない・止まる", "MSX2 以上の機種を選んでいるか確かめてください。MSX1 では「MSX2 専用」と出て止まります。"),
          ("「THIS GAME REQUIRES MSX2.」と出る", "MSX1 の機種で起動しています。MSX2 の機種に変えてください。"),
          ("blueMSX でおかしくなる", "ROM の種類（マッパー）を ASCII16 にしてください。"),
          ("動きが速すぎる・遅すぎる", "タイトル画面の SPEED（1〜5）で、試合ぜんたいの速さを変えられます。"
                                       "エミュレーターの速度は 100%（実機と同じ）にしてください。"),
          ("キーがきかない", "日本語入力（IME）がオンだと、キーが届かないことがあります。オフにしてください。"),
          ("2P が動かない", "2P のキーは W A S D と G H です（" + pg("2P のキー・一時停止") + " ページ）。ジョイスティック 2 も使えます。"),
          ("デモが始まってしまう", "タイトルで 10 秒何もしないとデモになります。A か START で戻れます。"),
          ("「ディスク ドライブ ガ アリマセン」と出る", "ディスクドライブのない機種です。openMSX ならドライブのある機種（HB-F1XD など）で -diska を付けてください。"),
          ("「ディスク ニ セーブ デキマセン」", "ディスクが入っていないか、書き込み禁止です。ディスクを入れて、もう一度 START を押してください。")]
    for q, a in qa:
        b.box(M, b.y, W - 2 * M, 22, Color(0.92, 0.92, 0.94))
        b.c.setFillColor(INK)
        b.c.setFont("GB", 11)
        b.c.drawString(M + 10, b.y - 15, "？ " + q)
        b.y -= 27
        b.para(a, x=M + 10, w=W - 2 * M - 20, size=10.2, gap=7)
    b.end()


def p_words(b):
    b.begin(8, "用語集")
    words = [("先攻・後攻", "先に攻撃するチーム（表）と、後に攻撃するチーム（裏）"),
             ("打率", "ヒットを打つ割合。.300 なら 10 回に 3 回"), ("本塁打", "ホームラン"),
             ("フォースアウト", "押し出されたランナーより先に、ボールを持って塁を踏むアウト"),
             ("タッチアウト", "塁にいないランナーに、ボールを持って触るアウト"),
             ("タッチアップ", "フライが捕られたあと、元の塁に戻ってから次の塁へ走ること"),
             ("盗塁", "投球の間に次の塁へ走ること"), ("代打", "打者を交代すること"), ("リリーフ", "投手を交代すること"),
             ("内角・外角", "打者に近いコース・遠いコース"), ("引っぱり・流し打ち", "体の向きと同じ方向・反対方向に打つこと"),
             ("エンタイトルツーベース", "はずんだ打球がフェンスを越えたときの二塁打"),
             ("サヨナラ", "最後の回の裏に後攻が勝ち越して、試合が終わること"), ("延長戦", "同点のときに続ける回"),
             ("スタミナ（ST）", "投手の体力。少なくなると球が遅くなる"),
             ("挟殺（ランダウン）", "塁の間で前後の守備に挟まれた走者を、送球しながら追いつめてタッチすること"),
             ("シード", "トーナメントで 1 回戦がなく、2 回戦から出られること")]
    rows = [["ことば", "いみ"]] + [[a, d] for a, d in words]
    b.table(rows, [150, 361], size=9.6)
    b.end()


def p_quick(b):
    b.begin(8, "操作早見表")
    sections = [("打つ（攻撃）", RED, [("十字キー", "バッターボックスの中で動く"), ("A", "振る"),
                                      ("当たる瞬間 ↓ / ↑ / → / ←", "打ち上げる / たたきつける / 右方向 / 左方向"),
                                      ("B（押し続ける）", "バントの構え"), ("SELECT（投げる前）", "代打")]),
                ("投げる（守備）", Color(0.13, 0.45, 0.75), [("←→（投げる前）", "プレートの位置"),
                                                       ("A / ↓ ＋ A / ↑ ＋ A", "投げる / 速球 / 遅い球"), ("↓↓ ＋ A / ←← か →→ ＋ A", "フォーク / カーブ・シュート"),
                                                       ("投げたあと ←→ / ↓ / ↑", "曲げる / フォーク / チェンジアップ"),
                                                       ("B ＋ →↑←（投げる前）", "牽制球（一塁・二塁・三塁）"),
                                                       ("SELECT（投げる前）", "リリーフ")]),
                ("守る", GREEN, [("十字キー", "追う選手を動かす（はなすと自動）"), ("B（ボールを持っていない）", "操作する野手を切り替え"),
                                ("A ＋ 方向", "送球（↑二塁 →一塁 ←三塁 ↓本塁）"),
                                ("A のみ", "一塁へ送球"), ("B ＋ 方向", "ボールを持ってその塁へ走る")]),
                ("走る", Color(0.85, 0.45, 0.1), [("B / B ＋ 方向", "全員 / そのランナーが進む"), ("A / A ＋ 方向", "全員 / そのランナーが戻る"),
                                                 ("B ＋ ↑ / B ＋ ←（投球中）", "盗塁（二塁へ / 三塁へ）。B ＋ 元の塁の方向で戻る"),
                                                 ("A か B（ホームラン）", "一周を速く")]),
                ("その他", GRAY, [("START / A・START（デモ中）", "一時停止・再開 / タイトルへ"), ("タイトルの SPEED", "全体の速さ 1〜5"),
                                 ("EDIT：A / B / START", "書きかえ / 入れかえ / 保存"),
                                 ("トーナメント：A / B / START", "入れかえ / 1P のチーム / 開始")])]
    for title, col, rows in sections:
        b.c.setFillColor(col)
        b.c.roundRect(M, b.y - 20, 120, 20, 7, stroke=0, fill=1)
        b.c.setFillColor(white)
        b.c.setFont("GB", 11)
        b.c.drawCentredString(M + 60, b.y - 14, title)
        b.y -= 24
        b.table([["操作", "動き"]] + [[a, d] for a, d in rows], [190, 321], size=9.2, head_col=col)
        b.y += 4
    b.end()


def p_end(b):
    b.begin(8, "おわりに")
    c = b.c
    art.player(c, M + 110, b.y - 260, 170, "cheer", cap=RED)
    art.player(c, W - M - 110, b.y - 260, 170, "wave", cap=NAVY, flip=True)
    art.ballkun(c, W / 2, b.y - 120, 46, "open", "up")
    b.y -= 300
    b.para("最後まで読んでくれてありがとう！<br/>さあ、球場へ行こう。プレイボール！", size=15, font="GB", align=1)
    b.y -= 10
    b.box(M, b.y, W - 2 * M, 150, Color(0.95, 0.95, 0.97))
    b.para("<b>MSX STADIUM</b>（MSX2 用 野球ゲーム）<br/>"
           "ROM：MSXSTADIUM.ROM（512KB = 4M ビット・メガROM ASCII16、フロッピーディスクに保存）<br/>"
           "絵・曲・チーム名・選手名・このマニュアルの挿絵は、すべてこのゲームのために作ったオリジナルです。"
           "実在の団体・人物とは関係ありません。<br/>"
           "ファンメイドの作品です。(C)2026 FAN MADE", x=M + 16, w=W - 2 * M - 32, y=b.y - 14, size=10.5)
    b.end()


def build():
    tdata = TM.make_teams()
    pages = [p_intro, p_friends, p_need, p_emu, p_keys1, p_keys2, p_title, p_select, p_lineup, p_flow, p_screen, p_hud1, p_hud2,
             p_bat_box, p_swing, p_sweet, p_contact, p_bunt, p_eye, p_bat_tips,
             p_plate, p_speed, p_curve, p_zone, p_stamina, p_pickoff, p_pitch_tips,
             p_field, p_field_manual, p_throw, p_runball, p_fly, p_def_tips,
             p_run, p_steal, p_tagup, p_rundown, p_run_tips,
             p_messages, p_umpire, p_homerun, p_sub, p_board, p_gameend,
             p_edit1, p_edit2, p_tour1, p_tour2, p_save]
    team_pages = [(lambda b, t=t, info=info: p_team(b, t, info)) for t, info in zip(tdata, TM.TEAMS)]
    tail = [p_trouble, p_words, p_quick, p_end]
    # 1 回目：ページ番号を数える
    tmp = Book(os.path.join(CACHE, "tmp.pdf"))
    os.makedirs(CACHE, exist_ok=True)
    p_cover(tmp)
    tmp.page += 1                       # もくじ
    for f in pages + team_pages + tail:
        f(tmp)
    toc = [e for e in tmp.toc if e[2] != "表紙"]
    PAGEREF.update({t: p for p, ch, t in tmp.toc})
    PAGEREF["_all"] = list(tmp.toc)
    # 2 回目：本番
    b = Book(OUTPDF)
    p_cover(b)
    p_toc(b, [(pg, ch, t) for pg, ch, t in toc])
    for f in pages + team_pages + tail:
        f(b)
    b.c.save()
    print("pages:", b.page, "->", OUTPDF)


if __name__ == "__main__":
    build()
