# -*- coding: utf-8 -*-
"""スコアボードの画面（イニングの終わり）の背景：プロ野球の球場のセンター後方（バックスクリーン）。
256x216 ドット（32x27 マス）。各 8 ドットの行は 2 色まで。ボード本体（中央の 9〜16 行）はプログラムが上に描く。
・夜空と星、左右の照明塔
・ボードの上に時計と両チームの旗（チームの色）、左右に屋根つきの上段スタンド
・ボードの下に黒いバックスクリーン（縁は暗い緑）、左右は外野スタンド
・外野フェンス（紺・上は黄色の線）と広告板、ウォーニングトラック、しま模様の芝"""
import numpy as np
from common import *
import gfx_font

W, H = 256, 216
NAVY = WALL
SKY = WALL


def crowd_tile():
    G, S, R, Wt, Y = GRAY, SKIN, RED, WHITE, YELLOW
    return np.array([
        [G, S, G, G, G, S, G, G],
        [R, R, G, G, G, R, R, G],
        [G, G, G, G, G, G, G, G],
        [G, G, G, S, G, G, G, S],
        [G, G, Wt, Wt, G, G, G, Wt],
        [G, G, G, G, G, G, G, G],
        [S, G, G, G, S, G, G, G],
        [Y, Y, G, G, Y, Y, G, G],
    ], np.uint8)


def text(img, x, y, s, col, step=8):
    """ゲームの字（8x8）を絵に書く"""
    for i, ch in enumerate(s):
        for r, row in enumerate(gfx_font.glyph(ch)):
            for c, v in enumerate(row[:8]):
                if v == '#':
                    img[y + r, x + i * step + c] = col


def draw():
    img = np.full((H, W), SKY, np.uint8)
    ys, xs = np.mgrid[0:H, 0:W]
    cr = crowd_tile()[ys % 8, xs % 8]
    # 星
    for x, y in ((20, 6), (60, 20), (100, 4), (150, 14), (190, 26), (236, 10), (128, 30), (40, 44), (214, 50), (84, 38)):
        img[y, x] = WHITE
        img[y - 1, x] = img[y + 1, x] = img[y, x - 1] = img[y, x + 1] = WHITE
    # 照明塔（左右）：灯の板（白と黄の格子）と柱
    for x0 in (8, 216):
        img[8:32, x0:x0 + 32] = GRAY
        for yy in range(10, 30, 4):
            for xx in range(x0 + 2, x0 + 30, 4):
                img[yy:yy + 2, xx:xx + 2] = YELLOW if (yy // 4 + xx // 4) % 2 else WHITE
        img[32:88, x0 + 14:x0 + 18] = GRAY
    # 上段スタンド（ボードの左右・屋根の下）
    stand = (ys >= 56) & (ys < 136) & ((xs < 40) | (xs >= 216))
    img[stand] = cr[stand]
    roof = (ys >= 48) & (ys < 56) & ((xs < 48) | (xs >= 208))
    img[roof] = WHITE
    img[(ys >= 54) & (ys < 56) & ((xs < 48) | (xs >= 208))] = GRAY
    # ボードの裏の構造（ボードより少し大きい黒い面。ボードの幅が変わっても縁が見えるように）
    img[(ys >= 64) & (ys < 136) & (xs >= 32) & (xs < 224)] = BLACK
    # 時計（ボードの上・中央）
    cx, cy = 128, 44
    d = (xs - cx + 0.5) ** 2 + (ys - cy + 0.5) ** 2
    img[d <= 15 ** 2] = WHITE
    img[(d <= 15 ** 2) & (d > 13 ** 2)] = GRAY
    img[(np.abs(xs - cx) <= 0) & (ys >= cy - 10) & (ys <= cy)] = BLACK
    img[(ys == cy) & (xs >= cx) & (xs <= cx + 7)] = BLACK
    img[60:64, 120:136] = GRAY                               # 時計の台
    # 旗（両チームの色）とポール
    for x0, col in ((56, T1A), (184, T2A)):
        img[24:64, x0:x0 + 2] = WHITE
        img[24:40, x0 + 2:x0 + 18] = col
    # バックスクリーン（黒）と外野スタンド
    bs = (ys >= 136) & (ys < 176)
    img[bs] = cr[bs]
    img[bs & (xs >= 64) & (xs < 192)] = GRASS2                # 縁（暗い緑）
    img[bs & (xs >= 72) & (xs < 184) & (ys >= 136)] = BLACK  # バックスクリーン
    # 球場の名前（ボードの上の黒い面）
    text(img, 84, 64, "MSX STADIUM", WHITE)
    # 外野フェンス：紺、上に黄色の線。広告板（地の色に字）と、センターの距離（122m）
    fence = (ys >= 176) & (ys < 192)
    img[fence] = NAVY
    img[(ys >= 176) & (ys < 178)] = YELLOW
    ads = [(8, 56, WHITE, RED, "MSX2"), (200, 248, YELLOW, NAVY, "PLAY"), (64, 104, RED, WHITE, "BALL"), (152, 192, WHITE, NAVY, "GAME")]
    for a, b, bg, fg, word in ads:
        img[180:190, a:b] = bg
        text(img, a + (b - a - len(word) * 8) // 2 + 1, 181, word, fg)
    text(img, 112, 181, "122ｍ", YELLOW)        # センターまでの距離
    # ウォーニングトラックと芝
    img[(ys >= 192) & (ys < 200)] = DIRT2
    grass = ys >= 200
    img[grass] = GRASS
    img[grass & (((xs // 16) % 2) == 1)] = GRASS2
    return img


def to_rows_2color(img):
    """各 8 ドットの行を 2 色に（多い 2 色に寄せる）"""
    out = img.copy()
    for y in range(H):
        for tx in range(W // 8):
            seg = out[y, tx * 8:tx * 8 + 8]
            vals, cnt = np.unique(seg, return_counts=True)
            if len(vals) > 2:
                keep = vals[np.argsort(-cnt)[:2]]
                for i, v in enumerate(seg):
                    if v not in keep:
                        seg[i] = keep[0]
    return out


def tiles(base, limit):
    """→ (各バンクの (柄, 色) の一覧, 名前表 32x27)。タイル番号は base から"""
    img = to_rows_2color(draw())
    nt = np.zeros((27, 32), np.int32)
    banks = [[] for _ in range(4)]
    for ty in range(27):
        b = ty >> 3
        for tx in range(32):
            blk = img[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]
            pat, col = [], []
            for r in range(8):
                row = blk[r]
                vals = sorted(set(row.tolist()))
                if len(vals) == 1:
                    pat.append(0)
                    col.append((vals[0] << 4) | vals[0])
                    continue
                bg, fg = vals[0], vals[1]
                bits = 0
                for i, v in enumerate(row):
                    if v == fg:
                        bits |= 0x80 >> i
                pat.append(bits)
                col.append((fg << 4) | bg)
            key = (tuple(pat), tuple(col))
            if key not in banks[b]:
                banks[b].append(key)
            nt[ty, tx] = base + banks[b].index(key)
    for b in range(4):
        assert len(banks[b]) <= limit, ("board bg tiles", b, len(banks[b]))
    return banks, nt


def preview(path):
    from PIL import Image
    img = to_rows_2color(draw())
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        for x in range(W):
            px[x, y] = rgb8(img[y, x])
    im.resize((W * 3, H * 3), Image.NEAREST).save(path)


if __name__ == "__main__":
    b, nt = tiles(52, 76)
    print([len(x) for x in b])
    preview("../build/board_bg.png")
