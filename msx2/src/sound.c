/* PSG の音楽と効果音（割り込みから毎フレーム呼ぶ） */
#include "game.h"

typedef struct {
    const u8* p;
    const u8* loop;
    u16 per;
    u8 wait, vol, decay, floor, dcnt, cur, gate;
} Ch;

static Ch ch[3];
/* 曲の楽譜（ROM から読む）：ループする曲とジングルは別のバッファ（ジングルの後にループの曲へ戻れる） */
static u8 bgm_buf[BGM_LOOP_MAX], jin_buf[BGM_JIN_MAX];
static const struct { u8 bank; u16 ofs; u16 len; } bgm_rom[] = { BGM_TABLE };
static u8 cur_bgm = 0xFF, resume_bgm = 0xFF;
static const u8* sfx_p;
static u16 sfx_per;
static u8 sfx_n, sfx_mode, sfx_vol, sfx_dper, sfx_dnz, sfx_dvol;   /* 効果音の今の区間 */
static u8 noise_per;
static u8 cheer_t, cheer_r = 0x5A;      /* 歓声の残りフレーム・ゆらぎの乱数（ゲームの乱数とは別） */
u8 fly_note, fly_hold;

static void ch_start(Ch* c, const u8* p)
{
    c->p = c->loop = p;
    c->wait = 1;
    c->vol = 12;
    c->decay = 0;
    c->floor = 0;
    c->dcnt = 0;
    c->cur = 0;
    c->gate = 0;
}

static void bgm_start(u8 id)
{
    u8 i;
    cur_bgm = id;
    const u8* base = bgm_loop[id] ? bgm_buf : jin_buf;
    for (i = 0; i < 3; i++) ch_start(&ch[i], base + bgm_ofs[id * 3 + i]);
}

void bgm_play(u8 id)
{
    __asm__("di");
    if (!bgm_loop[id]) {
        if (cur_bgm != 0xFF && bgm_loop[cur_bgm]) resume_bgm = cur_bgm;
    } else {
        resume_bgm = 0xFF;
    }
    ch[0].p = ch[1].p = ch[2].p = 0;            /* 読み込む間は鳴らさない */
    rom2ram(bgm_rom[id].ofs, bgm_loop[id] ? bgm_buf : jin_buf, bgm_rom[id].bank, bgm_rom[id].len);
    __asm__("di");
    bgm_start(id);
    __asm__("ei");
}

void sfx_play(u8 id)
{
    __asm__("di");
    sfx_p = sfx_tab[id];
    sfx_n = 0;
    __asm__("ei");
}

/* 効果音を 1 フレーム進める。区間の始めは書いてある値、あとは毎フレーム増分を足す。終わったら sfx_p = 0、A = 0 */
static u8 sfx_step(void) __naked
{
    __asm
        ld   hl, (_sfx_p)
        ld   a, (_sfx_n)
        or   a
        jr   nz, 2$
        ld   a, (hl)
        or   a
        jr   z, 9$
        ld   (_sfx_n), a
        inc  hl
        ld   a, (hl)
        ld   (_sfx_mode), a
        inc  hl
        ld   e, (hl)
        inc  hl
        ld   d, (hl)
        inc  hl
        ld   (_sfx_per), de
        ld   a, (hl)
        ld   (_sfx_dper), a
        inc  hl
        ld   a, (hl)
        ld   (_noise_per), a
        inc  hl
        ld   a, (hl)
        ld   (_sfx_dnz), a
        inc  hl
        ld   a, (hl)
        ld   (_sfx_vol), a
        inc  hl
        ld   a, (hl)
        ld   (_sfx_dvol), a
        inc  hl
        ld   (_sfx_p), hl
        jr   3$
2$:     ld   a, (_sfx_dper)
        ld   e, a
        rlca
        sbc  a, a
        ld   d, a
        ld   hl, (_sfx_per)
        add  hl, de
        ld   (_sfx_per), hl
        ld   a, (_sfx_dnz)
        ld   hl, #_noise_per
        add  a, (hl)
        ld   (hl), a
        ld   a, (_sfx_dvol)
        ld   hl, #_sfx_vol
        add  a, (hl)
        ld   (hl), a
3$:     ld   hl, #_sfx_n
        dec  (hl)
        ld   a, #1
        ret
9$:     ld   hl, #0
        ld   (_sfx_p), hl
        xor  a
        ret
    __endasm;
}

/* 歓声：C をノイズにして、ふくらんで（約 0.3 秒）→ にぎやかに続き → 静まる（全部で 3 秒）。
 * 音量を毎フレーム小さくゆらし、ノイズの高さも動かすと、大勢の声が重なったように聞こえる */
#define CHEER_LEN 180
void sfx_cheer(void)
{
    cheer_t = CHEER_LEN;
}

/* 歓声を 1 フレーム進める → C の音量。cheer_t・cheer_r・noise_per を書きかえる（割り込みの中なので短いアセンブラ）
 *   t = 経過フレーム。t < 20：ふくらむ（音量 6→12、ノイズは低→高）。残り 60 フレームまで：音量 12〜13。
 *   そのあと静まる（残り/4 - 2 → 0）。音量を乱数で 1 ゆらし、ノイズの高さ（周期 5〜12）を 2 フレームごとに動かす */
static u8 cheer_step(void) __naked
{
    __asm
        ld   hl, #_cheer_t
        ld   c, (hl)
        dec  (hl)
        ld   a, #CHEER_LEN
        sub  c
        ld   b, a               ; B = t
        ld   a, (_cheer_r)
        srl  a
        jr   nc, 1$
        xor  #0xB8
1$:     ld   (_cheer_r), a
        ld   e, a               ; E = rnd
        ld   a, b
        cp   #20
        jr   nc, 2$
        srl  a
        srl  a
        ld   d, a
        srl  a
        add  a, d
        add  a, #6
        jr   5$
2$:     ld   a, c
        dec  a                  ; frames left
        cp   #61
        jr   c, 3$
        ld   a, e
        and  #1
        add  a, #12
        jr   5$
3$:     cp   #9
        jr   nc, 4$
        xor  a
        jr   6$
4$:     srl  a
        srl  a
        sub  #2
5$:     cp   #14
        jr   c, 51$
        ld   a, #13
51$:    ld   d, a
        ld   a, e
        and  #6
        jr   z, 52$
        bit  3, e
        jr   z, 52$
        dec  d
52$:    ld   a, d
6$:     ld   d, a               ; D = volume
        bit  0, b
        jr   nz, 8$
        ld   a, b
        cp   #20
        jr   nc, 7$
        srl  a
        neg
        add  a, #14
        jr   71$
7$:     ld   a, #5
71$:    ld   h, a
        ld   a, e
        rrca
        rrca
        and  #7
        add  a, h
        ld   (_noise_per), a
8$:     ld   a, d
        ret
    __endasm;
}

void sound_init(void)
{
    __asm__("di");
    ch[0].p = ch[1].p = ch[2].p = 0;
    sfx_p = 0;
    cheer_t = 0;
    __asm__("ei");
}

/* 3 チャンネルを 1 フレーム進める（IX = チャンネル。Ch の並び：p0 loop2 per4 wait6 vol7 decay8 floor9 dcnt10 cur11 gate12） */
static void ch_tick3(void) __naked
{
    __asm
        push ix
        ld   ix, #_ch
        call 100$
        ld   ix, #_ch + 13
        call 100$
        ld   ix, #_ch + 26
        call 100$
        pop  ix
        ret
100$:   ld   a, 0(ix)
        or   1(ix)
        ret  z
        ld   a, 10(ix)
        or   a
        jr   z, 102$
        dec  10(ix)
        jr   nz, 102$
        ld   a, 11(ix)
        cp   9(ix)
        jr   z, 101$
        jr   c, 101$
        dec  11(ix)
101$:   ld   a, 8(ix)
        ld   10(ix), a
102$:   dec  6(ix)
        jr   z, 104$
        ld   a, 6(ix)
        dec  a
        ret  nz
        ld   a, 12(ix)
        or   a
        ret  z
        ld   11(ix), #0
        ret
104$:   ld   l, 0(ix)
        ld   h, 1(ix)
105$:   ld   a, (hl)
        inc  hl
        cp   #0x60
        jp   c, 120$
        jp   z, 130$
        cp   #0xF0
        jr   nz, 106$
        ld   a, (hl)
        inc  hl
        ld   7(ix), a
        jr   105$
106$:   cp   #0xF1
        jr   nz, 107$
        ld   a, (hl)
        inc  hl
        ld   8(ix), a
        jr   105$
107$:   cp   #0xF2
        jr   nz, 108$
        ld   a, (hl)
        inc  hl
        ld   9(ix), a
        jr   105$
108$:   cp   #0xFD
        jr   nz, 109$
        ld   2(ix), l
        ld   3(ix), h
        jr   105$
109$:   cp   #0xFE
        jr   nz, 110$
        ld   l, 2(ix)
        ld   h, 3(ix)
        jr   105$
110$:   xor  a
        ld   0(ix), a
        ld   1(ix), a
        ld   11(ix), a
        ret
120$:   push hl
        push bc
        ld   c, #0              ; オクターブ
170$:   cp   #12
        jr   c, 171$
        sub  #12
        inc  c
        jr   170$
171$:   add  a, a
        ld   e, a
        ld   d, #0
        ld   hl, #_note_base
        add  hl, de
        ld   e, (hl)
        inc  hl
        ld   d, (hl)            ; いちばん低いオクターブの周期
        ld   a, c
        or   a
        jr   z, 174$
        dec  a
        jr   z, 173$
172$:   srl  d                  ; オクターブごとに半分
        rr   e
        dec  a
        jr   nz, 172$
173$:   inc  de                 ; 最後の半分は四捨五入
        srl  d
        rr   e
174$:   ld   a, d
        cp   #16
        jr   c, 175$
        ld   de, #0x0FFF        ; 12 ビットまで
175$:   ld   4(ix), e
        ld   5(ix), d
        pop  bc
        pop  hl
        ld   a, (hl)
        inc  hl
        ld   6(ix), a
        ld   0(ix), l
        ld   1(ix), h
        cp   #4
        ld   a, #0
        jr   c, 121$
        inc  a
121$:   ld   12(ix), a
        ld   a, 7(ix)
        ld   11(ix), a
        ld   a, 8(ix)
        ld   10(ix), a
        ret
130$:   ld   a, (hl)
        inc  hl
        ld   6(ix), a
        ld   0(ix), l
        ld   1(ix), h
        xor  a
        ld   11(ix), a
        ld   12(ix), a
        ret
    __endasm;
}

static u8 psg_buf[11];

/* PSG の 0〜10 番に psg_buf を書く */
static void psg_flush(void) __naked
{
    __asm
        ld   hl, #_psg_buf
        ld   bc, #0x0B00
1$:     ld   a, c
        out  (0xA0), a
        ld   a, (hl)
        out  (0xA1), a
        inc  hl
        inc  c
        djnz 1$
        ret
    __endasm;
}

void sound_tick(void)
{
    u8 mix = 0xB8;
    u16 pc;
    u8 vc;
    ch_tick3();
    if (cur_bgm != 0xFF && !ch[0].p && !ch[1].p && !ch[2].p) {
        cur_bgm = 0xFF;
        if (resume_bgm != 0xFF) {
            u8 r = resume_bgm;
            resume_bgm = 0xFF;
            bgm_start(r);
        }
    }
    pc = ch[2].per;
    vc = ch[2].cur;
    if (sfx_p && sfx_step()) {
        u8 m = sfx_mode;
        pc = sfx_per;
        vc = sfx_vol;
        if (!(m & 1)) mix |= 0x04;           /* C の音を止める */
        if (m & 2) mix &= ~0x20;             /* C にノイズ */
    }
    else if (cheer_t) {
        vc = cheer_step();
        mix = 0x9C;                     /* C の音（曲）を止めて、C にノイズ */
    } else if (fly_hold) {              /* フライの軌道音「ぴ〜〜」：高いほど高い音 */
        fly_hold--;
        pc = (u16)fly_note << 1;
        vc = 10;
    }
    *(u16*)&psg_buf[0] = ch[0].per;
    *(u16*)&psg_buf[2] = ch[1].per;
    *(u16*)&psg_buf[4] = pc;
    psg_buf[6] = noise_per;
    psg_buf[7] = mix;
    psg_buf[8] = ch[0].cur;
    psg_buf[9] = ch[1].cur;
    psg_buf[10] = vc;
    psg_flush();
}
