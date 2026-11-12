# -*- coding: utf-8 -*-
"""球場の絵（512x416 ドット）を描き、G3 のタイル（各ライン 2 色）に変換する"""
import numpy as np
from common import *


def poly_mask(pts, W, H):
    from PIL import Image, ImageDraw
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).polygon(pts, fill=1, outline=1)
    return np.array(im, bool)


def sym(pts, cx):
    """左半分の点列（上→下）から左右対称の多角形を作る"""
    left = [(cx + x, y) for x, y in pts]
    right = [(cx - x - 1, y) for x, y in reversed(pts)]
    return left + right


def draw_field(stripes=True):
    W, H = WORLD_W, WORLD_H
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
    xs += 0.5
    ys += 0.5
    hx, hy = HOME
    dx = xs - hx
    dy = hy - ys
    adx = np.abs(dx)
    img = np.full((H, W), GRASS, np.uint8)

    fair = (dy >= 0) & (adx * 69 <= dy * 92)
    img[~fair] = GRASS2
    if stripes:
        stripe = ((ys // 16).astype(int) % 2 == 1) & fair & (ys < 216)
        img[stripe] = GRASS2

    # 内野の土（折れ線の多角形：傾き 0, 1/2, 1, 2）
    mx, my = MOUND
    arc = poly_mask(sym([(-32, 214), (-80, 238), (-104, 262), (-116, 286), (-116, 318),
                         (-100, 350), (-60, 350)], mx), W, H)
    img[arc & fair] = DIRT
    # 内野の芝（ダイヤモンドの内側。辺の傾きは塁間と同じ 3/4）
    cy = BASE1[1]
    inner = (adx / 79.0 + np.abs(ys - cy) / 59.25) <= 1.0
    img[inner] = GRASS
    # ファウルラインに沿った土の帯（ホームのサークル〜一塁・三塁の土まで、線の両側 6 ドット）
    dline = (adx * 69 - dy * 92) / 115.0
    img[(np.abs(dline) < 6) & (dy > 0) & (dy < 80)] = DIRT
    # ホーム周り（八角形）
    # バッターボックスの外の線（x 228・283）と芝の境目が同じ 8 ドットに入らないよう、横は ±34 まで広げる
    home_c = poly_mask(sym([(-12, hy - 24), (-34, hy - 16), (-34, hy - 8), (-34, hy + 12),
                            (-24, hy + 24), (-8, hy + 28)], hx), W, H)
    img[home_c] = DIRT
    # マウンド
    mound = poly_mask(sym([(-6, my - 10), (-14, my - 6), (-14, my + 4), (-6, my + 10)], mx), W, H)
    img[mound] = DIRT
    img[(np.abs(xs - mx) <= 4) & (ys >= my - 2) & (ys <= my)] = WHITE

    # フェンス・ウォーニングトラック・スタンド
    fy = np.array([fence_y(x + 0.5) if fence_y(x + 0.5) is not None else -1 for x in range(W)])
    FY = fy[None, :].repeat(H, 0)
    has = FY >= 0
    track = has & (ys > FY) & (ys <= FY + 10)
    img[track] = DIRT2
    wall = has & (ys > FY - WALL_H) & (ys <= FY)
    img[wall] = WALL
    stands = has & (ys <= FY - WALL_H)
    side = (xs < WALL_X0) | (xs >= WALL_X1)
    img[side] = 0
    sidewall = ((xs >= WALL_X0 - 8) & (xs < WALL_X0)) | ((xs >= WALL_X1) & (xs < WALL_X1 + 8))
    img[sidewall & (ys > 208 - WALL_H)] = WALL
    img[stands] = 0
    # ファウル側のトラック
    side_track = ~side & ((xs < WALL_X0 + 8) | (xs >= WALL_X1 - 8)) & ~has
    img[side_track & (ys < BACKSTOP_Y)] = DIRT2
    st2 = ~side & ((xs < WALL_X0 + 8) | (xs >= WALL_X1 - 8)) & has & (ys > FY + 10)
    img[st2] = DIRT2
    bs = (ys >= BACKSTOP_Y) & ~side
    img[bs] = WALL
    img[(ys >= BACKSTOP_Y + 8)] = 0

    # ファウルゾーンの壁（45 度）とベンチ。dr = 壁からの外への距離（横方向のドット）
    xi, yi = xs - 0.5, ys - 0.5
    dr = np.maximum(xi + yi - SIDE_R, yi - xi - SIDE_L)
    near_home = yi < BACKSTOP_Y
    out_side = (dr >= 0) & near_home & ~side & ~(has & (ys <= FY))
    bench = (yi >= DUGOUT_Y[0]) & (yi < DUGOUT_Y[1])
    img[out_side] = 0                                           # 観客席
    img[out_side & (dr < 8)] = WALL                             # 低いフェンス（ベンチの前も同じ色：ホームランでいっしょに光る）
    img[out_side & (dr >= 8) & (dr < 24) & bench] = GRAY        # ベンチの屋根
    # 観客（8x8 の繰り返し。各ラインは 2 色まで）
    cr = np.array(CROWD, np.uint8)
    tile_cr = cr[(ys.astype(int) % 8), (xs.astype(int) % 8)]
    m = img == 0
    img[m] = tile_cr[m]
    # スタンド中央の得点板（中の 12x3 マスは文字タイルにする）
    img[(ys < 40) & (xs >= 200) & (xs < 312)] = WALL

    # 白線（ファウルライン）
    d = (adx * 69 - dy * 92) / 115.0
    fline = (np.abs(d) < 0.75) & (dy >= -1) & (ys > FY) & ~side & (img != WALL) & (img != DIRT2)
    img[fline] = WHITE
    # ベース
    for bx, by in (BASE1, BASE2, BASE3):
        img[(np.abs(xs - bx) / 5.0 + np.abs(ys - by) / 4.0) <= 1.0] = WHITE
    # ホームベース
    hp = (np.abs(xs - hx) <= 5) & (ys >= hy - 4) & (ys <= hy + 1)
    hp |= (ys > hy + 1) & (ys <= hy + 4) & (np.abs(xs - hx) <= 5 - (ys - hy - 1) * 1.6)
    img[hp] = WHITE
    # バッターボックス（ファウルラインはボックスの中には引かない）
    for x0 in (230, 266):
        x1 = x0 + 16
        y0, y1 = 364, 388
        inner = (xs > x0) & (xs < x1 - 1) & (ys > y0) & (ys < y1 - 1)
        img[inner & fline] = DIRT
        box = ((((np.abs(xs - x0 - 0.5) < 0.6) | (np.abs(xs - x1 + 0.5) < 0.6)) & (ys >= y0) & (ys < y1)) |
               (((np.abs(ys - y0 - 0.5) < 0.6) | (np.abs(ys - y1 + 0.5) < 0.6)) & (xs >= x0) & (xs < x1)))
        img[box] = WHITE
    # ポール
    for px in (WALL_X0 - 2, WALL_X1):
        img[(xs >= px) & (xs < px + 2) & (ys >= 150) & (ys <= 208)] = YELLOW
    return img


# 観客の 8x8（各ラインは 2 色まで）。CROWD = ふだん、CROWD2 = 点が入って喜ぶ（1 ドット上に跳ね、手を上げる）
_G, _S, _R, _W, _Y = GRAY, SKIN, RED, WHITE, YELLOW
CROWD = [
    [_G, _S, _G, _G, _G, _S, _G, _G],
    [_R, _R, _G, _G, _G, _R, _R, _G],
    [_G, _G, _G, _G, _G, _G, _G, _G],
    [_G, _G, _G, _S, _G, _G, _G, _S],
    [_G, _G, _W, _W, _G, _G, _G, _W],
    [_G, _G, _G, _G, _G, _G, _G, _G],
    [_S, _G, _G, _G, _S, _G, _G, _G],
    [_Y, _Y, _G, _G, _Y, _Y, _G, _G],
]
CROWD2 = [CROWD[(r + 1) % 8][:] for r in range(8)]
CROWD2[1] = [_S if x in (0, 2, 4, 6) else _G for x in range(8)]     # 頭（3・7 列）の上に両手
CROWD2[4] = [_S if x in (1, 3, 5, 7) else _G for x in range(8)]     # 頭（0・4 列）の上に両手


def tile_of(block):
    """8x8（各ラインは 2 色まで）→ (柄 8 バイト, 色 8 バイト)。to_tiles と同じ決め方"""
    pat, col = [], []
    for row in block:
        vals = sorted(set(int(v) for v in row))
        assert len(vals) <= 2
        if len(vals) == 1:
            pat.append(0)
            col.append((vals[0] << 4) | vals[0])
            continue
        bg, fg = vals
        pat.append(sum(0x80 >> i for i, v in enumerate(row) if v == fg))
        col.append((fg << 4) | bg)
    return tuple(pat), tuple(col)


def to_tiles(img):
    """画像 → (タイル辞書, マップ)。各ラインは使用数の多い 2 色に寄せる"""
    H, W = img.shape
    tiles = {}
    order = []
    tmap = np.zeros((H // 8, W // 8), np.int32)
    lossy = 0
    for ty in range(H // 8):
        for tx in range(W // 8):
            blk = img[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]
            pat = []
            col = []
            for r in range(8):
                row = blk[r]
                vals, cnt = np.unique(row, return_counts=True)
                if len(vals) > 2:
                    lossy += 1
                    idx = np.argsort(-cnt)[:2]
                    keep = sorted(vals[idx])
                else:
                    keep = sorted(vals)
                if len(keep) == 1:
                    pat.append(0)
                    col.append((keep[0] << 4) | keep[0])
                    continue
                bg, fg = keep[0], keep[1]
                bits = 0
                for i, v in enumerate(row):
                    if v not in keep:
                        v = fg if abs(int(v) - int(fg)) < abs(int(v) - int(bg)) else bg
                    if v == fg:
                        bits |= 0x80 >> i
                pat.append(bits)
                col.append((fg << 4) | bg)
            key = (tuple(pat), tuple(col))
            if key not in tiles:
                tiles[key] = len(order)
                order.append(key)
            tmap[ty, tx] = tiles[key]
    return order, tmap, lossy


def render_tiles(order, tmap):
    from PIL import Image
    H, W = tmap.shape
    im = Image.new("RGB", (W * 8, H * 8))
    px = im.load()
    for ty in range(H):
        for tx in range(W):
            pat, col = order[tmap[ty, tx]]
            for r in range(8):
                fg, bg = col[r] >> 4, col[r] & 15
                for c in range(8):
                    v = fg if pat[r] & (0x80 >> c) else bg
                    px[tx * 8 + c, ty * 8 + r] = rgb8(v)
    return im


if __name__ == "__main__":
    import sys
    img = draw_field(stripes="nostripe" not in sys.argv)
    order, tmap, lossy = to_tiles(img)
    print("unique tiles:", len(order), "lossy rows:", lossy)
    im = render_tiles(order, tmap)
    im.save("../build/field_preview.png")
    im.resize((im.width * 2, im.height * 2)).save("../build/field_preview2x.png")
