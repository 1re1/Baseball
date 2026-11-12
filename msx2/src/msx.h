/* ハードウェアの下まわり（crt0.s） */
#ifndef MSX_H
#define MSX_H
#include "types.h"

void vdp_reg(u8 reg, u8 val);
void vdp_waddr(u16 addr);
void vdp_raddr(u16 addr);
void vdp_out(u8 v);
void vdp_ldir(u16 vram, const void* src, u16 len) __sdcccall(0);
void vdp_fill(u16 vram, u8 val, u16 len) __sdcccall(0);
void vdp_palette(const u8* p);
void nt_row(u16 vram, const u8* src);
void vdp_send(u8 n, const u8* src);
void sat_commit(void);
void wait_vblank(void);
void rom2vram(u8 bank, u16 src, u16 len);
void rom2ram(u16 src, void* dst, u8 bank, u16 len) __sdcccall(0);
void ram2sram(u16 ofs, const void* src, u16 len) __sdcccall(0);    /* SRAM へ書く（読むのは rom2ram に SR_BANK） */
void psg_write(u8 reg, u8 val);
void read_input(void);

extern u8 kbd[9];
extern u8 joyraw[2];
extern u8 sat[128];
extern volatile u8 vblank_flag;

/* VRAM の配置（G3） */
#define VR_PAT        0x0000   /* 2KB × 4 */
#define VR_COL        0x2000   /* 2KB × 4 */
#define VR_NT0        0x4000
#define VR_NT1        0x4400
#define VR_SPRCOL     0x5C00
#define VR_SAT        0x5E00
#define VR_SPAT_ATBAT 0x6000
#define VR_SPAT_FIELD 0x6800

#define RG9SAV (*(volatile u8*)0xFFE8)

/* ROM のデータを VRAM へ（A_xxx は bank,ofs,len） */
#define LOADV(addr, asset) do { vdp_waddr(addr); rom2vram(asset); } while (0)
#endif
