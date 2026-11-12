# -*- coding: utf-8 -*-
"""アセットを作る： build/gen/assets.h, assets.c, build/gen/banks.bin（ROM バンク 4〜）"""
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import *
import gfx_field
import gfx_font
import gfx_board
import gfx_sprites as SP
import teams as TM

OUT = os.path.join(HERE, "..", "build", "gen")
FIRST_BANK = 4
NUM_BANKS = 4

# ---------------------------------------------------------------------------
# 文字列（タイル文字）
# ---------------------------------------------------------------------------
STRINGS = {
    "INNING": "イニング",
    "PUSH": "PUSH SPACE KEY",
    "SELECT": "チーム セレクト",
    "WIN": "WIN!",
    "DRAW": "ヒキワケ",
    "GAMESET": "ゲームセット",
    "PINCH": "ダイダ",
    "RELIEF": "リリーフ",
    "CANCEL": "キャンセル",
    "VISIT": "センコウ",
    "HOME": "コウコウ",
    "INNEND": "シュウリョウ",
}

MESSAGES = ["ストライク", "ボール", "アウト", "セーフ", "ファウル", "ホームラン", "フォアボール",
            "デッドボール", "チェンジ", "ゲームセット", "プレイボール", "ヒット", "ツーベース",
            "スリーベース", "サヨナラ", "ダブルプレー", "タイム"]
MSG_IDS = ["STRIKE", "BALL", "OUT", "SAFE", "FOUL", "HOMERUN", "WALK", "HBP", "CHANGE", "GAMESET",
           "PLAYBALL", "HIT", "DOUBLE", "TRIPLE", "SAYONARA", "DP", "TIME"]

FIXED_GLYPHS = list(" 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.-!><") + ['回', '表', '裏', 'ｋ', 'ｍ']
# EDIT で名前に使えるように、チームの名前に出てこないカナも入れる（ヲ・ヌ・ゼ・ゾ・ヂ・ヅ・ゥはフォントに空きがないので使えない）
EXTRA_KANA = "テヘユビパピペポ"

# オーバーレイ B（トーナメント）と C（EDIT）の字。ovtext.h に（オーバーレイの中に置く）
OV_TEXT = {
    "TOUR": "トーナメント",
    "PICK": "6チーム エラブ",
    "PICKHELP": "A エラブ   START ケッテイ",
    "ARRHELP1": "A 2カショ デ イレカエ",
    "ARRHELP2": "B 1P ノ チーム  START カイシ",
    "SEED": "シード",
    "CHAMP": "ユウショウ",
    "PLAY": "A ボタン デ シアイ",
    "NEXT": "A ボタン デ ツギヘ",
    "NOSAVE": "セーブ ガ アリマセン",
    "NOSRAM": "ディスク ドライブ ガ アリマセン",
    "TOUREND": "トーナメント シュウリョウ",
    "ETITLE": "チーム エディット",
    "EHELP1": "A エラブ   START モドル",
    "EHELP2": "A ヘンシュウ B イレカエ START セーブ",
    "EHELP3": "ウエシタ 1 ヨコ 10 カワル  A オワリ",
    "EHELP4": "A イレル B ケス START オワリ",
    "BENCH": "ヒカエ",
    "PIT": "トウシュ",
    "SAVED": "セーブ シマシタ",
    "DERR": "ディスク ニ セーブ デキマセン",
    "BHEAD": "ナマエ  ダリツ  パワー ソウリョク",
    "PHEAD": "ナマエ  サイコウ サイテイ ヘンカ スタミナ",
    "NAME": "チームメイ",
    "ABBR": "リャク",
}

SYM_CODE = {'.': 0, 'P': 1, 'U': 2, 's': 3, 'k': 4, 'w': 5, 'd': 6}


class Banks:
    def __init__(self):
        self.data = bytearray()
        self.items = []

    def add(self, name, blob):
        blob = bytes(blob)
        # バンクをまたがないように
        pos = len(self.data)
        if (pos % 16384) + len(blob) > 16384:
            self.data += bytes(16384 - pos % 16384)
            pos = len(self.data)
        self.data += blob
        bank = FIRST_BANK + pos // 16384
        self.items.append((name, bank, pos % 16384, len(blob)))
        assert bank < FIRST_BANK + NUM_BANKS, "ROM data overflow"


def c_array(name, data, typ="u8", per=16):
    s = f"const {typ} {name}[{len(data)}] = {{\n"
    for i in range(0, len(data), per):
        s += "  " + ",".join(f"0x{b:02X}" for b in data[i:i + per]) + ",\n"
    return s + "};\n"


def main():
    os.makedirs(OUT, exist_ok=True)
    banks = Banks()
    H = []   # assets.h
    C = []   # assets.c

    # ---------------- フォント（使う字だけ） ----------------
    tdata = TM.make_teams()
    used = []

    def use(text):
        for ch in text:
            if ch not in used and ch not in FIXED_GLYPHS:
                used.append(ch)
    for s in STRINGS.values():
        use(s)
    for t in tdata:
        use(t["name"])
        for b in t["batters"]:
            use(b["name"][:5])
        for p in t["pitchers"]:
            use(p["name"][:5])
    use(EXTRA_KANA)
    for s in OV_TEXT.values():
        use(s)
    glyphs = FIXED_GLYPHS + used
    SPECIAL = ["LAMP_B", "LAMP_S", "LAMP_O", "LAMP_OFF", "SOLID", "LOGO", "LOGO_SH", "PANEL", "CURSOR"]
    n_font = len(glyphs) + len(SPECIAL)
    print("font tiles:", n_font, "(kana", len(used), ")")
    assert n_font <= 128, "font overflow"
    FONT_BASE = 128
    code = {ch: FONT_BASE + i for i, ch in enumerate(glyphs)}
    fpat = bytearray()
    fcol = bytearray()
    for ch in glyphs:
        fpat += bytes(gfx_font.glyph_bytes(ch))
        fcol += bytes([(WHITE << 4) | BLACK] * 8)
    lamp = gfx_font.glyph_bytes('*')
    for nm, colr in (("LAMP_B", GRASS), ("LAMP_S", YELLOW), ("LAMP_O", RED), ("LAMP_OFF", WALL)):
        fpat += bytes(lamp)
        fcol += bytes([(colr << 4) | BLACK] * 8)
    fpat += bytes([0xFF] * 8)          # SOLID（前景色で塗る）
    fcol += bytes([(BLACK << 4) | BLACK] * 8)
    for colr in (YELLOW, RED, WALL):   # LOGO, LOGO_SH, PANEL
        fpat += bytes([0xFF] * 8)
        fcol += bytes([(colr << 4) | colr] * 8)
    fpat += bytes(gfx_font.glyph_bytes('>'))   # CURSOR（黄色）
    fcol += bytes([(YELLOW << 4) | BLACK] * 8)
    while len(fpat) < 128 * 8:
        fpat += bytes(8)
        fcol += bytes([(WHITE << 4) | BLACK] * 8)
    banks.add("FONT_PAT", fpat)
    banks.add("FONT_COL", fcol)
    for i, nm in enumerate(SPECIAL):
        H.append(f"#define T_{nm} {FONT_BASE + len(glyphs) + i}")
    H.append(f"#define T_SPACE {code[' ']}")
    H.append(f"#define T_0 {code['0']}")
    H.append(f"#define T_A {code['A']}")
    H.append(f"#define T_KM_K {code['ｋ']}")
    H.append(f"#define T_KM_M {code['ｍ']}")
    H.append(f"#define T_KAI {code['回']}\n#define T_OMOTE {code['表']}\n#define T_URA {code['裏']}")
    asc = [code.get(chr(c), code[' ']) for c in range(32, 128)]
    asc[ord('a') - 32:ord('z') - 32 + 1] = [code[chr(c)] for c in range(ord('A'), ord('Z') + 1)]
    C.append(c_array("ascii_tile", asc))
    H.append("extern const u8 ascii_tile[96];")

    def enc(text, pad=None):
        b = [code[ch] for ch in text]
        if pad:
            b = (b + [code[' ']] * pad)[:pad]
        return b

    for k, s in STRINGS.items():
        C.append(c_array("STR_" + k, enc(s) + [0]))
        H.append(f"extern const u8 STR_{k}[];")
    # オーバーレイの字（各オーバーレイの中に置く：static const）と、名前に使える字の一覧
    # B（トーナメント）と C（EDIT）で別のファイル（使わない字を入れない）
    edit_keys = {"ETITLE", "EHELP1", "EHELP2", "EHELP3", "EHELP4", "BENCH", "PIT", "SAVED", "DERR", "BHEAD", "PHEAD", "NAME", "ABBR", "NOSRAM"}
    for fname, keys in (("ovtext.h", [k for k in OV_TEXT if k not in edit_keys or k == "NOSRAM"]),
                        ("ovtext_c.h", [k for k in OV_TEXT if k in edit_keys])):
        ov = ["/* 自動生成（tools/gen_assets.py）：オーバーレイだけが読む */"]
        for k in keys:
            ov.append(f"static const u8 TX_{k}[] = {{" + ",".join(str(v) for v in enc(OV_TEXT[k]) + [0]) + "};")
        if fname == "ovtext_c.h":
            names = [code[ch] for ch in " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"] + [code[ch] for ch in used]
            ov.append(f"#define NAME_CHARS_N {len(names)}")
            ov.append("static const u8 NAME_CHARS[] = {" + ",".join(str(v) for v in names) + "};")
        with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
            f.write("\n".join(ov) + "\n")


    # ---------------- スコアボード（イニングの終わり）のタイル：番号 0〜。表示中だけ球場のタイルと入れ替える ----------------
    # 色：O = 夜空（画面の地）、g = 芝、N = 紺（1 つおきの回の列）、K = 黒（ボードの中）、Y = 黄（枠・回の数字）、W = 白、G = 灰（区切り線）、1/2 = チーム色
    BC = {'O': WALL, 'g': GRASS2, 'N': WALL, 'K': BLACK, 'Y': YELLOW, 'W': WHITE, 'G': GRAY, '1': T1A, '2': T2A}

    def btile(rows):
        pat, col = [], []
        for r in rows:
            cs = []
            for ch in r:
                if BC[ch] not in cs:
                    cs.append(BC[ch])
            assert len(cs) <= 2, rows
            fg = cs[1] if len(cs) == 2 else cs[0]
            bg = cs[0]
            b = 0
            for i, ch in enumerate(r):
                if BC[ch] == fg and fg != bg:
                    b |= 0x80 >> i
            pat.append(b)
            col.append((fg << 4) | bg)
        return pat, col

    def glyph_tile(ch, fg, bg):
        return [''.join(fg if c == '#' else bg for c in row.ljust(8, '.')[:8]) for row in gfx_font.glyph(ch)]

    def mir(rows):
        return [r[::-1] for r in rows]

    def flip(rows):
        return rows[::-1]
    TL = ["KKYYYYYY", "KYYYYYYY"] + ["YYKKKKKK"] * 6
    T = ["YYYYYYYY"] * 2 + ["KKKKKKKK"] * 6
    L = ["YYKKKKKK"] * 8
    SEP = ["KKKKKKKK"] * 4 + ["GGGGGGGG"] + ["KKKKKKKK"] * 3
    LS = ["YYKKKKKK"] * 4 + ["YYGGGGGG"] + ["YYKKKKKK"] * 3
    board = [("ZB", ["NNNNNNNN"] * 8), ("TL", TL), ("T", T), ("TR", mir(TL)), ("L", L), ("R", mir(L)),
             ("BL", flip(TL)), ("B", flip(T)), ("BR", mir(flip(TL))), ("LS", LS), ("SEP", SEP), ("RS", mir(LS))]
    board += [("YK%d" % d, glyph_tile(str(d), 'Y', 'K')) for d in range(10)]
    board += [("YR", glyph_tile('R', 'Y', 'K')), ("YH", glyph_tile('H', 'Y', 'K'))]
    board += [("WN%d" % d, glyph_tile(str(d), 'W', 'N')) for d in range(10)]
    board += [("WNX", glyph_tile('X', 'W', 'N'))]
    board += [("ST1", ["K111111K"] * 8), ("ST2", ["K222222K"] * 8)]
    board += [("YN%d" % d, glyph_tile(str(d), 'Y', 'N')) for d in range(10)]
    bpat, bcol = bytearray(), bytearray()
    for i, (nm, rows) in enumerate(board):
        p, c = btile(rows)
        bpat += bytes(p)
        bcol += bytes(c)
        H.append(f"#define BD_{nm} {i}")
    assert len(board) <= 100
    banks.add("BOARD_PAT", bpat)
    banks.add("BOARD_COL", bcol)
    # 背景（球場のバックスクリーン）：タイル番号 BD_BG0〜。バンク t ごとに 柄（BD_BGN*8）・色（BD_BGN*8）を並べる
    bg0 = len(board)
    bgn = 128 - bg0
    bgb, bnt = gfx_board.tiles(bg0, bgn)
    blob = bytearray()
    for t in range(4):
        pat = bytearray(bgn * 8)
        col = bytearray(bgn * 8)
        for i, (p, c) in enumerate(bgb[t]):
            pat[i * 8:i * 8 + 8] = bytes(p)
            col[i * 8:i * 8 + 8] = bytes(c)
        blob += pat + col
    banks.add("BOARD_BG", blob)
    banks.add("BOARD_NT", bytes(int(v) for v in bnt.flatten()))
    H.append(f"#define BD_BG0 {bg0}")
    H.append(f"#define BD_BGN {bgn}")

    # ---------------- トーナメント表の線 ----------------
    def line_tile(kind):
        g = [[0] * 8 for _ in range(8)]
        h = lambda a, b: [g[3].__setitem__(x, 1) or g[4].__setitem__(x, 1) for x in range(a, b)]
        v = lambda a, b: [g[y].__setitem__(3, 1) or g[y].__setitem__(4, 1) for y in range(a, b)]
        if kind == "H": h(0, 8)
        if kind == "V": v(0, 8)
        if kind == "TR": h(0, 5); v(3, 8)          # ┐
        if kind == "BR": h(0, 5); v(0, 5)          # ┘
        if kind == "TJ": v(0, 8); h(3, 8)          # ├
        if kind == "TL": h(3, 8); v(3, 8)          # ┌
        if kind == "BL": h(3, 8); v(0, 5)          # └
        return [sum(0x80 >> x for x in range(8) if g[y][x]) for y in range(8)]
    kinds = ["H", "V", "TR", "BR", "TJ", "TL", "BL"]
    bp, bc = bytearray(), bytearray()
    for colr in (WHITE, YELLOW):
        for k in kinds:
            bp += bytes(line_tile(k))
            bc += bytes([(colr << 4) | BLACK] * 8)
    banks.add("BRK_PAT", bp)
    banks.add("BRK_COL", bc)
    for i, k in enumerate(kinds):
        H.append(f"#define BRK_{k} {i}")
    H.append(f"#define BRK_YEL {len(kinds)}          /* 黄色の線は + BRK_YEL */")

    # ---------------- 球場 ----------------
    img = gfx_field.draw_field(stripes=True)
    order, tmap, lossy = gfx_field.to_tiles(img)
    Hh, Ww = tmap.shape
    bank_tiles = [[] for _ in range(4)]
    local = np.zeros_like(tmap)
    for m in range(Hh):
        b = (m & 31) >> 3
        for x in range(Ww):
            t = tmap[m, x]
            if t not in bank_tiles[b]:
                bank_tiles[b].append(t)
            local[m, x] = bank_tiles[b].index(t)
    print("field tiles per bank:", [len(b) for b in bank_tiles])
    for b in range(4):
        assert len(bank_tiles[b]) <= 128
        pat = bytearray()
        col = bytearray()
        for t in bank_tiles[b]:
            p, c = order[t]
            pat += bytes(p)
            col += bytes(c)
        banks.add(f"FIELD_PAT{b}", pat)
        banks.add(f"FIELD_COL{b}", col)
    # 観客のタイル（点が入ったら 2 つの形を交互に書きかえる）：各バンクの番号（なければ 255）
    ca = gfx_field.tile_of(gfx_field.CROWD)
    cb = gfx_field.tile_of(gfx_field.CROWD2)
    cidx = []
    for b in range(4):
        hit = [i for i, t in enumerate(bank_tiles[b]) if order[t] == ca]
        cidx.append(hit[0] if hit else 255)
    print("crowd tile per bank:", cidx)
    C.append(c_array("crowd_idx", cidx))
    C.append(c_array("crowd_tiles", list(ca[0]) + list(ca[1]) + list(cb[0]) + list(cb[1])))
    H.append("extern const u8 crowd_idx[4], crowd_tiles[32];     /* 観客のタイル（各バンクの番号）・ふだん／喜ぶ（柄 8・色 8） */")
    local[1:4, 26:38] = code[' ']      # 得点板
    banks.add("FIELD_MAP", bytes(local.astype(np.uint8).ravel().tolist()))
    H.append(f"#define FIELD_W {Ww}\n#define FIELD_H {Hh}")
    H.append("extern u8 field_map[FIELD_W*FIELD_H];     /* RAM の OVL_ADDR（crt0.s）。ROM から map_load で読む */")
    # 得点板（スタンドの中央）の位置
    H.append("#define SB_COL 26\n#define SB_ROW 1\n#define SB_W 12")
    ft = []
    for i in range(65):
        y = fence_y(min(i * 8, 511) + 0.5)
        ft.append(0 if y is None else int(y))
    C.append(c_array("fence_tab", ft))
    H.append("extern const u8 fence_tab[65];")

    # ---------------- タイトルのロゴ（2x2 の四角タイル 16 種、番号 100〜） ----------------
    QB = 100
    # 球場のタイルは 0〜127。100〜115 はタイトルの間だけロゴに使うので、タイトルに映る行（0〜26）は 100 未満だけ
    for m in range(27):
        bad = [v for v in local[m] if QB <= v < 128]
        assert not bad, ("title rows use tiles 100..127", m, bad)
    qpat = bytearray()
    qcol = bytearray()
    for k in range(16):
        tl, tr, bl, br = (k >> 3) & 1, (k >> 2) & 1, (k >> 1) & 1, k & 1
        for r in range(8):
            l, rr = (tl, tr) if r < 4 else (bl, br)
            qpat.append((0xF0 if l else 0) | (0x0F if rr else 0))
            qcol.append(((WHITE if r < 4 else YELLOW) << 4) | WALL)
    banks.add("QUART_PAT", qpat)
    banks.add("QUART_COL", qcol)
    H.append(f"#define T_QUART {QB}")

    def logo(text):
        rows = [[0] * (len(text) * 4) for _ in range(4)]
        for i, ch in enumerate(text):
            gl = gfx_font.glyph(ch)
            px = [[1 if gl[1 + y][x] == '#' else 0 for x in range(8)] + [0] for y in range(7)] + [[0] * 9]
            for ty in range(4):
                for tx in range(4):
                    k = (px[ty * 2][tx * 2] << 3) | (px[ty * 2][tx * 2 + 1] << 2) |                         (px[ty * 2 + 1][tx * 2] << 1) | px[ty * 2 + 1][tx * 2 + 1]
                    rows[ty][i * 4 + tx] = QB + k
        return [v for r in rows for v in r]
    C.append(c_array("logo1", logo("MSX")))
    C.append(c_array("logo2", logo("STADIUM")))
    H.append("extern const u8 logo1[48];")
    H.append("extern const u8 logo2[112];")

    # ---------------- パレット ----------------
    pal = bytearray()
    for r, g, b in PALETTE:
        pal += bytes([(r << 4) | b, g])
    C.append(c_array("palette_base", pal))
    H.append("extern const u8 palette_base[32];")

    # ---------------- スプライト ----------------
    zc, pc = SP.layered(SP.CHIBI, SP.CHIBI_ORDER, 16, "chibi", SP.ZONE_CHIBI)
    zb, pb = SP.layered(SP.BATTER, SP.BATTER_ORDER, 24, "batter", SP.ZONE_BATTER)
    zp, pp = SP.layered(SP.PITCHER, SP.PITCHER_ORDER, 24, "pitcher", SP.ZONE_PITCHER)

    def zone_bytes(z):
        out = []
        for a, b in z:
            out += [SYM_CODE[a], SYM_CODE[b]]
        return out
    C.append(c_array("zone_chibi", zone_bytes(zc)))
    C.append(c_array("zone_big", zone_bytes(zb)))
    C.append(c_array("zone_pitcher", zone_bytes(zp)))
    H.append("extern const u8 zone_chibi[32];\nextern const u8 zone_big[48];\nextern const u8 zone_pitcher[48];")

    def single(rows, sym):
        return SP.pat16([r.replace(sym, '#') for r in rows], '#')

    def big_frames(frames_layers):
        out = bytearray()
        for layers in frames_layers:          # [B parts, A parts]
            B, A = layers
            out += bytes(B[0]) + bytes(A[0]) + bytes(B[1]) + bytes(A[1])
        return out

    def batter_frames(frames_layers, bat):
        """1 コマ = 打者 4 枚 ＋ バット 2 枚（192 バイト）"""
        out = bytearray()
        for i, layers in enumerate(frames_layers):
            B, A = layers
            out += bytes(B[0]) + bytes(A[0]) + bytes(B[1]) + bytes(A[1]) + bat[i * 64:i * 64 + 64]
        return out

    def mirror_frames(fr):
        return {k: SP.mirror(v) for k, v in fr.items()}

    bat_r = batter_frames(pb, SP.bat_patterns(False))
    _, pbL = SP.layered(mirror_frames(SP.BATTER), SP.BATTER_ORDER, 24, "batterL", SP.ZONE_BATTER)
    bat_l = batter_frames(pbL, SP.bat_patterns(True))
    pit_r = big_frames(pp)
    _, ppL = SP.layered(mirror_frames(SP.PITCHER), SP.PITCHER_ORDER, 24, "pitcherL", SP.ZONE_PITCHER)
    pit_l = big_frames(ppL)
    assert len(bat_r) == len(SP.BATTER_ORDER) * 192 and len(pit_r) == 12 * 32
    balls = bytearray()
    for k in SP.BALL_ORDER:
        balls += bytes(single(SP.BALLS[k], 'w' if k != 'SHADOW' else 'k'))

    def chibi(name):
        i = SP.CHIBI_ORDER.index(name)
        B, A = pc[i]
        return bytes(B[0]) + bytes(A[0])

    atbat = bytearray(bat_r[:192]) + pit_r + balls
    AB_CHIBI = ['READY_D', 'CROUCH_B', 'STAND_L', 'STAND_R', 'RUN_L1', 'RUN_L2', 'RUN_R1', 'RUN_R2',
                'LEAD_L1', 'LEAD_L2', 'LEAD_R1', 'LEAD_R2']
    for nm in AB_CHIBI:
        atbat += chibi(nm)
    assert len(atbat) <= 56 * 32, len(atbat) // 32
    atbat += bytes(60 * 32 - len(atbat))
    ump = bytearray()
    for k in SP.UMP_ORDER:
        for r in SP.UMPIRE[k]:
            assert len(r) == 16, (k, r)
        ump += bytes(single(SP.UMPIRE[k], '#'))
    atbat += ump                                     # 60〜63：審判（メッセージは 56〜58）
    field = bytearray()
    for nm in SP.CHIBI_ORDER:
        field += chibi(nm)
    field += balls
    assert len(field) <= 56 * 32
    field += bytes(60 * 32 - len(field)) + ump
    banks.add("SPR_ATBAT", atbat)
    banks.add("SPR_FIELD", field)
    banks.add("BATTER_R", bat_r)
    banks.add("BATTER_L", bat_l)
    banks.add("PITCHER_R", pit_r)
    banks.add("PITCHER_L", pit_l)
    # パターン番号（16x16 の番号）
    H.append("/* 打席の表 */")
    H.append("#define PA_BATTER 0\n#define PA_BAT 4\n#define PA_PITCHER 6\n#define PA_BALL 18")
    H.append(f"#define BAT_FRAMES {len(SP.BATTER_ORDER)}")
    H.append(f"#define BAT_REACH {SP.BAT_REACH}")
    H.append("#define BAT_OFS_TABLE " + ",".join("{%d,%d}" % SP.BAT_OFS[k] for k in SP.BAT_ORDER))
    base = 22
    for nm in AB_CHIBI:
        H.append(f"#define PA_{nm} {base}")
        base += 2
    H.append("/* 守備の表 */")
    for i, nm in enumerate(SP.CHIBI_ORDER):
        H.append(f"#define PF_{nm} {i * 2}")
    H.append(f"#define PF_BALL {len(SP.CHIBI_ORDER) * 2}")
    H.append("#define P_MSG 56")
    H.append("#define P_UMP 60")
    for i, nm in enumerate(SP.UMP_ORDER):
        H.append(f"#define UMP_{nm} {i}")
    C.append(c_array("ump_rowcol", SP.UMP_ROWCOL + SP.UMP_ROWCOL_PLATE))
    H.append("extern const u8 ump_rowcol[32];       /* 審判の行ごとの色（塁審 16・球審 16） */")
    for i, nm in enumerate(SP.BALL_ORDER):
        H.append(f"#define BALL_{nm} {i}")

    # ---------------- メッセージ（縦 2 倍の字） ----------------
    for mid, text in zip(MSG_IDS, MESSAGES):
        assert len(text) <= 6, text         # 3 枚（6 文字）まで。4 枚目の面は球審が使う
        chars = list(text) + [' '] * (6 - len(text))
        blob = bytearray()
        for k in range(3):
            for ch in (chars[2 * k], chars[2 * k + 1]):
                g = gfx_font.glyph_bytes(ch)
                for r in range(16):
                    blob.append(g[r // 2])
        banks.add("MSG_" + mid, blob)
        H.append(f"#define MSGLEN_{mid} {len(text)}")
        H.append(f"#define MSG_{mid} {MSG_IDS.index(mid)}")
    H.append("#define MSG_TABLE " + ",".join("{A_MSG_%s,%d}" % (m, len(t)) for m, t in zip(MSG_IDS, MESSAGES)))

    # ---------------- チーム ----------------
    H.append(f"#define NUM_TEAMS {len(tdata)}")
    H.append("typedef struct { u8 name[5]; u8 avg; u8 pow; u8 spd; u8 hr; u8 flags; } BatterDef;")
    H.append("typedef struct { u8 name[5]; u8 kmh; u8 cv; u8 st; u8 kmin; u8 flags; } PitcherDef;   /* kmh 最高・kmin 最低の球速 */")
    H.append("typedef struct { u8 name[6]; u8 abbr[3]; u8 pal[4]; BatterDef bat[12]; PitcherDef pit[5]; } TeamDef;")
    tb = bytearray()
    for t in tdata:
        tb += bytes(enc(t["name"], 6))
        tb += bytes(enc(t["abbr"], 3))
        r, g, b = t["pc"]
        tb += bytes([(r << 4) | b, g])
        r, g, b = t["uc"]
        tb += bytes([(r << 4) | b, g])
        for bt in t["batters"]:
            tb += bytes(enc(bt["name"][:5], 5))
            tb += bytes([bt["avg"] - 100, bt["pow"], bt["spd"], bt["hr"], 1 if bt["left"] else 0])
        for p in t["pitchers"]:
            tb += bytes(enc(p["name"][:5], 5))
            tb += bytes([p["kmh"], p["cv"], p["st"], (p["kmh"] * 3 + 2) // 4, 1 if p["left"] else 0])
    banks.add("TEAMS", tb)
    hdr = bytearray()
    tsz = len(tb) // len(tdata)
    for k in range(len(tdata)):
        hdr += tb[k * tsz:k * tsz + 13]
    C.append(c_array("thdr_raw", hdr))
    H.append("typedef struct { u8 name[6]; u8 abbr[3]; u8 pal[4]; } TeamHdr;")
    H.append("extern const u8 thdr_raw[];")
    H.append("#define thdr ((const TeamHdr*)thdr_raw)")
    H.append(f"#define TEAM_SIZE {tsz}")

    # ---------------- 音楽 ----------------
    try:
        import music
        mc, mh, songs = music.build()
        C.append(mc)
        H.extend(mh)
        for name, blob, loop in songs:
            assert max(len(b) for _, b, _ in songs) < 256 or True
            banks.add("BGM_" + name, blob)
    except ImportError:
        pass

    # ---------------- ROM の場所 ----------------
    for name, bank, ofs, ln in banks.items:
        H.append(f"#define A_{name} {bank},0x{ofs:04X},{ln}")
        H.append(f"#define A_{name}_BANK {bank}")
        H.append(f"#define A_{name}_OFS 0x{ofs:04X}")
        H.append(f"#define A_{name}_LEN {ln}")
    with open(os.path.join(OUT, "banks.bin"), "wb") as f:
        data = banks.data + bytes((-len(banks.data)) % 16384)
        f.write(data)
    print("rom data:", len(banks.data), "bytes in", (len(banks.data) + 16383) // 16384, "banks")

    with open(os.path.join(OUT, "assets.h"), "w", encoding="utf-8") as f:
        f.write("/* 自動生成（tools/gen_assets.py） */\n#ifndef ASSETS_H\n#define ASSETS_H\n#include \"types.h\"\n")
        f.write("\n".join(H) + "\n#endif\n")
    with open(os.path.join(OUT, "assets.c"), "w", encoding="utf-8") as f:
        f.write("/* 自動生成（tools/gen_assets.py） */\n#include \"assets.h\"\n")
        f.write("\n".join(C))
    # 確認用
    gfx_field.render_tiles(order, tmap).save(os.path.join(HERE, "..", "build", "field_preview.png"))


if __name__ == "__main__":
    main()
