/* VDP（G3 = SCREEN 4）の設定と絵の読み込み */
#include "game.h"

void vdp_pal(u8 v);

void vdp_display(u8 on)
{
    vdp_reg(1, on ? 0x62 : 0x22);
}

void vdp_load_field_tiles(void)
{
    u8 b;
    for (b = 0; b < 4; b++) {
        u16 o = (u16)b << 11;
        LOADV(VR_PAT + o + 0x400, A_FONT_PAT);
        LOADV(VR_COL + o + 0x400, A_FONT_COL);
    }
    LOADV(VR_PAT + 0x0000, A_FIELD_PAT0);
    LOADV(VR_COL + 0x0000, A_FIELD_COL0);
    LOADV(VR_PAT + 0x0800, A_FIELD_PAT1);
    LOADV(VR_COL + 0x0800, A_FIELD_COL1);
    LOADV(VR_PAT + 0x1000, A_FIELD_PAT2);
    LOADV(VR_COL + 0x1000, A_FIELD_COL2);
    LOADV(VR_PAT + 0x1800, A_FIELD_PAT3);
    LOADV(VR_COL + 0x1800, A_FIELD_COL3);
}

/* タイトルのロゴ（パターン 100〜115。試合中はここも球場のタイル） */
void vdp_load_logo(void)
{
    u8 b;
    for (b = 0; b < 4; b++) {
        u16 o = ((u16)b << 11) + T_QUART * 8;
        LOADV(VR_PAT + o, A_QUART_PAT);
        LOADV(VR_COL + o, A_QUART_COL);
    }
}

/* パレット 8..11 = 先攻・後攻のチーム色 */
void vdp_set_team_palette(void)
{
    const u8* a = thdr[side[0].team].pal;
    const u8* b = thdr[side[1].team].pal;
    u8 i;
    vdp_reg(16, 8);
    for (i = 0; i < 4; i++) vdp_pal(a[i]);
    for (i = 0; i < 4; i++) vdp_pal(b[i]);
}

void pal_set(u8 idx, u8 rb, u8 g)
{
    vdp_reg(16, idx);
    vdp_pal(rb);
    vdp_pal(g);
}

void vdp_clear_nt(void)
{
    vdp_fill(VR_NT0, T_SPACE, 1024);
    vdp_fill(VR_NT1, T_SPACE, 1024);
}
