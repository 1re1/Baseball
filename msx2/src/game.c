/* 試合の流れ：打席・投球・判定・HUD・攻守交代 */
#include "game.h"

Side side[2];
TeamDef tm[2];
u8 inning, half, balls, strikes, outs;
u8 max_inning = 9;
u8 game_mode;
Actor fld[9];
Runner run[4];
Ball ball;
u8 batter_left, pitcher_left;
u8 gstate;
u16 gtimer;
u8 sayonara;

const s16 base_x[5] = { HOME_X, B1_X, B2_X, B3_X, HOME_X };
const s16 base_y[5] = { HOME_Y, B1_Y, B2_Y, B3_Y, HOME_Y };
const s16 home_pos_x[9] = { 256, 256, 334, 298, 178, 214, 140, 256, 372 };
const s16 home_pos_y[9] = { 294, 394, 288, 252, 288, 252, 170, 128, 170 };

/* 打席の状態 */
s16 bat_x, bat_y;
u8 swing_t;
s8 pit_off;
u8 pit_t;
static u8 bunt_on, bunt_try;
static s16 plate_x;
static u8 crossed, swung;
static u8 pit_key;              /* 投げるときの ↑↓（↓ = 速い球、↑ = 遅い球）。振りかぶる間に押しても効く */
static u8 hit_stop;             /* 当たった瞬間を見せるフレーム数（そのあと打球が飛ぶ） */
static s16 hs_v[3];
static u8 so_wait;              /* 三振：「ストライク」を見せてから「アウト」を出すまで */
static u8 fork_on, slow_on;     /* 投げた後に押した ↓（フォーク）・↑（チェンジアップ） */
static u8 at_acc, at_adv;       /* 打席の時間の進み（速さの段階） */
static s8 pv_acc, pv_max;       /* 曲がりの強さ・最大（投手の「変化」から） */
static s16 vy_slow, vy_fork;    /* チェンジアップ・フォークで遅くする下限 */
static u8 pitch_kmh;
u8 ptype;                       /* 投げた球の球種（0 = まっすぐ） */
static u8 brk_a, brk_neg;       /* カーブ・シュートの曲がり幅（サブ）・向き（1 = 左へ） */
static s16 brk_last;            /* いままでに曲げた分（サブ） */
static u8 cmd_k, cmd_t, cmd_ok; /* 球種のコマンド：最後に押した方向・その後のフレーム・2 回続けて押された方向 */
u8 rt_t;                        /* 捕手から投手への返球（0 = まだ、1〜32 = 飛んでいる） */
u8 res_next;
static u8 steal_on;
static s16 pitch_v0;
static u8 pin, pnew, pprev, bin, bnew, bprev;
u8 play_phase;
static u8 acc_new[3];
static BatterDef pbat;      /* 打席に立つ投手 */

#define BAT_Y0 378
#define HUD_T 25
#define HUD_B 48

/* ------------------------------------------------------------------ */
const PitcherDef* cur_pitcher(void)
{
    return &tm[DEF].pit[side[DEF].pit];
}

const BatterDef* cur_batter(void)
{
    Side* s = &side[OFF];
    u8 o = s->order[s->bat_no];
    if (o == 255) {
        const PitcherDef* p = &tm[OFF].pit[s->pit];
        u8 i;
        for (i = 0; i < 5; i++) pbat.name[i] = p->name[i];
        pbat.avg = 60;
        pbat.pow = 1;
        pbat.spd = 3;
        pbat.hr = 0;
        pbat.flags = p->flags;
        return &pbat;
    }
    return &tm[OFF].bat[o];
}

u8 ctrl_pad(u8 sd)
{
    u8 c = side[sd].ctrl;
    return c ? c - 1 : 0xFF;
}

u8 inp(u8 sd)
{
    u8 c = side[sd].ctrl;
    return c ? pad[c - 1] : 0;
}

u8 inp_new(u8 sd)
{
    u8 c = side[sd].ctrl;
    return c ? pad_new[c - 1] : 0;
}

/* 投手・打者の入力（人または COM） */
static void read_roles(void)
{
    u8 v;
    v = side[DEF].ctrl ? pad[side[DEF].ctrl - 1] : ai_pitch_input();
    pnew = v & ~pprev;
    pprev = v;
    pin = v;
    v = side[OFF].ctrl ? pad[side[OFF].ctrl - 1] : ai_bat_input();
    bnew = v & ~bprev;
    bprev = v;
    bin = v;
}


/* ------------------------------------------------------------------ */
u8 bat_req = 0xFF;              /* 読み込む打者のコマ（0xFF = なし。frame_sync が読む） */
static u8 bat_cur = 0xFF;       /* 打席の表に入っているコマ */

void load_batter_sprites(void)
{
    batter_left = cur_batter()->flags & 1;
    bat_cur = 0xFF;
}

void batter_frame_upload(void)
{
    vdp_waddr(VR_SPAT_ATBAT + PA_BATTER * 32);
    if (batter_left) rom2vram(A_BATTER_L_BANK, A_BATTER_L_OFS + (u16)bat_req * 192, 192);
    else rom2vram(A_BATTER_R_BANK, A_BATTER_R_OFS + (u16)bat_req * 192, 192);
    bat_req = 0xFF;
}

void load_pitcher_sprites(void)
{
    pitcher_left = cur_pitcher()->flags & 1;
    vdp_waddr(VR_SPAT_ATBAT + PA_PITCHER * 32);
    if (pitcher_left) rom2vram(A_PITCHER_L);
    else rom2vram(A_PITCHER_R);
}

/* ------------------------------------------------------------------ */
/* HUD（打席のときだけ。マップの 25〜27 行と 48〜50 行に書く） */
static u8 lamp(u8 on, u8 t)
{
    return on ? t : T_LAMP_OFF;
}

/* 名前の長さ（後ろの空白を除く） */
static u8 name_len(const u8* n)
{
    u8 l = 5;
    while (l && n[l - 1] == T_SPACE) l--;
    return l;
}

/* 右下 4x3：B●●● / S●● / O●● */
void hud_count(void)
{
    u8 i;
    txt_ascii(28, HUD_B, "B");
    for (i = 0; i < 3; i++) txt_tile(29 + i, HUD_B, lamp(balls > i, T_LAMP_B));
    txt_ascii(28, HUD_B + 1, "S");
    for (i = 0; i < 2; i++) txt_tile(29 + i, HUD_B + 1, lamp(strikes > i, T_LAMP_S));
    txt_tile(31, HUD_B + 1, T_SPACE);
    txt_ascii(28, HUD_B + 2, "O");
    for (i = 0; i < 2; i++) txt_tile(29 + i, HUD_B + 2, lamp(outs > i, T_LAMP_O));
    txt_tile(31, HUD_B + 2, T_SPACE);
}

/* 右上の枠の幅（投手名か「145KM」の長い方） */
static u8 tr_w = 5;

static void hud_speed(void)
{
    txt_fill(32 - tr_w, HUD_T + 1, T_SPACE, tr_w);
    if (pitch_kmh) {
        txt_num(27, HUD_T + 1, pitch_kmh, 3);
        txt_tile(30, HUD_T + 1, T_KM_K);      /* 単位は小文字の km */
        txt_tile(31, HUD_T + 1, T_KM_M);
    }
}

/* 打席の表示：四隅に必要な大きさだけ（左上 得点・回 / 右上 投手 / 左下 打者 / 右下 BSO） */
void hud_draw(void)
{
    const BatterDef* b = cur_batter();
    const PitcherDef* p = cur_pitcher();
    u8 i, l;
    hud_clear();
    /* 左上 5x3：DOL 0 / STA 3 / 1回表 */
    for (i = 0; i < 3; i++) txt_fill(0, HUD_T + i, T_SPACE, 5);
    for (i = 0; i < 2; i++) {
        txt_n(0, HUD_T + i, thdr[side[i].team].abbr, 3);
        txt_num(3, HUD_T + i, side[i].runs, 2);
    }
    l = inning + 1 >= 10 ? 2 : 1;
    txt_num(0, HUD_T + 2, inning + 1, l);
    txt_tile(l, HUD_T + 2, T_KAI);
    txt_tile(l + 1, HUD_T + 2, half ? T_URA : T_OMOTE);
    /* 右上（右寄せ）：投手名 / 145KM / ST99 */
    l = name_len(p->name);
    tr_w = l > 5 ? l : 5;
    for (i = 0; i < 3; i++) txt_fill(32 - tr_w, HUD_T + i, T_SPACE, tr_w);
    txt_n(32 - l, HUD_T, p->name, l);
    hud_speed();
    txt_ascii(28, HUD_T + 2, "ST");
    txt_num(30, HUD_T + 2, side[DEF].stamina > 99 ? 99 : side[DEF].stamina, 2);
    /* 左下 7x2（いつも 7 文字幅）：1ヤマダ / .291H 3 */
    txt_fill(0, HUD_B + 1, T_SPACE, 7);
    txt_fill(0, HUD_B + 2, T_SPACE, 7);
    txt_num(0, HUD_B + 1, side[OFF].bat_no + 1, 1);
    txt_n(1, HUD_B + 1, b->name, name_len(b->name));
    txt_ascii(0, HUD_B + 2, ".");
    txt_num(1, HUD_B + 2, (u16)b->avg + 100, 3);
    txt_ascii(4, HUD_B + 2, "H");
    txt_num(5, HUD_B + 2, b->hr, 2);
    hud_count();
}

void hud_clear(void)
{
    scroll_restore_rows(HUD_T, HUD_T + 2);
    scroll_restore_rows(HUD_B, HUD_B + 2);
}

/* ------------------------------------------------------------------ */
void add_out(void)
{
    outs++;
    sfx_play(SFX_OUT);
}

/* 点が入った後、観客を 0.3 秒（18 フレーム）ごとにふだん／喜ぶ形に交互に書きかえる。
 * 次の投球が始まる・チェンジ・試合の終わりで止めて、ふだんの形に戻す */
static u8 crowd_on, crowd_t, crowd_ph;

static void crowd_put(u8 ph)
{
    u8 b;
    const u8* d = crowd_tiles + (ph << 4);
    for (b = 0; b < 4; b++) {
        u16 o = crowd_idx[b];
        if (o == 255) continue;
        o = ((u16)b << 11) + (o << 3);
        vdp_ldir(VR_PAT + o, d, 8);
        vdp_ldir(VR_COL + o, d + 8, 8);
    }
}

static void crowd_tick(void)
{
    if (!crowd_on) return;
    if (gstate == GS_PITCH || gstate == GS_CHANGE || gstate == GS_OVER) {
        crowd_on = 0;
        crowd_put(0);
        return;
    }
    if (++crowd_t >= 18) {
        crowd_t = 0;
        crowd_ph ^= 1;
        crowd_put(crowd_ph);
    }
}

void add_run(void)
{
    Side* s = &side[OFF];
    if (!crowd_on) {                /* 観客が喜ぶ（すぐに 1 回目） */
        crowd_on = 1;
        crowd_ph = 0;
        crowd_t = 17;
    }
    DBG(D_RUN);
    sfx_cheer();                    /* 点が入った：歓声 */
    s->runs++;
    if (s->score[inning] < 99) s->score[inning]++;
    scoreboard_update();
    if (half == 1 && inning + 1 >= max_inning && side[1].runs > side[0].runs) sayonara = 1;
}

void next_batter(void)
{
    Side* s = &side[OFF];
    s->bat_no++;
    if (s->bat_no >= 9) s->bat_no = 0;
}

/* 押し出し・四球：打者を一塁へ、詰まった走者を進める */
static void walk_advance(void)
{
    u8 occ[4] = { 0xFF, 0xFF, 0xFF, 0xFF };
    u8 i, b;
    for (i = 0; i < 4; i++)
        if (run[i].on) occ[run[i].base] = i;
    for (b = 1; b < 4 && occ[b] != 0xFF; b++) ;
    /* 1..b-1 が埋まっている → 1 つずつ進める */
    while (b > 1) {
        b--;
        i = occ[b];
        if (b == 3) {
            run[i].on = 0;
            add_run();
        } else {
            run[i].base = b + 1;
        }
    }
    for (i = 0; i < 4; i++) {
        if (!run[i].on) {
            Runner* r = &run[i];
            r->on = 1;
            r->base = 1;
            r->prog = 0;
            r->dir = 0;
            r->out = 0;
            r->who = side[OFF].bat_no;
            r->spd = 389 + cur_batter()->spd * 23;
            break;
        }
    }
    runners_place();
}

/* ------------------------------------------------------------------ */
static void pitcher_fresh(u8 sd)
{
    Side* s = &side[sd];
    s->stamina = 40 + tm[sd].pit[s->pit].st * 7;
    if (s->stamina > 99) s->stamina = 99;
}

static void reset_pitch_state(void)
{
    swing_t = 0;
    bunt_on = bunt_try = 0;
    hit_stop = 0;
    pit_t = 0;
    swung = 0;
    crossed = 0;
    steal_on = 0;
    ball.mode = BM_NONE;
    pprev = bprev = 0xFF;
    ai_pitch_plan();
    ai_bat_reset();
}

static void view_atbat(void)
{
    cam_x = ATBAT_CX;
    cam_y = ATBAT_CY;
    if (spr_mode != SM_ATBAT) spr_set_mode(SM_ATBAT);
    scroll_reset();
}

static void atbat_start(void)
{
    balls = strikes = 0;
    load_batter_sprites();
    bat_x = batter_left ? 275 : 237;
    bat_y = BAT_Y0;
    pit_off = 0;
    pitch_kmh = 0;
    reset_pitch_state();
    view_atbat();
    fielders_reset();
    ump_reset();
    runners_place();
    hud_draw();
    gstate = GS_ATBAT;
    gtimer = 0;
}

static void pitch_resume(void)
{
    reset_pitch_state();
    view_atbat();
    fielders_reset();
    ump_reset();
    runners_place();
    hud_draw();
    gstate = GS_ATBAT;
    gtimer = 0;
}

static void half_start(void)
{
    u8 i;
    outs = 0;
    for (i = 0; i < 4; i++) run[i].on = 0;
    side[OFF].score[inning] = 0;
    spr_set_mode(SM_ATBAT);
    load_pitcher_sprites();
    scoreboard_update();
    atbat_start();
    bgm_play(half ? BGM_ATBAT2 : BGM_ATBAT);
}

void game_start(void)
{
    u8 s, i;
    team_load();                    /* オーバーレイ A */
    for (s = 0; s < 2; s++) {
        Side* d = &side[s];
        for (i = 0; i < 8; i++) d->order[i] = i;
        d->order[8] = 255;
        d->bat_no = 0;
        d->pit = 0;
        d->runs = 0;
        d->hits = 0;
        d->bench_used = 0;
        d->pit_used = 1;
        for (i = 0; i < 12; i++) d->score[i] = 0xFF;
    }
    pitcher_fresh(0);
    pitcher_fresh(1);
    screen_lineup();
    map_load();
    vdp_load_field_tiles();         /* タイトルのロゴ（100〜115）を球場のタイルに戻す */
    inning = 0;
    half = 0;
    sayonara = 0;
    vdp_display(0);
    vdp_reg(7, 0x03);
    vdp_set_team_palette();
    vdp_clear_nt();
    spr_hide_all();
    half_start();
    vdp_display(1);
    msg_show(MSG_PLAYBALL, 100);
    bgm_play(BGM_PLAYBALL);
    gstate = GS_RESULT;
    res_next = 0;
    gtimer = 110;
}

/* ------------------------------------------------------------------ */
static void result_wait(u8 next, u8 frames)
{
    res_next = next;
    gstate = GS_RESULT;
    gtimer = frames;
}

/* 捕手が捕った：ストライク・ボールの判定 */
static void pitch_called(void)
{
    /* ボール（4 ドット幅：x-2..x+1）がホームベース（HOME_X-5..HOME_X+4）に 1 ドットでもかかればストライク */
    u8 strike = swung || bunt_on || (plate_x >= HOME_X - 6 && plate_x <= HOME_X + 6);
    u8 next = 0;
    ball.mode = BM_HELD;
    ball.holder = POS_C;
    rt_t = 0;
    sfx_play(SFX_CATCH);
    side[DEF].stamina -= side[DEF].stamina ? 1 : 0;
    if (strike) {
        strikes++;
        ump_call(0, UMP_PUNCH, strikes >= 3 ? 110 : 40);
        if (strikes >= 3) {
            if (steal_on && outs < 3) {         /* 盗塁中はプレーが続くので、すぐアウトにする */
                DBG(D_SO);
                add_out();
                msg_show(MSG_OUT, 60);
            } else {                            /* まず「ストライク」、1 秒後に「アウト」 */
                msg_show(MSG_STRIKE, 60);
                sfx_play(SFX_STRIKE);
                so_wait = 60;
            }
            next = 1;
        } else {
            msg_show(MSG_STRIKE, 50);
            sfx_play(SFX_STRIKE);
        }
    } else {
        balls++;
        if (balls >= 4) {
            msg_show(MSG_WALK, 60);
            DBG(D_BB);
            steal_on = 0;
            walk_advance();
            next = 1;
        } else {
            msg_show(MSG_BALL, 50);
        }
    }
    hud_count();
    if (steal_on && outs < 3) {
        res_next = next;
        play_begin_held(POS_C);
        return;
    }
    result_wait(next, so_wait ? 120 : 60);
}

/* 当たった */
/* 当たった：打球の向き・角度・速さ
 *   向き：振ったタイミング（バットの角度）がいちばん大きい。早いと引っぱり、遅いと流し。←→ を押していると少しその向きへ
 *   角度：バットのどこに当たったか（根っこ → ゴロ、芯 → ライナー、先 → フライ）、球の高さ（低い → ゴロ、高い → フライ）、
 *         ↓ を押していると打ち上げ、↑ だとたたきつけ（低いライナー・ゴロ）。フォークは低くなる
 *   速さ：芯に近いほど、パワーがあるほど、速い球ほど強い。芯でとらえたフライはたまに「会心」（ホームラン級） */
/* 当たる瞬間のキーと球速で、打球の角度（la）に足す分を決める。
 * ct_push3 = 球速に押されている分 ×3（速い球ほど・非力な打者ほど押されて打球が弱い。0〜9） */
static s8 ct_push3;
static s8 lift_add(u8 keys, u8 pow)
{
    s8 a, push;
    s16 t = (s16)pitch_kmh - 130 - pow * 3;
    push = t <= 0 ? 0 : (t >= 24 ? 3 : (s8)(t >> 3));     /* 押されていなければ 0（遅い球でも強くはならない） */
    ct_push3 = push * 3;
    if (keys & K_DOWN) {                    /* ↓：打ち上げる。高いフライが多く、押されているとポップフライになりやすい */
        a = rnd() < 170 ? 3 : 2;
        if (push > 0 && rnd() < (u8)(push * 40)) a++;
    } else a = (s8)rnd_n(3) - 1;
    if (keys & K_UP) a -= 2;                /* ↑：たたきつける */
    if (fork_on) a--;
    return a;
}

/* 痛烈なゴロ（芯の近くでとらえたゴロのうち、パワーのある打者ほど多い）：何度も弾んで外野を抜けることがある。
 * v に足す速さを返す（0 = ふつうのゴロ） */
static u8 hard_try(u8 ae)
{
    if (ae <= 2 && rnd() < 24 + cur_batter()->pow * 6) {
        hardg = 1;
        return 20;
    }
    return 0;
}

static void do_contact(s16 d, s16 e, u8 is_bunt)
{
    const BatterDef* b = cur_batter();
    s8 th, la;
    s16 v, vz, vx, vy;
    u8 r = rnd(), keys = bin, ae, zb;
    hardg = 0;
    if (is_bunt) {
        th = (s8)(e / 3) + (s8)((r & 7) - 3);
        if (batter_left) th = -th;
        if (keys & K_RIGHT) th += 6;
        if (keys & K_LEFT) th -= 6;
        v = 14 + (r & 7);
        vz = 4 + (r & 3);
        bunt_try = 1;
    } else {
        /* 方向はバットの角度で決まる：振り始めてから長いほど（バットが前に出ているほど）、
         * またボールを前（投手寄り）でとらえるほど引っ張る。右打者の引っ張り = 左（th が負） */
        {
            s8 tau = (s8)(swing_t - 5) * 3 - (s8)d;
            th = (s8)(((6 - tau) * 9) / 4) + (s8)(r & 7) - 3;
        }
        if (batter_left) th = -th;
        if (keys & K_RIGHT) th += 4;
        if (keys & K_LEFT) th -= 4;
        if (th > 22) th = 22;
        if (th < -22) th = -22;
        la = e <= -8 ? -2 : (e <= -4 ? -1 : (e <= 1 ? 0 : (e <= 3 ? 1 : 2)));     /* 根元 ゴロ … 芯 ライナー … 先 フライ */
        zb = (u8)PXL(ball.z);
        if (zb <= 5) la--;
        else if (zb >= 10) la++;
        la += lift_add(keys, b->pow);
        ae = (u8)abs16(e);
        /* 芯ほど・速い球ほど強く飛ぶ。ただし球速に押されると弱くなる */
        v = 48 + (8 - ae) * 2 + b->pow * 3 + (((s16)pitch_kmh - 116) >> 3) - ct_push3;
        r = rnd();
        if (la <= -3) {                     /* 弱いゴロ */
            vz = r & 3;
            v = (v * 5) >> 3;
        } else if (la == -2) {              /* ゴロ */
            vz = 2 + (r & 7);
            v = (v * 7) >> 3;
        } else if (la == -1) {              /* 強いゴロ・低いライナー */
            vz = 6 + (r & 7);
            if ((zb = hard_try(ae))) {
                v += zb;
                vz += 6;
            }
        } else if (la == 0) {               /* ライナー */
            vz = 10 + (r & 15);
        } else if (la == 1) {               /* フライ */
            vz = 26 + (r & 15);
            v = (v * 7) >> 3;
        } else if (la == 2) {               /* 大きなフライ */
            vz = 38 + (r & 15);
            v = (v * 15) >> 4;
        } else if (la == 3) {               /* 高いフライ */
            vz = 48 + (r & 15);
            v = (v * 3) >> 2;
        } else {                            /* ポップフライ */
            vz = 64 + (r & 15);
            v = v / 3;
        }
        if ((keys & K_DOWN) && la >= 1 && la <= 3) vz += 4 + (rnd() & 7);     /* ↓ のフライはより高く */
        if (ae <= 1 && la >= 0 && la <= 3 && rnd() < b->pow * 12) {     /* 会心の当たり（芯でとらえて上がった） */
            vz = 50 + (rnd() & 15);
            v += 16;
        }
    }
    v = (v * 181) >> 8;
    vz = (vz * 181) >> 8;
    vx = (v * SIN(th)) / 48;
    vy = -((v * COS(th)) / 64);
    sfx_play(is_bunt ? SFX_BOUND : SFX_HIT);
    DBG(D_CONTACT);
    hs_v[0] = vx;
    hs_v[1] = vy;
    hs_v[2] = vz;
    hit_stop = 1;
    /* ボールの絵をバットの線（bat_y-8）に重ねる */
    vz = ball.y - S(bat_y - 8);
    ball.z = vz > 0 ? vz : 0;
}

static void try_contact(u8 is_bunt)
{
    s16 by = PXL(ball.y), bx = PXL(ball.x);
    s16 d = by - (bat_y - 4);
    s16 e;
    u8 band = 4 + (cur_batter()->avg >= 190 ? 1 : 0) - (fork_on ? 2 : 0);   /* フォークは当てにくい */
    if (d < -(s16)band || d > (s16)band) return;
    e = batter_left ? (bat_x - BAT_REACH) - bx : bx - (bat_x + BAT_REACH);
    /* ボール（幅 4 ドット）がバットの絵（振る bat_x+5〜+19・バント +2〜+16）に重なれば当たる
     * （手元側は 1 ドット、先は振る 1 ドット・バント 3 ドットまで、ボールの端がかかればよい） */
    if (is_bunt ? (e < -14 || e > 3) : (e < -11 || e > 5)) return;
    do_contact(d, e, is_bunt);
}

static void release(void)
{
    const PitcherDef* p = cur_pitcher();
    s16 kmh = p->kmh, lo = p->kmin;
    u8 st = side[DEF].stamina;
    if (st < 30) {
        kmh -= (30 - st) / 2;
        lo -= (30 - st) / 2;
    }
    if (pit_key & K_UP) kmh = lo;               /* ↑：遅い球（最低の球速） */
    else if (!(pit_key & K_DOWN)) {             /* 何も押さない：最高 - 8（↓ は最高） */
        kmh -= 8;
        if (kmh < lo) kmh = lo;
    }
    kmh -= ptype == PT_CURVE ? 16 : (ptype == PT_FORK ? 8 : (ptype ? 5 : 0));     /* 変化球は少し遅い */
    if (kmh < 80) kmh = 80;
    pitch_kmh = (u8)kmh;
    DBG(D_PITCH);
    pitch_v0 = ((32 + ((kmh - 100) >> 1)) * grate) / 60;      /* 速さの段階に合わせる */
    if (kmh >= 140) pitch_v0 += pitch_v0 >> 4;                  /* 速球（140km 以上）は見た目もひと回り速く */
    ball.mode = BM_PITCH;
    ball.x = S(HOME_X + pit_off + (pitcher_left ? 5 : -5));
    ball.y = S(292);
    ball.z = S(14);
    ball.vx = 0;
    ball.vy = pitch_v0;
    ball.vz = -(pitch_v0 / 10);
    crossed = 0;
    fork_on = ptype == PT_FORK;
    slow_on = 0;
    brk_last = 0;
    brk_a = ptype == PT_CURVE ? 96 + p->cv * 16 : 64 + p->cv * 8;      /* カーブ 7〜15・シュート 4.5〜8.5 ドット */
    brk_neg = (ptype == PT_SHOOT) ^ pitcher_left;                       /* 右投手のカーブは右（一塁側）へ */
    if (ptype == PT_CURVE) ball.vz = 0;                                 /* カーブの高さは pitch_steer で距離から決める */
    pv_acc = 1 + ((p->cv / 3) * grate) / 60;
    pv_max = ((6 + p->cv * 2) * grate) / 60;
    vy_slow = (pitch_v0 * 3) >> 2;
    vy_fork = pitch_v0 - (pitch_v0 >> 3);
    hud_speed();
    sfx_play(kmh >= 140 ? SFX_FAST : SFX_PITCH);                /* 速球は「ひゅん！」 */
}

/* 投げた後の変化（人の目で見て反応できるよう、手元では小さく、ホームベースに近いほど大きく曲がる）
 *   ←→（押している間）：カーブ・シュート。曲がりの強さ・幅は投手の「変化」で決まる
 *   ↓（押した瞬間）：フォーク。後半で急に落ちて少し遅くなる（当てにくく、当たってもゴロになりやすい）
 *   ↑（押した瞬間）：チェンジアップ。沈めて遅くする
 * 投げる範囲は左右のバッターボックスの外側（x 230〜282）まで */
/* カーブ・シュートがこれから曲がる残り（サブ）。COM の打者が読む */
s16 brk_left(void)
{
    s16 t;
    if ((u8)(ptype - PT_CURVE) >= 2) return 0;
    t = (s16)((brk_a * (ptype == PT_CURVE ? 156u : 121u)) >> 7);
    if (brk_neg) t = -t;
    return t - brk_last;
}

static void pitch_steer(void)
{
    s8 acc = pv_acc;
    s16 px = PXL(ball.x);
    u8 prog = (u8)(PXL(ball.y) - 292);          /* 0 = 手をはなした所 〜 84 = ホームベース */
    if (prog < 28) acc = (frame_count & 1) ? acc : 0;
    else if (prog >= 56) acc <<= 1;
    if (pin & K_LEFT) ball.vx -= acc;
    if (pin & K_RIGHT) ball.vx += acc;
    if (ball.vx > pv_max) ball.vx = pv_max;
    if (ball.vx < -pv_max) ball.vx = -pv_max;
    if (px <= 230 && ball.vx < 0) ball.vx = 0;
    if (px >= 282 && ball.vx > 0) ball.vx = 0;
    if (pnew & K_DOWN) fork_on = 1;
    if (pnew & K_UP) slow_on = 1;
    if (slow_on && (frame_count & 1) && ball.vy > vy_slow) ball.vy--;
    if ((u8)(ptype - PT_CURVE) < 2) {
        /* カーブはだんだん大きく（距離の 2 乗）、シュートは手元で鋭く（3 乗）曲がる */
        u16 q = ((u16)prog * prog) >> 6;
        s16 off;
        if (ptype == PT_SHOOT) q = (q * prog) >> 7;
        off = (s16)((brk_a * q) >> 7);
        if (brk_neg) off = -off;
        ball.x += off - brk_last;
        brk_last = off;
        /* カーブは山なり：手をはなしてから少し浮き（最高 16 ドット）、ホームベースで 4 ドットまで落ちる（球速によらない） */
        if (ptype == PT_CURVE) ball.z = 224 + ((prog * 35) >> 4) - ((q * 19) >> 3);
    }
    if (fork_on && prog >= 42) {
        ball.vz -= 3;
        if (!(frame_count & 3) && ball.vy > vy_fork) ball.vy--;
    }
}

static void batter_move(void)
{
    s16 lo = batter_left ? 271 : 235;          /* 足（bat_x-5〜+4）がボックスの中か線の上 */
    if (swing_t || bunt_on) return;
    if ((bin & K_LEFT) && bat_x > lo) bat_x--;
    if ((bin & K_RIGHT) && bat_x < lo + 6) bat_x++;
    if ((bin & K_UP) && bat_y > 370) bat_y--;
    if ((bin & K_DOWN) && bat_y < 386 && !(bin & K_A)) bat_y++;
}

/* B（方向キーなし）を押している間はバントの構え。人が打つときだけ */
static void bunt_set(void)
{
    if (side[OFF].ctrl && (bin & K_B) && !(bin & (K_UP | K_DOWN | K_LEFT | K_RIGHT))) bunt_on = 1;
}

static void batter_swing(void)
{
    if (swing_t) {
        swing_t += at_adv;
        if (swing_t >= 5 && swing_t <= 8 && ball.mode == BM_PITCH) try_contact(0);
        if (swing_t > 40) swing_t = 40;
    } else if (bunt_on) {
        if (!(bin & K_B)) bunt_on = 0;      /* B を離すとバットを引く */
        else if (ball.mode == BM_PITCH) try_contact(1);
    } else if ((bnew & K_A) && ball.mode == BM_PITCH) {
        swing_t = 1;
        swung = 1;
        DBG(D_SWING);
    } else bunt_set();
}

/* 盗塁：B ＋ 行きたい塁の方向（→ 一塁 ↑ 二塁 ← 三塁）。塁にいる走者はその塁へスタート、
 * 盗塁中の走者は元の塁の方向で戻り、また次の塁の方向で進み直す（何度でも）。B だけはバント */
static void steal_input(void)
{
    u8 i, tgt, h;
    if (side[OFF].ctrl) {
        h = inp(OFF);
        if (!(inp_new(OFF) & K_B)) return;
        tgt = (h & K_RIGHT) ? 1 : ((h & K_UP) ? 2 : ((h & K_LEFT) ? 3 : 0));
    } else {
        tgt = ai_steal();
        if (tgt) tgt++;
    }
    if (!tgt) return;
    for (i = 0; i < 4; i++) {
        Runner* r = &run[i];
        if (!r->on) continue;
        if (r->base == tgt && r->dir > 0) r->dir = -1;          /* 元の塁へ戻る */
        else if (r->base + 1 == tgt) {
            if (r->dir < 0) r->dir = 1;                        /* また進む */
            else if (!r->dir && tgt <= 3) {
                u8 k;
                for (k = 0; k < 4; k++)
                    if (run[k].on && run[k].base == tgt && !run[k].dir) return;
                r->dir = 1;
                r->dest = tgt;
                r->prog = LEAD;
                steal_on = 1;
            }
        }
    }
}

static void steal_move(void)
{
    u8 i;
    for (i = 0; i < 4; i++) {
        Runner* r = &run[i];
        u16 st;
        if (!r->on || !r->dir) continue;
        st = (r->spd * grate) / 60;
        if (r->dir < 0) {
            if (r->prog <= st) {
                r->prog = 0;
                r->dir = 0;
            } else r->prog -= st;
        } else if ((u16)(r->prog + r->spd) < r->prog) r->prog = 0xFF00;
        else if (r->prog < 0xC000) r->prog += st;
        runner_pos(r);
    }
}

/* ------------------------------------------------------------------ */
static void st_atbat(void)
{
    ump_tick(0);
    read_roles();
    gtimer++;
    if (bunt_on && !(bin & K_B)) bunt_on = 0;
    bunt_set();
    batter_move();
    {                                       /* 同じ方向を 16 フレーム以内に 2 回押すと球種のコマンド（0.7 秒で消える） */
        u8 k = pnew & (K_LEFT | K_RIGHT | K_DOWN);
        if (cmd_t < 255) cmd_t++;
        if (k) {
            cmd_ok = (k == cmd_k && cmd_t < 16) ? k : 0;
            cmd_k = k;
            cmd_t = 0;
        } else if (cmd_t > 40) cmd_ok = 0;
    }
    if ((pin & K_LEFT) && pit_off > -8 && (frame_count & 1)) pit_off--;
    if ((pin & K_RIGHT) && pit_off < 8 && (frame_count & 1)) pit_off++;
    if (gtimer > 24 && (pnew & (K_A | K_B))) {
        if (side[DEF].ctrl ? ((pnew & K_A) ? 0 : pick_try(pin)) : pick_com()) return;
        gstate = GS_PITCH;
        pit_t = 0;
        pit_key = pin & (K_UP | K_DOWN);
        /* 球種：↓↓ フォーク、←← か →→ でその向きに曲がる球（利き腕と反対へ曲がるのがカーブ、利き腕側がシュート） */
        ptype = side[DEF].ctrl ? (cmd_ok == K_DOWN ? PT_FORK : (cmd_ok ? (((cmd_ok == K_RIGHT) ^ pitcher_left) ? PT_CURVE : PT_SHOOT) : 0)) : ai_ptype;
        cmd_ok = 0;
    }
    if ((side[DEF].ctrl && (inp_new(DEF) & K_SEL)) || (side[OFF].ctrl && (inp_new(OFF) & K_SEL))) {
        ovl_load();
        screen_menu_sub();
        map_load();                 /* オーバーレイの上に球場マップを戻して、メニューの行を描き直す */
        scroll_restore_rows(30, 38);
        hud_draw();
    }
}

static void st_pitch(void)
{
    if (hit_stop) {
        if (--hit_stop == 0) play_begin_hit(hs_v[0], hs_v[1], hs_v[2]);
        return;
    }
    ump_tick(0);
    read_roles();
    at_adv = time_adv(&at_acc, 1);
    pit_t += at_adv;
    batter_move();
    if (pit_t <= 24) {
        if (pin & (K_UP | K_DOWN)) pit_key = pin & (K_UP | K_DOWN);
        steal_input();
        if (pit_t == 24 && at_adv) release();
        steal_move();
        return;
    }
    steal_input();
    steal_move();
    pitch_steer();
    batter_swing();
    if (hit_stop || ball.mode != BM_PITCH) return;     /* 当たった */
    ball.x += ball.vx;
    ball.y += ball.vy;
    ball.z += ball.vz;
    if (ball.z < S(3)) ball.z = S(3);
    {
        s16 py = PXL(ball.y), px = PXL(ball.x);
        if (!crossed && py >= HOME_Y) {
            crossed = 1;
            plate_x = px;
        }
        if (!swung && !bunt_on && py >= bat_y - 14 && py <= bat_y - 2 && abs16(px - bat_x) < 5) {
            ball.mode = BM_DEAD;
            msg_show(MSG_HBP, 70);
            sfx_play(SFX_BOUND);
            walk_advance();
            result_wait(1, 70);
            return;
        }
        if (py >= 392) {
            if (!crossed) plate_x = px;
            pitch_called();
        }
    }
}

static u8 game_over_check(void)
{
    u8 last = inning + 1 >= max_inning;
    if (sayonara) return 1;
    if (!last) return 0;
    if (half == 0 && side[1].runs > side[0].runs) return 1;
    if (half == 1 && side[0].runs != side[1].runs) return 1;
    if (half == 1 && inning + 1 >= max_inning + 3) return 1;
    return 0;
}

static void st_result(void)
{
    if (gtimer) {
        gtimer--;
        /* 捕手から投手へ返球（捕ってから 0.25 秒後、0.53 秒で届く） */
        if (spr_mode == SM_ATBAT && ball.mode == BM_HELD && ball.holder == POS_C && gtimer < 46 && ++rt_t >= 32) ball.holder = POS_P;
        if (so_wait && --so_wait == 0) {
            DBG(D_SO);
            add_out();
            msg_show(MSG_OUT, 60);
            hud_count();
        }
        return;
    }
    if (sayonara) {
        msg_show(MSG_SAYONARA, 120);
        bgm_play(BGM_HOMERUN);
        gstate = GS_CHANGE;
        gtimer = 150;
        return;
    }
    if (outs >= 3) {
        msg_show(MSG_CHANGE, 90);
        bgm_play(BGM_CHANGE);
        gstate = GS_CHANGE;
        gtimer = 100;
        return;
    }
    if (res_next) {
        next_batter();
        atbat_start();
    } else {
        pitch_resume();
    }
}

static void st_change(void)
{
    if (gtimer) {
        gtimer--;
        return;
    }
    if (outs >= 3 && !sayonara) next_batter();
    if (game_over_check()) {
        ovlx_load(OVC_BANK);
        OVC_BOARD(1);
        gstate = GS_OVER;
        return;
    }
    ovlx_load(OVC_BANK);
    OVC_BOARD(0);
    ovl_load();                     /* 試合中に使うオーバーレイ A と球場マップを戻す */
    map_load();
    half ^= 1;
    if (!half) inning++;
    vdp_display(0);
    vdp_reg(7, 0x03);
    vdp_set_team_palette();
    vdp_clear_nt();
    spr_hide_all();
    half_start();
    /* 表示を出す前に、打席の縦スクロールと、それに合わせて隠したスプライトを VRAM へ
     * （そうしないと最初の 1 フレームだけ、隠したスプライトが画面の中に出る） */
    spr_frame_begin();
    spr_commit();
    scroll_commit();
    vdp_display(1);
}

/* ------------------------------------------------------------------ */
/* 打席の場面を描く */
static void big_put(u8 plane, s16 x, s16 y, u8 pat)
{
    x -= 8;
    spr_put2(plane, x, y - 23, pat);
    spr_put2(plane + 2, x, y - 7, pat + 2);
}

static const s8 bat_ofs[BAT_FRAMES][2] = { BAT_OFS_TABLE };

static void draw_atbat(void)
{
    u8 pf = 0, bf, i;
    s16 ox, oy;
    if (gstate == GS_PITCH) {
        if (pit_t < 14) pf = 1;
        else if (pit_t < 36) pf = 2;
    }
    big_put(PL_PITCHER, HOME_X + pit_off, 294, PA_PITCHER + pf * 4);
    /* 振る（7 コマ）：構え → 踏み込み（1〜2）→ 引き（3）→ 振り出し（4）→ 当たる瞬間（5〜8）→ 振り抜き（9〜10）→ 振り終わり。
     * バントは専用のコマ（バントの構え）。コマが変わったら、そのコマだけを次の帰線期間に読み込む */
    bf = 0;
    if (swing_t) bf = swing_t < 3 ? 1 : (swing_t < 4 ? 2 : (swing_t < 5 ? 3 : (swing_t < 9 ? 4 : (swing_t < 11 ? 5 : 6))));
    if (bunt_on) bf = 7;                    /* バントの構え */
    if (bf != bat_cur) {
        bat_cur = bf;
        bat_req = bf;
    }
    big_put(PL_BATTER, bat_x, bat_y, PA_BATTER);
    ox = bat_ofs[bf][0];
    oy = bat_ofs[bf][1];
    if (batter_left) ox = -16 - ox;
    ox += bat_x - 8;
    oy += bat_y - 23;
    spr_put(PL_BAT, ox, oy, PA_BAT);
    spr_put(PL_BAT + 1, ox + 16, oy, PA_BAT + 1);
    /* 捕手と内野手 */
    spr_actor2(PL_FLD_AB, &fld[POS_C], PA_CROUCH_B);
    /* 一塁手・三塁手は投手と同じ高さに並ぶ。走者がその高さを通るときは 2 人の縁取りの層を省き、
     * 1 ラインに 9 枚以上並ばないようにする（点滅も消えもしない） */
    {
        s16 fy = fld[POS_1B].y;
        u8 thin = 0, pl = PL_FLD_AB + 2;
        Actor* a = &fld[POS_1B];
        for (i = 0; i < 4; i++) {
            s16 d = run[i].a.y - fy;
            if (run[i].on && d > -S(16) && d < S(16)) thin = 1;
        }
        if (rt_t > 12 && ball.mode == BM_HELD && ball.holder == POS_C) thin = 1;     /* 返球がその高さを通る */
        for (i = 0; i < 4; i++, a++, pl += 2) {
            if (thin && !(i & 1)) {
                spr_hide(pl);
                spr_actor(pl + 1, a, PA_READY_D + 1);
            } else spr_actor2(pl, a, PA_READY_D);
        }
    }
    /* 走者 */
    {
        u8 k = 0;
        for (i = 0; i < 4 && k < 3; i++) {
            Runner* r = &run[i];
            u8 pat;
            if (!r->on) continue;
            if (r->dir > 0) {
                u8 fr = (frame_count >> 3) & 1;
                pat = (r->base == 3) ? (fr ? PA_RUN_R2 : PA_RUN_R1) : (fr ? PA_RUN_L2 : PA_RUN_L1);
            } else {                    /* リードの構え：三塁は右向き、ほかは左向き。0.27 秒ごとにすり足 */
                pat = PA_LEAD_L1 + ((r->base == 3) ? 4 : 0) + (((u8)frame_count >> 3) & 2);
            }
            spr_actor2(PL_RUN + k * 2, &r->a, pat);
            k++;
        }
        ump_draw(PL_RUN + k * 2, PL_RUN + 6);       /* 審判（塁審は走者の空いた面） */
    }
    /* ボール */
    if (ball.mode == BM_PITCH) {
        s16 bx = PXL(ball.x), by = PXL(ball.y), bz = PXL(ball.z);
        spr_put(PL_BALL, bx - 8, by - bz - 8, PA_BALL + 1);
        spr_put(PL_SHADOW, bx - 8, by - 8, PA_BALL + 3);
    } else if (rt_t && ball.mode == BM_HELD && ball.holder == POS_C) {
        /* 返球：影は捕手の足元から投手の足元へまっすぐ、ボールは山なり（最高 16 ドット） */
        s16 cx = PXL(fld[POS_C].x), cy = PXL(fld[POS_C].y);
        s16 gx = cx + (((HOME_X + pit_off - cx) * rt_t) >> 5);
        s16 gy = cy + (((301 - cy) * rt_t) >> 5);
        u8 h = 8 + ((rt_t * (32 - rt_t)) >> 4);
        gy -= h + 8;
        /* 真ん中の判定の文字と同じ高さを通る間は、ボールは文字の後ろ（1 ラインのスプライトが 8 枚を超えないように） */
        if (msg_timer && (u16)(gy - view_y - msg_y + 16) < 32) spr_hide(PL_BALL);
        else spr_put(PL_BALL, gx - 8, gy, PA_BALL + 1);
        gy += h + 8;
        /* 影は前半だけ（投手・一塁手・三塁手の並ぶ高さでは、1 ラインのスプライトが 8 枚を超えないように出さない） */
        if (rt_t < 18) spr_put(PL_SHADOW, gx - 8, gy - 8, PA_BALL + 3);
        else spr_hide(PL_SHADOW);
    }
}

/* ------------------------------------------------------------------ */
u8 game_frame(void)
{
    crowd_tick();
    switch (gstate) {
    case GS_ATBAT:
        st_atbat();
        break;
    case GS_PITCH:
        st_pitch();
        break;
    case GS_PLAY:
        /* プレーの計算は 1 フレームおき（その間に押されたボタンも渡す） */
        play_phase ^= 1;
        if (!play_phase) {
            acc_new[0] |= pad_new[0];
            acc_new[1] |= pad_new[1];
            acc_new[2] |= pad_new[2];
            break;
        }
        pad_new[0] |= acc_new[0];
        pad_new[1] |= acc_new[1];
        pad_new[2] |= acc_new[2];
        acc_new[0] = acc_new[1] = acc_new[2] = 0;
        if (play_update()) {
            if (play_result == PR_FOUL) {
                if (bunt_try && strikes >= 2) {     /* スリーバント失敗：三振 */
                    DBG(D_SO);
                    add_out();
                    msg_show(MSG_OUT, 60);
                    result_wait(1, 60);
                    break;
                }
                if (strikes < 2) strikes++;
                result_wait(0, 10);
            } else if (play_result == PR_STEAL) {
                result_wait(res_next, 30);
            } else {
                result_wait(1, 30);
            }
            if (sayonara) gtimer = 0;
        }
        break;
    case GS_RESULT:
        st_result();
        break;
    case GS_CHANGE:
        st_change();
        break;
    case GS_OVER:
        return 1;
    }
    if (gstate == GS_OVER) return 1;
    if (gstate == GS_PLAY) play_camera();
    scroll_update();
    if (gstate == GS_PLAY && play_phase) {
        spr_keep();                     /* 計算したフレームは表示しない */
    } else {
        spr_frame_begin();
        if (spr_mode == SM_ATBAT) draw_atbat();
        else play_draw();
        msg_draw();
    }
    if (msg_timer) msg_timer--;
    return 0;
}
