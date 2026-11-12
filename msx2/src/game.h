/* 試合の共通定義 */
#ifndef GAME_H
#define GAME_H
#include "types.h"
#include "msx.h"
#include "assets.h"

/* ---- 座標：ワールドはドット、動くものは 1/16 ドット（サブ） ---- */
#define SUBS 4
#define S(v) ((s16)((v) << SUBS))
#define PXL(v) ((s16)((v) >> SUBS))

#define HOME_X 256
#define HOME_Y 376
#define B1_X 348
#define B1_Y 307
#define B2_X 256
#define B2_Y 238
#define B3_X 164
#define B3_Y 307
#define MOUND_X 256
#define MOUND_Y 298
#define WALL_LX 20
#define WALL_RX 492
#define BACK_Y 406
#define SIDE_R 712              /* ファウルゾーンの壁（45 度）：一塁側 x+y < SIDE_R、三塁側 y-x < SIDE_L の内側 */
#define SIDE_L 201              /* 一塁側の壁をダイヤモンドの縦の中心（x = 256）で折り返した位置 */
extern u8 ball_tint;            /* 1 = ボールを灰色に（ライン際で止まったときの点滅） */

#define ATBAT_CX 128
#define ATBAT_CY 200

/* ---- 入力 ---- */
#define K_UP    0x01
#define K_DOWN  0x02
#define K_LEFT  0x04
#define K_RIGHT 0x08
#define K_A     0x10
#define K_B     0x20
#define K_START 0x40
#define K_SEL   0x80
extern u8 pad[3], pad_new[3];     /* [0]=1P [1]=2P [2]=どちらか */
void input_update(void);

/* ---- 汎用 ---- */
extern u16 frame_count;
u8 rnd(void);
u8 rnd_n(u8 n);
u16 dist_approx(s16 dx, s16 dy);
u16 bsd(u8 b, const void* p);
extern u8 hardg;                /* 痛烈なゴロ（play.c） */   /* 塁 b までの距離（サブ）。p = Actor か Ball */
s16 abs16(s16 v);
extern const s8 sin_tab[64];        /* 64 = 1 周、±64 */
#define COS(a) sin_tab[((a) + 16) & 63]
#define SIN(a) sin_tab[(a) & 63]

/* ---- VDP ---- */
void vdp_display(u8 on);
void vdp_load_field_tiles(void);
void vdp_load_logo(void);
void vdp_set_team_palette(void);
void vdp_clear_nt(void);
void pal_set(u8 idx, u8 rb, u8 g);

/* ---- 画面スクロール・文字 ---- */
extern s16 cam_x, cam_y;            /* 望むカメラ（ドット、左上） */
extern u8 view_cx;                  /* 次に見せる粗い x（タイル） */
extern s16 view_y;
void scroll_reset(void);
void scroll_update(void);
void scroll_commit(void);
void scroll_invalidate(void);
void scroll_restore_rows(u8 r0, u8 r1);
void txt_map(u8 col, u8 maprow, const u8* s);          /* 0 終わり */
void txt_ascii(u8 col, u8 maprow, const char* s);
void txt_tile(u8 col, u8 maprow, u8 t);
void txt_n(u8 col, u8 maprow, const u8* s, u8 n);
void txt_num(u8 col, u8 maprow, u16 v, u8 width);
void txt_fill(u8 col, u8 maprow, u8 t, u8 n);
void scoreboard_update(void);
/* 画面固定（メニュー等）用：表示中の名前表の直書き */
void nt_text(u8 col, u8 row, const u8* s);
void nt_ascii(u8 col, u8 row, const char* s);
void nt_tile(u8 col, u8 row, u8 t);
void nt_n(u8 col, u8 row, const u8* s, u8 n);
void nt_num(u8 col, u8 row, u16 v, u8 width);
void nt_fill(u8 col, u8 row, u8 t, u8 n);

/* ---- スプライト ---- */
#define SM_ATBAT 0
#define SM_FIELD 1
extern u8 spr_mode;
void spr_set_mode(u8 mode);
void spr_colors(void);
void spr_frame_begin(void);
void spr_put(u8 plane, s16 x, s16 y, u8 pat);   /* x,y = 左上（ワールド・ドット） */
void spr_hide(u8 plane);
void spr_put2(u8 plane, s16 x, s16 y, u8 pat);   /* plane / plane+1 に pat / pat+1 */
/* 人（Actor：x,y はサブ。足もと）を 16x16 で置く：左上 = (PXL(x)-8, PXL(y)-15)。2 = plane と plane+1 */
void spr_actor(u8 plane, const void* a, u8 pat);
void spr_actor2(u8 plane, const void* a, u8 pat);
/* 走者・守備をまとめて置く。em_pre は先に数える (t, 枚数) の組（t = 画面の上端 + 15） */
extern u8 em_pre[16], em_pre_n, em_fr;
void emit_actors(void);
#define ABS(v) ((v) < 0 ? -(v) : (v))
void spr_hide_all(void);
void spr_commit(void);
void msg_show(u8 id, u8 frames);
void msg_draw(void);
void spr_keep(void);
extern u8 msg_timer;
extern u8 msg_y;
/* 判定の文字（画面の真ん中）を、帰線期間に今のスクロールの値で置き直す（スクロール中もぶれない） */
void msg_fix(void);
extern u8 show_fine;
/* 面の割り当て */
#define PL_MSG 0          /* 0〜2：判定の文字（6 文字まで） */
#define PL_UMP 3          /* 球審 */
#define PL_BALL 4
#define PL_SHADOW 5
#define PL_RUN 6          /* 打席: 6-11 走者 3 組 / 守備: 6-13 走者 4 組 */
#define PL_BATTER 12      /* 打席のみ: 12-15 */
#define PL_PITCHER 16     /* 打席のみ: 16-19 */
#define PL_FLD_AB 20      /* 打席: 20-29 捕手・内野 5 組 */
#define PL_BAT 30
#define PL_FLD 14         /* 守備: 14-31 守備 9 組 */

/* ---- 試合のデータ ---- */
enum { POS_P, POS_C, POS_1B, POS_2B, POS_3B, POS_SS, POS_LF, POS_CF, POS_RF };

typedef struct {
    s16 x, y;          /* サブ */
    s16 tx, ty;        /* 目標（サブ） */
    u8 pat;            /* 16x16 の番号 */
    u8 anim;
    u8 face;           /* 0 下 1 上 2 左 3 右 */
    u8 moving;
} Actor;

typedef struct {
    Actor a;
    u8 on;
    u8 base;           /* 最後に踏んだ塁 0..3、4 = 生還 */
    u16 prog;          /* 次の塁までの進み 0..65535 */
    s8 dir;            /* +1 進む / -1 戻る / 0 止まる */
    u8 dest;           /* 止まる塁 */
    u8 forced;
    u8 start;          /* 打った瞬間の塁 */
    u8 who;            /* 打順 */
    u16 spd;           /* prog / フレーム */
    u8 out;
    u8 tagged;         /* フライ捕球後に塁に触れた */
} Runner;

#define BM_NONE  0
#define BM_HELD  1
#define BM_PITCH 2
#define BM_HIT   3
#define BM_THROW 4
#define BM_DEAD  5

typedef struct {
    s16 x, y, z;       /* サブ */
    s16 vx, vy, vz;
    u8 mode;
    u8 holder;         /* BM_HELD の守備 */
    u8 bounced;
    u8 fair;           /* 0 未定 1 フェア 2 ファウル */
    u8 target;         /* 送球を受ける守備 */
    u8 tbase;          /* 送球先の塁 (0..3, 255 = 人) */
    u8 hr;
    u8 passed_inf;     /* 内野を越えた */
} Ball;

typedef struct {
    u8 team;
    u8 order[9];       /* 打順（BatterDef の番号、255 = 投手） */
    u8 bat_no;         /* 次の打者 0..8 */
    u8 pit;            /* 投手（PitcherDef の番号） */
    u8 stamina;        /* 0..100 */
    u8 bench_used;
    u8 pit_used;
    u8 score[12];
    u8 runs;
    u8 hits;
    u8 ctrl;           /* 0 COM / 1 1P / 2 2P */
} Side;

extern Side side[2];
extern TeamDef tm[2];            /* 試合中の 2 チーム（ROM から読む） */
void team_load(void);
extern u8 inning, half, balls, strikes, outs;
extern u8 max_inning;
extern u8 game_mode;     /* 0: 1P vs COM, 1: 1P vs 2P, 2: COM vs COM, 3: EDIT, 4: トーナメント, 5: トーナメントのつづき */
extern Actor fld[9];
extern Runner run[4];
extern Ball ball;
extern u8 batter_left;   /* 打者が左打ち */
extern u8 pitcher_left;

/* 塁の位置（ドット） */
extern const s16 base_x[5], base_y[5];
extern const s16 home_pos_x[9], home_pos_y[9];

/* 打者・投手の情報 */
const BatterDef* cur_batter(void);
const PitcherDef* cur_pitcher(void);
#define OFF (half)          /* 攻撃側 */
#define DEF (half ^ 1)      /* 守備側 */
u8 ctrl_pad(u8 sd);         /* その側の操作者のパッド（COM は 0xFF） */

/* 状態 */
#define GS_ATBAT   0
#define GS_PITCH   1
#define GS_PLAY    2
#define GS_RESULT  3
#define GS_CHANGE  4
#define GS_OVER    5
extern u8 gstate;
extern u16 gtimer;

/* game.c */
void game_start(void);
u8 game_frame(void);           /* 1 を返すと試合終了 */
void hud_draw(void);
void hud_clear(void);
void hud_count(void);
void next_batter(void);
void add_out(void);
void add_run(void);
void load_batter_sprites(void);
void load_pitcher_sprites(void);

/* プレーの結果 */
#define PR_NORMAL 0
#define PR_FOUL   1
#define PR_HR     2
#define PR_STEAL  3

/* 打席の情報（ai.c も見る） */
extern s16 bat_x, bat_y;
extern u8 swing_t;
extern s8 pit_off;
extern u8 pit_t;
extern u8 sayonara;
u8 inp(u8 sd);
u8 inp_new(u8 sd);
extern u8 res_next;

/* play.c */
void play_begin_hit(s16 vx, s16 vy, s16 vz);
void play_begin_held(u8 holder);      /* ボールを持った守備から始まるプレー（盗塁の捕手・牽制の投手） */
#define LEAD 0x1000                   /* 塁の上の走者のリード（塁間の 1/16、約 6 ドット） */
/* play2.c（オーバーレイ A の後ろ、F000h〜）：牽制 */
extern u8 pk_wait;
u8 pick_try(u8 p);                      /* 人の投手：B を押した。1 = 牽制した（か、何もしない）、0 = 投げる */
u8 pick_com(void);                      /* COM の投手：投げる前に、ときどき牽制する。1 = 牽制した */
void pick_tick(void);                   /* 牽制の走者：反応の遅れが終わったら塁へ戻る */
void hold_runners(void);                /* 走者のいる塁の近くに守備を寄せる（一塁手はベースにつく） */
u8 play_update(void);          /* 1 = プレー終了 */
void play_draw(void);
void play_camera(void);
void fielders_reset(void);
void runners_place(void);
void runner_pos(Runner* r);
void rgo(s8 d, Runner* r);      /* 向き d（+1 次の塁へ・-1 今の塁へ戻る） */
void throw_to_base(u8 b);
void move_to(u8 i);
void run_with_ball(u8 b);
u8 play_cover(u8 b);
/* 挟殺：ボールを持った守備（COM）が追いかける走者（番号 + 1。0 = なし） */
extern u8 chase_k;
u8 rd_holder(void);                     /* 挟殺の守備（COM）。1 = 決めた（追う・投げる） */
u8 rd_runner(Runner* r, u8 nb);
u8 rd_force(void);                      /* 押し出された走者がまだ走っている（フォースプレーが先） */         /* はさまれた走者（COM）。1 = 向きを決めた */
#define OFF8 0x1200             /* 塁から約 8 ドット（塁と塁の間は約 115 ドット = 10000h） */
u8 play_fly_caught(void);
u8 play_chaser(void);
extern const u8 fspeed[9];
#define TS 45                   /* 送球の速さ（投球と同じ物差し。140km の速球は 52） */
extern u8 play_result;          /* 結果の種類 */
extern u8 ctl_fielder;          /* 操作中の守備 */
extern u8 play_outs;            /* このプレーで取ったアウト */
extern u8 play_runs;

/* ai.c */
void ai_pitch_plan(void);
/* 球種（game.c）。ai_ptype = COM が次に投げる球種（ai.c） */
#define PT_CURVE 1
#define PT_SHOOT 2
#define PT_FORK 3
extern u8 ptype, ai_ptype;
s16 brk_left(void);
u8 ai_pitch_input(void);
u8 ai_bat_input(void);
void ai_bat_reset(void);
u8 ai_steal(void);
void ai_holder(void);
void ai_runners(void);

/* sound.c */
void sound_init(void);
void sound_tick(void);
void bgm_play(u8 id);
void sfx_play(u8 id);
void sfx_cheer(void);           /* 歓声（外野へのヒット・得点・ホームラン）。曲は A・B で鳴り続け、C で「ワーッ」 */
/* フライの軌道音：fly_note（PSG の周期 / 2）を fly_hold フレームの間 C で鳴らす（ゲームが毎回書きなおす） */
extern u8 fly_note, fly_hold;
/* 守備：B で操作する野手を切り替える（screens.c のオーバーレイの前の部分。球場マップに上書きされない） */
void fielder_switch(void);
/* 内野と外野の守備範囲：(x, y)（サブ）がはっきり外野（外野手の定位置のあたり）か／そこにいちばん近い外野手 */
#define NPRED 10                        /* 打球の先読みの点の数 */
u8 out_redirect(u8 best);               /* 追う者 best を、はっきり外野なら近い外野手に替える */
void qa_first(void);                    /* 転がる打球の 12 フレーム先がはっきり外野なら qa_i0 = POS_LF、ちがえば 0 */
extern u8 qa_i0;
extern s16 land_x, land_y, pred_x[NPRED * 2];
extern u8 land_t, fk[9];
extern u8 ctl_fielder, sel_blink;
#define BGM_TITLE 0
#define BGM_ATBAT 1
#define BGM_HOMERUN 2
#define BGM_CHANGE 3
#define BGM_GAMESET 4
#define BGM_PLAYBALL 5
#define BGM_ATBAT2 6
#define SFX_HIT 0
#define SFX_CATCH 1
#define SFX_THROW 2
#define SFX_STRIKE 3
#define SFX_OUT 4
#define SFX_CURSOR 5
#define SFX_PITCH 6
#define SFX_FOUL 7
#define SFX_BOUND 8
#define SFX_SAFE 9
#define SFX_FAST 10
#define SFX_BOUND2 11                   /* 小さな弾み */                     /* 速球（140km 以上）の「ひゅん！」 */

/* screens.c */
/* オーバーレイ B（タイトル・EDIT・トーナメント）：ROM のバンク OVB_BANK → OVL_ADDR。入口は 3 バイトおきの表 */
#define OVB_BANK 8
/* 保存の中身（フロッピーディスクの MSXSTAD.DAT を VRAM 7000h〜 に置く）。rom2ram のバンク 10h・ram2sram で読み書き */
#define SR_BANK 0x10
#define SR_MAGIC 0                              /* "MSXS" と版 */
#define SR_TEAMS 8                              /* 8 チーム × TEAM_SIZE（EDIT で書きかえる） */
#define SR_TOUR (SR_TEAMS + 8 * TEAM_SIZE)      /* トーナメント（TOUR_SIZE バイト） */
#define TOUR_SIZE 32
u8 disk_save(void);             /* ディスクに保存（DISKMODE のときだけ）。0 = 成功 */
#define DISKMODE (*(volatile u8*)0xF218)   /* 1 = ディスクに保存する（boot.asm の関数群の diskmode） */
extern u8 esc_new;                              /* ESC を押した瞬間（トーナメントの画面からタイトルへ） */
extern u8 sram_ok;                              /* 0 まだ調べていない／1 保存できない（ドライブなし）／2 保存できる（中身も正しい） */
void ovlb_load(void);
#define OVB_TITLE() ((void (*)(void))(OVL_ADDR + 0))()
#define OVB_TOUR(c) ((u8 (*)(u8))(OVL_ADDR + 3))(c)       /* トーナメントを始める（c = 1：つづきから）。1 = 試合をする */
#define OVB_TOUR_NEXT() ((u8 (*)(void))(OVL_ADDR + 6))()
#define OVB_BOOT() ((void (*)(void))(OVL_ADDR + 9))()        /* 起動のときだけ：VDP の設定・スプライトの絵の読み込み */  /* 試合の結果を書いて次へ。1 = 次の試合をする */
#define OVC_BANK 9                                      /* オーバーレイ C：EDIT モード */
#define OVC_EDIT() ((void (*)(void))(OVL_ADDR + 0))()
void ovlx_load(u8 bank);
extern u8 tour[];                                       /* トーナメント（保存の中身の SR_TOUR と同じ並び） */
void screen_select(void);
#define OVC_BOARD(f) ((void (*)(u8))(OVL_ADDR + 3))(f)   /* イニングの間・試合の終わりのスコアボード（オーバーレイ C） */
void screen_menu_sub(void);
/* オーバーレイ：タイトル・選択・オーダー・スコアボードのプログラム（ROM バンク 7）を DD00h〜EFFFh に読む（球場マップ E300h〜 と重なる） */
#define OVL_ADDR 0xDD00
#define OVL_BANK 7
#define OVL_LEN 0x1500
void ovl_load(void);
/* ゲームの速さ（タイトルで 1〜5）。grate = 60 フレームあたりに進むゲームのフレーム数（36〜60） */
extern u8 game_speed, grate;
u8 time_adv(u8* acc, u8 frames);
extern u8 bat_req;
void batter_frame_upload(void);
/* 審判（play.c）：塁 0/4 = 本塁の球審、1〜3 = 塁審 */
void ump_reset(void);
void ump_call(u8 base, u8 pose, u8 t);
void ump_tick(u8 avoid);
void ump_draw(u8 first, u8 last);
void spr_ump_planes(u8 first, u8 last);
void map_load(void);
void screen_lineup(void);

/* main.c */
void frame_sync(void);          /* 1 フレーム待って VDP へ反映 */
void rnd_mix(u16 v);
extern u8 demo;                 /* タイトル放置のデモ試合 */
/* 集計（テスト用） */
extern u16 dbg[16];
#define D_PITCH 0
#define D_SWING 1
#define D_CONTACT 2
#define D_FOUL 3
#define D_HR 4
#define D_HIT 5
#define D_SO 6
#define D_BB 7
#define D_FLYOUT 8
#define D_OUT 9
#define D_RUN 10
#define D_DOUBLE 11
#define D_TRIPLE 12
#define D_GAMES 13
#define D_TIMEOUT 14
#define D_OVERRUN 15
#define DBG(k) (dbg[k]++)
void scoreboard_clear(void);
#endif
