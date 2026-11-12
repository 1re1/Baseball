/* 球場のスクロール
 *   縦：R#23（マップの行 m は名前表の行 m&31 に置く。8 ドット進むごとに 1 行書く）
 *   横：R#18 で 0〜7 ドット、8 ドットごとに裏の名前表を作って切り替える（先読みする） */
#include "game.h"

s16 cam_x, cam_y;
u8 view_cx;
s16 view_y;
static u8 front;
u8 nt_cx[2] = { 0xFF, 0xFF };
static s8 nt_lo[2], nt_hi[2];
u8 show_fine;                    /* R#18 に書く細かい横スクロール（0〜7。画面もスプライトも左へずれる） */
static s16 last_cx;
static s8 cam_dir;

#define NT_ADDR(t) ((t) ? VR_NT1 : VR_NT0)

/* 名前表 rs_t の行 rs_m から rs_n 行ぶん、マップの行（列 nt_cx[t] から 32 個）を書く（アセンブラ） */
static u8 rs_t, rs_m, rs_n;

static void render_span(void) __naked
{
    __asm
1$:     ld   a, (_rs_n)
        or   a
        ret  z
        ld   a, (_rs_t)
        ld   b, a
        ld   a, (_rs_m)
        ld   c, a
        and  #31
        ld   l, a
        ld   h, #0
        add  hl, hl
        add  hl, hl
        add  hl, hl
        add  hl, hl
        add  hl, hl
        ld   a, b
        or   a
        ld   a, #0x40
        jr   z, 2$
        ld   a, #0x44
2$:     add  a, h
        ld   h, a
        ld   a, #1
        di
        out  (0x99), a
        ld   a, #0x8E
        out  (0x99), a
        ld   a, l
        out  (0x99), a
        ld   a, h
        and  #0x3F
        or   #0x40
        out  (0x99), a
        ei
        ld   l, c
        ld   h, #0
        add  hl, hl
        add  hl, hl
        add  hl, hl
        add  hl, hl
        add  hl, hl
        add  hl, hl
        ld   de, #_field_map
        add  hl, de
        ld   e, b
        ld   d, #0
        push hl
        ld   hl, #_nt_cx
        add  hl, de
        ld   e, (hl)
        pop  hl
        add  hl, de
        ld   c, #0x98
        .rept 32
        outi
        .endm
        ld   hl, #_rs_m
        inc  (hl)
        ld   hl, #_rs_n
        dec  (hl)
        jp   1$
    __endasm;
}

static void render_row(u8 t, u8 m)
{
    rs_t = t;
    rs_m = m;
    rs_n = 1;
    render_span();
}

static void nt_forget(u8 t)
{
    nt_lo[t] = 0;
    nt_hi[t] = -1;
}

/* 名前表 t の行 r0..r1 をそろえる（1 フレームに budget 行まで）。そろえば 1 */
static u8 ensure(u8 t, s8 r0, s8 r1, u8 budget)
{
    s8 lo = nt_lo[t], hi = nt_hi[t];
    u8 n;
    if (hi < lo || r1 < lo - 1 || r0 > hi + 1) {
        lo = r0;
        hi = r0 - 1;
    }
    rs_t = t;
    if (lo > r0) {                      /* 上に足す */
        n = (u8)(lo - r0);
        if (n > budget) n = budget;
        lo -= n;
        rs_m = (u8)lo;
        rs_n = n;
        render_span();
        budget -= n;
        if (hi - lo >= 32) hi = lo + 31;
    }
    if (budget && hi < r1) {            /* 下に足す */
        n = (u8)(r1 - hi);
        if (n > budget) n = budget;
        rs_m = (u8)(hi + 1);
        rs_n = n;
        render_span();
        hi += n;
        if (hi - lo >= 32) lo = hi - 31;
    }
    nt_lo[t] = lo;
    nt_hi[t] = hi;
    return lo <= r0 && hi >= r1;
}

void scroll_invalidate(void)
{
    nt_cx[0] = nt_cx[1] = 0xFF;
    nt_forget(0);
    nt_forget(1);
}

void scroll_update(void)
{
    s16 cx = cam_x, cy = cam_y;
    u8 want, fine, back;
    s8 r0, r1;
    if (cx < 0) cx = 0;
    if (cx > 256) cx = 256;
    if (cy < 0) cy = 0;
    if (cy > 204) cy = 204;
    if (cx > last_cx) cam_dir = 1;
    else if (cx < last_cx) cam_dir = -1;
    last_cx = cx;
    want = (u8)(cx >> 3);
    fine = (u8)(cx & 7);
    r0 = (s8)(cy >> 3);
    r1 = (s8)((cy + 211) >> 3);
    if (r1 > FIELD_H - 1) r1 = FIELD_H - 1;
    back = front ^ 1;
    if (nt_cx[front] == want) {
        ensure(front, r0, r1, 32);
        view_cx = want;
        show_fine = fine;
        if (cam_dir) {
            s8 pre = (s8)want + cam_dir;
            if (pre >= 0 && pre <= 32) {
                if (nt_cx[back] != (u8)pre) {
                    nt_cx[back] = (u8)pre;
                    nt_forget(back);
                }
                ensure(back, r0, r1, 7);
            }
        }
    } else {
        if (nt_cx[back] != want) {
            nt_cx[back] = want;
            nt_forget(back);
        }
        if (ensure(back, r0, r1, 14)) {
            front = back;
            view_cx = want;
            show_fine = fine;
        } else if (nt_cx[front] != 0xFF) {
            s16 f = cx - (s16)nt_cx[front] * 8;
            ensure(front, r0, r1, 32);
            view_cx = nt_cx[front];
            show_fine = (u8)(f < 0 ? 0 : (f > 7 ? 7 : f));
        }
    }
    view_y = cy;
}

/* 今のカメラで表の名前表を作り直す（場面の切り替え用） */
void scroll_reset(void)
{
    scroll_invalidate();
    front = 0;
    cam_dir = 0;
    last_cx = cam_x;
    nt_cx[0] = (u8)((cam_x < 0 ? 0 : (cam_x > 256 ? 256 : cam_x)) >> 3);
    scroll_update();
}

void scroll_commit(void)
{
    vdp_reg(2, front ? 0x11 : 0x10);
    vdp_reg(18, show_fine);
    vdp_reg(23, (u8)view_y);
}

void scroll_restore_rows(u8 r0, u8 r1)
{
    u8 m;
    for (m = r0; m <= r1; m++) {
        if ((s8)m >= nt_lo[front] && (s8)m <= nt_hi[front]) render_row(front, m);
    }
}

/* ---- 表示中の名前表に文字を書く（マップの行で指定） ---- */
static void at(u8 col, u8 maprow)
{
    vdp_waddr(NT_ADDR(front) + ((u16)(maprow & 31) << 5) + col);
}

void txt_map(u8 col, u8 maprow, const u8* s)
{
    at(col, maprow);
    while (*s) vdp_out(*s++);
}

void txt_ascii(u8 col, u8 maprow, const char* s)
{
    at(col, maprow);
    while (*s) vdp_out(ascii_tile[(u8)(*s++) - 32]);
}

void txt_n(u8 col, u8 maprow, const u8* s, u8 n)
{
    at(col, maprow);
    while (n--) vdp_out(*s++);
}

void txt_tile(u8 col, u8 maprow, u8 t)
{
    at(col, maprow);
    vdp_out(t);
}

void txt_fill(u8 col, u8 maprow, u8 t, u8 n)
{
    at(col, maprow);
    while (n--) vdp_out(t);
}

static u8 numbuf[6];
static void num_to(u16 v, u8 width)
{
    u8 i = width;
    numbuf[width] = 0;
    do {
        numbuf[--i] = T_0 + (u8)(v % 10);
        v /= 10;
    } while (v && i);
    while (i) numbuf[--i] = T_SPACE;
}

void txt_num(u8 col, u8 maprow, u16 v, u8 width)
{
    num_to(v, width);
    txt_map(col, maprow, numbuf);
}

/* ---- スクロールしない画面（メニュー・得点表）用 ---- */
static void nt_at(u8 col, u8 row)
{
    vdp_waddr(VR_NT0 + ((u16)row << 5) + col);
}

void nt_text(u8 col, u8 row, const u8* s)
{
    nt_at(col, row);
    while (*s) vdp_out(*s++);
}

void nt_ascii(u8 col, u8 row, const char* s)
{
    nt_at(col, row);
    while (*s) vdp_out(ascii_tile[(u8)(*s++) - 32]);
}

void nt_n(u8 col, u8 row, const u8* s, u8 n)
{
    nt_at(col, row);
    while (n--) vdp_out(*s++);
}

void nt_tile(u8 col, u8 row, u8 t)
{
    nt_at(col, row);
    vdp_out(t);
}

void nt_fill(u8 col, u8 row, u8 t, u8 n)
{
    nt_at(col, row);
    while (n--) vdp_out(t);
}

void nt_num(u8 col, u8 row, u16 v, u8 width)
{
    num_to(v, width);
    nt_text(col, row, numbuf);
}

/* ---- スタンドの得点板（マップを書き換える） ---- */
static void sb_put(u8 col, u8 row, const u8* s, u8 n)
{
    u8* p = (u8*)field_map + (u16)row * FIELD_W + col;
    while (n--) *p++ = *s++;
}

void scoreboard_clear(void)
{
    u8 i;
    for (i = 0; i < 3; i++) {
        u8* p = (u8*)field_map + (u16)(SB_ROW + i) * FIELD_W + SB_COL;
        u8 k;
        for (k = 0; k < SB_W; k++) p[k] = T_SPACE;
    }
}

void scoreboard_update(void)
{
    u8 i;
    for (i = 0; i < 2; i++) {
        sb_put(SB_COL + 1, SB_ROW + i, thdr[side[i].team].abbr, 3);
        num_to(side[i].runs, 3);
        sb_put(SB_COL + 8, SB_ROW + i, numbuf, 3);
    }
    num_to(inning + 1, 2);
    numbuf[2] = T_KAI;
    numbuf[3] = half ? T_URA : T_OMOTE;
    sb_put(SB_COL + 1, SB_ROW + 2, numbuf, 4);
    /* 表示中なら描き直す */
    scroll_restore_rows(SB_ROW, SB_ROW + 2);
}
