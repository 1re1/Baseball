/* プレー中：打球・送球・守備・走者・アウトの判定・カメラ */
#include "game.h"

u8 play_result, ctl_fielder, play_outs, play_runs;
static u16 play_t;
static u8 end_t;
static u8 fly_caught;
static u8 chaser;
static u8 cover[5];             /* 塁 1..4（4 = 本塁）に入る守備 */
static u8 reassign_t;
static u8 dead_t;
static u8 hr_flag;
static u8 throw_from, throw_t;
static u8 hold_t;
static u8 bslot;                /* 打者走者の番号 */
static u8 run_to;               /* 球を持って走る先の塁（0 = なし） */
static u8 anim_throw;
static u8 grd;                  /* エンタイトル二塁打 */
static u8 react;                /* 打った直後の反応の遅れ */
static u8 ra_left;              /* 打った直後の割り当て：残りの守備の数（反応の遅れの間に 1 人ずつ計算して、止まらないように） */
static u8 ip_f;                 /* 計算の時刻と本当の時刻の差（0〜255 = 0〜1 歩）。ボールの絵をその分だけ先に描く */
static s16 cam_fx, cam_fy;      /* カメラ（1/16 ドット） */
static u8 wall_hit;             /* 打球が壁に当たった（予測が外れる） */
static u8 pat_turn;
u8 hardg;                       /* 痛烈なゴロ：弾みが強く、転がりの抵抗が半分（外野の壁まで届くことがある） */

/* 打球・送球・守備・走者の速さは、投球の速さと同じ物差し（打球の速さ ≒ 投球の速さ）にそろえてある。
 * 以前より 1/√2（0.707）倍の速さにして、重力を 2 → 1 にした（軌道の形と飛ぶ距離は同じで、時間だけ 1.41 倍） */
#define G 1
/* NPRED は game.h */
#define PSTEP 8
s16 pred_x[NPRED * 2];         /* 後ろ半分が y */
#define pred_y (pred_x + NPRED)
s16 land_x, land_y;
u8 land_t;

const u8 fspeed[9] = { 12, 11, 13, 14, 13, 14, 13, 14, 13 };
/* プレー中は 30 回/秒で動かすので、1 回あたりは 2 フレーム分 */
static const u8 fsp2[9] = { 24, 22, 26, 28, 26, 28, 26, 28, 26 };
u8 fsp_cur[9];                   /* この回の守備の歩幅（fspeed × sub_n）。move_to が使う */
static u8 sub_n, sub_acc, fsp_n;

u8 play_cover(u8 b) { return cover[b]; }
u8 play_fly_caught(void) { return fly_caught; }
u8 play_chaser(void) { return chaser; }

/* ------------------------------------------------------------------ */
/* 走者の位置：塁間は (±92, ±69) なので、進み t = prog の上位 8 ビットに対して
 * dx = (t * 92) >> 8、dy = (t * 69) >> 8 を足し引きする（表を使わず、足し算とずらしで計算）。
 * 塁 0・3 は x を足す（それ以外は引く）、塁 0・1 は y を引く（それ以外は足す）。HL = r */
void runner_pos(Runner* r) __naked
{
    (void)r;
    __asm
        push hl
        ld   de, #13
        add  hl, de
        ld   b, (hl)            ; base
        inc  hl
        inc  hl
        ld   c, (hl)            ; t
        ld   a, b
        cp   #4
        jr   c, 1$
        ld   hl, #HOME_X
        ld   de, #HOME_Y
        jr   8$
1$:     ld   l, c
        ld   h, #0
        add  hl, hl
        add  hl, hl
        ld   e, l
        ld   d, h               ; 4t
        add  hl, hl
        add  hl, hl
        add  hl, de             ; 20t
        add  hl, hl
        add  hl, de             ; 44t
        add  hl, hl
        add  hl, de             ; 92t
        ld   a, h
        push af                 ; dx
        ld   l, c
        ld   h, #0
        ld   e, l
        ld   d, h
        add  hl, hl
        add  hl, hl
        add  hl, hl
        add  hl, hl
        add  hl, de             ; 17t
        add  hl, hl
        add  hl, hl
        add  hl, de             ; 69t
        ld   c, h               ; dy
        pop  af
        ld   l, b
        ld   h, #0
        add  hl, hl
        push hl
        ld   de, #_base_x
        add  hl, de
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        ld   l, a
        ld   h, #0
        ld   a, b
        or   a
        jr   z, 2$
        cp   #3
        jr   z, 2$
        ex   de, hl
        or   a
        sbc  hl, de
        jr   3$
2$:     add  hl, de
3$:     ex   (sp), hl
        ld   de, #_base_y
        add  hl, de
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        ld   l, c
        ld   h, #0
        ld   a, b
        cp   #2
        jr   nc, 4$
        ex   de, hl
        or   a
        sbc  hl, de
        jr   5$
4$:     add  hl, de
5$:     ex   de, hl
        pop  hl
8$:     add  hl, hl
        add  hl, hl
        add  hl, hl
        add  hl, hl
        ex   de, hl
        add  hl, hl
        add  hl, hl
        add  hl, hl
        add  hl, hl
        ex   (sp), hl
        ld   (hl), e
        inc  hl
        ld   (hl), d
        inc  hl
        pop  de
        ld   (hl), e
        inc  hl
        ld   (hl), d
        ret
    __endasm;
}

void runners_place(void)
{
    u8 i;
    for (i = 0; i < 4; i++) {
        Runner* r = &run[i];
        r->out = 0;
        if (!r->on) continue;
        r->prog = 0;
        r->dir = 0;
        r->forced = 0;
        r->prog = LEAD;                 /* リードの位置に描く（試合の計算では塁の上） */
        runner_pos(r);
        r->prog = 0;
    }
}

void fielders_reset(void)
{
    u8 i;
    for (i = 0; i < 9; i++) {
        Actor* a = &fld[i];
        a->x = a->tx = S(home_pos_x[i]);
        a->y = a->ty = S(home_pos_y[i]);
        a->face = 0;
        a->moving = 0;
        a->anim = 0;
    }
    hold_runners();
}

/* ------------------------------------------------------------------ */
/* 転がりの抵抗（アセンブラ）：HL = 速さ → HL = 抵抗をかけた速さ。
 * |v| を (|v|>>5) + (|v|>>6) 減らす（0 なら 1）。向き（+/-）で差が出ないように絶対値で計算する。
 * A を壊す。ほかのレジスタは保存（速さは 4096 未満） */
static void fric(void) __naked
{
    __asm
        ld   a, h
        or   l
        ret  z
        push de
        bit  7, h
        jr   nz, 5$
        push hl
        add  hl, hl
        add  hl, hl
        ld   a, (_hardg)
        or   a
        jr   nz, 0$
        add  hl, hl
0$:     ld   a, h
        or   a
        jr   nz, 1$
        inc  a
1$:     pop  hl
        ld   e, a
        ld   a, l
        sub  e
        ld   l, a
        jr   nc, 2$
        dec  h
2$:     pop  de
        ret
5$:     push hl
        xor  a
        sub  l
        ld   l, a
        sbc  a, a
        sub  h
        ld   h, a
        add  hl, hl
        add  hl, hl
        ld   a, (_hardg)
        or   a
        jr   nz, 4$
        add  hl, hl
4$:     ld   a, h
        or   a
        jr   nz, 6$
        inc  a
6$:     pop  hl
        add  a, l
        ld   l, a
        jr   nc, 7$
        inc  h
7$:     pop  de
        ret
    __endasm;
}

/* 打球の 1 フレーム（予測にも使う） */
/* 打球の 1 フレーム（予測にも使う。アセンブラ）
 * Ball：x0 y2 z4 vx6 vy8 vz10 … bounced14 */
static void ball_step(Ball* b) __naked
{
    (void)b;
    __asm
        push ix
        push hl
        pop  ix
        ld   l, 0(ix)
        ld   h, 1(ix)
        ld   e, 6(ix)
        ld   d, 7(ix)
        add  hl, de
        ld   0(ix), l
        ld   1(ix), h
        ld   l, 2(ix)
        ld   h, 3(ix)
        ld   e, 8(ix)
        ld   d, 9(ix)
        add  hl, de
        ld   2(ix), l
        ld   3(ix), h
        ld   a, 5(ix)
        bit  7, a
        jr   nz, 1$
        or   4(ix)
        jr   nz, 2$
1$:     ld   a, 11(ix)
        bit  7, a
        jp   nz, 10$
        or   10(ix)
        jp   z, 10$
2$:     ld   l, 4(ix)
        ld   h, 5(ix)
        ld   e, 10(ix)
        ld   d, 11(ix)
        add  hl, de
        ld   4(ix), l
        ld   5(ix), h
        ex   de, hl
        dec  hl
        ld   10(ix), l
        ld   11(ix), h
        ld   a, 5(ix)
        bit  7, a
        jr   nz, 3$
        or   4(ix)
        jp   nz, 9$
3$:     xor  a
        ld   4(ix), a
        ld   5(ix), a
        ld   a, 14(ix)
        cp   #250
        jr   nc, 4$
        inc  14(ix)
4$:     ld   l, 10(ix)
        ld   h, 11(ix)
        ld   a, (_hardg)
        or   a
        ld   de, #7
        jr   z, 5$
        ld   e, #3
5$:     add  hl, de
        bit  7, h
        jr   z, 8$
        ld   l, 10(ix)
        ld   h, 11(ix)
        call 30$
        ld   d, h
        ld   e, l
        add  hl, hl
        add  hl, de
        ld   a, (_hardg)
        or   a
        jr   z, 6$
        add  hl, de
6$:     srl  h
        rr   l
        srl  h
        rr   l
        srl  h
        rr   l
        ld   10(ix), l
        ld   11(ix), h
        or   a
        jr   nz, 9$
        ld   l, 6(ix)
        ld   h, 7(ix)
        ld   d, h
        ld   e, l
        add  hl, hl
        add  hl, de
        sra  h
        rr   l
        sra  h
        rr   l
        ld   6(ix), l
        ld   7(ix), h
        ld   l, 8(ix)
        ld   h, 9(ix)
        ld   d, h
        ld   e, l
        add  hl, hl
        add  hl, de
        sra  h
        rr   l
        sra  h
        rr   l
        ld   8(ix), l
        ld   9(ix), h
        jr   9$
8$:     xor  a
        ld   10(ix), a
        ld   11(ix), a
9$:     pop  ix
        ret
10$:    ld   l, 6(ix)
        ld   h, 7(ix)
        call 20$
        ld   6(ix), l
        ld   7(ix), h
        ld   l, 8(ix)
        ld   h, 9(ix)
        call 20$
        ld   8(ix), l
        ld   9(ix), h
        ld   l, 6(ix)
        ld   h, 7(ix)
        call 40$
        jr   nz, 9$
        ld   l, 8(ix)
        ld   h, 9(ix)
        call 40$
        jr   nz, 9$
        xor  a
        ld   6(ix), a
        ld   7(ix), a
        ld   8(ix), a
        ld   9(ix), a
        jr   9$
20$:    jp   _fric
30$:    xor  a
        sub  l
        ld   l, a
        sbc  a, a
        sub  h
        ld   h, a
        ret
40$:    bit  7, h
        call nz, 30$
        ld   a, h
        or   a
        ret  nz
        ld   a, l
        cp   #3
        jr   c, 41$
        or   a
        ret
41$:    xor  a
        ret
    __endasm;
}

/* フライが落ちるまでのフレーム数（最大 160）。HL=z DE=vz → A（アセンブラ） */
static u8 fly_steps(s16 z, s16 vz) __naked
{
    (void)z; (void)vz;
    __asm
        ld   b, #0
1$:     bit  7, h
        jr   nz, 2$
        ld   a, h
        or   l
        jr   nz, 3$
2$:     bit  7, d
        jr   nz, 9$
        ld   a, d
        or   e
        jr   z, 9$
3$:     add  hl, de
        dec  de
        inc  b
        ld   a, b
        cp   #160
        jr   c, 1$
9$:     ld   a, b
        ret
    __endasm;
}

/* 転がるボールの予測（アセンブラ）：予測点を 1 つ（PSTEP フレーム先）計算して pred_n を 1 増やす。
 * ball_step の転がりと同じ計算（fric、|vx|,|vy| < 3 で止まる）。
 * IX = x, IY = y, BC = vx, DE = vy。速さは 2048 未満なので v>>5 は 8 ビットに収まる。
 * レジスタは全部保存する（ft_scan の途中から呼ぶ） */
static s16 rl_x, rl_y, rl_vx, rl_vy;
static u8 pred_n;               /* 計算済みの予測点の数 */

static void roll_one(void) __naked
{
    __asm
        push af
        push bc
        push de
        push hl
        push ix
        push iy
        ld   ix, (_rl_x)
        ld   iy, (_rl_y)
        ld   bc, (_rl_vx)
        ld   de, (_rl_vy)
        ld   a, #PSTEP
2$:     push af
        add  ix, bc
        add  iy, de
        ld   h, b
        ld   l, c
        call _fric
        ld   b, h
        ld   c, l
        ex   de, hl
        call _fric
        ex   de, hl
        ld   hl, #2
        add  hl, bc
        ld   a, h
        or   a
        jr   nz, 3$
        ld   a, l
        cp   #5
        jr   nc, 3$
        ld   hl, #2
        add  hl, de
        ld   a, h
        or   a
        jr   nz, 3$
        ld   a, l
        cp   #5
        jr   nc, 3$
        ld   bc, #0
        ld   d, b
        ld   e, c
3$:     pop  af
        dec  a
        jr   nz, 2$
        ld   (_rl_x), ix
        ld   (_rl_y), iy
        ld   (_rl_vx), bc
        ld   (_rl_vy), de
        ld   a, (_pred_n)
        inc  a
        ld   (_pred_n), a
        dec  a
        add  a, a
        ld   l, a
        ld   h, #0
        ld   de, #_pred_x
        add  hl, de
        push ix
        pop  de
        ld   (hl), e
        inc  hl
        ld   (hl), d
        ld   de, #NPRED * 2 - 1
        add  hl, de
        push iy
        pop  de
        ld   (hl), e
        inc  hl
        ld   (hl), d
        pop  iy
        pop  ix
        pop  hl
        pop  de
        pop  bc
        pop  af
        ret
    __endasm;
}

/* 打球の予測：空中なら落ちる場所と時間、転がっていれば NPRED 点 */
static void predict(void)
{
    if (ball.z > 0 || ball.vz > 0) {
        /* 落ちる場所は「胸の高さ（8 ドット）まで下りてきた所」：守備はそこで構えて捕る */
        land_t = fly_steps(ball.z - S(8), ball.vz);
        if (!land_t) land_t = fly_steps(ball.z, ball.vz);
        land_x = ball.x + (s16)land_t * ball.vx;
        land_y = ball.y + (s16)land_t * ball.vy;
        return;
    }
    land_t = 0;
    rl_x = ball.x;
    rl_y = ball.y;
    rl_vx = ball.vx;
    rl_vy = ball.vy;
    pred_n = 0;
}

static s16 fence_at(s16 px)
{
    u8 i, y0, y1;
    if (px < WALL_LX || px > WALL_RX) return 0;
    i = (u8)(px >> 3);
    y0 = fence_tab[i];
    y1 = fence_tab[i + 1];
    if (!y1) y1 = y0;
    if (!y0) return y1;
    return (s16)y0 + ((((s16)y1 - (s16)y0) * (s16)(px & 7)) >> 3);
}

static u8 inside_lines(s16 px, s16 py)
{
    s16 dx = abs16(px - HOME_X);
    s16 dy = HOME_Y - py;
    if (dy < 0) return 0;
    /* 塁線の傾きは 69:92 = 3:4 なので、3dx <= 4dy で比べる（掛け算なし） */
    return (u16)((dx << 1) + dx) <= (u16)(dy << 2);
}

/* ------------------------------------------------------------------ */
static u8 base_dist_ok(Actor* a, u8 b, u8 r)
{
    return bsd(b, a) <= S(r) + S(2);       /* おおよその距離で（四角の r とほぼ同じ広さ） */
}

static void set_target_base(u8 i, u8 b)
{
    s16 ox = 0, oy = 0;
    if (b == 1) ox = -5;            /* 一塁・三塁はベースのフェアグラウンド側に入る */
    if (b == 3) ox = 5;
    if (b == 4) oy = -4;
    fld[i].tx = S(base_x[b] + ox);
    fld[i].ty = S(base_y[b] + oy);
}

static u16 ftime[9];
u8 fk[9];

/* 守備 i が打球に追いつく時間（フレーム）と、そのときの予測位置の番号 */
/* 予測位置 pred[k] に初めて届く k を探す（届かなければ NPRED）。HL=ax DE=ay（アセンブラ） */
static s16 ft_ax, ft_ay;
static u16 ft_step, ft_reach;
static u8 ft_kmax;              /* 調べる点の数（これより後は今の最短より遅いので見ない） */

static u8 ft_scan(s16 ax, s16 ay) __naked
{
    (void)ax; (void)ay;
    __asm
        ld   (_ft_ax), hl
        ld   (_ft_ay), de
        ld   hl, #96
        ld   (_ft_reach), hl
        ld   b, #0
1$:     ld   a, (_pred_n)
        cp   b
        call z, _roll_one
        push bc
        ld   hl, (_ft_reach)
        ld   de, (_ft_step)
        add  hl, de
        ld   (_ft_reach), hl
        ld   l, b
        ld   h, #0
        add  hl, hl
        push hl
        ld   de, #_pred_x
        add  hl, de
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        ld   hl, (_ft_ax)
        ex   de, hl
        or   a
        sbc  hl, de
        ex   (sp), hl
        ld   de, #_pred_x + NPRED * 2
        add  hl, de
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        ld   hl, (_ft_ay)
        ex   de, hl
        or   a
        sbc  hl, de
        ex   de, hl
        pop  hl
        call _dist_approx
        ld   hl, (_ft_reach)
        or   a
        sbc  hl, de
        pop  bc
        jr   nc, 2$
        inc  b
        ld   a, (_ft_kmax)
        cp   b
        jr   nz, 1$
2$:     ld   a, b
        ret
    __endasm;
}

/* 今までの最短（追う者は 8 引いた値）。これより遅い守備は選ばれないので、計算を打ち切って 0xFFFF にする */
static u16 ft_best;

static void fielder_time(u8 i)
{
    Actor* a = &fld[i];
    u16 t = 0xFFFF, b = ft_best, d;
    u8 sp = fspeed[i];
    u8 k = NPRED - 1;
    if (i == POS_C && PXL(ball.y) < 330) {
        ftime[i] = 0xFFFF;
        return;
    }
    if (i == chaser) b = 0xFFFF;            /* 追う者は先に、全部計算する */
    if (land_t) {
        /* t = max(d / sp, land_t)。割り算は要るときだけ */
        d = dist_approx(land_x - a->x, land_y - a->y);
        if (d < (u16)sp * land_t) {
            if (land_t <= b) t = land_t;
        } else if (b == 0xFFFF || d < (u16)sp * (b + 1)) {
            t = d / sp;
        }
    } else {
        ft_kmax = b >= NPRED * PSTEP ? NPRED : (u8)b / PSTEP;
        if (ft_kmax) {
            ft_step = (u16)sp * PSTEP;
            k = ft_scan(a->x, a->y);
            if (k < ft_kmax) {
                t = (u16)(k + 1) * PSTEP;
            } else if (k == NPRED) {
                k = NPRED - 1;
                d = dist_approx(pred_x[k] - a->x, pred_y[k] - a->y);
                if (b == 0xFFFF || d < (u16)sp * (b - (NPRED * PSTEP - 1))) t = NPRED * PSTEP + d / sp;
            }
        }
    }
    ftime[i] = t;
    fk[i] = k;
    if (t != 0xFFFF) {
        if (i == chaser && t > 8) t -= 8;
        if (t < ft_best) ft_best = t;
    }
}

/* 追う者・ベースに入る者・目標を決める（時間は計算済み） */
static u8 use_pred;             /* 追う者の目標に予測の点を使う（打った瞬間の割り当てだけ） */
static void assign_targets(void);

static void assign_finish(void)
{
    u8 i, best = POS_P;
    u16 bt = 0xFFFF;
    if (ball.mode == BM_HIT) {
        for (i = 0; i < 9; i++) {
            u16 t = ftime[i];
            if (i == chaser && t > 8 && t != 0xFFFF) t -= 8;     /* 追いかけている者を優先 */
            if (t < bt) {
                bt = t;
                best = i;
            }
        }
        chaser = out_redirect(best);   /* はっきり外野へ飛んだ打球は、内野手は追わずに外野手へ任せる */
    } else {
        chaser = 0xFF;
    }
    use_pred = 1;
    assign_targets();
}

/* 塁 b にいちばん近い、追う者でもほかの塁に入る者でもない内野手 */
static u8 near_cover(u8 b)
{
    u8 i, k, best = POS_P;
    u16 bd = 0xFFFF;
    for (i = 0; i <= POS_SS; i++) {
        u16 d;
        if (i == chaser) continue;
        for (k = 1; k <= 4; k++)
            if (cover[k] == i) break;
        if (k <= 4) continue;
        d = bsd(b, &fld[i]);
        if (d < bd) {
            bd = d;
            best = i;
        }
    }
    return best;
}

/* ベースに入る者と、各守備の目標 */
static void assign_targets(void)
{
    u8 i, k, role[9];
    Actor* a;
    s16 bx = PXL(ball.x);
    cover[1] = POS_1B;
    cover[2] = bx >= HOME_X ? POS_SS : POS_2B;
    cover[3] = POS_3B;
    cover[4] = POS_C;
    /* 塁に入るはずの守備が打球を追っていたら、その塁にいちばん近い、手の空いた内野手（投手・捕手を含む）が入る */
    if (ball.mode == BM_HIT && chaser < 9)
        for (k = 1; k <= 4; k++)
            if (cover[k] == chaser) cover[k] = near_cover(k);
    for (i = 0; i < 9; i++) role[i] = 0;
    for (k = 4; k; k--) role[cover[k]] = k;      /* 2 つ受け持つときは小さい方 */
    a = fld;
    for (i = 0; i < 9; i++, a++) {
        if (ball.mode == BM_HELD && ball.holder == i) continue;
        if (i == chaser) {
            /* 予測したて：空中なら（跳ねている間も）落ちる場所、転がっていれば追いつく点。
             * 軽い見直しで替わった者はボールへ（fielders_update の先回りが毎回ねらいを決める） */
            if (!use_pred) {
                a->tx = ball.x;
                a->ty = ball.y;
            } else if (land_t) {
                a->tx = land_x;
                a->ty = land_y;
            } else {
                a->tx = pred_x[fk[i]];
                a->ty = pred_y[fk[i]];
            }
            continue;
        }
        k = role[i];
        if (k) {
            set_target_base(i, k);
            continue;
        }
        /* 外野はボールの方へ少し寄る */
        a->tx = S(home_pos_x[i]);
        a->ty = S(home_pos_y[i]);
        if (i >= POS_LF) {
            a->tx += (ball.x - a->tx) >> 2;
            a->ty += (ball.y - a->ty) >> 2;
        }
    }
    if (ball.mode == BM_HELD) ctl_fielder = ball.holder;
    else if (ball.mode == BM_THROW) ctl_fielder = ball.target;
    else if (chaser != 0xFF) ctl_fielder = chaser;
}

/* 素早い見直し（8 フレームごと）：ボールの 12 フレーム先にいちばん近い守備が追う。フライは落ちるまで変えない */
static void quick_assign(void)
{
    u8 i, best = 0xFF;
    u16 bd = 0xFFFF;
    s16 px, py;
    if (ball.z > 0 && !ball.bounced) return;
    qa_first();
    px = ball.x + (ball.vx << 3) + (ball.vx << 2);
    py = ball.y + (ball.vy << 3) + (ball.vy << 2);
    for (i = qa_i0; i < 9; i++) {      /* はっきり外野なら外野手だけ */
        u16 d;
        if (i == POS_C && PXL(ball.y) < 330) continue;
        d = dist_approx(px - fld[i].x, py - fld[i].y);
        if (i == chaser) d = d > S(16) ? d - S(16) : 0;     /* 今の者を少し優先 */
        if (d < bd) {
            bd = d;
            best = i;
        }
    }
    if (best != chaser) {
        chaser = best;
        use_pred = 0;
        assign_targets();
    }
}

/* すぐに全部計算する（打った瞬間・捕った瞬間など） */
static void assign_roles(void)
{
    u8 i;
    if (ball.mode == BM_HIT) {
        predict();
        ft_best = 0xFFFF;
        if (chaser < 9) fielder_time(chaser);
        for (i = 0; i < 9; i++)
            if (i != chaser) fielder_time(i);
    }
    assign_finish();
}

/* ---- 守備の移動（アセンブラ）：fld[i] を目標 (tx,ty) へ 8 方向で fspeed[i] だけ動かす ----
 * Actor の並び：x0 y2 tx4 ty6 pat8 anim9 face10 moving11（12 バイト） */
static s16 mt_dx, mt_dy;
static u16 mt_ax, mt_ay;
static u8 mt_d;

void move_to(u8 i) __naked
{
    (void)i;
    __asm
        push ix
        ld   e, a
        ld   d, #0
        ld   hl, #_fsp_cur
        add  hl, de
        ld   c, (hl)
        ld   l, a
        ld   h, #0
        add  hl, hl
        add  hl, hl
        ld   d, h
        ld   e, l
        add  hl, hl
        add  hl, de
        ld   de, #_fld
        add  hl, de
        push hl
        pop  ix
        ld   a, 0(ix)
        cp   4(ix)
        jr   nz, 60$
        ld   a, 1(ix)
        cp   5(ix)
        jr   nz, 60$
        ld   a, 2(ix)
        cp   6(ix)
        jr   nz, 60$
        ld   a, 3(ix)
        cp   7(ix)
        jr   nz, 60$
        ld   11(ix), #0
        pop  ix
        ret
60$:    ld   11(ix), #1
        ld   l, 4(ix)
        ld   h, 5(ix)
        ld   e, 0(ix)
        ld   d, 1(ix)
        or   a
        sbc  hl, de
        ld   (_mt_dx), hl
        bit  7, h
        jr   z, 1$
        ex   de, hl
        ld   hl, #0
        or   a
        sbc  hl, de
1$:     ld   (_mt_ax), hl
        ld   l, 6(ix)
        ld   h, 7(ix)
        ld   e, 2(ix)
        ld   d, 3(ix)
        or   a
        sbc  hl, de
        ld   (_mt_dy), hl
        bit  7, h
        jr   z, 2$
        ex   de, hl
        ld   hl, #0
        or   a
        sbc  hl, de
2$:     ld   (_mt_ay), hl
        ld   b, #0
        ld   hl, (_mt_ax)
        or   a
        sbc  hl, bc
        jr   z, 3$
        jr   nc, 6$
3$:     ld   hl, (_mt_ay)
        or   a
        sbc  hl, bc
        jr   z, 4$
        jr   nc, 6$
4$:     ld   l, 0(ix)
        ld   h, 1(ix)
        ld   de, (_mt_dx)
        add  hl, de
        ld   0(ix), l
        ld   1(ix), h
        ld   l, 2(ix)
        ld   h, 3(ix)
        ld   de, (_mt_dy)
        add  hl, de
        ld   2(ix), l
        ld   3(ix), h
        ld   a, d
        or   e
        ld   hl, (_mt_dx)
        or   h
        or   l
        jr   nz, 5$
        ld   11(ix), #0
5$:     pop  ix
        ret
6$:     ld   a, c
        srl  a
        ld   b, a
        srl  a
        srl  a
        ld   e, a
        srl  a
        add  a, e
        add  a, b
        ld   (_mt_d), a
        ld   hl, (_mt_ay)
        add  hl, hl
        ld   de, (_mt_ax)
        or   a
        sbc  hl, de
        jr   nc, 10$
        ld   a, c
        call 40$
        jr   20$
10$:    ld   hl, (_mt_ax)
        add  hl, hl
        ld   de, (_mt_ay)
        or   a
        sbc  hl, de
        jr   nc, 11$
        ld   a, c
        call 50$
        jr   20$
11$:    ld   a, (_mt_d)
        call 40$
        ld   a, (_mt_d)
        call 50$
20$:    ld   hl, (_mt_ay)
        ld   de, (_mt_ax)
        or   a
        sbc  hl, de
        jr   nc, 21$
        ld   a, (_mt_dx + 1)
        bit  7, a
        ld   a, #3
        jr   z, 22$
        ld   a, #2
        jr   22$
21$:    ld   a, (_mt_dy + 1)
        bit  7, a
        ld   a, #0
        jr   z, 22$
        ld   a, #1
22$:    ld   10(ix), a
        pop  ix
        ret
40$:    ld   e, a
        ld   d, #0
        ld   a, (_mt_dx + 1)
        bit  7, a
        jr   z, 41$
        xor  a
        sub  e
        ld   e, a
        sbc  a, a
        ld   d, a
41$:    ld   l, 0(ix)
        ld   h, 1(ix)
        add  hl, de
        ld   0(ix), l
        ld   1(ix), h
        ret
50$:    ld   e, a
        ld   d, #0
        ld   a, (_mt_dy + 1)
        bit  7, a
        jr   z, 51$
        xor  a
        sub  e
        ld   e, a
        sbc  a, a
        ld   d, a
51$:    ld   l, 2(ix)
        ld   h, 3(ix)
        add  hl, de
        ld   2(ix), l
        ld   3(ix), h
        ret
    __endasm;
}

/* 十字キーで守備 i を動かす（move_to の目標を押した方向へ少し先に置く） */
static void move_pad(u8 i, u8 p)
{
    Actor* a = &fld[i];
    a->tx = a->x;
    a->ty = a->y;
    if (p & K_LEFT) a->tx -= 64;
    if (p & K_RIGHT) a->tx += 64;
    if (p & K_UP) a->ty -= 64;
    if (p & K_DOWN) a->ty += 64;
    move_to(i);
    a->tx = a->x;
    a->ty = a->y;
}

/* ------------------------------------------------------------------ */
/* 走者 */
/* ---- 審判 4 人（球審・一塁・二塁・三塁） ----
 * 打球には当たらない。止まりかけた球のそば（2 人分くらい）にいたら、球から離れる。
 * ストライク・アウトはこぶしを上げ、セーフは両手を広げ、ファウルは両手を上げる */
typedef struct { s16 x, y; u8 pose, t; } Ump;
Ump ump[4];                      /* 審判 4 人（球審・一塁・二塁・三塁） */
static u8 ump_away;              /* 定位置を離れた審判がいる */
/* 一塁・三塁の審判は内野の画面（x 128〜383）の右端・左端に見える位置。y 268 はほかの選手と横に並ばない（1 行 8 枚） */
static const s16 ump_home[8] = { 256, 404, 374, 268, 272, 226, 138, 268 };     /* x, y の組（球審・一塁・二塁・三塁） */
static const u8 base_ump[5] = { 0, 1, 2, 3, 0 };

void ump_reset(void)
{
    u8 i;
    for (i = 0; i < 4; i++) {
        ump[i].x = ump_home[i * 2];
        ump[i].y = ump_home[i * 2 + 1];
        ump[i].pose = UMP_STAND;
        ump[i].t = 0;
    }
    ump_away = 0;
}

void ump_call(u8 base, u8 pose, u8 t)
{
    Ump* u = &ump[base_ump[base]];
    u->pose = pose;
    u->t = t;
}

/* 1 回分（打席は 1 フレーム、守備は 2 フレームごと）。A = avoid（止まりかけた球をよける）
 *   判定の身ぶりの時間を数え、止まりかけた球のそば（横 ±19・縦 ±15 ドット）にいたら 1 ドット離れ、
 *   離れていたら定位置へ 1 ドットずつ戻る。毎回呼ぶのでアセンブラ（Ump は x0 y2 pose4 t5 の 6 バイト） */
static u8 ut_slow;
static s16 ut_bx, ut_by;
static const s16* ut_hp;

void ump_tick(u8 avoid) __naked
{
    (void)avoid;
    __asm
        push ix
        ld   c, #0                  ; C = slow
        or   a
        jr   z, 3$
        ld   a, (_ball + 12)        ; ball.mode
        cp   #BM_HIT
        jr   z, 1$
        cp   #BM_DEAD
        jr   nz, 3$
1$:     ld   hl, (_ball + 6)        ; |vx| < 24
        ld   a, #24
        call 80$
        jr   nc, 3$
        ld   hl, (_ball + 8)        ; |vy| < 24
        ld   a, #24
        call 80$
        jr   nc, 3$
        inc  c
        ld   hl, (_ball + 0)
        call 90$
        ld   (_ut_bx), hl
        ld   hl, (_ball + 2)
        call 90$
        ld   (_ut_by), hl
3$:     ld   a, c
        ld   (_ut_slow), a
        or   a
        jr   nz, 5$
        ld   a, (_ump_away)
        or   a
        jr   nz, 5$
        ld   a, (_ump + 5)          ; 身ぶりの時間がだれも残っていなければ何もしない
        ld   hl, #_ump + 11
        or   (hl)
        ld   hl, #_ump + 17
        or   (hl)
        ld   hl, #_ump + 23
        or   (hl)
        jr   nz, 5$
        pop  ix
        ret
5$:     ld   ix, #_ump
        ld   hl, #_ump_home
        ld   (_ut_hp), hl
        ld   b, #4
6$:     push bc
        ld   a, 5(ix)               ; 身ぶりの時間
        or   a
        jr   z, 7$
        dec  a
        ld   5(ix), a
        jr   nz, 7$
        ld   4(ix), #UMP_STAND
7$:     ld   a, (_ut_slow)
        or   a
        jr   z, 20$
        ld   hl, (_ut_bx)           ; dx = bx - x
        ld   e, 0(ix)
        ld   d, 1(ix)
        or   a
        sbc  hl, de
        push hl
        ld   a, #20
        call 80$
        pop  de                     ; DE = dx
        jr   nc, 20$
        ld   hl, (_ut_by)           ; dy = by - y
        ld   c, 2(ix)
        ld   b, 3(ix)
        or   a
        sbc  hl, bc
        push de                     ; dx
        push hl                     ; dy
        ld   a, #16
        call 80$
        pop  hl                     ; HL = dy
        pop  de                     ; DE = dx
        jr   nc, 20$
        push hl                     ; 球から 1 ドット離れる
        ex   de, hl
        call 70$
        ld   l, 0(ix)
        ld   h, 1(ix)
        add  hl, de
        ld   0(ix), l
        ld   1(ix), h
        pop  hl
        call 70$
        ld   l, 2(ix)
        ld   h, 3(ix)
        add  hl, de
        ld   2(ix), l
        ld   3(ix), h
        ld   a, #1
        ld   (_ump_away), a
        jr   30$
20$:    ld   a, (_ump_away)         ; 定位置へ戻る
        or   a
        jr   z, 30$
        ld   hl, (_ut_hp)
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        ld   l, 0(ix)
        ld   h, 1(ix)
        call 60$
        ld   0(ix), l
        ld   1(ix), h
        ld   hl, (_ut_hp)
        inc  hl
        inc  hl
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        ld   l, 2(ix)
        ld   h, 3(ix)
        call 60$
        ld   2(ix), l
        ld   3(ix), h
30$:    ld   hl, (_ut_hp)
        ld   de, #4
        add  hl, de
        ld   (_ut_hp), hl
        ld   de, #6
        add  ix, de
        pop  bc
        dec  b
        jp   nz, 6$
        ld   a, (_ut_slow)          ; よけていないときは、みんな定位置に戻ったか確かめる
        or   a
        jr   nz, 50$
        ld   a, (_ump_away)
        or   a
        jr   z, 50$
        xor  a
        ld   (_ump_away), a
        ld   ix, #_ump
        ld   hl, #_ump_home
        ld   b, #4
40$:    ld   c, #4
41$:    ld   a, (hl)
        cp   0(ix)
        jr   nz, 45$
        inc  hl
        inc  ix
        dec  c
        jr   nz, 41$
        inc  ix
        inc  ix
        djnz 40$
        jr   50$
45$:    ld   a, #1
        ld   (_ump_away), a
50$:    pop  ix
        ret
60$:    push hl                     ; HL を DE へ 1 近づける
        or   a
        sbc  hl, de
        pop  hl
        ret  z
        jp   m, 61$
        dec  hl
        ret
61$:    inc  hl
        ret
70$:    ld   de, #1                 ; DE = HL > 0 ? -1 : 1
        bit  7, h
        ret  nz
        ld   a, h
        or   l
        ret  z
        ld   de, #-1
        ret
80$:    ld   e, a                   ; |HL| < A ならキャリー
        ld   d, #0
        add  hl, de
        ld   a, h
        or   a
        ret  nz
        ld   a, e
        add  a, a
        ld   d, a
        ld   a, l
        cp   d
        ret
90$:    sra  h                      ; HL >>= 4
        rr   l
        sra  h
        rr   l
        sra  h
        rr   l
        sra  h
        rr   l
        ret
    __endasm;
}

/* 描く：球審は PL_UMP、塁審は空いている走者の面 first〜last-1（足りなければ描かない）。
 * ud_pre = 1（守備の画面）のときは、8 ライン帯の枚数にも先に数える（pre_add と同じ）。
 * 毎フレーム呼ぶのでアセンブラ（A=first L=last）。Ump は x0 y2 pose4 t5 の 6 バイト */
static u8 ud_first, ud_last, ud_pl, ud_pre;

void ump_draw(u8 first, u8 last) __naked
{
    (void)first; (void)last;
    __asm
        push ix
        ld   (_ud_first), a
        ld   h, a
        ld   a, l
        ld   (_ud_last), a
        ld   a, h
        call _spr_ump_planes
        ld   ix, #_ump
        ld   a, #PL_UMP
        ld   (_ud_pl), a
        ld   b, #4
1$:     push bc
        ld   a, (_ud_pre)
        or   a
        jr   z, 3$
        ld   l, 2(ix)
        ld   h, 3(ix)
        ld   de, (_view_y)
        or   a
        sbc  hl, de             ; t = y - view_y（帯の番号の基準は pre_add と同じ）
        ld   a, h
        or   a
        jr   nz, 3$
        ld   a, l
        cp   #227
        jr   nc, 3$
        ld   c, a
        ld   a, (_em_pre_n)
        cp   #8
        jr   nc, 3$
        ld   e, a
        inc  a
        ld   (_em_pre_n), a
        ld   d, #0
        ld   hl, #_em_pre
        add  hl, de
        add  hl, de
        ld   (hl), c
        inc  hl
        ld   (hl), #1
3$:     ld   a, 4(ix)
        add  a, #P_UMP
        push af
        inc  sp
        ld   l, 2(ix)
        ld   h, 3(ix)
        ld   de, #-15
        add  hl, de
        push hl
        ld   l, 0(ix)
        ld   h, 1(ix)
        ld   de, #-8
        add  hl, de
        ex   de, hl
        ld   a, (_ud_pl)
        call _spr_put
        ld   a, (_ud_last)
        ld   l, a
        ld   a, (_ud_first)
        cp   l
        jr   nc, 9$             ; first >= last：もう面がない
        ld   (_ud_pl), a
        inc  a
        ld   (_ud_first), a
        ld   de, #6
        add  ix, de
        pop  bc
        djnz 1$
        pop  ix
        ret
9$:     pop  bc
        pop  ix
        ret
    __endasm;
}

/* 走者のいちばん近い塁（アウト・セーフを見る審判を決める） */
static u8 near_base(Runner* r)
{
    u8 b, best = 1;
    u16 bd = 0xFFFF;
    for (b = 1; b <= 4; b++) {
        u16 d = bsd(b, r);
        if (d < bd) {
            bd = d;
            best = b;
        }
    }
    return best;
}

/* アウトになった走者は、すぐには消さない（out = 2 以上の間は絵だけ残る。試合の判定には入らない）。
 * 一塁へ走っていた打者は、そのまま一塁まで走り抜ける（最大 1.5 秒）。ほかの走者はその場に 0.5 秒立つ */
#define GHOST_RUN 47
#define GHOST_STAND 17
static void runner_out(Runner* r)
{
    u8 k;
    if (r->out || !r->on) return;
    if (r->base == 0 && r->dir > 0) r->out = GHOST_RUN;
    else {
        r->out = GHOST_STAND;
        r->dir = 0;
    }
    r->on = 0;
    play_outs++;
    DBG(D_OUT);
    add_out();
    msg_show(outs >= 3 && play_outs >= 2 ? MSG_DP : MSG_OUT, 50);
    ump_call(near_base(r), UMP_PUNCH, 25);
    /* 後ろの走者がアウトになったら、前の走者の封殺は消える */
    for (k = 0; k < 4; k++)
        if (run[k].on && run[k].start > r->start) run[k].forced = 0;
}

static u8 base_busy(u8 b, Runner* me)
{
    u8 k;
    for (k = 0; k < 4; k++) {
        Runner* o = &run[k];
        if (o == me || !o->on) continue;
        if (o->base == b && o->prog == 0 && o->dir <= 0) return 1;
    }
    return 0;
}

static void runner_move(Runner* r)
{
    u16 step = sub_n == 2 ? r->spd << 1 : r->spd;
    s8 was = r->dir;
    if (r->dir > 0) {
        u8 nb = r->base + 1;
        u16 lim = 0xFFFF;
        /* フライが落ちる前は本塁に入らない */
        if (nb == 4 && ball.mode == BM_HIT && !ball.bounced && !hr_flag && !grd) lim = 0xB000;
        if (nb < 4 && r->prog > 0xA000 && !r->forced && base_busy(nb, r)) {
            rgo(-1, r);
            return;
        }
        if ((u16)(r->prog + step) < r->prog) {
            r->base = nb;
            r->prog = 0;
            if (nb == 4) {
                r->on = 0;
                if (outs < 3) {
                    play_runs++;
                    add_run();
                }
                return;
            }
            r->forced = 0;
            if (r->dest <= r->base) r->dir = 0;
        } else if (r->prog + step > lim) {
            r->prog = lim;
        } else {
            r->prog += step;
        }
    } else if (r->dir < 0) {
        if (r->prog <= step) {
            r->prog = 0;
            if (r->base > r->dest) {
                r->base--;
                r->prog = 0xFFFF;
            } else {
                r->dir = 0;
            }
        } else {
            r->prog -= step;
        }
    }
    if (fly_caught && r->base == r->start && r->prog == 0) r->tagged = 1;
    if (was || r->dir) runner_pos(r);
}

/* 人の走塁：B で進む、A で戻る（方向で塁を選ぶ。なしは全員） */
static void human_running(u8 p, u8 pn)
{
    u8 i, want = 0, back;
    if (!(pn & (K_A | K_B))) return;
    back = (pn & K_A) != 0;
    if (p & K_RIGHT) want = 1;
    else if (p & K_UP) want = 2;
    else if (p & K_LEFT) want = 3;
    else if (p & K_DOWN) want = 4;
    for (i = 0; i < 4; i++) {
        Runner* r = &run[i];
        u8 nb;
        if (!r->on) continue;
        nb = r->base + 1;
        if (!back && want && want == r->base && r->prog && !r->forced) {    /* B ＋ 元の塁の方向：戻る */
            rgo(-1, r);
            continue;
        }
        if (want && nb != want && !(r->prog == 0 && r->base + 1 == want)) continue;
        if (back) {
            if (r->forced && (ball.mode != BM_HIT || ball.bounced)) continue;     /* フライが落ちるまでは、押し出された走者も戻れる */
            if (r->prog) {
                rgo(-1, r);
            }
        } else {
            if (nb > 4) continue;
            if (fly_caught && !r->tagged) continue;
            if (ball.mode == BM_HIT && !ball.bounced && r->dir < 0) continue;
            r->dir = 1;
            if (r->prog == 0) r->dest = nb;
            else if (r->dest <= r->base) r->dest = nb;
            else if (r->dest < 4 && r->dest == nb) r->dest = nb;
        }
    }
}

/* ------------------------------------------------------------------ */
/* 送球・持って走る */
/* 成分 dsub（サブ）を、長さ d（サブ）のとき速さ TS にする（16 ビットで計算） */
static s16 vcomp(s16 dsub, u16 d)
{
    u16 a = (u16)abs16(dsub) >> 4;
    u16 dp = d >> 4;
    u16 v;
    if (!dp) dp = 1;
    v = (a * TS) / dp;
    return dsub < 0 ? -(s16)v : (s16)v;
}

u8 chase_k;

void throw_to_base(u8 b)
{
    chase_k = 0;
    Actor* h = &fld[ball.holder];
    u8 rcv = cover[b];
    s16 tx = S(base_x[b]), ty = S(base_y[b]);
    s16 dx, dy;
    u16 d;
    if (rcv == ball.holder) {
        run_to = b;
        return;
    }
    dx = tx - h->x;
    dy = ty - h->y;
    d = dist_approx(dx, dy);
    if (d < S(4)) return;
    ball.vx = vcomp(dx, d);
    ball.vy = vcomp(dy, d);
    ball.z = S(10);
    ball.vz = (s16)(d / (TS * 2));
    ball.bounced = 0;
    ball.mode = BM_THROW;
    ball.target = rcv;
    ball.tbase = b;
    throw_from = ball.holder;
    throw_t = 0;
    anim_throw = 7;
    fld[throw_from].face = dx > 0 ? 3 : 2;
    set_target_base(rcv, b);
    run_to = 0;
    sfx_play(SFX_THROW);
}

void run_with_ball(u8 b)
{
    run_to = b;
}

static u8 dir_to_base(u8 p)
{
    if (p & K_UP) return 2;
    if (p & K_RIGHT) return 1;
    if (p & K_LEFT) return 3;
    if (p & K_DOWN) return 4;
    return 0;
}

/* ------------------------------------------------------------------ */
static void catch_ball(u8 i)
{
    Actor* a = &fld[i];
    u8 was_fly = ball.mode == BM_HIT && !ball.bounced;
    if (ball.mode == BM_THROW && ball.target == i) {
        u8 k, tb = ball.tbase;
        for (k = 0; k < 4; k++) {
            Runner* r = &run[k];
            if (r->on && r->base == tb && !r->prog && r->start != tb) {
                msg_show(MSG_SAFE, 50);
                sfx_play(SFX_SAFE);
                ump_call(tb, UMP_SAFE, 25);
                break;
            }
        }
    }
    if (ball.mode == BM_HIT && !ball.fair) ball.fair = inside_lines(PXL(ball.x), PXL(ball.y)) ? 1 : 2;
    ball.mode = BM_HELD;
    ball.holder = i;
    ball.vx = ball.vy = ball.vz = 0;
    hardg = 0;
    hold_t = 0;
    run_to = 0;
    sfx_play(SFX_CATCH);
    if (was_fly) {
        u8 k;
        Runner* b = &run[bslot];
        fly_caught = 1;
        DBG(D_FLYOUT);
        ball.fair = 1;
        if (b->on) runner_out(b);
        for (k = 0; k < 4; k++) {
            Runner* r = &run[k];
            if (!r->on) continue;
            r->forced = 0;
            r->dest = r->start;
            if (r->base != r->start || r->prog) {
                r->dir = -1;
                r->tagged = 0;
            } else {
                r->dir = 0;
                r->tagged = 1;
            }
        }
    } else if (ball.fair == 2) {
        dead_t = 20;
    }
    (void)a;
    assign_roles();
}

static u8 cc_skip;
static const u16* cc_p;

/* 捕れる窓（守備 - ボール のサブ値 v が (v + ofs) < 幅 なら入る）：横・奥行き・見た目の縦（奥行き + 高さ） */
static const u16 cc_win[3][6] = {
    { 111, 223, 95, 191, 0x8000, 0xFFFF },      /* 転がる球：横 7・縦 6 ドット */
    { 96, 193, 96, 193, 0x8000, 0xFFFF },       /* 送球：グラブに届くまで（6 ドット） */
    /* 空中の打球：横 7、奥行きは守備の 8 ドット前〜6 ドット後ろ、見た目の球が守備の体（足元〜頭）に重なる */
    { 111, 223, 96, 225, 16, 257 },
};

/* 捕れる位置にいる守備（なければ 0xFF） */
static u8 find_catcher(void) __naked
{
    __asm
        push ix
        push iy
        ld   iy, (_cc_p)
        ld   ix, #_fld
        ld   b, #0
1$:     ld   a, (_cc_skip)
        cp   b
        jr   z, 3$
        ld   l, 0(ix)
        ld   h, 1(ix)
        ld   de, (_ball)
        call 10$
        jr   nc, 3$
        ld   l, 2(ix)
        ld   h, 3(ix)
        ld   de, (_ball + 2)
        or   a
        sbc  hl, de
        push hl
        call 11$
        pop  hl
        jr   nc, 3$
        ld   de, (_ball + 4)
        add  hl, de
        call 12$
        jr   nc, 3$
        ld   a, b
        jr   9$
3$:     ld   de, #12
        add  ix, de
        inc  b
        ld   a, b
        cp   #9
        jr   c, 1$
        ld   a, #0xFF
9$:     pop  iy
        pop  ix
        ret
    ; (hl - de + ofs) < width  → CF。ofs・幅は 0(iy)/2(iy)、11$ は 4(iy)/6(iy)、12$ は 8(iy)/10(iy)
10$:    or   a
        sbc  hl, de
        ld   e, 0(iy)
        ld   d, 1(iy)
        add  hl, de
        ld   e, 2(iy)
        ld   d, 3(iy)
        jr   13$
11$:    ld   e, 4(iy)
        ld   d, 5(iy)
        add  hl, de
        ld   e, 6(iy)
        ld   d, 7(iy)
        jr   13$
12$:    ld   e, 8(iy)
        ld   d, 9(iy)
        add  hl, de
        ld   e, 10(iy)
        ld   d, 11(iy)
13$:    or   a
        sbc  hl, de
        ret
    __endasm;
}

static void check_catch(void)
{
    u8 i;
    if (ball.z > S(14)) return;
    cc_skip = (ball.mode == BM_THROW && throw_t < 17) ? throw_from : 0xFF;   /* throw_t はフレーム数 */
    cc_p = cc_win[ball.mode == BM_THROW ? 1 : (ball.bounced ? 0 : 2)];
    i = find_catcher();
    if (i != 0xFF) catch_ball(i);
}

/* 封殺・タッチ・帰塁前の塁 */
static void judge(void)
{
    Actor* h;
    u8 b, k;
    if (ball.mode != BM_HELD || outs >= 3) return;
    h = &fld[ball.holder];
    for (b = 1; b <= 4; b++) {
        if (!base_dist_ok(h, b, 7)) continue;
        for (k = 0; k < 4; k++) {
            Runner* r = &run[k];
            if (!r->on) continue;
            if (r->forced && r->base == b - 1 && r->prog < 0xF600) runner_out(r);   /* 足が塁にかかった走者（残り 4.5 ドット未満）はセーフ */
            else if (fly_caught && !r->tagged && r->start == b && b < 4) runner_out(r);
        }
    }
    for (k = 0; k < 4; k++) {
        Runner* r = &run[k];
        if (!r->on || r->prog < 0x0A00 || r->prog >= 0xF600) continue;    /* 塁の上（足がかかっている）はタッチされない */
        if (abs16(r->a.x - h->x) < S(7) && abs16(r->a.y - h->y) < S(7)) runner_out(r);
    }
}

/* ------------------------------------------------------------------ */
static u8 foul_b, foul_n;        /* ファウルの球：この回数はずむまで（最大 foul_n 回）動かして見せる */

/* ファウルにする（球は 2 回目にはずむまで動かして見せる） */
static void call_foul(u8 roll)
{
    DBG(D_FOUL);
    ball.fair = 2;
    dead_t = 23;
    msg_show(MSG_FOUL, 45);
    sfx_play(SFX_FOUL);
    ump_call(0, UMP_FOUL, 25);
    ball.mode = BM_DEAD;
    foul_b = roll ? ball.bounced + 1 : 0;
    foul_n = 24;
}

/* 壁で跳ね返す。1 = 壁に当たった、2 = 高い球がスタンドに入った（どの壁もファウルゾーン） */
static u8 ball_walls(s16 px, s16 py)
{
    u8 hit = 0;
    if (px < WALL_LX) {
        ball.x = S(WALL_LX);
        ball.vx = -ball.vx / 2;
        hit = 1;
    } else if (px > WALL_RX) {
        ball.x = S(WALL_RX);
        ball.vx = -ball.vx / 2;
        hit = 1;
    }
    if (py > BACK_Y) {
        ball.y = S(BACK_Y);
        ball.vy = -ball.vy / 2;
        hit = 1;
    }
    /* ファウルゾーンの 45 度の壁：一塁側は (vx,vy)→(-vy,-vx)、三塁側は (vy,vx) と跳ね返る */
    if (px + py >= SIDE_R || py - px >= SIDE_L) {
        s16 t = ball.vx;
        if (ball.z > S(12)) return 2;
        ball.x -= ball.vx;
        ball.y -= ball.vy;
        if (px + py >= SIDE_R) {
            ball.vx = -ball.vy / 2;
            ball.vy = -t / 2;
        } else {
            ball.vx = ball.vy / 2;
            ball.vy = t / 2;
        }
        hit = 1;
    }
    if (hit) wall_hit = 1;
    return hit;
}

static void ball_update(void)
{
    s16 px, py, fy;
    if (ball.mode == BM_DEAD && foul_b) {           /* ファウルの球：2 回目にはずむまで */
        ball_step(&ball);
        if (dead_t < 12) dead_t = 12;
        if (ball_walls(PXL(ball.x), PXL(ball.y)) == 2 || ball.bounced >= foul_b || !--foul_n) foul_b = 0;
        return;
    }
    if (ball.mode == BM_HELD) {
        Actor* h = &fld[ball.holder];
        ball.x = h->x;
        ball.y = h->y;
        ball.z = S(8);
        return;
    }
    if (ball.mode != BM_HIT && ball.mode != BM_THROW) return;
    if (ball.mode == BM_THROW) throw_t++;
    {
        u8 before = ball.bounced;
        ball_step(&ball);
        if (ball.bounced != before) {
            sfx_play(ball.bounced < 3 ? SFX_BOUND : SFX_BOUND2);    /* 弾むたびに必ず鳴らす（3 回目からは小さく） */
            if (!before && ball.mode == BM_HIT) {      /* 外野へのヒット（フェアの打球が外野で弾んだ）：歓声 */
                s16 dy = HOME_Y - PXL(ball.y), dx = abs16(PXL(ball.x) - HOME_X);
                if (dy + (dx >> 1) >= 150 && inside_lines(PXL(ball.x), PXL(ball.y))) sfx_cheer();
            }
        }
        if (ball.mode == BM_THROW && ball.bounced != before) ball.mode = BM_HIT;
    }
    px = PXL(ball.x);
    py = PXL(ball.y);
    /* フェア・ファウル */
    if (ball.mode == BM_HIT && !ball.fair && !hr_flag) {
        u8 in = inside_lines(px, py);
        s16 dy = HOME_Y - py;
        if (ball.bounced) {
            if (!in) ball.fair = 2;
            else if (dy >= 69) ball.fair = 1;
            else if (!ball.vx && !ball.vy) ball.fair = 1;
        }
        if (ball.fair == 2) {
            call_foul(1);
            return;
        }
    }
    /* 壁（高いファウルフライはスタンドへ）。フェアと決まる前に壁に当たったらファウル */
    fy = ball_walls(px, py);
    if (fy == 2 || (fy && ball.mode == BM_HIT && !ball.fair && !hr_flag)) {
        call_foul(fy == 1);
        return;
    }
    fy = py < 216 ? fence_at(px) : 0;
    if (fy && py < fy) {
        if (ball.z > S(12)) {
            u8 in = inside_lines(px, py) && ball.fair != 2;
            ball.mode = BM_DEAD;
            if (!in) {
                call_foul(0);
            } else if (!ball.bounced) {
                u8 k;
                hr_flag = 1;
                DBG(D_HR);
                ball.hr = 1;
                ball.fair = 1;
                play_result = PR_HR;
                msg_show(MSG_HOMERUN, 160);
                bgm_play(BGM_HOMERUN);
                sfx_cheer();                            /* 歓声（曲といっしょに） */
                for (k = 0; k < 4; k++) {
                    Runner* r = &run[k];
                    if (!r->on) continue;
                    r->dest = 4;
                    r->dir = 1;
                    r->spd = 440;
                }
            } else {
                u8 k;
                grd = 1;
                ball.fair = 1;
                msg_show(MSG_DOUBLE, 80);
                for (k = 0; k < 4; k++) {
                    Runner* r = &run[k];
                    if (!r->on) continue;
                    r->dest = r->start + 2;
                    if (r->dest > 4) r->dest = 4;
                    r->dir = 1;
                    r->forced = 0;
                }
            }
            return;
        }
        if (ball.mode == BM_HIT && !ball.fair && !inside_lines(px, py)) {
            call_foul(1);
            return;
        }
        ball.y = S(fy);
        ball.vy = -ball.vy / 2;
        wall_hit = 1;
        ball.vx = ball.vx / 2;
    }
    check_catch();
}

/* ------------------------------------------------------------------ */
static u16 mv_skip;

/* mv_skip のビットが立っていない守備を move_to で動かす */
static void move_all(void) __naked
{
    __asm
        ld   hl, (_mv_skip)
        ld   b, #0
1$:     bit  0, l
        jr   nz, 2$
        push bc
        push hl
        ld   a, b
        call _move_to
        pop  hl
        pop  bc
2$:     srl  h
        rr   l
        inc  b
        ld   a, b
        cp   #9
        jr   c, 1$
        ret
    __endasm;
}

u8 sel_blink;                    /* B で切り替えた野手を点滅させる残り（描く回数） */

static void fielders_update(void)
{
    u8 i, hp = ctrl_pad(DEF);
    u8 p = hp != 0xFF ? pad[hp] : 0, pn = hp != 0xFF ? pad_new[hp] : 0;
    if (anim_throw) anim_throw--;
    react = react > sub_n ? react - sub_n : 0;
    if (dead_t || hr_flag || grd || react) {
        for (i = 0; i < 9; i++) fld[i].moving = 0;
        return;
    }
    mv_skip = 0;
    if (ball.mode == BM_HELD) {
        Actor* a;
        i = ball.holder;
        a = &fld[i];
        mv_skip = 1 << i;
        hold_t += sub_n;
        if (hp != 0xFF) {
            if (pn & K_A) {
                u8 b = dir_to_base(p);
                throw_to_base(b ? b : 1);
            } else if (pn & K_B) {
                u8 b = dir_to_base(p);
                if (b) run_with_ball(b);
            } else if (p & (K_UP | K_DOWN | K_LEFT | K_RIGHT)) {
                if (!(p & K_B)) run_to = 0;
                if (!run_to) move_pad(i, p);
            }
        } else if (hold_t > (fly_caught && i >= POS_LF ? 24 : 14)) {     /* フライを捕った外野手は、足を止めてから投げる */
            ai_holder();
        }
        if (ball.mode == BM_HELD && run_to) {
            a->tx = S(base_x[run_to]);
            a->ty = S(base_y[run_to]);
            move_to(i);
            if (base_dist_ok(a, run_to, 2)) run_to = 0;
        } else if (ball.mode == BM_HELD && hp == 0xFF && chase_k) {
            Runner* r = &run[chase_k - 1];      /* 挟殺：走者に向かって走る（触ればタッチアウト） */
            if (!r->on || !r->dir) chase_k = 0;
            else {
                a->tx = r->a.x;
                a->ty = r->a.y;
                move_to(i);
            }
        } else if (ball.mode == BM_HELD && hp == 0xFF) {
            a->moving = 0;
        }
    }
    /* 追う守備は毎回、ボールの今の位置と速さから先回りの地点を決める
     * （フライは落ちるまで落下地点。予測より遅れる跳ね返りにも付いていける） */
    if (ball.mode == BM_HIT && chaser < 9 && (ball.bounced || (ball.z <= 0 && ball.vz <= 0))) {
        Actor* c = &fld[chaser];
        u16 d = dist_approx(ball.x - c->x, ball.y - c->y);
        /* 予測した地点へ向かうのが基本。近い・壁で跳ねた・着いたのに来ない ときだけ先回りで追う */
        if (!use_pred || wall_hit || d < S(40) || (c->x == c->tx && c->y == c->ty)) {
            u8 lead = (u8)(d / fspeed[chaser]);
            if (lead > 24) lead = 24;
            c->tx = ball.x + ball.vx * lead;
            c->ty = ball.y + ball.vy * lead;
        }
    }
    /* B で操作する野手を切り替える。十字キーを押している間は手動。離すと自動で動く */
    if (hp != 0xFF && ball.mode == BM_HIT && (pn & K_B)) fielder_switch();
    if (hp != 0xFF && ball.mode == BM_HIT && ctl_fielder < 9 && (p & (K_UP | K_DOWN | K_LEFT | K_RIGHT))) {
        mv_skip |= 1 << ctl_fielder;
        move_pad(ctl_fielder, p);
    }
    move_all();
}

static void ghost_step(Runner* r)
{
    if (r->dir > 0) {
        u16 step = sub_n == 2 ? r->spd << 1 : r->spd;
        if ((u16)(r->prog + step) < r->prog) {      /* 一塁に着いた：消える */
            r->out = 1;
            return;
        }
        r->prog += step;
        runner_pos(r);
    }
    if (--r->out < 2) r->out = 1;
}

static void ghosts_step(void)
{
    u8 i;
    for (i = 0; i < 4; i++)
        if (!run[i].on && run[i].out >= 2) ghost_step(&run[i]);
}

static void runners_update(void)
{
    u8 i;
    if (side[OFF].ctrl) human_running(inp(OFF), inp_new(OFF));
    else if (!(play_t & 3)) ai_runners();
    ghosts_step();
    if (pk_wait) pick_tick();
    if (dead_t) return;
    for (i = 0; i < 4; i++)
        if (run[i].on) runner_move(&run[i]);
}

/* ------------------------------------------------------------------ */
static void play_common_begin(void)
{
    u8 i;
    cam_fx = S(cam_x);
    cam_fy = S(cam_y);
    play_t = 0;
    end_t = 0;
    fly_caught = 0;
    dead_t = 0;
    hr_flag = 0;
    grd = 0;
    play_outs = 0;
    play_runs = 0;
    run_to = 0;
    anim_throw = 0;
    chaser = 0xFF;
    reassign_t = 0;
    ra_left = 0;
    pk_wait = 0;
    for (i = 0; i < 4; i++) {
        Runner* r = &run[i];
        if (!r->on) continue;
        r->start = r->base;
        r->tagged = 0;
        r->out = 0;
    }
    spr_set_mode(SM_FIELD);
    /* 投手と捕手は球場の上の位置へ */
    fld[POS_P].x = S(HOME_X + pit_off);
    fld[POS_P].y = S(294);
}

void play_begin_hit(s16 vx, s16 vy, s16 vz)
{
    chase_k = 0;
    u8 i, occ[4] = { 0, 0, 0, 0 };
    Runner* b;
    play_common_begin();
    play_result = PR_NORMAL;
    react = 13;                     /* 反応の遅れ（ゲームのフレーム。打球が 0.707 倍の速さなので 12 × 1.41） */
    wall_hit = 0;
    ball.mode = BM_HIT;
    ball.vx = vx;
    ball.vy = vy;
    ball.vz = vz;
    ball.z = S(6);
    ball.bounced = 0;
    ball.fair = 0;
    ball.hr = 0;
    /* 打者走者 */
    for (i = 0; i < 4; i++)
        if (run[i].on) occ[run[i].base] = 1;
    for (bslot = 0; bslot < 4 && run[bslot].on; bslot++) ;
    b = &run[bslot];
    b->on = 1;
    b->base = 0;
    b->prog = 0;
    b->dir = 1;
    b->dest = 1;
    b->forced = 1;
    b->start = 0;
    b->who = side[OFF].bat_no;
    b->spd = 389 + cur_batter()->spd * 23;
    b->out = 0;
    b->tagged = 0;
    b->a.x = S(bat_x);
    b->a.y = S(bat_y);
    for (i = 0; i < 4; i++) {
        Runner* r = &run[i];
        if (!r->on || r == b) continue;
        r->forced = (r->base == 1) || (r->base == 2 && occ[1]) || (r->base == 3 && occ[1] && occ[2]);
        r->dest = r->forced ? r->base + 1 : r->base;
        r->dir = r->forced ? 1 : 0;
        runner_pos(r);
    }
    ai_runners();
    predict();
    ft_best = 0xFFFF;
    ra_left = 9;
    gstate = GS_PLAY;
}

void play_begin_held(u8 holder)
{
    play_common_begin();
    play_result = PR_STEAL;
    bslot = 0xFF;
    ball.mode = BM_HELD;
    ball.holder = holder;
    hold_t = 0;
    assign_roles();
    gstate = GS_PLAY;
}

/* カメラ（毎フレーム。プレーの計算は 1 フレームおき） */
void play_camera(void)
{
    s16 tx, ty, dx, dy;
    /* カメラ */
    if (hr_flag && play_t > 45) {
        tx = HOME_X - 128;
        ty = 200;
    } else if (ball.mode == BM_DEAD && !hr_flag) {
        tx = cam_x;
        ty = cam_y;
    } else {
        tx = PXL(ball.x) - 128;
        ty = PXL(ball.y) - PXL(ball.z) / 2 - 110;
    }
    /* 1/16 ドット単位で、差の 1/8 ずつ近づく。横は 1 フレーム 2 ドット・縦は 4 ドットまで
     * （横は 8 ドットごとに名前表を作り直すので、先読みが間に合う速さにしておく） */
    if (tx < 0) tx = 0;
    if (tx > 256) tx = 256;
    if (ty < 0) ty = 0;
    if (ty > 204) ty = 204;
    dx = (S(tx) - cam_fx) >> 3;
    dy = (S(ty) - cam_fy) >> 3;
    if (dx > 32) dx = 32;
    if (dx < -32) dx = -32;
    if (dy > 64) dy = 64;
    if (dy < -64) dy = -64;
    cam_fx += dx;
    cam_fy += dy;
    cam_x = cam_fx >> 4;
    cam_y = cam_fy >> 4;

}

/* 1 = プレー終了 */
u8 play_update(void)
{
    u8 i, settled = 1;
    if (++play_t == 2) hud_clear();     /* 四隅の表示は 2 回目の計算で消す（打った瞬間の 1 フレームに仕事を集めない） */
    if (outs < 3 && !hr_flag) {
        /* 追う守備の見直し（8 フレームごと、軽い計算）。全部の計算は打った瞬間・捕った瞬間だけ */
        if (ra_left) {
            if (ball.mode != BM_HIT) ra_left = 0;
            else fielder_time(9 - ra_left--);
            if (!ra_left && ball.mode == BM_HIT) assign_finish();
        } else if (ball.mode == BM_HIT && ++reassign_t >= 4) {
            reassign_t = 0;
            quick_assign();
        }
        if (ball.mode == BM_THROW && throw_t > 128) {
            ball.mode = BM_HIT;
            assign_roles();
        }
        /* 速さの段階：この回で進めるゲームのフレーム数（1 か 2）。守備の歩幅もそれに合わせる */
        sub_n = time_adv(&sub_acc, 2);
        ip_f = (sub_acc * 17) >> 2;
        if (sub_n != fsp_n) {
            fsp_n = sub_n;
            for (i = 0; i < 9; i++) fsp_cur[i] = sub_n == 2 ? fsp2[i] : fspeed[i];
        }
        ump_tick(1);
        ball_update();
        fielders_update();      /* 2 歩のボールの間で動かす（捕る判定で守備が 1 フレーム遅れないように） */
        if (sub_n == 2) ball_update();
        if (ball.mode == BM_HIT && !ball.bounced && ball.z > S(6)) {   /* フライの軌道音：高さ 0〜100 → 周期 200〜50 */
            u8 z = ball.z > S(100) ? 100 : (u8)PXL(ball.z);
            fly_note = 100 - (z >> 1) - (z >> 2);
            fly_hold = 6;
        }
        judge();                /* 走者が 2 フレーム分進む前にも判定（際どいプレーで走者が得をしないように） */
        runners_update();
        judge();
        if (ball.mode == BM_HELD && hold_t == sub_n) assign_roles();
    } else if (hr_flag) {
        /* ホームランの一周：A か B を押している間は 3 倍の速さ（演出を早く終える） */
        u8 n = (pad[2] & (K_A | K_B)) ? 3 : 1;
        while (n--)
            for (i = 0; i < 4; i++)
                if (run[i].on) runner_move(&run[i]);
        if (!(play_t & 3)) {
            if (play_t & 4) pal_set(13, 0x70, 0x07);     /* フェンスを黄色に */
            else pal_set(13, 0x14, 0x02);
        }
    } else {
        ghosts_step();          /* 3 アウトの後も、アウトになった走者は走り抜ける */
    }
    /* 終わり */
    for (i = 0; i < 4; i++)
        if ((run[i].on && (run[i].dir || run[i].prog)) || run[i].out >= 2) settled = 0;
    if (dead_t) {
        if (--dead_t == 0) {
            if (ball.fair == 2) {
                play_result = play_result == PR_STEAL ? PR_STEAL : PR_FOUL;
                for (i = 0; i < 4; i++) {
                    Runner* r = &run[i];
                    if (i == bslot) r->on = 0;
                    else if (r->on) {
                        r->base = r->start;
                        r->prog = 0;
                        r->dir = 0;
                    }
                }
            }
            return 1;
        }
        return 0;
    }
    if (outs >= 3) {
        if (++end_t > 25) return 1;
        return 0;
    }
    if (hr_flag || grd) {
        if (settled && ++end_t > 20) {
            side[OFF].hits++;
            pal_set(13, 0x14, 0x02);
            return 1;
        }
        return 0;
    }
    if (ball.mode == BM_HELD && settled) {
        if (++end_t > (side[DEF].ctrl ? 25 : 15)) {
            if (bslot < 4 && run[bslot].on && play_outs == 0) {
                u8 bb = run[bslot].base;
                DBG(D_HIT);
                side[OFF].hits++;
                if (bb == 2) msg_show(MSG_DOUBLE, 60), DBG(D_DOUBLE);
                else if (bb == 3) msg_show(MSG_TRIPLE, 60), DBG(D_TRIPLE);
            }
            return 1;
        }
    } else {
        end_t = 0;
    }
    if (play_t > 900) {
        DBG(D_TIMEOUT);
        return 1;
    }
    return 0;
}

/* ------------------------------------------------------------------ */
static u8 rot;
static const u8 run_pat[8] = { PF_RUN_D1, PF_RUN_D2, PF_RUN_U1, PF_RUN_U2, PF_RUN_L1, PF_RUN_L2, PF_RUN_R1, PF_RUN_R2 };
static const u8 stand_pat[4] = { PF_STAND_D, PF_STAND_U, PF_STAND_L, PF_STAND_R };

/* 先に数える帯（ボール・影・大きな文字）。t = 画面の上端 + 15 が 0..226 のときだけ */
extern u8 bk[32], em_over;      /* 8 ライン帯の枚数・9 枚以上の帯があるか（emit_actors が数える） */

static void pre_add(s16 ytop, u8 n)
{
    s16 t = ytop - view_y + 15;
    if (t < 0 || t > 226) return;
    em_pre[em_pre_n * 2] = (u8)t;
    em_pre[em_pre_n * 2 + 1] = n;
    em_pre_n++;
}

static u8 fielder_pat(u8 i)
{
    Actor* a = &fld[i];
    a->anim = a->moving;
    if (a->moving) return run_pat[a->face << 1];
    if (ball.mode == BM_HELD && ball.holder == i && anim_throw) return a->face == 3 ? PF_THROW_R : PF_THROW_L;
    if (i == POS_C && ball.mode != BM_HELD) return PF_CROUCH_B;
    if (ball.mode == BM_HIT && i == chaser && !ball.bounced && ball.z > S(24)) {
        s16 dx = ball.x - a->x, dy = ball.y - a->y;
        if (ABS(dx) < S(24) && ABS(dy) < S(24)) return PF_CATCH;
    }
    return stand_pat[a->face];
}

/* 優先度の高い順：ボール・影・走者・守備。混んだ帯では後ろから縁取りを省く */
/* PXL(p + v * ip_f / 256)（|v| < 128）。HL = p, DE = v -> DE */
static s16 ipx(s16 p, s16 v) __naked
{
    (void)p;
    (void)v;
    __asm
        push hl
        ld   c, #0
        bit  7, d
        jr   z, 1$
        xor  a
        sub  e
        ld   e, a
        sbc  a, a
        sub  d
        ld   d, a
        inc  c
1$:     ld   a, (_ip_f)
        ld   hl, #0
        ld   b, #8
2$:     add  hl, hl
        add  a, a
        jr   nc, 3$
        add  hl, de
3$:     djnz 2$
        ld   e, h
        ld   d, #0
        dec  c
        jr   nz, 4$
        xor  a
        sub  e
        ld   e, a
        sbc  a, a
        ld   d, a
4$:     pop  hl
        add  hl, de
        sra  h
        rr   l
        sra  h
        rr   l
        sra  h
        rr   l
        sra  h
        rr   l
        ex   de, hl
        ret
    __endasm;
}

void play_draw(void)
{
    u8 i;
    s16 bx, by, bz;
    u8 fr = (frame_count >> 3) & 1;
    em_pre_n = 0;
    if ((ball.mode != BM_HIT && ball.mode != BM_THROW) || hr_flag) ip_f = 0;
    bx = ipx(ball.x, ball.vx);
    by = ipx(ball.y, ball.vy);
    bz = ipx(ball.z, ball.vz);
    if (bz < 0) bz = 0;
    if (msg_timer) pre_add(view_y + msg_y, 3);
    /* ライン際で止まった球は灰色と白で点滅（白線と見分けがつくように） */
    ball_tint = 0;
    if (ball.mode == BM_HIT && !ball.vx && !ball.vy && ball.z <= 0) {
        s16 ax = bx - HOME_X, dd;
        if (ax < 0) ax = -ax;
        dd = (ax << 1) + ax - ((HOME_Y - by) << 2);       /* 3|dx| - 4dy：線の上で 0 */
        if (dd > -24 && dd < 24) ball_tint = (play_t >> 2) & 1;
    }
    if (ball.mode == BM_HIT || ball.mode == BM_THROW || (ball.mode == BM_DEAD && !hr_flag && dead_t > 10) ||
        (hr_flag && play_t < 35)) {
        u8 sz = bz < 10 ? 0 : (bz < 40 ? 1 : 2);
        if (ball.mode == BM_DEAD && hr_flag) {
            ball.x += ball.vx;
            ball.y += ball.vy;
            ball.z += ball.vz;
            ball.vz -= G;
        }
        spr_put(PL_BALL, bx - 8, by - bz - 8, PF_BALL + sz);
        pre_add(by - bz - 8, 1);
        if (!hr_flag || play_t < 15) {
            spr_put(PL_SHADOW, bx - 8, by - 8, PF_BALL + 3);
            pre_add(by - 8, 1);
        }
    }
    /* 守備の絵：1 人あたり 10 フレームに 1 回決める（走る足の切り替えは emit_actors） */
    if (++pat_turn >= 5) pat_turn = 0;
    for (i = pat_turn; i < 9; i += 5) {
        Actor* a = &fld[i];
        if (!a->moving && i != POS_C) {
            s16 dx = ball.x - a->x, dy = ball.y - a->y;
            if (ABS(dx) > ABS(dy)) a->face = dx > 0 ? 3 : 2;
            else a->face = dy > 0 ? 0 : 1;
        }
        a->pat = fielder_pat(i);
    }
    em_fr = fr << 1;
    /* 走者の絵（2 人ずつ） */
    for (i = pat_turn & 1; i < 4; i += 2) {
        Runner* r = &run[i];
        u8 pat, right;
        if (!r->on && r->out < 2) continue;
        r->a.anim = 0;
        right = (r->base == 0 || r->base == 3);
        if (r->dir < 0) right = !right;
        if (r->dir) {
            if (r->dir > 0 && r->prog > 0xD800 && ball.mode == BM_HELD &&
                base_dist_ok(&fld[ball.holder], r->base + 1, 40))
                pat = right ? PF_SLIDE_R : PF_SLIDE_L;
            else {
                pat = right ? PF_RUN_R1 : PF_RUN_L1;
                r->a.anim = 1;
            }
        } else {
            pat = right ? PF_STAND_R : PF_STAND_L;
        }
        r->a.pat = pat;
    }
    /* 審判：球審は PL_UMP、塁審は走者が使っていない面（先に帯へ数えて、守備が 1 枚に減らせるように） */
    {
        u8 k = 0;
        for (i = 0; i < 4; i++)
            if (run[i].on || run[i].out >= 2) k++;
        ud_pre = 1;
        ump_draw(PL_RUN + k * 2, 14);
        ud_pre = 0;
        emit_actors();
        /* 選手を優先：帯が 9 枚以上になった審判は、このフレームだけ消す（選手の絵が欠けないように） */
        if (sel_blink) {                /* 切り替えた野手を少し点滅させる */
            sel_blink--;
            if ((sel_blink & 4) && ctl_fielder < 9 && ball.mode == BM_HIT) {
                spr_hide(PL_FLD + ctl_fielder * 2);
                spr_hide(PL_FLD + ctl_fielder * 2 + 1);
            }
        }
        if (em_over) for (i = 0; i < 4; i++) {
            u8 pl = i ? PL_RUN + k * 2 + i - 1 : PL_UMP;
            s16 t = ump[i].y - view_y;
            if (pl >= 14) break;
            if (t >= 0 && t <= 226) {
                u8 a = (u8)t >> 3, e = ((u8)t + 15) >> 3;
                for (; a <= e; a++)
                    if (bk[a] > 8) {
                        spr_hide(pl);
                        break;
                    }
            }
        }
    }
}
