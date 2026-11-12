;==============================================================================
; boot.asm  ASCII16 メガROM のバンク0（4000h-7FFFh）
;   起動するとプログラム本体（バンク1〜3）を RAM の 4000h-EFFFh に写して実行する。
;   マッパーは ASCII16 だが、ASCII8 と判定する環境（WebMSX など）でも動くよう、
;   起動時に種類を調べて切り替え方を変える（ASCII8 は 8KB 単位のレジスタ 2 つで 16KB バンクを出す）。
;   ROM のデータ（バンク4〜）は F200h に置いた小さな関数で読む。
;
;   RAM の使い方
;     4000h-EFFFh  プログラム本体（C とアセンブラ。const も変数もここ）
;     DD00h-F1FFh  オーバーレイ（画面）。F000h〜 は起動のときだけ起動用のプログラム
;     F200h-F2A7h  この関数群（stub）
;     F2A8h-F37Fh  スタック（SP=F380h から下へ）
;   ROM の使い方（16KB × 32 = 512KB = 4M ビット）
;     バンク0 = これ / 1〜3 = 本体 / 4〜6 = 絵と表 / 7 = メニュー画面のプログラム（オーバーレイ）/ 8〜31 = 空き
;==============================================================================

ENASLT      equ 0024h
RSLREG      equ 0138h
EXPTBL      equ 0FCC1h
SLTTBL      equ 0FCC5h
H_KEYI      equ 0FD9Ah
H_TIMI      equ 0FD9Fh
STUB        equ 0F200h      ; F200h-F2A7h（その上 F2A8h-F37Fh がスタック。使うのは 128 バイト以下）
BOOTC       equ 0F000h      ; 起動のときだけ（あとでオーバーレイが上に読まれる）
IMG_ENTRY   equ 4000h       ; 本体の入口（crt0.s）
IMG_ISR     equ 4003h       ; 本体の割り込み処理
H_STKE      equ 0FEDAh      ; すべての ROM（ディスクも）の初期化が終わってから呼ばれるフック
H_PHYD      equ 0FFA7h      ; ディスク ROM があれば C9h 以外
HIMEM       equ 0FC4Ah
BDOS        equ 0F37Dh      ; ディスク BASIC の BDOS の入口
DISKVE      equ 0F323h      ; ディスクエラーの処理（を指す番地）の番地
BREAKV      equ 0F325h      ; 中断の処理（を指す番地）の番地
; ディスクのときの VRAM（ゲームは 0000h-6FFFh だけを使う）
VR_VSRAM    equ 7000h       ; 保存の中身（1536 バイト = MSXSTAD.DAT の中身）
VR_HOOKS    equ 7600h       ; 起動時の H.KEYI・H.TIMI（10 バイト）
VR_SCR      equ 7800h       ; 作業場所 C000h-CBFFh の退避（3KB）
VR_DISK     equ 8400h       ; ディスクの作業領域 HIMEM〜F37Fh（最大 16KB）
VR_GAME     equ 0C400h      ; その間のゲームの中身 HIMEM〜F37Fh
SCR         equ 0C000h      ; ディスクを使う間の作業場所（プログラム C000h、FCB C200h、スタック 〜C3FFh、データ C400h-C9FFh）
DK_FCB      equ 0C200h
DK_DATA     equ 0C400h
DK_LEN      equ 0600h
DK_MINHI    equ 0D000h      ; HIMEM がこれより低いとディスクは使わない

            org 4000h
            db "AB"
            dw init
            dw 0, 0, 0
            ds 6, 0

init:       ; ここで SP を変えない（ディスク ROM を待つときは BIOS に戻る）
            ; MSX1 では動かない（V9938 がない）ので知らせて止まる
            ld a, (002Dh)       ; rdlow-ok
            or a
            jr nz, init_msx2
            ei
            call 006Ch          ; INITXT
            ld hl, msg_msx1
.pr:        ld a, (hl)
            or a
            jr z, .stop
            call 00A2h          ; CHPUT
            inc hl
            jr .pr
.stop:      jr .stop
msg_msx1:   db "MSX STADIUM", 13, 10, 13, 10, "THIS GAME REQUIRES MSX2.", 0
            ; ここではまだ始めない：H.STKE に入口をつないで BIOS に戻り、ほかのスロットの ROM（ディスク）の
            ; 初期化が終わってから始める（ディスク ROM の作業領域ができてから）
init_msx2:  call RSLREG
            rrca
            rrca
            and 3
            ld c, a
            ld b, 0
            ld hl, EXPTBL
            add hl, bc
            ld a, (hl)
            and 80h
            or c
            ld c, a
            inc hl
            inc hl
            inc hl
            inc hl
            ld a, (hl)
            and 0Ch
            or c
            ld (H_STKE + 1), a
            ; ディスク ROM がもう初期化されている／どこにもない → すぐ始める（内蔵ソフトのある機種では
            ; INIT から戻ると H.STKE が呼ばれないので、待つのはディスク ROM がこの後で初期化されるときだけ）
            ld a, (H_PHYD)
            cp 0C9h
            jp nz, start2
            call find_disk
            jp nz, start2
            ; ディスク ROM はこの後で初期化される：H.STKE（すべての ROM の初期化の後に呼ばれる）に入口をつないで BIOS に戻る
            ld hl, start2
            ld (H_STKE + 2), hl
            ld a, 0C9h
            ld (H_STKE + 4), a
            ld a, 0F7h          ; RST 30h（スロットをまたぐ呼び出し）
            ld (H_STKE), a
            ret

; ほかのスロットのページ1 にディスク ROM（"AB" と 4010h・4013h・4016h の JP）があれば Z
find_disk:  ld b, 0
.prim:      ld hl, EXPTBL
            ld e, b
            ld d, 0
            add hl, de
            ld a, (hl)
            and 80h
            or b
            ld c, a             ; C = スロット（拡張なら 80h | 基本）
.sec:       push bc
            ld a, c
            call is_disk
            pop bc
            ret z
            bit 7, c
            jr z, .next
            ld a, c
            add a, 4
            ld c, a
            and 0Ch
            jr nz, .sec
.next:      inc b
            ld a, b
            cp 4
            jr c, .prim
            or a                ; NZ
            ret
; A = スロット。この ROM 自身は除く
is_disk:    ld c, a
            ld a, (H_STKE + 1)
            cp c
            jr z, .no
            ld hl, 4000h
            ld e, 'A'
            call .chk
            ret nz
            inc hl
            ld e, 'B'
            call .chk
            ret nz
            ld hl, 4010h
            ld e, 0C3h
            call .chk
            ret nz
            ld hl, 4013h
            call .chk
            ret nz
            ld hl, 4016h
.chk:       push bc
            push de
            push hl
            ld a, c
            call 000Ch          ; RDSLT
            pop hl
            pop de
            pop bc
            cp e
            ret
.no:        or 1
            ret

; H.STKE から（ページ1 はこの ROM）。もう BIOS には戻らない
start2:     di
            ld sp, DK_MINHI     ; BIOS のスタックは作業場所（C000h〜）と重なることがあるので、その上（CC00h-CFFFh）へ
            ld a, 0C9h
            ld (H_STKE), a
            xor a
            ld (dk_tmp), a      ; 0 = ディスクなし
            ld a, (H_PHYD)
            cp 0C9h
            jr z, .nodisk
            ld hl, (HIMEM)
            ld de, DK_MINHI
            or a
            sbc hl, de
            jr c, .nodisk
            call disk_boot
.nodisk:    ; 関数群を F200h へ
            ld hl, stub_src
            ld de, STUB
            ld bc, stub_end - stub_start
            ldir
            ld hl, boot_src
            ld de, BOOTC
            ld bc, boot_end - boot_start
            ldir
            ld a, (H_STKE + 1)
            ld (rom_slot), a
            ld a, (dk_tmp)
            ld (diskmode), a
            ld hl, (HIMEM)
            ld (dk_lo), hl
            ld sp, 0F380h
            jp boot_main

; ---- 起動時のディスク：保存ファイルを読んで VRAM へ、ディスクの作業領域を VRAM へ写す ----
dk_tmp      equ 0C3FEh          ; ディスクを使うか（作業場所の中。スタックとは重ならない）
disk_boot:  ; 起動時の H.KEYI・H.TIMI（10 バイト続き）を VRAM へ
            ld hl, VR_HOOKS
            call vw_set
            ld hl, H_KEYI
            ld bc, 10
            call vw_copy
            ; 保存の中身を 0 に（ファイルがなければ、ゲームが ROM のチームで作り直す）
            ld hl, VR_VSRAM
            call vw_set
            ld bc, DK_LEN
.z:         xor a
            out (98h), a
            dec bc
            ld a, b
            or c
            jr nz, .z
            ; ディスクの作業領域（HIMEM〜F37Fh）を、まず手つかずのまま VRAM へ（読み込みが中断されたときはこれを使う）
            ld hl, VR_DISK
            call vw_set
            call dk_range
            call vw_copy
            ; エラーのときは中断して戻る
            ld hl, (DISKVE)
            push hl
            ld hl, (BREAKV)
            push hl
            ; エラー処理はディスク ROM がページ1 にいる間に呼ばれるので、RAM（C3D0h〜）に写して使う
            push hl
            ld hl, hand_src
            ld de, hand_start
            ld bc, hand_end - hand_start
            ldir
            pop hl
            ld hl, de_ptr
            ld (DISKVE), hl
            ld hl, br_ptr
            ld (BREAKV), hl
            ld (br_sp), sp
            xor a
            ld (dk_err), a
            ei
            ld de, DK_DATA
            ld c, 1Ah           ; DMA
            call BDOS
            call fcb_make
            ld de, DK_FCB
            ld c, 0Fh           ; 開く
            call BDOS
            or a
            jr nz, .fail
            call fcb_rec
            ld de, DK_FCB
            ld hl, DK_LEN
            ld c, 27h           ; まとめて読む
            call BDOS
            push af
            ld de, DK_FCB
            ld c, 10h           ; 閉じる
            call BDOS
            pop af
            cp 2
            jr nc, .fail
            di
            ld hl, VR_VSRAM
            call vw_set
            ld hl, DK_DATA
            ld bc, DK_LEN
            call vw_copy
.fail:      di
            ld sp, (br_sp)
            pop hl
            ld (BREAKV), hl
            pop hl
            ld (DISKVE), hl
            ; BDOS の途中で中断しなかったら、今のディスクの作業領域を VRAM へ（中断した後の作業領域は使わない）
            ld a, (dk_err)
            cp 4
            jr nc, .keep
            ld hl, VR_DISK
            call vw_set
            call dk_range
            call vw_copy
.keep:      ld a, 1
            ld (dk_tmp), a
            ret
br_sp       equ 0C3FCh
dk_err      equ 0C3FBh          ; ディスクエラーがあった
hand_src:
            disp 0C3D0h
hand_start:
de_hand:    ld a, (dk_err)      ; ディスクエラー：3 回まではやり直し（回り始め・ディスク交換）、4 回目は BDOS の途中から抜けて失敗に
            inc a
            ld (dk_err), a
            cp 4
            jr nc, br_hand
            ld c, 1
            ret
br_hand:    ld sp, (br_sp)      ; 中断された：ページ1 をこの ROM に戻して、失敗として続ける
            ld a, (H_STKE + 1)
            ld h, 40h
            call ENASLT
            jp disk_boot.fail
de_ptr:     dw de_hand
br_ptr:     dw br_hand
hand_end:
            ent
            assert hand_end <= 0C3FCh

; HL = HIMEM、BC = F380h - HIMEM
dk_range:   ld hl, (HIMEM)
            push hl
            ex de, hl
            ld hl, 0F380h
            or a
            sbc hl, de
            ld b, h
            ld c, l
            pop hl
            ret

; VRAM の書き込み位置 HL（R#14 も）。DI のまま
vw_set:     ld a, h
            rlca
            rlca
            and 3
            out (99h), a
            ld a, 8Eh
            out (99h), a
            ld a, l
            out (99h), a
            ld a, h
            and 3Fh
            or 40h
            out (99h), a
            ret
; (HL) から BC バイトを VRAM へ
vw_copy:    ld a, (hl)
            out (98h), a
            inc hl
            dec bc
            ld a, b
            or c
            jr nz, vw_copy
            ret

; FCB を作る（ドライブ 0 = 今のドライブ、MSXSTAD.DAT）
fcb_make:   ld hl, DK_FCB
            ld b, 37
.c:         ld (hl), 0
            inc hl
            djnz .c
            ld hl, fcb_name
            ld de, DK_FCB + 1
            ld bc, 11
            ldir
            ret
; 1 バイト単位・先頭から
fcb_rec:    ld hl, 1
            ld (DK_FCB + 14), hl
            dec hl
            ld (DK_FCB + 33), hl
            ld (DK_FCB + 35), hl
            ret
fcb_name:   db "MSXSTAD DAT"

;------------------------------------------------------------------------------
stub_src:
            disp STUB
stub_start:
            jp boot_main        ; F000h
            jp rom_to_vram      ; F203h  A=バンク HL=バンク内の位置 BC=長さ（VRAM の書き込み先は設定済み）
            jp rom_to_ram       ; F206h  A=バンク HL=バンク内の位置 DE=書き込み先（ページ2 以外） BC=長さ
            ret                 ; F209h  （使わない。SRAM はやめた。番地をずらさないための空き）
            nop
            nop
rom_slot:   db 0                ; F009h
ram1_slot:  db 0
ram2_slot:  db 0
ram3_slot:  db 0
cur_bank:   db 0
mapper8:    db 0                ; 1 = ASCII8 として動いている
save_bc:    dw 0
save_de:    dw 0
save_hl:    dw 0
diskmode:   db 0                ; 1 = ディスクに保存（保存の中身は VRAM 7000h）
dk_lo:      dw 0                ; 起動時の HIMEM（ディスクの作業領域の下端）

; 16KB バンク A をページ1 / ページ2 に出す（ページ1 に ROM があること）
sel_p1:     push af
            ld a, (mapper8)
            or a
            jr nz, .m8
            pop af
            ld (6000h), a
            ret
.m8:        pop af
            add a, a
            ld (6000h), a
            inc a
            ld (6800h), a
            ret
sel_p2:     push af
            ld a, (mapper8)
            or a
            jr nz, .m8
            pop af
            ld (7000h), a
            ret
.m8:        pop af
            add a, a
            ld (7000h), a
            inc a
            ld (7800h), a
            ret

; ページ2 に ROM のバンク A を出す（ページ1 は RAM に戻す）。HL BC は保存
map_bank:   ld (cur_bank), a
            ld (save_hl), hl
            ld (save_bc), bc
            ld (save_de), de
            ld a, (rom_slot)
            ld h, 40h
            call ENASLT
            ld a, (cur_bank)
            call sel_p2
            ld a, (rom_slot)
            ld h, 80h
            call ENASLT
            ld a, (ram1_slot)
            ld h, 40h
            call ENASLT
            ld hl, (save_hl)
            ld bc, (save_bc)
            ld de, (save_de)
            ret

unmap_bank: ld a, (ram2_slot)
            ld h, 80h
            call ENASLT
            ei
            ret

rom_to_vram:
            di
            call map_bank
            set 7, h
            ld a, b
            or c
            jr z, .done
.lp:        ld a, (hl)
            out (98h), a
            inc hl
            dec bc
            ld a, b
            or c
            jr nz, .lp
.done:      jp unmap_bank

rom_to_ram:
            di
            call map_bank
            set 7, h
            ld a, b
            or c
            jr z, .done
            ldir
.done:      jp unmap_bank

stub_end:
            ent
            assert diskmode == 0F218h   ; game.h の DISKMODE
            display "stub size: ", /d, stub_end - stub_start
            assert stub_end - stub_start < 0100h

;------------------------------------------------------------------------------
; 起動のときだけ使う（F000h〜。あとでオーバーレイが読まれる）
boot_src:
            disp BOOTC
boot_start:
boot_main:
            ; ページ3 の RAM のスロット
            in a, (0A8h)
            rlca
            rlca
            and 3
            ld c, a
            ld b, 0
            ld hl, EXPTBL
            add hl, bc
            ld a, (hl)
            and 80h
            jr z, .noexp
            or c
            ld c, a
            ld a, (0FFFFh)
            cpl
            and 0C0h
            rrca
            rrca
            rrca
            rrca
            or c
            ld c, a
.noexp:     ld a, c
            ld (ram3_slot), a
            ; ページ2・ページ1 の RAM を探す
            ld h, 80h
            call find_ram
            ld (ram2_slot), a
            ld h, 40h
            call find_ram
            ld (ram1_slot), a
            ; マッパーの種類：7000h に 1 を書いて 8000h を見る
            ;   ASCII16 → バンク1 の先頭（本体の JP = C3h） / ASCII8 → 8KB バンク1（FFh）
            ld a, (rom_slot)
            ld h, 40h
            call ENASLT
            ld a, 1
            ld (7000h), a
            ld a, (rom_slot)
            ld h, 80h
            call ENASLT
            ld a, (8000h)
            cp 0C3h
            ld a, 0
            jr z, .m16
            inc a
.m16:       ld (mapper8), a

            ; バンク1 → 4000h（ページ2 に ROM、ページ1 に RAM）
            ld a, (rom_slot)
            ld h, 40h
            call ENASLT
            ld a, 1
            call sel_p2
            ld a, (rom_slot)
            ld h, 80h
            call ENASLT
            ld a, (ram1_slot)
            ld h, 40h
            call ENASLT
            ld hl, 8000h
            ld de, 4000h
            ld bc, 4000h
            ldir
            ; バンク2 → 8000h（ページ1 に ROM、ページ2 に RAM）
            ld a, (rom_slot)
            ld h, 40h
            call ENASLT
            ld a, 2
            call sel_p1
            ld a, (ram2_slot)
            ld h, 80h
            call ENASLT
            ld hl, 4000h
            ld de, 8000h
            ld bc, 4000h
            ldir
            ; バンク3 → C000h-EFFFh
            ld a, 3
            call sel_p1
            ld hl, 4000h
            ld de, 0C000h
            ld bc, 3000h
            ldir
            xor a
            call sel_p1
            ld a, (ram1_slot)
            ld h, 40h
            call ENASLT
            ; 割り込みの入口
            ld a, 0C9h
            ld (H_KEYI), a
            ld hl, IMG_ISR
            ld (H_TIMI + 1), hl
            ld a, 0C3h
            ld (H_TIMI), a
            jp IMG_ENTRY

; H=40h/80h のページで書ける RAM のスロットを返す（A）。見つからなければページ3 と同じ
find_ram:   ld a, h
            ld (.page), a
            ld a, (ram3_slot)
            call test_ram
            ret z
            ld b, 0
.prim:      ld a, b
            ld hl, EXPTBL
            ld e, b
            ld d, 0
            add hl, de
            ld a, (hl)
            and 80h
            jr nz, .exp
            ld a, b
            push bc
            call test_ram
            pop bc
            ret z
            jr .next
.exp:       ld c, 0
.sec:       ld a, c
            rlca
            rlca
            or b
            or 80h
            push bc
            call test_ram
            pop bc
            ret z
            inc c
            ld a, c
            cp 4
            jr c, .sec
.next:      inc b
            ld a, b
            cp 4
            jr c, .prim
            ld a, (ram3_slot)
            ret
.page:      db 0

; A=スロット。ページ（find_ram.page）に RAM があれば Z（A はそのまま）
test_ram:   ld (.slot), a
            ld a, (find_ram.page)
            ld h, a
            ld a, (.slot)
            call ENASLT
            ld a, (find_ram.page)
            or 3Fh
            ld h, a
            ld l, 0F0h
            ld a, (hl)
            ld b, a
            cpl
            ld (hl), a
            cp (hl)
            ld (hl), b
            ld a, (.slot)
            ret
.slot:      db 0

boot_end:
            ent
            display "boot size: ", /d, boot_end - boot_start
            assert boot_end - boot_start < 0200h

;------------------------------------------------------------------------------
; ディスクに保存する（バンク0 の 7000h に置き、C000h に写して実行する。本体の disk_save から）
;   C002h に戻る先（本体の dk_ret）。A = 0 成功 / 1 失敗 で戻る
            ds 7000h - $, 0FFh
body_src:
            disp SCR
body_start:
            jr b_go
dk_retp:    dw 0
b_go:       ld sp, DK_DATA
            ld hl, (dk_lo)
            ld (b_lo), hl
            ld a, (ram1_slot)
            ld (b_ram1), a
            ; 保存の中身（VRAM）→ データ
            ld hl, VR_VSRAM
            call b_rset
            ld hl, DK_DATA
            ld bc, DK_LEN
            call b_rcopy
            ; ゲームの中身（HIMEM〜F37Fh。オーバーレイ・関数群・スタック）を VRAM へ
            ld hl, VR_GAME
            call b_wset
            call b_grange
            call b_wcopy
            ; ディスクの作業領域を戻す
            ld hl, VR_DISK
            call b_rset
            call b_range
            call b_rcopy
            ; 起動時の H.KEYI・H.TIMI
            ld hl, VR_HOOKS
            call b_rset
            ld hl, H_KEYI
            ld bc, 10
            call b_rcopy
            ld hl, b_deptr
            ld (DISKVE), hl
            ld hl, b_brptr
            ld (BREAKV), hl
            ld (b_sp), sp
            xor a
            ld (b_errf), a
            ei
            ld de, DK_DATA
            ld c, 1Ah
            call BDOS
            ld hl, DK_FCB
            ld b, 37
.c:         ld (hl), 0
            inc hl
            djnz .c
            ld hl, b_name
            ld de, DK_FCB + 1
            ld bc, 11
            ldir
            ld de, DK_FCB
            ld c, 16h           ; 作る（あれば中身を消して作り直す）
            call BDOS
            or a
            jr nz, b_err
            ld hl, 1
            ld (DK_FCB + 14), hl
            dec hl
            ld (DK_FCB + 33), hl
            ld (DK_FCB + 35), hl
            ld de, DK_FCB
            ld hl, DK_LEN
            ld c, 26h           ; まとめて書く
            call BDOS
            or a
            jr nz, b_err
            ld de, DK_FCB
            ld c, 10h           ; 閉じる
            call BDOS
            or a
            jr nz, b_err
            xor a
            jr b_fin
b_err:      ld a, 1
b_fin:      di
            ld sp, (b_sp)
            ld (b_res), a
            ; 成功したときだけ、今のディスクの作業領域を VRAM へ（次に使うときの続き）。
            ; 失敗（BDOS の途中で中断した）ときの作業領域は壊れていることがあるので、前のものを使い続ける
            or a
            jr nz, b_keep
            ld hl, VR_DISK
            call b_wset
            call b_range
            call b_wcopy
b_keep:
            ; ゲームの中身を戻す
            ld hl, VR_GAME
            call b_rset
            call b_grange
            call b_rcopy
            ld a, 0C9h
            ld (H_KEYI), a
            ld hl, IMG_ISR
            ld (H_TIMI + 1), hl
            ld a, 0C3h
            ld (H_TIMI), a
            ld a, (b_res)
            ld hl, (dk_retp)
            jp (hl)
b_dehand:   ld a, (b_errf)      ; ディスクエラー：3 回まではやり直し、4 回目は BDOS の途中から抜けて失敗に
            inc a
            ld (b_errf), a
            cp 4
            jr nc, b_brhand
            ld c, 1
            ret
b_brhand:   ld sp, (b_sp)       ; 中断された：ページ1 を RAM に戻して失敗
            ld a, (b_ram1)
            ld h, 40h
            call ENASLT
            jr b_err
b_deptr:    dw b_dehand
b_brptr:    dw b_brhand
b_name:     db "MSXSTAD DAT"
b_sp:       dw 0
b_res:      db 0
b_ram1:     db 0
b_errf:     db 0
b_lo:       dw 0
; HL = 下端、BC = F380h - 下端（下端は関数群の dk_lo。最初に読んでおく）
b_range:    ld hl, (b_lo)
            push hl
            ex de, hl
            ld hl, 0F380h
            or a
            sbc hl, de
            ld b, h
            ld c, l
            pop hl
            ret
; ゲームの中身は D000h〜F37Fh を退避する（HIMEM の下もディスク BASIC がスタックなどに使うことがある）
b_grange:   ld hl, DK_MINHI
            ld bc, 0F380h - DK_MINHI
            ret
b_wset:     ld a, 40h
            jr b_set
b_rset:     xor a
b_set:      push af
            ld a, h
            rlca
            rlca
            and 3
            out (99h), a
            ld a, 8Eh
            out (99h), a
            ld a, l
            out (99h), a
            pop af
            ld e, a
            ld a, h
            and 3Fh
            or e
            out (99h), a
            ret
b_wcopy:    ld a, (hl)
            out (98h), a
            inc hl
            dec bc
            ld a, b
            or c
            jr nz, b_wcopy
            ret
b_rcopy:    in a, (98h)
            ld (hl), a
            inc hl
            dec bc
            ld a, b
            or c
            jr nz, b_rcopy
            ret
body_end:
            ent
            display "disk body size: ", /d, body_end - body_start
            assert body_end - body_start <= 0200h

; マッパーの種類を当ててもらうための目印（実行しない）
            rept 8
            ld (77FFh), a
            ld (7000h), a
            ld (6000h), a
            endr
            ds 8000h - $, 0FFh
