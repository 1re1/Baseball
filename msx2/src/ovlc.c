/* オーバーレイ C（ROM のバンク 9 → RAM の OVL_ADDR〜）：EDIT モード。
 * チーム名・略称、選手名、打順（スタメン 8 人と控え 4 人の入れかえ）、打率・パワー・走力、
 * 投手の名前・最高と最低の球速・変化・スタミナを書きかえて、フロッピーディスクに保存する。
 * 本体とは別にリンクする（RAM の変数は置かない。編集中のチームは本体の tm[0]） */
#include "game.h"
#include "ovtext_c.h"

void screen_edit(void);
void screen_scoreboard(u8 final);

/* 入口の表（game.h の OVC_*） */
void ovlc_entry(void) __naked
{
    __asm
        jp   _screen_edit
        jp   _screen_scoreboard
    __endasm;
}

#define ED (&tm[0])
#define HELP_ROW 24

static void oc_sync(void)
{
    wait_vblank();
    spr_commit();
    input_update();
}

/* スクロールしない画面にする（名前表 0・枠は黒） */
static void oc_fixed(void)
{
    vdp_display(0);
    scroll_invalidate();
    vdp_reg(2, 0x10);
    vdp_reg(18, 0);
    vdp_reg(23, 0);
    vdp_reg(7, 0x01);
    vdp_fill(VR_NT0, T_SPACE, 1024);
    view_cx = 0;
    view_y = 0;
    spr_hide_all();
    spr_commit();
    pad_new[0] = pad_new[1] = pad_new[2] = 0;
}

static void oc_screen(void)
{
    oc_fixed();
    nt_text(8, 0, TX_ETITLE);
}

static void help(const u8* s)
{
    nt_fill(0, HELP_ROW, T_SPACE, 32);
    nt_text(1, HELP_ROW, s);
}

/* 行：0 チーム、1〜12 打者（1〜8 がスタメンの打順、9〜12 が控え）、13〜17 投手 */
static const u8 cx_team[2] = { 5, 16 };
static const u8 cx_bat[4] = { 2, 8, 14, 19 };
static const u8 cx_pit[5] = { 2, 8, 13, 18, 22 };

static u8 row_y(u8 r)
{
    return r == 0 ? 2 : (r <= 12 ? 4 + r : 5 + r);
}

static u8 nfields(u8 r)
{
    return r == 0 ? 2 : (r <= 12 ? 4 : 5);
}

static u8 field_x(u8 r, u8 f)
{
    return r == 0 ? cx_team[f] : (r <= 12 ? cx_bat[f] : cx_pit[f]);
}

static void draw_row(u8 r)
{
    u8 y = row_y(r);
    if (r == 0) {
        nt_text(1, y, TX_ABBR);
        nt_n(6, y, ED->abbr, 3);
        nt_text(10, y, TX_NAME);
        nt_n(17, y, ED->name, 6);
    } else if (r <= 12) {
        BatterDef* b = &ED->bat[r - 1];
        nt_tile(0, y, r <= 8 ? T_0 + r : T_SPACE);
        nt_n(3, y, b->name, 5);
        nt_tile(9, y, ascii_tile['.' - 32]);
        nt_num(10, y, b->avg + 100, 3);
        nt_num(15, y, b->pow, 1);
        nt_num(20, y, b->spd, 1);
    } else {
        PitcherDef* p = &ED->pit[r - 13];
        nt_n(3, y, p->name, 5);
        nt_num(9, y, p->kmh, 3);
        nt_num(14, y, p->kmin, 3);
        nt_num(19, y, p->cv, 1);
        nt_num(23, y, p->st, 1);
    }
}

static void draw_team(void)
{
    u8 r;
    nt_text(3, 4, TX_BHEAD);
    nt_text(26, 13, TX_BENCH);
    nt_text(3, 17, TX_PHEAD);
    for (r = 0; r < 18; r++) draw_row(r);
}

/* 数の欄：番地と範囲 */
static u8* num_ptr(u8 r, u8 f, u8* lo, u8* hi)
{
    *lo = 1;
    *hi = 9;
    if (r >= 1 && r <= 12) {
        BatterDef* b = &ED->bat[r - 1];
        if (f == 1) {
            *lo = 0;
            *hi = 255;
            return &b->avg;
        }
        return f == 2 ? &b->pow : &b->spd;
    } else {
        PitcherDef* p = &ED->pit[r - 13];
        if (f == 1) {
            *lo = p->kmin > 100 ? p->kmin : 100;
            *hi = 165;
            return &p->kmh;
        }
        if (f == 2) {
            *lo = 70;
            *hi = p->kmh;
            return &p->kmin;
        }
        return f == 3 ? &p->cv : &p->st;
    }
}

/* 数を変える：↑↓ で 1、←→ で 10、A か B で終わる */
static void edit_num(u8 r, u8 f)
{
    u8 lo, hi;
    u8* v = num_ptr(r, f, &lo, &hi);
    help(TX_EHELP3);
    for (;;) {
        s16 x = *v;
        oc_sync();
        if (pad_new[2] & K_UP) x++;
        if (pad_new[2] & K_DOWN) x--;
        if (pad_new[2] & K_RIGHT) x += 10;
        if (pad_new[2] & K_LEFT) x -= 10;
        if (x < lo) x = lo;
        if (x > hi) x = hi;
        if ((u8)x != *v) {
            *v = (u8)x;
            draw_row(r);
            sfx_play(SFX_CURSOR);
        }
        if (pad_new[2] & (K_A | K_B)) break;
    }
    help(TX_EHELP2);
}

/* 字の表の k 番目のます（14 列）に t を書く（割り算のライブラリを使わない） */
static void cell(u8 k, u8 x0, u8 t)
{
    u8 r = 0;
    while (k >= 14) {
        k -= 14;
        r++;
    }
    nt_tile(x0 + k * 2, 7 + r * 2, t);
}

/* 名前を書く：字の表から選ぶ。A で入れる、B で 1 つ消す、START で終わり */
static void edit_name(u8* name, u8 n)
{
    u8 c = 0, pos = 0, k, prev = 0;
    oc_screen();
    for (k = 0; k < NAME_CHARS_N; k++) cell(k, 2, NAME_CHARS[k]);
    help(TX_EHELP4);
    vdp_display(1);
    for (;;) {
        nt_n(10, 3, name, n);
        nt_fill(10, 4, T_SPACE, 8);
        nt_tile(10 + pos, 4, T_LAMP_S);
        cell(prev, 1, T_SPACE);
        cell(c, 1, T_CURSOR);
        prev = c;
        oc_sync();
        if ((pad_new[2] & K_RIGHT) && c + 1 < NAME_CHARS_N) c++;
        if ((pad_new[2] & K_LEFT) && c) c--;
        if ((pad_new[2] & K_DOWN) && c + 14 < NAME_CHARS_N) c += 14;
        if ((pad_new[2] & K_UP) && c >= 14) c -= 14;
        if (pad_new[2] & K_A) {
            name[pos] = NAME_CHARS[c];
            if (pos + 1 < n) pos++;
            sfx_play(SFX_CURSOR);
        }
        if (pad_new[2] & K_B) {
            if (pos) pos--;
            name[pos] = T_SPACE;
            sfx_play(SFX_CURSOR);
        }
        if (pad_new[2] & K_START) break;
    }
    sfx_play(SFX_SAFE);
}

/* チームを 1 つ書きかえる（START でディスクへ保存） */
static void edit_team(u8 t)
{
    u8 r = 1, f = 0, mark = 0xFF, i;
    rom2ram(SR_TEAMS + (u16)t * TEAM_SIZE, ED, SR_BANK, TEAM_SIZE);
    for (;;) {
        oc_screen();
        draw_team();
        help(TX_EHELP2);
        vdp_display(1);
        for (;;) {
            u8 y = row_y(r), x = field_x(r, f);
            nt_tile(x, y, T_CURSOR);
            if (mark != 0xFF) nt_tile(1, row_y(mark), T_LAMP_S);
            oc_sync();
            if (pad_new[2] & (K_UP | K_DOWN | K_LEFT | K_RIGHT)) {
                nt_tile(x, y, T_SPACE);
                if (pad_new[2] & K_UP) r = r ? r - 1 : 17;
                if (pad_new[2] & K_DOWN) r = r < 17 ? r + 1 : 0;
                if (pad_new[2] & K_LEFT) f = f ? f - 1 : nfields(r) - 1;
                if (pad_new[2] & K_RIGHT) f++;
                if (f >= nfields(r)) f = 0;
                sfx_play(SFX_CURSOR);
            }
            if (pad_new[2] & K_A) {
                sfx_play(SFX_SAFE);
                if (r == 0) {
                    if (f == 0) edit_name(ED->abbr, 3);
                    else edit_name(ED->name, 6);
                    break;                      /* 画面を描き直す */
                }
                if (f == 0) {
                    edit_name(r <= 12 ? ED->bat[r - 1].name : ED->pit[r - 13].name, 5);
                    break;
                }
                edit_num(r, f);
            }
            if ((pad_new[2] & K_B) && r) {      /* 打者どうし・投手どうしを入れかえる */
                if (mark == 0xFF) mark = r;
                else {
                    if (mark != r && (mark <= 12) == (r <= 12)) {
                        u8* a = mark <= 12 ? (u8*)&ED->bat[mark - 1] : (u8*)&ED->pit[mark - 13];
                        u8* b = r <= 12 ? (u8*)&ED->bat[r - 1] : (u8*)&ED->pit[r - 13];
                        for (i = 0; i < sizeof(BatterDef); i++) {
                            u8 c = a[i];
                            a[i] = b[i];
                            b[i] = c;
                        }
                        draw_row(r);
                    }
                    nt_tile(1, row_y(mark), T_SPACE);
                    draw_row(mark);
                    mark = 0xFF;
                }
                sfx_play(SFX_CURSOR);
            }
            if (pad_new[2] & K_START) {         /* 保存して戻る */
                ram2sram(SR_TEAMS + (u16)t * TEAM_SIZE, ED, TEAM_SIZE);
                for (i = 0; i < 13; i++) ((u8*)thdr_raw)[t * 13 + i] = ((u8*)ED)[i];
                help(disk_save() ? TX_DERR : TX_SAVED);     /* ファイルに書く */
                sfx_play(SFX_SAFE);
                for (i = 0; i < 60; i++) oc_sync();
                return;
            }
        }
    }
}

void screen_edit(void)
{
    u8 cur = 0, i;
    for (;;) {
        oc_screen();
        if (sram_ok != 2) {                     /* ディスクドライブがないと保存できない */
            nt_text(6, 12, TX_NOSRAM);
            vdp_display(1);
            do oc_sync();
            while (!(pad_new[2] & (K_A | K_B | K_START)));
            return;
        }
        for (i = 0; i < NUM_TEAMS; i++) {
            nt_n(6, 4 + i * 2, thdr[i].abbr, 3);
            nt_n(11, 4 + i * 2, thdr[i].name, 6);
        }
        help(TX_EHELP1);
        vdp_display(1);
        for (;;) {
            for (i = 0; i < NUM_TEAMS; i++) nt_tile(3, 4 + i * 2, i == cur ? T_CURSOR : T_SPACE);
            oc_sync();
            if (pad_new[2] & K_UP) {
                cur = cur ? cur - 1 : NUM_TEAMS - 1;
                sfx_play(SFX_CURSOR);
            }
            if (pad_new[2] & K_DOWN) {
                cur = cur + 1 < NUM_TEAMS ? cur + 1 : 0;
                sfx_play(SFX_CURSOR);
            }
            if (pad_new[2] & K_A) {
                sfx_play(SFX_SAFE);
                edit_team(cur);
                break;
            }
            if (pad_new[2] & (K_B | K_START)) {
                sfx_play(SFX_SAFE);
                return;
            }
        }
    }
}

/* ---- スコアボード（イニングの終わり・試合の終わり） ----
 * 背景はプロ野球の球場のセンター後方：夜空・照明塔・時計・両チームの旗・屋根つきの上段スタンド・
 * 黒いバックスクリーン・外野フェンスと広告・芝（絵は tools/gfx_board.py、名前表ごと ROM にある）。
 * その真ん中に黄色い枠の黒いボード。
 *   枠|帯 ABC 空 1 2 3 … n 空 R R 空 H H|枠   （幅 13+n）。回のマスは 1 つおきに紺で、すき間なしでも読める
 * 1 行ずつ bd[] に組み立てて書く。表示中だけパターン 0〜 をボードのタイルに入れ替える（終わったら全部読み直す） */
#define BD_Y0 9
/* 枠の 8 行：左・中・右 */
static const u8 bd_frame[8 * 3] = {
    BD_TL, BD_T, BD_TR, BD_L, T_SPACE, BD_R, BD_LS, BD_SEP, BD_RS, BD_L, T_SPACE, BD_R,
    BD_L, T_SPACE, BD_R, BD_LS, BD_SEP, BD_RS, BD_L, T_SPACE, BD_R, BD_BL, BD_B, BD_BR
};
extern u8 bk[32];               /* スプライトの帯の表を借りる（この画面では使わない） */
#define bd bk

/* 2 けたの数（10 の位がなければ空き）。t0 = 0 の字 */
static void bd_num2(u8* q, u8 v, u8 t0)
{
    u8 d = 0;
    while (v >= 10) {               /* 割り算のライブラリを使わない（オーバーレイは本体の外） */
        v -= 10;
        d++;
    }
    q[0] = d ? t0 + d : T_SPACE;
    q[1] = t0 + v;
}

void screen_scoreboard(u8 final)
{
    u8 i, t, w, x0, y, k;
    u8* p;
    const u8* f;
    u8 n = inning + 1 > max_inning ? inning + 1 : max_inning;
    if (n > 12) n = 12;
    oc_fixed();
    for (t = 0; t < 4; t++) {
        u16 o = (u16)t << 11, r = A_BOARD_BG_OFS + t * (BD_BGN * 16);
        LOADV(VR_PAT + o, A_BOARD_PAT);
        LOADV(VR_COL + o, A_BOARD_COL);
        vdp_waddr(VR_PAT + o + BD_BG0 * 8);
        rom2vram(A_BOARD_BG_BANK, r, BD_BGN * 8);
        vdp_waddr(VR_COL + o + BD_BG0 * 8);
        rom2vram(A_BOARD_BG_BANK, r + BD_BGN * 8, BD_BGN * 8);
    }
    w = 13 + n;
    x0 = (32 - w) >> 1;
    p = bd + x0;
    for (y = 0; y < 27; y++) {
        rom2ram(A_BOARD_NT_OFS + y * 32, bd, A_BOARD_NT_BANK, 32);
        k = y - BD_Y0;
        if (k < 8) {
            f = bd_frame + k * 3;
            for (i = 1; i < w - 1; i++) p[i] = f[1];
            p[0] = f[0];
            p[w - 1] = f[2];
            if (k == 1) {               /* 見出し：回・R・H */
                for (i = 0; i < n; i++) p[6 + i] = ((i & 1) ? BD_YN0 : BD_YK0) + (i < 9 ? i + 1 : i - 9);
                p[8 + n] = BD_YR;
                p[11 + n] = BD_YH;
            } else if (k == 3 || k == 4) {      /* 色の帯・略称・各回の点・R（黄）・安打 */
                const Side* sd = &side[k - 3];
                p[1] = BD_ST1 + k - 3;
                for (i = 0; i < 3; i++) p[2 + i] = thdr[sd->team].abbr[i];
                for (i = 0; i < n; i++) {
                    u8 v = sd->score[i];
                    if (v == 0xFF) t = (i & 1) ? BD_ZB : T_SPACE;
                    else if (v > 9) t = (i & 1) ? BD_WNX : ascii_tile['X' - 32];
                    else t = ((i & 1) ? BD_WN0 : T_0) + v;
                    p[6 + i] = t;
                }
                bd_num2(p + 7 + n, sd->runs, BD_YK0);
                bd_num2(p + 10 + n, sd->hits, T_0);
            }
        }
        nt_n(0, y, bd, 32);
    }
    /* 下の段：「1回表 シュウリョウ」／「ゲームセット ABC WIN!」 */
    y = BD_Y0 + 6;
    if (final) {
        nt_text(x0 + 2, y, STR_GAMESET);
        if (side[0].runs == side[1].runs) {
            nt_text(x0 + 9, y, STR_DRAW);
        } else {
            t = side[0].runs > side[1].runs ? 0 : 1;
            nt_n(x0 + 9, y, thdr[side[t].team].abbr, 3);
            nt_text(x0 + 13, y, STR_WIN);
        }
        bgm_play(BGM_GAMESET);
    } else {
        t = inning + 1 >= 10 ? 2 : 1;
        nt_num(x0 + 2, y, inning + 1, t);
        bd[0] = T_KAI;
        bd[1] = half ? T_URA : T_OMOTE;
        nt_n(x0 + 2 + t, y, bd, 2);
        nt_text(x0 + 5 + t, y, STR_INNEND);
    }
    vdp_display(1);
    for (i = 0; i < 20; i++) oc_sync();
    t = 0;
    for (;;) {
        oc_sync();
        if (pad_new[2] & (K_A | K_START)) break;
        if (++t > (final ? 250 : 150) && game_mode == 2) break;
        if (!final && t > 200) break;
    }
    vdp_display(0);
    vdp_load_field_tiles();         /* 球場のタイル・文字の色を元に戻す */
}
