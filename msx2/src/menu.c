/* タイトルで使う文字・表（本体に置く。タイトルのプログラムはオーバーレイの先頭 E000h〜E2FFh：球場マップと重ならない） */
#include "game.h"

const char* const mode_name[6] = { "1P  VS  COM", "1P  VS  2P ", "COM VS  COM", "EDIT", "TOURNAMENT", "CONTINUE" };
const u8 inn_tab[3] = { 3, 6, 9 };
const char str_start[] = "SPACE  TO START";
const char str_lr[] = "< >";
const char str_speed[] = "SPEED";
const u8 speed_rate[5] = { 36, 42, 48, 54, 60 };

