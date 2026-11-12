/* メインループ・入力・小さな道具 */
#include "game.h"

u8 kbd[9];
u8 joyraw[2];
u8 sat[128];
volatile u8 vblank_flag;
u16 frame_count;
u8 pad[3], pad_new[3];
u8 demo;
u8 test_teams;                  /* テスト用（0 = ふだんどおり） */
u16 dbg[16];
u16 seed = 0x2D61;              /* テストから書き換えられるように外から見える */

/* H.TIMI から呼ばれる（BIOS がレジスタを保存済み） */
void isr_c(void)
{
    read_input();
    vblank_flag = 1;
    frame_count++;
    sound_tick();
}

u8 esc_new, esc_prev;
void input_update(void)
{
    u8 p1 = 0, p2 = 0;
    u8 r2 = ~kbd[2], r3 = ~kbd[3], r4 = ~kbd[4], r5 = ~kbd[5];
    u8 r6 = ~kbd[6], r7 = ~kbd[7], r8 = ~kbd[8];
    if (r8 & 0x20) p1 |= K_UP;
    if (r8 & 0x40) p1 |= K_DOWN;
    if (r8 & 0x10) p1 |= K_LEFT;
    if (r8 & 0x80) p1 |= K_RIGHT;
    if ((r8 & 0x01) || (r5 & 0x80)) p1 |= K_A;        /* スペース・Z */
    if ((r5 & 0x20) || (r4 & 0x04) || (r2 & 0x80)) p1 |= K_B;     /* X・M・B */
    if (r7 & 0x80) p1 |= K_START;                     /* リターン */
    esc_new = (r7 & 0x04) & ~esc_prev;                /* ESC（押した瞬間） */
    esc_prev = r7 & 0x04;
    if ((r6 & 0x20) || (r7 & 0x40)) p1 |= K_SEL;      /* F1・SELECT */
    p1 |= (~joyraw[0]) & 0x3F;
    if (r5 & 0x10) p2 |= K_UP;                        /* W */
    if (r5 & 0x01) p2 |= K_DOWN;                      /* S */
    if (r2 & 0x40) p2 |= K_LEFT;                      /* A */
    if (r3 & 0x02) p2 |= K_RIGHT;                     /* D */
    if (r3 & 0x10) p2 |= K_A;                         /* G */
    if (r3 & 0x20) p2 |= K_B;                         /* H */
    if (r7 & 0x08) p2 |= K_START;                     /* TAB */
    if (r6 & 0x40) p2 |= K_SEL;                       /* F2 */
    p2 |= (~joyraw[1]) & 0x3F;
    pad_new[0] = p1 & ~pad[0];
    pad_new[1] = p2 & ~pad[1];
    pad[0] = p1;
    pad[1] = p2;
    pad[2] = p1 | p2;
    pad_new[2] = pad_new[0] | pad_new[1];
}

u8 rnd(void)
{
    seed ^= seed << 7;
    seed ^= seed >> 9;
    seed ^= seed << 8;
    return (u8)seed;
}

u8 rnd_n(u8 n)
{
    return (u8)(((u16)rnd() * n) >> 8);
}

void rnd_mix(u16 v)
{
    seed ^= v;
    if (!seed) seed = 1;
}

s16 abs16(s16 v) { return v < 0 ? -v : v; }

/* ディスクに保存する（ディスクのときだけ呼ぶ）。SRAM の代わり（VRAM 7000h〜）の 1536 バイトを MSXSTAD.DAT に書く。
 * 作業場所 C000h-CBFFh を VRAM へ退避し、保存のプログラム（ROM のバンク0 の 7000h〜）を C000h に写して実行する。
 * 保存のプログラムが、ディスクの作業領域とゲームの中身を入れかえて BDOS を呼び、元に戻して dk_ret へ来る。0 = 成功 */
static u16 dk_sp;
u8 disk_save(void) __naked
{
    __asm
        push ix                 ; BDOS・CALSLT は IX・IY を壊す（IX は C のフレーム）
        push iy
        di
        ld   (_dk_sp), sp
        ld   hl, #0x7800
        ld   a, #0x40
        call dkvs
        ld   hl, #0xC000
        ld   bc, #0x0C00
1$:     ld   a, (hl)
        out  (0x98), a
        inc  hl
        dec  bc
        ld   a, b
        or   c
        jr   nz, 1$
        xor  a
        ld   hl, #0x3000
        ld   de, #0xC000
        ld   bc, #0x0200
        call 0xF206
        di
        ld   hl, #_dk_ret
        ld   (0xC002), hl
        jp   0xC000
_dk_ret::
        push af
        ld   hl, #0x7800
        xor  a
        call dkvs
        ld   hl, #0xC000
        ld   bc, #0x0C00
2$:     in   a, (0x98)
        ld   (hl), a
        inc  hl
        dec  bc
        ld   a, b
        or   c
        jr   nz, 2$
        pop  af
        ld   sp, (_dk_sp)
        pop  iy
        pop  ix
        ei
        ret
    ; VRAM の位置 HL（A = 40h 書く / 0 読む）
dkvs:   ld   e, a
        ld   a, h
        rlca
        rlca
        and  #3
        out  (0x99), a
        ld   a, #0x8E
        out  (0x99), a
        ld   a, l
        out  (0x99), a
        ld   a, h
        and  #0x3F
        or   e
        out  (0x99), a
        ret
    __endasm;
}

/* 走者 r の向きを d にする（止まる塁は、進むなら次の塁、戻るなら今の塁）。A=d DE=r（アセンブラ） */
void rgo(s8 d, Runner* r) __naked
{
    (void)d; (void)r;
    __asm
        ex   de, hl
        ld   de, #13
        add  hl, de
        ld   c, (hl)
        inc  hl
        inc  hl
        inc  hl
        ld   (hl), a
        inc  hl
        dec  a
        jr   nz, 1$
        inc  c
1$:     ld   (hl), c
        ret
    __endasm;
}

/* 塁 b までのおおよその距離（サブ）。p は x, y（サブ）で始まる構造体（Actor・Ball）。A=b DE=p → DE（アセンブラ） */
u16 bsd(u8 b, const void* p) __naked
{
    (void)b; (void)p;
    __asm
        ex   de, hl
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        inc  hl
        push de
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        push de
        add  a, a
        ld   c, a
        ld   b, #0
        ld   hl, #_base_y
        call 1$
        pop  de
        or   a
        sbc  hl, de
        push hl
        ld   hl, #_base_x
        call 1$
        pop  bc
        pop  de
        or   a
        sbc  hl, de
        ld   d, b
        ld   e, c
        jp   _dist_approx
1$:     add  hl, bc
        ld   a, (hl)
        inc  hl
        ld   h, (hl)
        ld   l, a
        add  hl, hl
        add  hl, hl
        add  hl, hl
        add  hl, hl
        ret
    __endasm;
}

/* おおよその距離（max + min*3/8）。HL=dx DE=dy、戻り値 DE（アセンブラ） */
u16 dist_approx(s16 dx, s16 dy) __naked
{
    (void)dx; (void)dy;
    __asm
        bit  7, h
        jr   z, 1$
        xor  a
        sub  l
        ld   l, a
        sbc  a, a
        sub  h
        ld   h, a
1$:     ex   de, hl
        bit  7, h
        jr   z, 2$
        xor  a
        sub  l
        ld   l, a
        sbc  a, a
        sub  h
        ld   h, a
2$:     or   a
        sbc  hl, de
        add  hl, de
        jr   c, 3$
        ex   de, hl
3$:     ld   b, h
        ld   c, l
        add  hl, hl
        add  hl, bc
        srl  h
        rr   l
        srl  h
        rr   l
        srl  h
        rr   l
        add  hl, de
        ex   de, hl
        ret
    __endasm;
}

const s8 sin_tab[64] = {
    0, 6, 12, 19, 24, 30, 36, 41, 45, 49, 53, 56, 59, 61, 63, 64,
    64, 64, 63, 61, 59, 56, 53, 49, 45, 41, 36, 30, 24, 19, 12, 6,
    0, -6, -12, -19, -24, -30, -36, -41, -45, -49, -53, -56, -59, -61, -63, -64,
    -64, -64, -63, -61, -59, -56, -53, -49, -45, -41, -36, -30, -24, -19, -12, -6
};

/* 1 フレーム待ち、用意したものを VDP に出す */
static u16 last_sync;
void frame_sync(void)
{
    wait_vblank();
    /* スクロール（レジスタ 3 つ）を先に。スプライトの色表を書き直すフレームは帰線期間を
     * はみ出すので、後にすると 1 フレームだけ古いスクロールで新しいスプライトが出てしまう */
    scroll_commit();
    msg_fix();                      /* 判定の文字は、いま書いたスクロールの値で置き直す */
    spr_commit();
    if (bat_req != 0xFF) batter_frame_upload();     /* 打者のコマ（画面の下のほうなので、ここで書けば間に合う） */
    if ((u16)(frame_count - last_sync) > 1) {   /* 1 フレームに収まらなかった */
        DBG(D_OVERRUN);
    }
    last_sync = frame_count;
    input_update();
}

u8 sram_ok;
u8 game_speed = 2;               /* 0〜4（60・70・80・90・100%） */
u8 grate = 48;

/* frames（実際のフレーム数）の間に進むゲームのフレーム数。acc に端数をためる */
u8 time_adv(u8* acc, u8 frames)
{
    u8 n = 0;
    *acc += grate * frames;           /* frames は 1 か 2：最大 120 */
    while (*acc >= 60) {
        *acc -= 60;
        n++;
    }
    return n;
}

u8 tour[TOUR_SIZE];

void ovlx_load(u8 bank)
{
    rom2ram(0, (void*)OVL_ADDR, bank, OVL_LEN);
}

void ovlb_load(void)
{
    ovlx_load(OVB_BANK);
}

/* 試合を 1 つ（オーバーレイ A を読んでから） */
static void play_game(void)
{
    game_start();
    for (;;) {
        frame_sync();
        if (game_frame()) break;
        if (demo && (pad_new[2] & (K_A | K_START))) break;
        if (!demo && (pad_new[2] & K_START)) {
            /* 一時停止（もう一度 START で再開） */
            do {
                wait_vblank();
                input_update();
            } while (!(pad_new[2] & K_START));
        }
    }
    DBG(D_GAMES);
}

void ovl_load(void)
{
    rom2ram(0, (void*)OVL_ADDR, OVL_BANK, OVL_LEN);
}

void map_load(void)
{
    rom2ram(A_FIELD_MAP_OFS, field_map, A_FIELD_MAP_BANK, FIELD_W * FIELD_H);
}

void main(void)
{
    ovlb_load();
    OVB_BOOT();
    sound_init();
    vdp_load_field_tiles();
    for (;;) {
        ovlb_load();
        map_load();
        vdp_load_logo();
        OVB_TITLE();
        rnd_mix(frame_count);
        if (game_mode == 3) {           /* EDIT モード（オーバーレイ C） */
            ovlx_load(OVC_BANK);
            OVC_EDIT();
            continue;
        }
        if (game_mode >= 4) {           /* トーナメント（オーバーレイ B と試合を交互に） */
            ovlb_load();
            if (OVB_TOUR(game_mode == 5)) {
                do {
                    ovl_load();
                    play_game();
                    ovlb_load();
                } while (OVB_TOUR_NEXT());
            }
            continue;
        }
        ovl_load();
        if (demo) {
            side[0].team = rnd_n(NUM_TEAMS);
            do side[1].team = rnd_n(NUM_TEAMS); while (side[1].team == side[0].team);
            if (test_teams) {           /* テスト用：対戦を固定する（上位 4 ビット = 先攻） */
                side[0].team = (test_teams >> 4) & 7;
                side[1].team = test_teams & 7;
            }
            side[0].ctrl = side[1].ctrl = 0;
        } else {
            screen_select();
        }
        play_game();
    }
}
