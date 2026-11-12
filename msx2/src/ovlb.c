/* オーバーレイ B（ROM のバンク 8 → RAM の OVL_ADDR〜）：タイトル・トーナメント。
 * 本体とは別にリンクする（本体の関数・変数は番地で呼ぶ）。このファイルには RAM の変数を置かない
 * （静的な変数を作らない。状態は本体の変数か保存の中身に置く）。
 * 本体からは先頭の入口の表（OVL_ADDR + 3 × 番号）で呼ぶ */
#include "game.h"

extern const char* const mode_name[];
extern const u8 inn_tab[3];
extern const char str_start[], str_lr[], str_speed[];
extern const u8 speed_rate[5];

void screen_title(void);
u8 tour_begin(u8 cont);
u8 tour_next(void);
void ob_boot(void);
static void sram_init(void);

/* 入口の表（この順番は game.h の OVB_* と同じ） */
void ovlb_entry(void) __naked
{
    __asm
        jp   _screen_title
        jp   _tour_begin
        jp   _tour_next
        jp   _ob_boot
    __endasm;
}

/* タイトル：入口の表のすぐ後ろ（E300h より前）。球場マップ（E300h〜）を読んだあとも壊れない。
 * 文字列は本体（menu.c）に置く（このファイルの定数はオーバーレイの後ろのほうに入るため）。
 * 行：モード 6 つ（1P VS COM・1P VS 2P・COM VS COM・EDIT・TOURNAMENT・CONTINUE）・イニング・SPEED */
#define TM_ROW 16
void screen_title(void)
{
    u8 cur = game_mode, mode = game_mode, inn = 2, i, y;
    u16 idle = 0;
    sram_init();
    if (cur > 5) cur = mode = 0;
    if (max_inning == 3) inn = 0;
    else if (max_inning == 6) inn = 1;
    vdp_display(0);
    side[0].team = 0;
    side[1].team = 1;
    half = 0;
    inning = 0;
    side[0].runs = side[1].runs = 0;
    vdp_set_team_palette();
    vdp_reg(7, 0x03);
    spr_hide_all();
    spr_set_mode(SM_FIELD);
    cam_x = 128;
    cam_y = 0;
    scoreboard_clear();
    scroll_reset();
    /* 看板 */
    for (y = 1; y < 15; y++) txt_fill(1, y, T_PANEL, 30);
    for (y = 0; y < 4; y++) {
        txt_n(10, 2 + y, logo1 + y * 12, 12);
        txt_n(2, 7 + y, logo2 + y * 28, 28);
    }
    txt_fill(2, 12, T_LOGO_SH, 28);
    for (y = 15; y < 27; y++) txt_fill(4, y, T_SPACE, 24);
    txt_ascii(9, 25, str_start);
    bgm_play(BGM_TITLE);
    vdp_display(1);
    for (;;) {
        /* ↑↓ で行、←→ でイニングか速さ。黄色のランプは選んだモード */
        for (i = 0; i < 8; i++) txt_tile(8, TM_ROW + i, i == cur ? T_CURSOR : (i == mode ? T_LAMP_S : T_SPACE));
        for (i = 0; i < 6; i++) txt_ascii(10, TM_ROW + i, mode_name[i]);
        txt_map(10, TM_ROW + 6, STR_INNING);
        txt_num(16, TM_ROW + 6, inn_tab[inn], 2);
        txt_ascii(19, TM_ROW + 6, str_lr);
        txt_ascii(10, TM_ROW + 7, str_speed);
        txt_num(17, TM_ROW + 7, game_speed + 1, 1);
        txt_ascii(19, TM_ROW + 7, str_lr);
        wait_vblank();
        spr_commit();
        scroll_commit();
        input_update();
        if (pad_new[2] & K_UP) {
            cur = cur ? cur - 1 : 7;
            sfx_play(SFX_CURSOR);
        }
        if (pad_new[2] & K_DOWN) {
            cur = cur < 7 ? cur + 1 : 0;
            sfx_play(SFX_CURSOR);
        }
        if (cur < 6) mode = cur;
        if (pad_new[2] & K_LEFT) {
            if (cur == 7) game_speed = game_speed ? game_speed - 1 : 4;
            else inn = inn ? inn - 1 : 2;
            sfx_play(SFX_CURSOR);
        }
        if (pad_new[2] & K_RIGHT) {
            if (cur == 7) game_speed = game_speed < 4 ? game_speed + 1 : 0;
            else inn = inn < 2 ? inn + 1 : 0;
            sfx_play(SFX_CURSOR);
        }
        if (pad_new[2] & (K_A | K_START)) break;
        if (pad[2]) idle = 0;
        else if (++idle > 600) break;
    }
    demo = idle > 600;
    grate = speed_rate[game_speed];
    max_inning = inn_tab[inn];
    if (demo) {
        game_mode = 2;
        return;
    }
    game_mode = mode;
    sfx_play(SFX_SAFE);
}

/* 保存の中身を調べる（1 回だけ）。フロッピーディスクのときだけ保存できる（中身は起動時にディスクから VRAM へ読んである）。
 * 印 "MSXS" と版がちがえば（ファイルがなかった）ROM のチームを写して印を書く。
 * チームの名前・略称・色（各チームの先頭 13 バイト）を保存の中身にする。
 * タイトルの間に呼ぶので、このファイルの定数（オーバーレイの後ろ・球場マップと重なる）は使わない */
#define SR_VER 2
static void sram_init(void)
{
    u8 b[5], t;
    if (sram_ok) return;
    sram_ok = 1;
    if (!DISKMODE) return;                      /* ディスクドライブがない：保存できない */
    rom2ram(SR_MAGIC, b, SR_BANK, 5);
    if (b[0] != 'M' || b[1] != 'S' || b[2] != 'X' || b[3] != 'S' || b[4] != SR_VER) {
        for (t = 0; t < NUM_TEAMS; t++) {       /* はじめて：ROM のチームを写す */
            rom2ram(A_TEAMS_OFS + (u16)t * TEAM_SIZE, &tm[0], A_TEAMS_BANK, TEAM_SIZE);
            ram2sram(SR_TEAMS + (u16)t * TEAM_SIZE, &tm[0], TEAM_SIZE);
        }
        b[0] = 0;                               /* トーナメントはなし */
        ram2sram(SR_TOUR, b, 1);
        b[0] = 'M';
        b[1] = 'S';
        b[2] = 'X';
        b[3] = 'S';
        b[4] = SR_VER;
        ram2sram(SR_MAGIC, b, 5);
    }
    for (t = 0; t < NUM_TEAMS; t++)             /* チームの名前・略称・色は保存の中身 */
        rom2ram(SR_TEAMS + (u16)t * TEAM_SIZE, (u8*)thdr_raw + t * 13, SR_BANK, 13);
    sram_ok = 2;
}

/* ここまでが E300h より前（build.py で確かめる） */
void ovlb_title_end(void)
{
}

/* ---- 起動のときだけ（本体の RAM を空けるため、ここに置く） ---- */
static void vdp_setup_g3(void)
{
    vdp_reg(1, 0x22);                 /* 表示オフ・割り込みあり・16x16 */
    vdp_reg(0, 0x04);                 /* G3 */
    vdp_reg(8, 0x08);                 /* 64K VRAM・色0 は透明 */
    vdp_reg(9, 0x80 | (RG9SAV & 0x02));   /* 212 ライン（50/60Hz は本体のまま） */
    vdp_reg(2, 0x10);                 /* 名前表 4000h */
    vdp_reg(3, 0xFF);                 /* 色表 2000h */
    vdp_reg(10, 0x00);
    vdp_reg(4, 0x03);                 /* 柄 0000h */
    vdp_reg(5, 0xBF);                 /* スプライト属性 5E00h（色 5C00h） */
    vdp_reg(11, 0x00);
    vdp_reg(6, 0x0C);                 /* スプライト柄 6000h */
    vdp_reg(7, 0x03);
    vdp_reg(18, 0);
    vdp_reg(23, 0);
    vdp_reg(15, 0);
    vdp_palette(palette_base);
}

static void vdp_load_sprites(void)
{
    LOADV(VR_SPAT_ATBAT, A_SPR_ATBAT);
    LOADV(VR_SPAT_FIELD, A_SPR_FIELD);
}

void ob_boot(void)
{
    vdp_setup_g3();
    vdp_load_sprites();
}

/* 字の表（オーバーレイの中の定数は、書いた場所に置かれるので、タイトルの後ろで読み込む） */
#include "ovtext.h"

/* ================= トーナメント =================
 * 6 チーム。スロット 0 と 5 はシード（2 回戦から）。
 *   試合 0：スロット 1 対 2      試合 1：スロット 3 対 4
 *   試合 2：スロット 0 対 試合 0 の勝ち   試合 3：試合 1 の勝ち 対 スロット 5
 *   試合 4（決勝）：試合 2 の勝ち 対 試合 3 の勝ち
 * 上の側が先攻。1P のチームの試合は 1P VS COM、COM 同士は結果だけ決める（1P のチームなしなら全部 COM VS COM で見る）。
 * 状態は本体の tour[]（保存の中身の SR_TOUR にも書き、ディスクへ保存） */
#define T_ON 0          /* 1 = 進行中 */
#define T_USER 1        /* 1P のスロット（6 = なし） */
#define T_SLOT 2        /* 6 スロットのチーム */
#define T_WIN 8         /* 5 試合の勝った側（0 上・1 下・255 まだ） */
#define T_SCORE 13      /* 5 試合の点（上・下） */
#define T_INN 23        /* イニング数 */
#define T_CUR 24        /* いまの試合 */

static const u8 m_src[10] = { 1, 2, 3, 4, 0, 0x80, 0x81, 5, 0x82, 0x83 };   /* 0x80 + m = 試合 m の勝ち */
static const u8 slot_row[6] = { 3, 7, 11, 15, 19, 23 };
static const u8 m_col[5] = { 14, 14, 19, 19, 24 };
static const u8 m_out[5] = { 9, 17, 6, 20, 13 };

static void tsave(void)
{
    if (sram_ok == 2) {                 /* フロッピーディスクのとき：保存の中身とファイルに書く */
        ram2sram(SR_TOUR, tour, TOUR_SIZE);
        disk_save();
    }
}

/* 試合の勝ち（0x80 + m）をたどってスロットにする（まだ決まっていなければ 255） */
static u8 who(u8 src)
{
    while (src & 0x80) {
        u8 w = tour[T_WIN + (src & 7)];
        if (w == 255) return 255;
        src = m_src[((src & 7) << 1) + w];
    }
    return src;
}

static u8 src_row(u8 src)
{
    return (src & 0x80) ? m_out[src & 7] : slot_row[src];
}

static void ob_sync(void)
{
    wait_vblank();
    spr_commit();
    input_update();
}

/* A か START を待つ。ESC なら 1（タイトルへ戻る） */
static u8 ob_wait(void)
{
    do {
        ob_sync();
        if (esc_new) return 1;
    } while (!(pad_new[2] & (K_A | K_START)));
    sfx_play(SFX_SAFE);
    return 0;
}

/* スクロールしない画面（名前表 0）。タイル 0〜13 をトーナメント表の線にする（終わったら球場のタイルに戻す） */
static void ob_screen(void)
{
    u8 t;
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
    for (t = 0; t < 4; t++) {
        LOADV(VR_PAT + ((u16)t << 11), A_BRK_PAT);
        LOADV(VR_COL + ((u16)t << 11), A_BRK_COL);
    }
    pad_new[0] = pad_new[1] = pad_new[2] = 0;
}

static void brk(u8 x, u8 y, u8 t, u8 yel)
{
    nt_tile(x, y, yel ? t + BRK_YEL : t);
}

static void score2(u8 x, u8 y, u8 a, u8 b)
{
    if (a > 99) a = 99;
    if (b > 99) b = 99;
    nt_num(x, y, a, a >= 10 ? 2 : 1);
    x += a >= 10 ? 2 : 1;
    nt_tile(x, y, ascii_tile['-' - 32]);
    nt_num(x + 1, y, b, b >= 10 ? 2 : 1);
}

/* トーナメント表を描く（cur = カーソルのスロット、mark = 入れかえで選んだスロット。255 = なし） */
static void draw_bracket(u8 cur, u8 mark)
{
    u8 i, m, x, y;
    nt_text(10, 0, TX_TOUR);
    for (i = 0; i < 6; i++) {
        u8 t = tour[T_SLOT + i];
        y = slot_row[i];
        nt_tile(0, y, i == cur ? T_CURSOR : (i == mark ? T_LAMP_S : T_SPACE));
        nt_n(1, y, thdr[t].abbr, 3);
        nt_tile(4, y, T_SPACE);
        nt_n(5, y, thdr[t].name, 6);
        nt_fill(1, y + 1, T_SPACE, 10);
        if (tour[T_USER] == i) nt_ascii(1, y + 1, "1P");
        if (i == 0 || i == 5) nt_text(5, y + 1, TX_SEED);
    }
    for (m = 0; m < 5; m++) {
        u8 top = m_src[m * 2], bot = m_src[m * 2 + 1];
        u8 ra = src_row(top), rb = src_row(bot), ro = m_out[m], col = m_col[m], w = tour[T_WIN + m];
        u8 xa = (top & 0x80) ? m_col[top & 7] + 1 : 11, xb = (bot & 0x80) ? m_col[bot & 7] + 1 : 11;
        u8 ya = (top & 0x80) && tour[T_WIN + (top & 7)] != 255, yb = (bot & 0x80) && tour[T_WIN + (bot & 7)] != 255;
        for (x = xa; x < col; x++) brk(x, ra, BRK_H, ya);
        for (x = xb; x < col; x++) brk(x, rb, BRK_H, yb);
        brk(col, ra, BRK_TR, w == 0);
        for (y = ra + 1; y < ro; y++) brk(col, y, BRK_V, w == 0);
        brk(col, ro, BRK_TJ, w != 255);
        for (y = ro + 1; y < rb; y++) brk(col, y, BRK_V, w == 1);
        brk(col, rb, BRK_BR, w == 1);
        if (w != 255) score2(col + 1, ro - 1, tour[T_SCORE + m * 2], tour[T_SCORE + m * 2 + 1]);
    }
    /* 優勝 */
    brk(25, 13, BRK_H, tour[T_WIN + 4] != 255);
    if (tour[T_WIN + 4] != 255) {
        nt_n(26, 13, thdr[tour[T_SLOT + who(0x84)]].abbr, 3);
        nt_text(25, 15, TX_CHAMP);
    }
}

static void bottom(const u8* s)
{
    nt_fill(0, 25, T_SPACE, 32);
    if (s) nt_text(1, 25, s);
}

/* チームの強さ（スタメン 8 人の打率・パワーと、いちばん速い投手の球速） */
static u16 team_power(u8 t)
{
    u8 i;
    u16 p = 0;
    if (sram_ok == 2) rom2ram(SR_TEAMS + (u16)t * TEAM_SIZE, &tm[0], SR_BANK, TEAM_SIZE);
    else rom2ram(A_TEAMS_OFS + (u16)t * TEAM_SIZE, &tm[0], A_TEAMS_BANK, TEAM_SIZE);
    for (i = 0; i < 8; i++) p += tm[0].bat[i].avg + tm[0].bat[i].pow * 8;
    return p + tm[0].pit[0].kmh * 2;
}

/* COM 同士の試合：強さで少し有利にして、点を決める（引き分けなし） */
static void sim_match(u8 m, u8 a, u8 b)
{
    u16 pa = team_power(tour[T_SLOT + a]), pb = team_power(tour[T_SLOT + b]);
    u8 ra = rnd_n(7), rb = rnd_n(7);
    if (pa > pb + 40) ra++;
    if (pb > pa + 40) rb++;
    if (ra == rb) {
        if (rnd() & 1) ra++;
        else rb++;
    }
    tour[T_SCORE + m * 2] = ra;
    tour[T_SCORE + m * 2 + 1] = rb;
    tour[T_WIN + m] = rb > ra;
}

/* 次の試合を用意する。1 = 試合をする（チーム・操作を決めた）。0 = タイトルへ（終わった・やめた） */
static u8 tour_step(void)
{
    for (;;) {
        u8 m, a, b, u = tour[T_USER];
        for (m = 0; m < 5; m++)
            if (tour[T_WIN + m] == 255) break;
        ob_screen();
        if (m == 5) {                           /* 優勝が決まった */
            draw_bracket(255, 255);
            bottom(TX_TOUREND);
            vdp_display(1);
            bgm_play(BGM_GAMESET);
            ob_wait();
            tour[T_ON] = 0;
            tsave();
            vdp_load_field_tiles();
            return 0;
        }
        a = who(m_src[m * 2]);
        b = who(m_src[m * 2 + 1]);
        tour[T_CUR] = m;
        draw_bracket(255, 255);
        if (u == 6 || a == u || b == u) {       /* 試合をする */
            bottom(TX_PLAY);
            vdp_display(1);
            if (ob_wait()) break;
            side[0].team = tour[T_SLOT + a];
            side[1].team = tour[T_SLOT + b];
            side[0].ctrl = a == u ? 1 : 0;
            side[1].ctrl = b == u ? 1 : 0;
            game_mode = u == 6 ? 2 : 0;
            max_inning = tour[T_INN];
            demo = 0;
            vdp_load_field_tiles();
            return 1;
        }
        sim_match(m, a, b);                     /* COM 同士は結果だけ */
        tsave();
        draw_bracket(255, 255);
        bottom(TX_NEXT);
        vdp_display(1);
        if (ob_wait()) break;
    }
    vdp_load_field_tiles();             /* ESC：タイトルへ（ここまでの結果は保存済み。つづきから再開できる） */
    return 0;
}

/* 試合の結果を書いて、次へ */
u8 tour_next(void)
{
    u8 m = tour[T_CUR], r0 = side[0].runs, r1 = side[1].runs, w;
    w = r1 > r0;
    if (r0 == r1) {                             /* 引き分けは安打の多いほう、それも同じならくじ */
        if (side[0].hits != side[1].hits) w = side[1].hits > side[0].hits;
        else w = rnd() & 1;
    }
    tour[T_SCORE + m * 2] = r0;
    tour[T_SCORE + m * 2 + 1] = r1;
    tour[T_WIN + m] = w;
    tsave();
    return tour_step();
}

/* 6 チームを選ぶ（A で選ぶ・はずす。6 つ選んで START）。ESC = 1 */
static u8 pick_teams(void)
{
    u8 cur = 0, n = 0, i, sel[NUM_TEAMS];
    for (i = 0; i < NUM_TEAMS; i++) sel[i] = i < 6;
    n = 6;
    ob_screen();
    nt_text(10, 0, TX_TOUR);
    nt_text(4, 2, TX_PICK);
    for (i = 0; i < NUM_TEAMS; i++) {
        nt_n(6, 5 + i * 2, thdr[i].abbr, 3);
        nt_n(11, 5 + i * 2, thdr[i].name, 6);
    }
    bottom(TX_PICKHELP);
    vdp_display(1);
    for (;;) {
        for (i = 0; i < NUM_TEAMS; i++) {
            nt_tile(2, 5 + i * 2, i == cur ? T_CURSOR : T_SPACE);
            nt_tile(4, 5 + i * 2, sel[i] ? T_LAMP_S : T_SPACE);
        }
        nt_num(4, 23, n, 1);
        ob_sync();
        if (pad_new[2] & K_UP) {
            cur = cur ? cur - 1 : NUM_TEAMS - 1;
            sfx_play(SFX_CURSOR);
        }
        if (pad_new[2] & K_DOWN) {
            cur = cur + 1 < NUM_TEAMS ? cur + 1 : 0;
            sfx_play(SFX_CURSOR);
        }
        if (pad_new[2] & K_A) {
            if (sel[cur]) {
                sel[cur] = 0;
                n--;
            } else if (n < 6) {
                sel[cur] = 1;
                n++;
            }
            sfx_play(SFX_CURSOR);
        }
        if ((pad_new[2] & K_START) && n == 6) break;
        if (esc_new) return 1;
    }
    sfx_play(SFX_SAFE);
    for (i = 0, n = 0; i < NUM_TEAMS; i++)
        if (sel[i]) tour[T_SLOT + n++] = i;
    return 0;
}

/* 組み合わせ：↑↓ でスロット、A を 2 か所で押すと入れかえ、B で 1P のチーム（もう一度でなし）、START で始める。ESC = 1 */
static u8 arrange(void)
{
    u8 cur = 0, mark = 255, t;
    ob_screen();
    vdp_display(1);
    for (;;) {
        draw_bracket(cur, mark);
        nt_text(1, 1, TX_ARRHELP1);
        bottom(TX_ARRHELP2);
        ob_sync();
        if (pad_new[2] & K_UP) {
            cur = cur ? cur - 1 : 5;
            sfx_play(SFX_CURSOR);
        }
        if (pad_new[2] & K_DOWN) {
            cur = cur < 5 ? cur + 1 : 0;
            sfx_play(SFX_CURSOR);
        }
        if (pad_new[2] & K_A) {
            if (mark == 255) mark = cur;
            else {
                t = tour[T_SLOT + mark];
                tour[T_SLOT + mark] = tour[T_SLOT + cur];
                tour[T_SLOT + cur] = t;
                if (tour[T_USER] == mark) tour[T_USER] = cur;
                else if (tour[T_USER] == cur) tour[T_USER] = mark;
                mark = 255;
            }
            sfx_play(SFX_CURSOR);
        }
        if (pad_new[2] & K_B) {
            tour[T_USER] = tour[T_USER] == cur ? 6 : cur;
            sfx_play(SFX_CURSOR);
        }
        if (pad_new[2] & K_START) break;
        if (esc_new) return 1;
    }
    sfx_play(SFX_SAFE);
    return 0;
}

/* 始める（cont = 1：保存したつづきから）。1 = 試合をする */
u8 tour_begin(u8 cont)
{
    u8 i;
    if (cont) {
        if (sram_ok == 2) rom2ram(SR_TOUR, tour, SR_BANK, TOUR_SIZE);
        if (sram_ok != 2 || tour[T_ON] != 1) {
            ob_screen();
            nt_text(10, 0, TX_TOUR);
            nt_text(6, 12, sram_ok != 2 ? TX_NOSRAM : TX_NOSAVE);
            vdp_display(1);
            ob_wait();
            vdp_load_field_tiles();
            return 0;
        }
        return tour_step();
    }
    for (i = 0; i < TOUR_SIZE; i++) tour[i] = 0;
    for (i = 0; i < 5; i++) tour[T_WIN + i] = 255;
    tour[T_USER] = 0;
    if (pick_teams() || arrange()) {    /* ESC：始めずにタイトルへ */
        vdp_load_field_tiles();
        return 0;
    }
    tour[T_ON] = 1;
    tour[T_INN] = max_inning;
    tsave();
    return tour_step();
}
