/* オーバーレイ A の後ろ（RAM の F000h〜F1FFh、ROM はバンク 7 の 1300h〜）：試合中に呼ぶ関数。
 * 球場マップ（E300h〜EFFFh）に上書きされないので、試合の間はずっと使える（ovl_load の後だけ。
 * タイトル・EDIT・トーナメントの画面では、オーバーレイ B・C に上書きされているので呼ばない）。
 * 本体の RAM が足りないので、新しい機能はここに置く */
#include "game.h"

/* ---------------- 牽制 ----------------
 * 投手が B ＋ 塁の方向で、その塁へ投げる。塁の走者はリード（LEAD）の位置にいて、
 * 反応の遅れ（pk_wait 回の計算）の後で塁へ戻る（人が走者なら A ですぐ戻れる）。
 * ボールが先に届いて、塁に入った守備が走者に触ればアウト（判定はふつうのタッチアウト） */
u8 pk_wait;
static u8 pk_i;

static void pick_start(u8 i)
{
    Runner* r = &run[i];
    play_begin_held(POS_P);
    ball.x = fld[POS_P].x;          /* ボールは投手の手から（前の投球で捕手の所にある） */
    ball.y = fld[POS_P].y;
    throw_to_base(r->base);
    r->prog = LEAD;
    r->dir = 0;
    r->dest = r->base;
    runner_pos(r);
    pk_i = i;
    /* 反応の遅れ：ふつうはすぐ戻る（1〜8 回の計算）。16 回に 1 回は逆を突かれる（24 回：送球が先に届く） */
    pk_wait = (rnd() < 16 ? 24 : (rnd() & 7)) + 1;
}

u8 pick_try(u8 p)
{
    u8 b = 0, i, any = 0;
    Runner* r = run;
    if (p & K_RIGHT) b = 1;
    else if (p & K_UP) b = 2;
    else if (p & K_LEFT) b = 3;
    for (i = 0; i < 4; i++, r++) {
        if (!r->on) continue;
        any = b;
        if (r->base == b) {
            pick_start(i);
            return 1;
        }
    }
    return any;                     /* 走者がいない・方向なし：投げる（0）。走者のいない塁の方向：何もしない */
}

u8 pick_com(void)
{
    u8 i;
    for (i = 0; i < 4; i++) {
        Runner* r = &run[i];
        if (r->on && r->base == 1 && r->spd >= 389 + 5 * 23 && rnd() < 40) {   /* 一塁の足の速い走者に 16% */
            pick_start(i);
            return 1;
        }
    }
    return 0;
}

void pick_tick(void)
{
    Runner* r = &run[pk_i];
    if (--pk_wait) return;
    if (r->on && !r->dir && r->prog) {
        rgo(-1, r);
    }
}

/* 塁に走者がいるときの守備位置（サブ単位）。一塁手・三塁手は走者がいても定位置（ベースにはつかない。牽制球のときだけベースへ走って入る）。
 * 二塁に走者：遊撃手は二塁ベースの三塁寄りの後ろ（フェアグラウンドの中、リードした走者と重ならない） */
static const s16 hold_xy[6] = { S(334), S(288), S(237), S(233), S(178), S(288) };
static const u8 hold_who[3] = { POS_1B, POS_SS, POS_3B };

void hold_runners(void) __naked
{
    __asm
        ld   hl, #_run + 12         ; run[0].on
        ld   b, #4
1$:     ld   a, (hl)
        or   a
        jr   z, 3$
        inc  hl
        ld   a, (hl)                ; base
        dec  hl
        dec  a
        cp   #3
        jr   nc, 3$
        push hl
        push bc
        ld   e, a
        ld   d, #0
        ld   hl, #_hold_who
        add  hl, de
        ld   a, (hl)                ; fielder
        ld   hl, #_hold_xy
        add  hl, de
        add  hl, de
        add  hl, de
        add  hl, de                 ; src = hold_xy + 4 * (base - 1)
        push hl
        ld   l, a
        ld   h, #0
        add  hl, hl
        add  hl, hl
        ld   e, l
        ld   d, h
        add  hl, hl
        add  hl, de                 ; fielder * 12
        ld   de, #_fld
        add  hl, de
        ex   de, hl                 ; dst = &fld[i]（x y tx ty）
        pop  hl
        ldi
        ldi
        ldi
        ldi
        ld   bc, #-4
        add  hl, bc
        ldi
        ldi
        ldi
        ldi
        pop  bc
        pop  hl
3$:     ld   de, #25
        add  hl, de
        djnz 1$
        ret
    __endasm;
}
