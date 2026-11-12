/* チーム選択・オーダー・スコアボード（タイトルは ovlb.c）。
 * このファイルはオーバーレイ（OVL）：ROM のバンク 7 に置き、使うときだけ球場マップの場所（OVL_ADDR）へ読み込む。
 * 先頭（DD00h〜E2FFh）には試合中に呼ぶ関数を置く（球場マップ E300h〜 に上書きされない）。
 * 試合中に使う関数（代打・リリーフ）は menu.c */
#include "game.h"


/* ---- 守備：B で操作する野手を切り替える（試合中に呼ぶ）----
 * オーバーレイの DD00h〜E2FFh は球場マップ（E300h〜）に上書きされず、試合中もずっと残るので、ここに置ける。
 * 画面に映っている野手の中で、画面の中心に近い順に切り替える：今の野手の次に近い野手へ。
 * いちばん遠い野手の次・今の野手が画面の外なら、いちばん近い野手へ */
static s16 fs_cx, fs_cy;
static u8 fs_dx;

/* 野手 i の画面の中心からの近さ |dx|+|dy|（0〜223）。画面に映っていなければ 255。A=i → A */
static u8 center_dist(u8 i) __naked
{
    (void)i;
    __asm
        ld   l, a
        ld   h, #0
        ld   e, l
        ld   d, h
        add  hl, hl
        add  hl, de
        add  hl, hl
        add  hl, hl             ; i * 12（Actor の大きさ）
        ld   de, #_fld
        add  hl, de
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
        ex   de, hl
        ld   de, (_fs_cx)
        or   a
        sbc  hl, de
        call 50$
        cp   #124
        jr   nc, 9$
        ld   (_fs_dx), a
        ld   l, c
        ld   h, b
        ld   de, (_fs_cy)
        or   a
        sbc  hl, de
        call 50$
        cp   #100
        jr   nc, 9$
        ld   hl, #_fs_dx
        add  a, (hl)
        ret
9$:     ld   a, #0xFF
        ret
50$:    bit  7, h               ; A = |HL|（256 以上なら 255）
        jr   z, 51$
        xor  a
        sub  l
        ld   l, a
        sbc  a, a
        sub  h
        ld   h, a
51$:    ld   a, h
        or   a
        ld   a, l
        ret  z
        ld   a, #0xFF
        ret
    __endasm;
}

void fielder_switch(void)
{
    u8 i, d, cur = ctl_fielder, dc, nb = 0xFF, nf = 0xFF, bd = 0xFF, fd = 0xFF;
    fs_cx = cam_x + 128;
    fs_cy = view_y + 114;                       /* 足もとの 8 ドット上を絵の中心として比べる */
    dc = cur < 9 ? center_dist(cur) : 0xFF;
    for (i = 0; i < 9; i++) {
        if (i == cur || (d = center_dist(i)) == 0xFF) continue;
        if (d < fd) {
            fd = d;
            nf = i;
        }
        if (d > dc && d < bd) {         /* 今より遠い中でいちばん近い（今が画面の外なら dc = 255 で選ばれない） */
            bd = d;
            nb = i;
        }
    }
    if (nb == 0xFF) nb = nf;
    if (nb != 0xFF) {
        ctl_fielder = nb;
        sel_blink = 24;
    }
}

/* ---- 内野と外野の守備範囲（試合中に呼ぶ）----
 * 打球の行き先が、はっきり外野（外野手の定位置のあたり。内野の土の外側からさらに 50 ドットほど先）なら、
 * 内野手は追わずに外野手に任せる。境目のあたり（内野のすぐ後ろ）はどちらが追ってもよい */
static u8 deep_out(s16 x, s16 y)
{
    s16 dx = abs16(PXL(x) - HOME_X), dy = HOME_Y - PXL(y);
    return dy + (dx >> 1) >= 200;
}

static u8 out_pick(s16 x, s16 y)
{
    u8 i, best = POS_CF;
    u16 bd = 0xFFFF;
    for (i = POS_LF; i < 9; i++) {
        u16 d = dist_approx(x - fld[i].x, y - fld[i].y);
        if (d < bd) {
            bd = d;
            best = i;
        }
    }
    return best;
}

u8 out_redirect(u8 best)
{
    s16 tx, ty;
    if (best >= POS_LF) return best;
    if (land_t) {
        tx = land_x;
        ty = land_y;
    } else {
        tx = pred_x[fk[best]];
        ty = pred_x[fk[best] + NPRED];
    }
    return deep_out(tx, ty) ? out_pick(tx, ty) : best;
}

u8 qa_i0;
void qa_first(void)
{
    qa_i0 = deep_out(ball.x + (ball.vx << 3) + (ball.vx << 2), ball.y + (ball.vy << 3) + (ball.vy << 2)) ? POS_LF : 0;
}

/* ---- 挟殺（ランダウンプレー）（試合中に呼ぶ）----
 * 守備（COM）：塁の間の走者には、ボールを持ったまま向かって走り、元の塁のほうへ追い返す。
 *   走者が逃げる先の塁に味方が入っていて、走者がその塁の近く（約 3 人分）まで来たら、その塁へ投げて
 *   はさむ（受けた味方がタッチする）。投げた守備は自分の塁へ戻るので、何度往復しても両側から詰まる。
 * 走者（COM）：ボールを持った守備が先の塁にいれば戻る。元の塁にいれば（もう 8 ドット以上離れていたら）
 *   先の塁へ進む。追いかけてきたら、その守備から遠いほうの塁へ逃げる */
/* |PXL(a.x) - base_x[b]| + |PXL(a.y) - base_y[b]|（ドット）。A = b, DE = a -> DE */
static s16 bdist(u8 b, Actor* a) __naked
{
    (void)b;
    (void)a;
    __asm
        add  a, a
        ld   c, a
        ld   b, #0
        ld   hl, #_base_y
        add  hl, bc
        push hl
        ld   hl, #_base_x
        add  hl, bc
        ex   de, hl
        call 70$
        pop  de
        push bc
        call 70$
        pop  hl
        add  hl, bc
        ex   de, hl
        ret
    ; bc = abs(PXL(*hl) - *de), hl += 2
70$:
        ld   c, (hl)
        inc  hl
        ld   b, (hl)
        inc  hl
        push hl
        sra  b
        rr   c
        sra  b
        rr   c
        sra  b
        rr   c
        sra  b
        rr   c
        ex   de, hl
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        ld   l, c
        ld   h, b
        or   a
        sbc  hl, de
        bit  7, h
        jr   z, 71$
        xor  a
        sub  l
        ld   l, a
        sbc  a, a
        sub  h
        ld   h, a
71$:
        ld   c, l
        ld   b, h
        pop  hl
        ret
    __endasm;
}

/* |PXL(a.x - b.x)| + |PXL(a.y - b.y)|（ドット）。HL = a, DE = b -> DE */
static s16 adist(Actor* a, Actor* b) __naked
{
    (void)a;
    (void)b;
    __asm
        call 80$
        push bc
        call 80$
        pop  hl
        add  hl, bc
        ex   de, hl
        ret
    ; bc = abs(*hl - *de) >> 4, hl += 2, de += 2
80$:
        ld   a, (de)
        inc  de
        ld   c, a
        ld   a, (de)
        inc  de
        ld   b, a
        push de
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        inc  hl
        ex   (sp), hl
        ex   de, hl
        or   a
        sbc  hl, bc
        bit  7, h
        jr   z, 81$
        xor  a
        sub  l
        ld   l, a
        sbc  a, a
        sub  h
        ld   h, a
81$:
        srl  h
        rr   l
        srl  h
        rr   l
        srl  h
        rr   l
        srl  h
        rr   l
        ld   c, l
        ld   b, h
        pop  hl
        ret
    __endasm;
}

/* 守備が走者に追いつける：近い（64 ドット未満）か、走者が塁に着くより先に届く */
static u8 rd_near(Actor* h, Runner* r, u8 to)
{
    s16 d = adist(h, &r->a);
    return d < 64 || d < bdist(to, &r->a);
}

u8 rd_holder(void)
{
    u8 i;
    Actor* h = &fld[ball.holder];
    chase_k = 0;
    if (rd_force()) return 0;
    for (i = 0; i < 4; i++) {
        Runner* r = &run[i];
        if (r->on && r->dir && r->base && (u16)(r->prog - OFF8) <= 0xFFFF - 2 * OFF8) {
            u8 to = r->dir > 0 ? r->base + 1 : r->base;    /* 走者が向かっている塁 */
            u8 c = play_cover(to);
            u8 can = c < 9 && c != ball.holder;             /* その塁に味方が入っている */
            s16 ht = bdist(to, h);
            if (r->dir > 0 && ht > bdist(to, &r->a)) continue;  /* 先へ逃げる走者の後ろ：先の塁へ投げる（ふつうの送球） */
            if (can && bdist(to, &r->a) < 28 && ht > 20) {  /* 走者が味方の塁の近くまで来た：投げてはさむ */
                throw_to_base(to);
                return 1;
            }
            if (rd_near(h, r, to)) {                        /* 追いつける：走者に向かって走って重なり（タッチ）、元の塁のほうへ追い返す */
                chase_k = i + 1;
                return 1;
            }
            /* 遠い：戻る走者より送球が早ければ、その塁へ投げる（挟殺の始まり） */
            if (r->dir < 0 && can && (ht >> 2) + (ht >> 3) + 14 < (s16)(r->prog / r->spd)) {
                throw_to_base(to);
                return 1;
            }
        }
    }
    return 0;
}

u8 rd_runner(Runner* r, u8 nb)
{
    Actor* h = &fld[ball.holder];
    s16 hf = bdist(nb, h);
    s8 d = 0;
    if (rd_force()) return 0;
    if (hf < 16) d = -1;
    else if (bdist(r->base, h) < 16 && r->prog >= OFF8) d = 1;
    else if (adist(h, &r->a) < 48)
        d = hf < bdist(nb, &r->a) ? -1 : 1;        /* 守備が走者より先の塁に近い（前にいる）なら戻る */
    if (!d) return 0;
    r->dir = d;
    r->dest = d > 0 ? nb : r->base;
    return 1;
}

/* ここまでが E300h より前（試合中も球場マップに上書きされない。build.py で確かめる） */
void ovl_persist_end(void)
{
}

/* 両チームの選手（EDIT していれば保存の中身から）。試合の始め（球場マップを読む前）に呼ぶ */
void team_load(void)
{
    u8 s;
    for (s = 0; s < 2; s++) {
        u16 o = (u16)side[s].team * TEAM_SIZE;
        if (sram_ok == 2) rom2ram(SR_TEAMS + o, &tm[s], SR_BANK, TEAM_SIZE);    /* EDIT した中身 */
        else rom2ram(A_TEAMS_OFS + o, &tm[s], A_TEAMS_BANK, TEAM_SIZE);
    }
}

static void sync_fixed(void)
{
    wait_vblank();
    spr_commit();
    input_update();
}

/* スクロールしない画面にする（名前表 0・枠は黒） */
static void fixed_screen(void)
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
    spr_commit();               /* 表示を消している間に VRAM へ（前の画面の隠し位置が縦スクロール 0 で見えないように） */
}

/* ---- チーム選択 ---- */
static void preview(u8 plane, s16 x, u8 t)
{
    (void)t;
    spr_put(plane, x, 174, PF_STAND_D);
    spr_put(plane + 1, x, 174, PF_STAND_D + 1);
}

void screen_select(void)
{
    u8 who, cur[2] = { 0, 1 }, i, done = 0;
    fixed_screen();
    pad_new[0] = pad_new[1] = pad_new[2] = 0;
    half = 0;
    spr_set_mode(SM_FIELD);
    nt_text(10, 2, STR_SELECT);
    for (i = 0; i < NUM_TEAMS; i++) {
        nt_n(6, 5 + i * 2, thdr[i].abbr, 3);
        nt_n(11, 5 + i * 2, thdr[i].name, 6);
    }
    nt_text(4, 22, STR_VISIT);
    nt_text(22, 22, STR_HOME);
    vdp_display(1);
    for (who = 0; who < 2; who++) {
        done = 0;
        while (!done) {
            u8 p = (game_mode == 1 && who == 1) ? 1 : 0;
            u8 pn = pad_new[p];
            side[0].team = cur[0];
            side[1].team = cur[1];
            vdp_set_team_palette();
            for (i = 0; i < NUM_TEAMS; i++) {
                nt_tile(2, 5 + i * 2, i == cur[0] ? T_CURSOR : T_SPACE);
                nt_tile(27, 5 + i * 2, (who == 1 && i == cur[1]) ? ascii_tile['<' - 32] : T_SPACE);
            }
            nt_n(4, 24, thdr[cur[0]].abbr, 3);
            if (who == 1) nt_n(22, 24, thdr[cur[1]].abbr, 3);
            spr_frame_begin();
            preview(PL_RUN, 72, cur[0]);
            if (who == 1) preview(PL_FLD, 216, cur[1]);
            sync_fixed();
            if (pn & K_UP) {
                cur[who] = cur[who] ? cur[who] - 1 : NUM_TEAMS - 1;
                sfx_play(SFX_CURSOR);
            }
            if (pn & K_DOWN) {
                cur[who] = cur[who] + 1 < NUM_TEAMS ? cur[who] + 1 : 0;
                sfx_play(SFX_CURSOR);
            }
            if (pn & (K_A | K_START)) {
                sfx_play(SFX_SAFE);
                done = 1;
            }
            if ((pn & K_B) && who == 1) {
                who = 0;
                nt_fill(22, 24, T_SPACE, 3);
                done = 2;
            }
        }
        if (done == 2) who = 0xFF;
    }
    side[0].team = cur[0];
    side[1].team = cur[1];
    side[0].ctrl = game_mode == 2 ? 0 : 1;
    side[1].ctrl = game_mode == 1 ? 2 : 0;
    for (i = 0; i < 30; i++) sync_fixed();
}

/* ---- スターティングオーダー ---- */
void screen_lineup(void)
{
    u8 s, i, t;
    fixed_screen();
    for (s = 0; s < 2; s++) {
        u8 c = s ? 17 : 1;
        nt_n(c + 2, 1, thdr[side[s].team].name, 6);
        nt_fill(c, 2, ascii_tile['-' - 32], 13);
        for (i = 0; i < 9; i++) {
            u8 row = 4 + i * 2;
            u8 o = side[s].order[i];
            nt_num(c, row, i + 1, 1);
            if (o == 255) {
                const PitcherDef* p = &tm[s].pit[side[s].pit];
                nt_n(c + 2, row, p->name, 5);
                nt_ascii(c + 8, row, "P");
                nt_num(c + 10, row, p->kmh, 3);
            } else {
                const BatterDef* b = &tm[s].bat[o];
                nt_n(c + 2, row, b->name, 5);
                nt_ascii(c + 8, row, ".");
                nt_num(c + 9, row, (u16)b->avg + 100, 3);
                if (b->flags & 1) nt_ascii(c + 13, row, "L");
            }
        }
    }
    nt_ascii(15, 1, "VS");
    nt_text(9, 24, STR_PUSH);
    vdp_display(1);
    for (i = 0; i < 20; i++) sync_fixed();
    t = 0;
    for (;;) {
        sync_fixed();
        if (pad_new[2] & (K_A | K_START)) break;
        if (game_mode == 2 && ++t > 200) break;
    }
    sfx_play(SFX_SAFE);
    vdp_display(0);
}

/* ---- 代打・リリーフ（打席で SELECT） ---- */

/* ---- 代打・リリーフ（打席の始まりに SELECT）。呼ぶ前に ovl_load ---- */
void screen_menu_sub(void)
{
    u8 pitch = 0, sd, i, n = 0, cur = 0;
    u8 list[6];
    u8 r0 = 30;
    if (side[DEF].ctrl && (inp_new(DEF) & K_SEL)) pitch = 1;
    sd = pitch ? DEF : OFF;
    if (pitch) {
        for (i = 0; i < 5; i++)
            if (!(side[sd].pit_used & (1 << i))) list[n++] = i;
    } else {
        for (i = 0; i < 4; i++)
            if (!(side[sd].bench_used & (1 << i))) list[n++] = 8 + i;
    }
    list[n] = 0xFF;
    for (i = 0; i < 8; i++) txt_fill(8, r0 + i, T_SPACE, 16);
    txt_map(10, r0, pitch ? STR_RELIEF : STR_PINCH);
    for (;;) {
        for (i = 0; i <= n; i++) {
            txt_tile(9, r0 + 2 + i, i == cur ? T_CURSOR : T_SPACE);
            if (i == n) txt_map(11, r0 + 2 + i, STR_CANCEL);
            else if (pitch) {
                const PitcherDef* p = &tm[sd].pit[list[i]];
                txt_n(11, r0 + 2 + i, p->name, 5);
                txt_num(17, r0 + 2 + i, p->kmh, 3);
            } else {
                const BatterDef* b = &tm[sd].bat[list[i]];
                txt_n(11, r0 + 2 + i, b->name, 5);
                txt_ascii(17, r0 + 2 + i, ".");
                txt_num(18, r0 + 2 + i, (u16)b->avg + 100, 3);
            }
        }
        frame_sync();
        {
            u8 pn = inp_new(sd);
            if (pn & K_UP) cur = cur ? cur - 1 : n;
            if (pn & K_DOWN) cur = cur < n ? cur + 1 : 0;
            if (pn & (K_UP | K_DOWN)) sfx_play(SFX_CURSOR);
            if (pn & K_B) cur = n;
            if (pn & (K_A | K_B | K_START)) break;
        }
    }
    if (cur < n) {
        if (pitch) {
            side[sd].pit = list[cur];
            side[sd].pit_used |= 1 << list[cur];
            side[sd].stamina = 40 + tm[sd].pit[list[cur]].st * 7;
            if (side[sd].stamina > 99) side[sd].stamina = 99;
            load_pitcher_sprites();
        } else {
            side[sd].bench_used |= 1 << (list[cur] - 8);
            side[sd].order[side[sd].bat_no] = list[cur];
            load_batter_sprites();
            bat_x = batter_left ? 275 : 237;
        }
        sfx_play(SFX_SAFE);
    }
    /* 球場マップの読み直しと行の書き直しは呼んだ側（本体）で。ここで読むとこのプログラムを上書きしてしまう */
}
