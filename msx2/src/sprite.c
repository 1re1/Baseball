/* スプライト：面の色（行ごと）と、ワールド座標からの置き方
 *   同じチーム・同じ形の面は色が同じなので、面の順番を入れ替えても色を書き直さなくてよい
 *   左端（x<0）は EC ビットで 32 ドットずらす（その面の色 16 バイトを書き直す） */
#include "game.h"

u8 spr_mode;
u8 msg_timer;
u8 msg_y = 98;                  /* 画面の上からの位置（真ん中） */
u8 ec_cur[32];
static u8 ec_want[32];
static s16 x0, y0;
static u8 hide_y;
static u8 ec_used, ec_prev;     /* このフレーム / 前のフレームで EC を使った */
static u8 sp_plane;
static u16 sp_y;
static u8 sp_ec;
static u8 pending_r6;
static u8 msg_len;
static u8 colors_dirty;
u8 ball_tint;
static u8 ball_tint_cur;
u16 ump_mask;
static u16 pl_dirty;   /* 審判の色にした走者の面 / 色を書き直す面（0〜15） */

static const struct { u8 bank; u16 ofs; u16 len; u8 n; } msg_tab[] = { MSG_TABLE };

/* 面 p の色（16 行）を VRAM へ書く（RAM に色の表を持たない。A = p）。
 *   0〜2 文字（白・黄・赤）／3 球審・審判にした走者の面（行ごとの色そのまま）／4 ボール（白か灰）／5 影（黒）
 *   打席：30〜 バット（黄）、12〜19 打者・投手（行の記号 → 色。下の 2 枚は 16 行目から）、ほかはちびキャラ
 *   2 枚重ねの絵は、偶数の面 = 上の層（記号の組の 2 つめ）、奇数の面 = 下の層（1 つめ）。
 *   記号 → 色：1 = チーム主色 P、2 = P+1、3 肌、4 黒、5 白、6 土色。後攻（half = 1）は P = 10、先攻は 8、
 *   守備側の絵（打席の 16〜・20〜、守備の 14〜）は P ^ 2。毎回 1 行ずつ計算して書く（アセンブラ） */
u8 pu_sym[8] = { 0, 0, 0, 6, 1, 7, 4, 0 };
static u8 pu_e;

static void plane_upload(u8 p) __naked
{
    (void)p;
    __asm
        ld   c, a                   ; C = p
        ld   hl, #_ec_cur
        ld   e, a
        ld   d, #0
        add  hl, de
        ld   a, (hl)
        or   a
        jr   z, 1$
        ld   a, #0x80
1$:     ld   (_pu_e), a
        ld   a, (_half)
        or   a
        ld   a, #8
        jr   z, 2$
        ld   a, #10
2$:     ld   b, a                   ; B = P
        ld   l, c
        ld   h, #0
        add  hl, hl
        add  hl, hl
        add  hl, hl
        add  hl, hl
        ld   de, #0x5C00            ; VR_SPRCOL
        add  hl, de
        push bc
        call _vdp_waddr
        pop  bc
        ld   a, c
        cp   #PL_UMP
        jp   c, 10$
        jp   z, 20$
        cp   #PL_BALL
        jp   z, 12$
        cp   #PL_SHADOW
        jp   z, 13$
        cp   #14
        jr   nc, 4$
        ld   hl, (_ump_mask)        
        or   a
        jr   z, 39$
38$:    srl  h
        rr   l
        dec  a
        jr   nz, 38$
39$:    bit  0, l
        jp   nz, 21$
4$:     ld   a, (_spr_mode)
        or   a                      ; SM_ATBAT
        jr   nz, 6$
        ld   a, c
        cp   #PL_BAT
        jp   nc, 14$
        cp   #PL_BATTER
        jr   c, 5$
        cp   #PL_FLD_AB
        jr   nc, 5$
        ld   hl, #_zone_big         
        cp   #PL_PITCHER
        jr   c, 41$
        ld   hl, #_zone_pitcher
        ld   a, b
        xor  #2
        ld   b, a
41$:    ld   e, #16
        bit  1, c
        jr   z, 30$
        ld   de, #32                
        add  hl, de
        ld   e, #8
        jr   30$
5$:     ld   hl, #_zone_chibi
        ld   a, c
        cp   #PL_FLD_AB
        jr   c, 51$
        ld   a, b
        xor  #2
        ld   b, a
51$:    ld   e, #16
        jr   30$
6$:     ld   hl, #_zone_chibi
        ld   a, c
        cp   #PL_FLD
        jr   c, 61$
        ld   a, b
        xor  #2
        ld   b, a
61$:    ld   e, #16
30$:    ld   a, b                   
        ld   (_pu_sym + 1), a
        inc  a
        ld   (_pu_sym + 2), a
        bit  0, c
        jr   nz, 31$
        inc  hl                     
31$:    ld   a, (_pu_e)
        ld   c, a
        ld   b, #16
32$:    ld   a, e
        or   a
        jr   z, 33$
        dec  e
        push hl
        ld   a, (hl)
        ld   hl, #_pu_sym
        add  a, l
        ld   l, a
        adc  a, h
        sub  l
        ld   h, a
        ld   a, (hl)
        pop  hl
33$:    or   c
        out  (0x98), a
        inc  hl
        inc  hl
        djnz 32$
        ret
10$:    ld   a, (_pu_e)             
        ld   c, a
        ld   b, #3
        ld   a, #7
        call 90$
        ld   b, #9
        ld   a, #15
        call 90$
        ld   b, #4
        ld   a, #12
        jr   90$
12$:    ld   a, (_ball_tint)
        or   a
        ld   a, #7
        jr   z, 15$
        ld   a, #14
        jr   15$
13$:    ld   a, #1
        jr   15$
14$:    ld   a, #15
15$:    ld   b, #16
        push af
        ld   a, (_pu_e)
        ld   c, a
        pop  af
90$:    push af
        or   c
        out  (0x98), a
        pop  af
        djnz 90$
        ret
20$:    ld   hl, #_ump_rowcol + 16
        jr   22$
21$:    ld   hl, #_ump_rowcol
22$:    ld   a, (_pu_e)
        ld   c, a
        ld   b, #16
23$:    ld   a, (hl)
        or   c
        out  (0x98), a
        inc  hl
        djnz 23$
        ret
    __endasm;
}

/* 面 p の色はそのままで、EC（左へ 32 ドットずらす）のビットだけ書き換える。
 * VRAM の色を読んで書き戻す（色を計算し直すより速い）。A=p L=e */
static void plane_ec(u8 p, u8 e) __naked
{
    (void)p; (void)e;
    __asm
        ld   c, l               ; C = e
        ld   l, a
        ld   h, #0
        add  hl, hl
        add  hl, hl
        add  hl, hl
        add  hl, hl
        ld   de, #0x5C00        ; VR_SPRCOL
        add  hl, de
        push hl
        push bc
        call _vdp_raddr
        pop  bc
        ld   hl, #-16
        add  hl, sp
        ld   sp, hl             ; 16 バイトの置き場
        ld   b, #16
1$:     in   a, (0x98)
        and  #0x7F
        or   c
        ld   (hl), a
        inc  hl
        djnz 1$
        ld   hl, #16
        add  hl, sp
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        ex   de, hl
        call _vdp_waddr
        ld   hl, #0
        add  hl, sp
        ld   b, #16
2$:     ld   a, (hl)
        out  (0x98), a
        inc  hl
        djnz 2$
        ld   hl, #18
        add  hl, sp
        ld   sp, hl
        ret
    __endasm;
}

void spr_colors(void)
{
    u8 i;
    ump_mask = pl_dirty = 0;
    colors_dirty = 32;
    ball_tint = ball_tint_cur = 0;
    for (i = 0; i < 32; i++) ec_cur[i] = 0;
}

/* 走者の面のうち first〜last-1 を審判の色に、PL_RUN〜first-1 を走者の色にする（変わった面だけ書き直す） */
void spr_ump_planes(u8 first, u8 last)
{
    /* first・last は PL_RUN〜14 の偶数。審判の面 = first〜last-1 */
    static const u16 below[8] = { 0, 0, 0, 0x003F, 0x00FF, 0x03FF, 0x0FFF, 0x3FFF };
    u16 ch = (below[last >> 1] - below[first >> 1]) ^ ump_mask;
    if (ch) {
        ump_mask ^= ch;
        pl_dirty |= ch;
    }
}

void spr_set_mode(u8 mode)
{
    spr_mode = mode;
    pending_r6 = mode == SM_ATBAT ? 0x0C : 0x0D;
    spr_colors();
}

void spr_frame_begin(void)
{
    u8 i, h;
    u8* p = sat;
    x0 = (s16)view_cx << 3;
    y0 = view_y;
    h = (u8)(view_y + 219);
    if (h == 216) h = 217;
    hide_y = h;
    for (i = 32; i; i--) {
        *p = h;
        p += 4;
    }
    ec_prev = ec_used;
    if (ec_used) {
        for (i = 0; i < 32; i++) ec_want[i] = 0;
        ec_used = 0;
    }
}

/* void spr_put(u8 plane, s16 x, s16 y, u8 pat)
 *   x,y = 左上（ワールド・ドット）。A=plane DE=x、y と pat はスタック（ここで片付ける）
 *   C で書くと 16 ビットの計算が重いのでアセンブラ */
void spr_put(u8 plane, s16 x, s16 y, u8 pat) __naked
{
    (void)plane; (void)x; (void)y; (void)pat;
    __asm
        ld   (_sp_plane), a
        pop  hl
        ex   (sp), hl
        ld   (_sp_y), hl
        ld   bc, (_y0)
        or   a
        sbc  hl, bc             ; sy
        ld   bc, #15
        add  hl, bc
        ld   a, h
        or   a
        jr   nz, 90$
        ld   a, l
        cp   #227
        jr   nc, 90$
        ex   de, hl             ; HL = x
        ld   bc, (_x0)
        or   a
        sbc  hl, bc             ; sx
        ld   bc, #31
        add  hl, bc
        ld   a, h
        or   a
        jr   z, 10$
        dec  a
        jr   nz, 90$
        ld   a, l
        cp   #31
        jr   nc, 90$
10$:    ex   de, hl             ; DE = sx+31
        ld   a, (_sp_plane)
        add  a, a
        add  a, a
        ld   c, a
        ld   b, #0
        ld   hl, #_sat
        add  hl, bc
        ld   a, (_sp_y)
        dec  a
        cp   #216
        jr   nz, 20$
        dec  a
20$:    ld   (hl), a
        inc  hl
        ld   a, d
        or   a
        jr   nz, 30$
        ld   a, e
        cp   #31
        jr   nc, 30$
        inc  a
        ld   (hl), a
        push hl
        ld   a, (_sp_plane)
        ld   c, a
        ld   b, #0
        ld   hl, #_ec_want
        add  hl, bc
        ld   (hl), #1
        ld   a, #1
        ld   (_ec_used), a
        pop  hl
        jr   40$
30$:    ld   a, e
        sub  #31
        ld   (hl), a
40$:    inc  hl
        ex   de, hl
        ld   hl, #2
        add  hl, sp
        ld   a, (hl)            ; pat
        add  a, a
        add  a, a
        ld   (de), a
        pop  hl
        inc  sp
        jp   (hl)
90$:    ld   a, (_sp_plane)
        add  a, a
        add  a, a
        ld   c, a
        ld   b, #0
        ld   hl, #_sat
        add  hl, bc
        ld   a, (_hide_y)
        ld   (hl), a
        pop  hl
        inc  sp
        jp   (hl)
    __endasm;
}

/* A=plane DE=a（スタック：戻り先, 呼び元の戻り先, pat）→ A=plane DE=x、スタックに y を積んで戻る */
static void actor_xy(void) __naked
{
    __asm
        ld   (_sp_plane), a
        ex   de, hl
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        inc  hl
        ld   c, (hl)
        inc  hl
        ld   b, (hl)
        sra  d
        rr   e
        sra  d
        rr   e
        sra  d
        rr   e
        sra  d
        rr   e
        sra  b
        rr   c
        sra  b
        rr   c
        sra  b
        rr   c
        sra  b
        rr   c
        ld   hl, #-8
        add  hl, de
        ex   de, hl             ; DE = x
        ld   hl, #-15
        add  hl, bc             ; HL = y
        pop  bc                 ; この関数の戻り先
        ex   (sp), hl           ; HL = 呼び元の戻り先、(sp) = y
        push hl
        push bc
        ld   a, (_sp_plane)
        ret
    __endasm;
}

/* void spr_actor(u8 plane, const Actor* a, u8 pat)：A=plane DE=a、pat はスタック。
 * 座標（サブ）をドットに直して spr_put / spr_put2 へ（C で書くと 16 ビットのシフトがとても重い） */
void spr_actor(u8 plane, const void* a, u8 pat) __naked
{
    (void)plane; (void)a; (void)pat;
    __asm
        call _actor_xy
        jp   _spr_put
    __endasm;
}

void spr_actor2(u8 plane, const void* a, u8 pat) __naked
{
    (void)plane; (void)a; (void)pat;
    __asm
        call _actor_xy
        jp   _spr_put2
    __endasm;
}

/* void spr_put2(u8 plane, s16 x, s16 y, u8 pat)：plane に pat、plane+1 に pat+1 を同じ位置で置く */
void spr_put2(u8 plane, s16 x, s16 y, u8 pat) __naked
{
    (void)plane; (void)x; (void)y; (void)pat;
    __asm
        ld   (_sp_plane), a
        pop  hl
        ex   (sp), hl
        ld   (_sp_y), hl
        ld   bc, (_y0)
        or   a
        sbc  hl, bc
        ld   bc, #15
        add  hl, bc
        ld   a, h
        or   a
        jp   nz, 90$
        ld   a, l
        cp   #227
        jp   nc, 90$
        ex   de, hl
        ld   bc, (_x0)
        or   a
        sbc  hl, bc
        ld   bc, #31
        add  hl, bc
        ld   a, h
        or   a
        jr   z, 10$
        dec  a
        jp   nz, 90$
        ld   a, l
        cp   #31
        jp   nc, 90$
10$:    ex   de, hl
        ld   a, (_sp_y)
        dec  a
        cp   #216
        jr   nz, 20$
        dec  a
20$:    ld   b, a
        xor  a
        ld   (_sp_ec), a
        ld   a, d
        or   a
        jr   nz, 30$
        ld   a, e
        cp   #31
        jr   nc, 30$
        inc  a
        ld   c, a
        ld   a, #1
        ld   (_sp_ec), a
        jr   40$
30$:    ld   a, e
        sub  #31
        ld   c, a
40$:    ld   hl, #2
        add  hl, sp
        ld   a, (hl)
        add  a, a
        add  a, a
        ld   e, a
        ld   a, (_sp_plane)
        add  a, a
        add  a, a
        ld   l, a
        ld   h, #0
        push bc
        ld   bc, #_sat
        add  hl, bc
        pop  bc
        ld   (hl), b
        inc  hl
        ld   (hl), c
        inc  hl
        ld   (hl), e
        inc  hl
        inc  hl
        ld   (hl), b
        inc  hl
        ld   (hl), c
        inc  hl
        ld   a, e
        add  a, #4
        ld   (hl), a
        ld   a, (_sp_ec)
        or   a
        jr   z, 50$
        ld   a, (_sp_plane)
        ld   c, a
        ld   b, #0
        ld   hl, #_ec_want
        add  hl, bc
        ld   (hl), #1
        inc  hl
        ld   (hl), #1
        ld   a, #1
        ld   (_ec_used), a
50$:    pop  hl
        inc  sp
        jp   (hl)
90$:    ld   a, (_sp_plane)
        add  a, a
        add  a, a
        ld   c, a
        ld   b, #0
        ld   hl, #_sat
        add  hl, bc
        ld   a, (_hide_y)
        ld   (hl), a
        ld   bc, #4
        add  hl, bc
        ld   (hl), a
        pop  hl
        inc  sp
        jp   (hl)
    __endasm;
}

/* ---- 走者・守備をまとめて置く（アセンブラ）----
 *   優先度の高い順（走者 → 守備 0..8）に、8 ライン単位の帯の枚数を見ながら置く。
 *   帯がすでに 7 枚以上なら、その選手は縁取りの層を省いて 1 枚にする（点滅させない）。
 *   Actor：x0 y2 … pat8（12 バイト）、Runner：Actor ＋ on12（25 バイト） */
u8 em_pre[16], em_pre_n;
u8 em_over;                     /* 9 枚以上になった帯がある */
u8 bk[32];                      /* 守備画面の 8 ライン帯の枚数（スコアボードの間は 1 行の組み立てに借りる） */
static u8 em_t, em_yb, em_xb, em_ec, em_n, em_pat, em_bc;
static u8* em_bp;
u8 em_fr;                       /* 走る絵の 2 コマ目なら 2（Actor.anim が 0 でない者に足す） */

void emit_actors(void) __naked
{
    __asm
        push ix
        ld   hl, #_bk
        xor  a
        .rept 32
        ld   (hl), a
        inc  hl
        .endm
        ld   (_em_over), a
        ld   a, (_em_pre_n)
        or   a
        jr   z, 2$
        ld   b, a
        ld   hl, #_em_pre
1$:     ld   a, (hl)
        inc  hl
        ld   c, (hl)
        inc  hl
        push hl
        push bc
        call 200$
        pop  bc
        pop  hl
        djnz 1$
2$:     ld   ix, #_run
        ld   b, #4
        ld   c, #6
3$:     ld   a, 23(ix)
        cp   #2
        jr   nc, 31$
        ld   a, 12(ix)
        or   a
        jr   z, 4$
31$:    push bc
        call 100$
        pop  bc
        inc  c
        inc  c
4$:     ld   de, #25
        add  ix, de
        djnz 3$
        ld   ix, #_fld
        ld   b, #9
        ld   c, #14
5$:     push bc
        call 100$
        pop  bc
        inc  c
        inc  c
        ld   de, #12
        add  ix, de
        djnz 5$
        pop  ix
        ret

100$:   ld   a, c
        ld   (_sp_plane), a
        ld   l, 2(ix)
        ld   h, 3(ix)
        sra  h
        rr   l
        sra  h
        rr   l
        sra  h
        rr   l
        sra  h
        rr   l
        ld   de, #-15
        add  hl, de
        ld   a, l
        dec  a
        cp   #216
        jr   nz, 101$
        dec  a
101$:   ld   (_em_yb), a
        ld   de, (_y0)
        or   a
        sbc  hl, de
        ld   de, #15
        add  hl, de
        ld   a, h
        or   a
        jp   nz, 190$
        ld   a, l
        cp   #227
        jp   nc, 190$
        ld   (_em_t), a
        ld   l, 0(ix)
        ld   h, 1(ix)
        sra  h
        rr   l
        sra  h
        rr   l
        sra  h
        rr   l
        sra  h
        rr   l
        ld   de, #-8
        add  hl, de
        ld   de, (_x0)
        or   a
        sbc  hl, de
        ld   de, #31
        add  hl, de
        ld   a, h
        or   a
        jr   z, 102$
        dec  a
        jp   nz, 190$
        ld   a, l
        cp   #31
        jp   nc, 190$
        sub  #31
        ld   (_em_xb), a
        xor  a
        ld   (_em_ec), a
        jr   104$
102$:   ld   a, l
        cp   #31
        jr   nc, 103$
        inc  a
        ld   (_em_xb), a
        ld   a, #1
        ld   (_em_ec), a
        jr   104$
103$:   sub  #31
        ld   (_em_xb), a
        xor  a
        ld   (_em_ec), a
104$:   ld   a, 8(ix)
        ld   c, a
        ld   a, 9(ix)
        or   a
        jr   z, 107$
        ld   a, (_em_fr)
        add  a, c
        ld   c, a
107$:   ld   a, c
        ld   (_em_pat), a
        ld   a, (_em_t)
        call 230$
        cp   #7
        ld   c, #2
        jr   c, 105$
        ld   c, #1
105$:   ld   a, c
        ld   (_em_n), a
        ld   hl, (_em_bp)
        ld   a, (_em_bc)
        ld   e, a
108$:   ld   a, (hl)
        add  a, c
        ld   (hl), a
        cp   #9
        jr   c, 109$
        ld   (_em_over), a
109$:   inc  hl
        dec  e
        jr   nz, 108$
        ld   a, (_sp_plane)
        add  a, a
        add  a, a
        ld   l, a
        ld   h, #0
        ld   de, #_sat
        add  hl, de
        ld   a, (_em_n)
        cp   #2
        jr   z, 106$
        ld   a, (_hide_y)
        ld   (hl), a
        inc  hl
        inc  hl
        inc  hl
        inc  hl
        ld   a, (_em_pat)
        inc  a
        ld   c, a
        ld   a, (_sp_plane)
        inc  a
        ld   b, a
        jp   220$
106$:   ld   a, (_em_pat)
        ld   c, a
        ld   a, (_sp_plane)
        ld   b, a
        call 220$
        ld   a, (_em_pat)
        inc  a
        ld   c, a
        ld   a, (_sp_plane)
        inc  a
        ld   b, a
        jp   220$
190$:   ld   a, (_sp_plane)
        add  a, a
        add  a, a
        ld   l, a
        ld   h, #0
        ld   de, #_sat
        add  hl, de
        ld   a, (_hide_y)
        ld   (hl), a
        ld   de, #4
        add  hl, de
        ld   (hl), a
        ret

200$:   ld   d, a
        add  a, #15
        srl  a
        srl  a
        srl  a
        ld   e, a
        ld   a, d
        srl  a
        srl  a
        srl  a
        ld   d, a
        ld   a, e
        sub  d
        inc  a
        ld   e, a
        ld   hl, #_bk
        ld   a, d
        add  a, l
        ld   l, a
        ld   a, #0
        adc  a, h
        ld   h, a
201$:   ld   a, (hl)
        add  a, c
        ld   (hl), a
        inc  hl
        dec  e
        jr   nz, 201$
        ret

210$:   ld   d, a
        add  a, #15
        srl  a
        srl  a
        srl  a
        ld   e, a
        ld   a, d
        srl  a
        srl  a
        srl  a
        ld   d, a
        ld   a, e
        sub  d
        inc  a
        ld   e, a
        ld   hl, #_bk
        ld   a, d
        add  a, l
        ld   l, a
        ld   a, #0
        adc  a, h
        ld   h, a
        xor  a
211$:   cp   (hl)
        jr   nc, 212$
        ld   a, (hl)
212$:   inc  hl
        dec  e
        jr   nz, 211$
        ret

230$:   ld   d, a
        add  a, #15
        srl  a
        srl  a
        srl  a
        ld   e, a
        ld   a, d
        srl  a
        srl  a
        srl  a
        ld   d, a
        ld   a, e
        sub  d
        inc  a
        ld   e, a
        ld   (_em_bc), a
        ld   hl, #_bk
        ld   a, d
        add  a, l
        ld   l, a
        ld   a, #0
        adc  a, h
        ld   h, a
        ld   (_em_bp), hl
        xor  a
231$:   cp   (hl)
        jr   nc, 232$
        ld   a, (hl)
232$:   inc  hl
        dec  e
        jr   nz, 231$
        ret

220$:   ld   a, (_em_yb)
        ld   (hl), a
        inc  hl
        ld   a, (_em_xb)
        ld   (hl), a
        inc  hl
        ld   a, c
        add  a, a
        add  a, a
        ld   (hl), a
        inc  hl
        inc  hl
        ld   a, (_em_ec)
        or   a
        ret  z
        push hl
        ld   c, b
        ld   b, #0
        ld   hl, #_ec_want
        add  hl, bc
        ld   (hl), #1
        ld   a, #1
        ld   (_ec_used), a
        pop  hl
        ret
    __endasm;
}

/* 表示しないフレーム：名前表が 8 ドットずれたらスプライトの x も合わせる */
void spr_keep(void)
{
    s16 nx = (s16)view_cx << 3;
    s16 d = x0 - nx;
    u8 i;
    if (!d) return;
    x0 = nx;
    for (i = 0; i < 32; i++) {
        u8* p = sat + (i << 2);
        s16 v;
        if (p[0] == hide_y) continue;
        v = (s16)p[1] + d;
        if (v < 0 || v > 255) p[0] = hide_y;
        else p[1] = (u8)v;
    }
}

void spr_hide(u8 plane)
{
    sat[plane << 2] = hide_y;
}

void spr_hide_all(void)
{
    u8 i;
    for (i = 0; i < 32; i++) sat[i * 4] = 217;
}

/* 垂直帰線の中で呼ぶ */
void spr_commit(void)
{
    u8 i;
    sat_commit();
    if (colors_dirty) {                     /* 絵の組を替えた：32 面の色を 8 フレームに分けて書く（打った瞬間に止まらないように） */
        u8 n = 4;
        i = 32 - colors_dirty;
        while (n-- && colors_dirty) {
            plane_upload(i++);
            colors_dirty--;
        }
    }
    if (!ec_used && !ec_prev) goto no_ec;
    for (i = 0; i < 32; i++) {
        if (ec_want[i] != ec_cur[i]) {
            ec_cur[i] = ec_want[i];
            plane_ec(i, ec_cur[i] ? 0x80 : 0);
        }
    }
no_ec:
    if (pl_dirty) {                         /* 審判と走者で色を入れ替えた面 */
        for (i = 0; i < 16; i++)
            if (pl_dirty & (1u << i)) plane_upload(i);
        pl_dirty = 0;
    }
    if (ball_tint != ball_tint_cur) {       /* ボールの色だけ書き換える（白 ⇔ 灰） */
        ball_tint_cur = ball_tint;
        plane_upload(PL_BALL);
    }
    if (pending_r6) {
        vdp_reg(6, pending_r6);
        pending_r6 = 0;
    }
}

/* ---- 中央の大きな文字（スプライト 4 枚 = 8 文字） ---- */
void msg_show(u8 id, u8 frames)
{
    vdp_waddr(VR_SPAT_ATBAT + P_MSG * 32);
    rom2vram(msg_tab[id].bank, msg_tab[id].ofs, msg_tab[id].len);
    vdp_waddr(VR_SPAT_FIELD + P_MSG * 32);
    rom2vram(msg_tab[id].bank, msg_tab[id].ofs, msg_tab[id].len);
    msg_len = msg_tab[id].n;
    msg_timer = frames;
}

/* スプライトもスクロール（縦 R#23・横 R#18）でいっしょに動くので、画面に止めて見せる文字は
 * 帰線期間に、いま書いたスクロールの値から位置を決め直す（描くのが 1 フレームおきでもぶれない） */
void msg_fix(void)
{
    u8 i, n, y, x;
    u8* p;
    if (!msg_timer) return;
    n = (msg_len + 1) >> 1;
    y = (u8)view_y + msg_y - 1;
    if (y == 216) y = 215;
    x = 128 - msg_len * 4 + show_fine;
    p = sat + (PL_MSG << 2);
    for (i = 0; i < n; i++, x += 16, p += 4) {
        p[0] = y;
        p[1] = x;
    }
}

void msg_draw(void)
{
    u8 i, n;
    s16 x;
    if (!msg_timer) return;
    n = (msg_len + 1) >> 1;
    x = x0 + 128 - (s16)msg_len * 4;
    for (i = 0; i < n; i++) spr_put(PL_MSG + i, x + i * 16, y0 + msg_y, P_MSG + i);
}
