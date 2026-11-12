;==============================================================================
; crt0.s  本体（RAM 4000h〜）の入口と、VDP・PSG・入力の下まわり
;   呼び方は SDCC 4.2 の sdcccall(1)：引数1 = A / HL、引数2 = L / DE、戻り値 = A / DE
;   __sdcccall(0) と書いたものは引数がすべてスタック（呼んだ側が片付ける）
;==============================================================================
        .module crt0
        .globl  _main
        .globl  _isr_c

STUB_ROM2VRAM   = 0xF203
STUB_ROM2RAM    = 0xF206
SCNCNT          = 0xF3F6

        .area   _CODE
        jp      init            ; 4000h
        jp      isr_entry       ; 4003h（H.TIMI から）

init:
        di
        ld      sp, #0xF380
        ld      hl, #s__DATA
        ld      bc, #l__DATA
        call    zero_fill
        ld      bc, #l__INITIALIZER
        ld      a, b
        or      c
        jr      z, 1$
        ld      de, #s__INITIALIZED
        ld      hl, #s__INITIALIZER
        ldir
1$:     call    gsinit
        ei
        call    _main
2$:     jr      2$

zero_fill:                      ; HL から BC バイトを 0 に
        ld      a, b
        or      c
        ret     z
        ld      (hl), #0
        dec     bc
        ld      a, b
        or      c
        ret     z
        ld      d, h
        ld      e, l
        inc     de
        ldir
        ret

isr_entry:
        ld      a, #0xFF        ; BIOS のキー走査を止める（毎回入れ直す）
        ld      (SCNCNT), a
        jp      _isr_c

;------------------------------------------------------------------------------
; VDP
;------------------------------------------------------------------------------
; void vdp_reg(u8 reg, u8 val)
_vdp_reg::
        ld      b, a
        ld      a, l
        di
        out     (0x99), a
        ld      a, b
        or      #0x80
        out     (0x99), a
        ei
        ret

; void vdp_waddr(u16 addr)   書き込み位置（0000h-FFFFh）
_vdp_waddr::
        ld      a, h
        rlca
        rlca
        and     #3
        di
        out     (0x99), a
        ld      a, #0x8E
        out     (0x99), a
        ld      a, l
        out     (0x99), a
        ld      a, h
        and     #0x3F
        or      #0x40
        out     (0x99), a
        ei
        ret

; void vdp_raddr(u16 addr)   読み出し位置
_vdp_raddr::
        ld      a, h
        rlca
        rlca
        and     #3
        di
        out     (0x99), a
        ld      a, #0x8E
        out     (0x99), a
        ld      a, l
        out     (0x99), a
        ld      a, h
        and     #0x3F
        out     (0x99), a
        ei
        ret

; void vdp_out(u8 v)
_vdp_out::
        out     (0x98), a
        ret

; void vdp_ldir(u16 vram, const void* src, u16 len) __sdcccall(0)
_vdp_ldir::
        ld      hl, #2
        add     hl, sp
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        inc     hl
        push    hl
        ex      de, hl
        call    _vdp_waddr
        pop     hl
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        inc     hl
        ld      c, (hl)
        inc     hl
        ld      b, (hl)
        ex      de, hl          ; HL=src BC=len
1$:     ld      a, b
        or      c
        ret     z
        ld      a, (hl)
        out     (0x98), a
        inc     hl
        dec     bc
        jr      1$

; void vdp_fill(u16 vram, u8 val, u16 len) __sdcccall(0)
_vdp_fill::
        ld      hl, #2
        add     hl, sp
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        inc     hl
        push    hl
        ex      de, hl
        call    _vdp_waddr
        pop     hl
        ld      e, (hl)         ; val
        inc     hl
        ld      c, (hl)
        inc     hl
        ld      b, (hl)
1$:     ld      a, b
        or      c
        ret     z
        ld      a, e
        out     (0x98), a
        dec     bc
        jr      1$

; void vdp_palette(const u8* p)   16 色 × 2 バイト
_vdp_palette::
        xor     a
        di
        out     (0x99), a
        ld      a, #0x90
        out     (0x99), a
        ei
        ld      bc, #0x209A
        otir
        ret

; void vdp_pal(u8 v)   パレットのポートへ 1 バイト
_vdp_pal::
        out     (0x9A), a
        ret

; void nt_row(u16 vram, const u8* src)   32 バイト（表示中でも安全な間隔 29T）
_nt_row::
        push    de
        call    _vdp_waddr
        pop     hl
        ld      c, #0x98
        .rept   32
        outi
        .endm
        ret

; void vdp_send(u8 n, const u8* src)   位置は設定済み。29T 間隔（n=0 は 256）
_vdp_send::
        ld      b, a
        ex      de, hl
        ld      c, #0x98
1$:     outi
        jp      nz, 1$
        ret

; void sat_commit(void)   スプライト属性 128 バイト（垂直帰線中に呼ぶ）
_sat_commit::
        ld      hl, #0x5E00
        call    _vdp_waddr
        ld      hl, #_sat
        ld      bc, #0x8098
        otir
        ret

; void wait_vblank(void)
_wait_vblank::
        ld      hl, #_vblank_flag
1$:     ld      a, (hl)
        or      a
        jr      nz, 2$
        ei
        halt
        jr      1$
2$:     ld      (hl), #0
        ret

;------------------------------------------------------------------------------
; ROM のデータ（F000h の関数を呼ぶ）
;------------------------------------------------------------------------------
; void rom2vram(u8 bank, u16 src, u16 len)   VRAM の位置は先に vdp_waddr で設定
;   sdcccall(1): A=bank DE=src, len はスタック（呼ばれた側が片付ける）
_rom2vram::
        pop     hl              ; 戻り先
        pop     bc              ; len
        push    hl
        ex      de, hl          ; HL=src
        jp      STUB_ROM2VRAM

; void rom2ram(u16 src, void* dst, u8 bank, u16 len) __sdcccall(0)
; 球場マップ（3328 バイト）。メニュー画面のあいだはオーバーレイのプログラムがここに入る
        .globl  _field_map
_field_map = 0xE300

_rom2ram::
        ld      hl, #2
        add     hl, sp
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        inc     hl
        push    de              ; src
        ld      e, (hl)
        inc     hl
        ld      d, (hl)         ; dst
        inc     hl
        ld      a, (hl)         ; bank
        inc     hl
        ld      c, (hl)
        inc     hl
        ld      b, (hl)         ; len
        pop     hl
        cp      #0x10           ; バンク 10h = 保存の中身（VRAM 7000h + ofs。ディスクのときだけ）
        jp      nz, STUB_ROM2RAM
        ld      a, (0xF218)
        or      a
        ret     z
        call    vsr_set
        and     #0x3F
        out     (0x99), a
        ex      de, hl
1$:     ld      a, b
        or      c
        jr      z, 9$
        in      a, (0x98)
        ld      (hl), a
        inc     hl
        dec     bc
        jr      1$
9$:     ei
        ret

; 保存の中身の VRAM 7000h + HL を出す（R#14・下位）。A = 上位を返す。DI にする
vsr_set:
        di
        push    de
        ld      de, #0x7000
        add     hl, de
        pop     de
        ld      a, h
        rlca
        rlca
        and     #3
        out     (0x99), a
        ld      a, #0x8E
        out     (0x99), a
        ld      a, l
        out     (0x99), a
        ld      a, h
        ret

; void ram2sram(u16 ofs, const void* src, u16 len) __sdcccall(0)   保存の中身（VRAM 7000h〜）の ofs へ書く（ディスクのときだけ）
_ram2sram::
        ld      hl, #2
        add     hl, sp
        ld      e, (hl)
        inc     hl
        ld      d, (hl)
        inc     hl
        push    de              ; ofs
        ld      e, (hl)
        inc     hl
        ld      d, (hl)         ; src
        inc     hl
        ld      c, (hl)
        inc     hl
        ld      b, (hl)         ; len
        pop     hl
        ld      a, (0xF218)
        or      a
        ret     z
        call    vsr_set
        and     #0x3F
        or      #0x40
        out     (0x99), a
        ex      de, hl
1$:     ld      a, b
        or      c
        jr      z, 9$
        ld      a, (hl)
        out     (0x98), a
        inc     hl
        dec     bc
        jr      1$
9$:     ei
        ret

;------------------------------------------------------------------------------
; PSG・入力
;------------------------------------------------------------------------------
; void psg_write(u8 reg, u8 val)
_psg_write::
        out     (0xA0), a
        ld      a, l
        out     (0xA1), a
        ret

; void read_input(void)   キーボード 0〜8 行と、ジョイスティック 1・2
_read_input::
        in      a, (0xAA)
        and     #0xF0
        ld      c, a
        ld      hl, #_kbd
        ld      b, #0
1$:     ld      a, c
        or      b
        out     (0xAA), a
        in      a, (0xA9)
        ld      (hl), a
        inc     hl
        inc     b
        ld      a, b
        cp      #9
        jr      nz, 1$
        ld      a, #15
        out     (0xA0), a
        in      a, (0xA2)
        and     #0xAF
        or      #0x03
        out     (0xA1), a
        ld      a, #14
        out     (0xA0), a
        in      a, (0xA2)
        ld      (_joyraw), a
        ld      a, #15
        out     (0xA0), a
        in      a, (0xA2)
        and     #0xDF
        or      #0x4C
        out     (0xA1), a
        ld      a, #14
        out     (0xA0), a
        in      a, (0xA2)
        ld      (_joyraw+1), a
        ret

;------------------------------------------------------------------------------
        .area   _HOME
        .area   _INITIALIZER
        .area   _GSINIT
gsinit::
        .area   _GSFINAL
        ret
        .area   _DATA
        .area   _INITIALIZED
        .area   _BSEG
        .area   _BSS
        .area   _HEAP
