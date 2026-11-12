/* COM の考え：投球・打撃・盗塁・送球・走塁 */
#include "game.h"

/* ---- 投手 ---- */
static s8 aim_x;
static u8 aim_speed;
static u8 wait_t;
u8 ai_ptype;

void ai_pitch_plan(void)
{
    u8 r = rnd_n(10);
    aim_x = (s8)rnd_n(29) - 14;
    if (r < 3) aim_x = (s8)rnd_n(7) - 3;          /* 真ん中 */
    r = rnd_n(10);
    aim_speed = r < 6 ? K_DOWN : (r < 8 ? 0 : K_UP);   /* ↓ = 速い球、↑ = 遅い球 */
    ai_ptype = 0;                   /* 変化球：「変化」の高い投手ほど多い。2 ストライクからはフォークが増える */
    if (rnd() < 40 + cur_pitcher()->cv * 12) {
        r = rnd_n(10);
        ai_ptype = r < (strikes == 2 ? 5 : 2) ? PT_FORK : (r < 7 ? PT_CURVE : PT_SHOOT);
    }
    wait_t = 30 + rnd_n(60);
}

u8 ai_pitch_input(void)
{
    u8 k;
    if (gstate == GS_ATBAT) return gtimer >= wait_t ? K_A : 0;
    if (gstate != GS_PITCH) return 0;
    k = ball.mode == BM_PITCH ? 0 : aim_speed;     /* 速さのキーは投げるまで押す */
    if (ball.mode == BM_PITCH && ball.vy > 0 && (u8)(ptype - PT_CURVE) >= 2) {     /* カーブ・シュートは曲がるにまかせる */
        s16 frames = (S(HOME_Y) - ball.y) / ball.vy;
        if (frames > 0) {
            s16 px = ball.x + ball.vx * frames;
            s16 tg = S(HOME_X + aim_x);
            if (px < tg - S(2)) k |= K_RIGHT;
            else if (px > tg + S(2)) k |= K_LEFT;
        }
    }
    return k;
}

/* ---- 打者 ---- */
static u8 decided, will, lead;
static s16 want_x;
static u8 ai_key;               /* 当たる瞬間に押すキー（↓ 打ち上げ・↑ たたきつけ） */

void ai_bat_reset(void)
{
    decided = 0;
    will = 0;
}

static u8 run3_on(void)
{
    u8 i;
    for (i = 0; i < 4; i++)
        if (run[i].on && run[i].base == 3) return 1;
    return 0;
}

u8 ai_bat_input(void)
{
    u8 k = 0;
    if (gstate != GS_PITCH || ball.mode != BM_PITCH || ball.vy <= 0) return 0;
    if (!decided && PXL(ball.y) > 316) {
        const BatterDef* b = cur_batter();
        s16 frames = (S(HOME_Y) - ball.y) / ball.vy;
        s16 bl = brk_left();
        s16 px = PXL(ball.x + ball.vx * frames + bl - (bl >> 2));     /* 変化球は曲がりを 3/4 だけ読む */
        u8 strike = abs16(px - HOME_X) <= 7;
        u8 p = strike ? 205 : (strikes == 2 ? 80 : 35);
        s8 err;
        u8 skill = b->avg > 230 ? 0 : (u8)((230 - b->avg) / 30);    /* 0..6 上手ほど小さい */
        u8 ex = 4 + skill + (strike ? 0 : 4);                        /* 横のずれ */
        will = rnd() < p;
        err = (s8)rnd_n(ex * 2 + 1) - (s8)ex;
        want_x = batter_left ? px + BAT_REACH + err : px - BAT_REACH - err;
        lead = 5 + rnd_n(2);
        lead = (lead * 60) / grate;         /* 振ってから当たるまでのフレーム（速さの段階で変わる） */
        ai_key = 0;
        if (b->pow >= 6 && rnd() < 80) ai_key = K_DOWN;
        else if (b->spd >= 7 && rnd() < 80) ai_key = K_UP;
        if (outs < 2 && run3_on() && rnd() < 110) ai_key = K_DOWN;      /* 犠牲フライをねらう */
        if (rnd_n(4) < 1 + (skill >> 1)) lead += rnd_n(5) - 2;      /* タイミングのずれ */      /* タイミングのずれ */
        decided = 1;
    }
    if (decided && swing_t) return ai_key;
    if (decided) {
        if (bat_x < want_x - 1) k |= K_RIGHT;
        else if (bat_x > want_x + 1) k |= K_LEFT;
        if (will && !swing_t) {
            s16 fr = (S(bat_y - 4) - ball.y) / ball.vy;
            if (fr <= lead) k |= K_A;
        }
    }
    return k;
}

/* ---- 盗塁 ---- */
u8 ai_steal(void)
{
    u8 i;
    if (pit_t != 8 || outs >= 2) return 0;
    for (i = 0; i < 4; i++) {
        Runner* r = &run[i];
        if (r->on && r->base == 1 && r->spd >= 389 + 6 * 23) {
            u8 k, busy = 0;
            for (k = 0; k < 4; k++)
                if (run[k].on && run[k].base == 2) busy = 1;
            if (!busy && rnd() < 26) return 1;
        }
    }
    return 0;
}

/* ---- 守備：球を持ったら ---- */
static u16 run_time(Runner* r)
{
    return (u16)(0xFFFFu - r->prog) / r->spd;
}

static u16 throw_time(Actor* h, u8 b)
{
    return bsd(b, h) / TS + 8;
}

/* 押し出された走者（打者走者など）がまだ走っている：フォースプレーが先なので、挟殺の判断はしない（screens.c から呼ぶ） */
u8 rd_force(void)
{
    u8 i;
    for (i = 0; i < 4; i++)
        if (run[i].on && run[i].forced && run[i].dir > 0) return 1;
    return 0;
}

void ai_holder(void)
{
    Actor* h = &fld[ball.holder];
    u8 i, best = 0, lead_b = 0;
    s16 best_gain = 0;
    for (i = 0; i < 4; i++) {
        Runner* r = &run[i];
        u8 nb;
        s16 gain;
        if (!r->on || r->dir <= 0) continue;
        nb = r->base + 1;
        if (nb > lead_b) lead_b = nb;
        gain = (s16)run_time(r) - (s16)throw_time(h, nb);
        if (gain > 3 && (nb > best || gain > best_gain + 20)) {
            best = nb;
            best_gain = gain;
        }
    }
    /* フライを捕った後：まだ元の塁に戻っていない走者がいれば、その塁へ（戻るより送球が早ければ） */
    if (!best && play_fly_caught()) {
        for (i = 0; i < 4; i++) {
            Runner* r = &run[i];
            if (!r->on || r->dir >= 0 || r->tagged || r->base != r->start || !r->start) continue;
            if ((s16)(r->prog / r->spd) - (s16)throw_time(h, r->start) > 2) best = r->start;
        }
    }
    if (best) {
        s16 dx = abs16(PXL(h->x) - base_x[best]), dy = abs16(PXL(h->y) - base_y[best]);
        if (dx < 24 && dy < 24) run_with_ball(best);
        else throw_to_base(best);
        return;
    }
    if (rd_holder()) return;            /* 挟殺（screens.c の常駐部分） */
    if (lead_b && lead_b <= 4) {
        if (play_cover(lead_b) != ball.holder) throw_to_base(lead_b);
        return;
    }
    /* 落ち着いた：外野なら内野へ返す */
    if (ball.holder >= POS_LF) throw_to_base(2);
}

/* ---- 走塁 ---- */
static u16 ball_time_to(u8 b)
{
    u16 t;
    u8 c;
    if (ball.mode == BM_HELD) return throw_time(&fld[ball.holder], b);
    t = bsd(b, &ball) / TS;
    if (ball.mode == BM_THROW) return ball.tbase == b ? t : t + 57;
    c = play_chaser();
    t += 14;
    if (c < 9) t += dist_approx(fld[c].x - ball.x, fld[c].y - ball.y) / fspeed[c];
    return t;
}

void ai_runners(void)
{
    u8 i, c = play_chaser();
    u8 in_air = ball.mode == BM_HIT && !ball.bounced;
    u8 fc = play_fly_caught();
    u8 deep = c >= POS_LF && c < 9;         /* 外野フライ */
    for (i = 0; i < 4; i++) {
        Runner* r = &run[i];
        u8 nb;
        if (!r->on) continue;
        nb = r->base + 1;
        if (fc) {
            /* タッチアップ：捕った後に元の塁を踏み直した走者は、送球より先に着けそうなら次の塁へ
             * （外野手の送球は捕ってから約 24 フレーム後。本塁へは少し思い切って） */
            if (r->tagged && r->dir == 0 && !r->prog && nb <= 4 && outs < 3 && ball.mode == BM_HELD &&
                run_time(r) + (nb == 4 ? 0 : 8) < ball_time_to(nb) + 24) {
                rgo(1, r);
            }
            continue;
        }
        if (in_air) {
            if (outs == 2) {                /* 2 アウト：打ったら走る */
                if (r->dir == 0) {
                    rgo(1, r);
                }
            } else if (deep && r->base >= 2) {
                /* 外野フライ：二・三塁の走者は塁に戻ってタッチアップに備える */
                if (r->prog) {
                    rgo(-1, r);
                }
            } else if (r->dir > 0 && r->prog >= (deep ? 0x6000 : 0x2800)) {
                r->dir = 0;                 /* 捕られたら戻れるところで待つ（外野フライはハーフウェイ） */
            }
            continue;
        }
        if (r->forced) {                    /* 落ちた：押し出された走者は走る */
            if (r->dir <= 0) {
                rgo(1, r);
            }
            continue;
        }
        if (r->dir == 0 && r->prog) {       /* 途中で待っていた：とりあえず進む（間に合わなければ下で戻る） */
            rgo(1, r);
        }
        /* はさまれた走者（リードの近さ（8 ドット未満）から塁へ戻っている走者は、そのまま戻る） */
        if (ball.mode == BM_HELD && r->dir && nb <= 4 && (r->dir > 0 || r->prog >= OFF8) && rd_runner(r, nb)) continue;
        if (r->dir == 0 && r->prog == 0 && nb <= 4) {
            u16 tr = 0xFFFFu / r->spd;
            u16 tb = ball_time_to(nb);
            u8 bold = (outs == 2) ? 23 : 3;
            if (ball.mode == BM_HIT && ball.y < S(260)) bold += 14;     /* 外野に抜けた */
            if (tr < tb + bold) {
                rgo(1, r);
            }
        } else if (r->dir > 0 && r->prog < 0x9000 && nb <= 4) {
            u16 tr = run_time(r);
            u16 tb = ball_time_to(nb);
            if (tr > tb + 20 && r->prog < 0x6000) {
                rgo(-1, r);
            }
        }
    }
}
