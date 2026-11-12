import pyxel
import math
import random

# 定数定義
SCREEN_WIDTH = 160
SCREEN_HEIGHT = 120
COLOR_GRASS = 11  # 緑
COLOR_DIRT = 4    # 茶色
COLOR_WHITE = 7
COLOR_BATTER = 12 # 青
COLOR_PITCHER = 8 # 赤
COLOR_BALL = 7
COLOR_FIELDER = 10 # 黄色
COLOR_SHADOW = 13 # グレー
FENCE_Y = -60 # フェンスのY座標
FENCE_R = 160 # フェンスの半径
REBOUND_COEFFICIENT = 0.9 # ボールの反発係数

# ゲームの状態
STATE_WAIT = 0
STATE_PITCHING = 1
STATE_HIT = 2
STATE_FOUL = 3
STATE_STRIKE = 4
STATE_OUT = 5
STATE_HOMERUN = 6
STATE_GAMEOVER = 7
STATE_BALL = 8
STATE_WALK = 9
STATE_TITLE = 10
STATE_THROW = 11
STATE_CHANGE = 12

class App:
    def __init__(self):
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Famista Style Baseball")
        
        # バッターデータ [CPU, Player]
        self.team_batters = [
            [
                {"avg": 0.310, "hr": 0.04}, {"avg": 0.270, "hr": 0.02}, {"avg": 0.330, "hr": 0.06},
                {"avg": 0.280, "hr": 0.10}, {"avg": 0.290, "hr": 0.08}, {"avg": 0.250, "hr": 0.03},
                {"avg": 0.230, "hr": 0.01}, {"avg": 0.210, "hr": 0.00}, {"avg": 0.120, "hr": 0.00},
            ],
            [
                {"avg": 0.290, "hr": 0.03}, {"avg": 0.260, "hr": 0.01}, {"avg": 0.310, "hr": 0.07},
                {"avg": 0.270, "hr": 0.12}, {"avg": 0.300, "hr": 0.05}, {"avg": 0.240, "hr": 0.02},
                {"avg": 0.220, "hr": 0.01}, {"avg": 0.190, "hr": 0.00}, {"avg": 0.100, "hr": 0.00},
            ]
        ]
        
        # ピッチャーデータ [CPU, Player]
        self.team_pitchers = [
            {"speed": 3.0, "stamina": 40}, # CPU
            {"speed": 3.2, "stamina": 45}  # Player
        ]
        
        # ゲーム変数の初期化
        self.restart_game() # スコアなども含めて初期化
        self.game_state = STATE_TITLE
        self.is_player_attack = False # False: プレイヤー守備(CPU攻撃), True: プレイヤー攻撃

        # 音の準備（簡易的なビープ音）
        pyxel.sound(0).set("a3a2c1a1", "p", "7", "vffn", 25) # Hit
        pyxel.sound(1).set("c2c2", "n", "7", "s", 10)       # Throw
        pyxel.sound(2).set("c1", "n", "3", "f", 3)          # Bounce
        
        pyxel.run(self.update, self.draw)

    def restart_game(self):
        self.scores = [0, 0] # [CPU, Player]
        self.balls = 0
        self.strikes = 0
        self.outs = 0
        self.runners = [0, 0, 0] # [1塁, 2塁, 3塁] (0:なし, 1:あり)
        self.inning = 1
        self.is_top = True # True: 表, False: 裏
        self.current_batter = [0, 0] # [CPU, Player] の打順
        self.current_stamina = [self.team_pitchers[0]["stamina"], self.team_pitchers[1]["stamina"]]
        self.reset_game()

    def reset_game(self):
        self.game_state = STATE_WAIT
        self.ball_x = SCREEN_WIDTH // 2
        self.ball_y = 40
        self.scroll_y = 0
        self.ball_vx = 0
        self.ball_vy = 0
        self.ball_z = 0
        self.ball_vz = 0
        
        self.pitcher_x = SCREEN_WIDTH // 2
        self.pitcher_y = 40
        
        # バッターの位置
        self.batter_x = SCREEN_WIDTH // 2 - 10
        self.batter_y = 90
        self.is_swinging = False
        self.swing_frame = 0
        self.result_timer = 0
        self.message = ""
        self.cpu_timer = 0
        self.is_grounder = False
        self.play_outs = 0
        
        # 守備選手 (x, y)
        self.fielders = [
            [30, 55], [60, 30], [100, 30], [130, 55], # 内野 (3B, SS, 2B, 1B)
            [30, -10], [80, -20], [130, -10], # 外野
            [80, 105] # キャッチャー
        ]
        self.fielders_initial_pos = [pos[:] for pos in self.fielders] # 定位置を保存
        
        self.anim_runners = [] # ランナーのアニメーション用 [x, y, target_x, target_y]
        self.throw_target = None # 送球先座標
        self.throw_targets = []
        self.play_runners = [] # [base, is_running] base: -1(H), 0(1B), 1(2B), 2(3B)

    def update(self):
        if self.game_state == STATE_TITLE:
            self.update_title()
        elif self.game_state == STATE_WAIT:
            self.update_wait()
        elif self.game_state == STATE_PITCHING:
            self.update_pitching()
        elif self.game_state == STATE_GAMEOVER:
            self.update_gameover()
        elif self.game_state == STATE_THROW:
            self.update_throw()
        elif self.game_state == STATE_CHANGE:
            self.update_change()
        elif self.game_state >= STATE_HIT:
            self.update_result()

    def update_title(self):
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.restart_game()

    def update_wait(self):
        self.pitcher_x = SCREEN_WIDTH // 2
        self.pitcher_y = 40
        # バッターの移動
        if self.is_player_attack:
            if pyxel.btn(pyxel.KEY_LEFT):
                self.batter_x = max(20, self.batter_x - 1)
            if pyxel.btn(pyxel.KEY_RIGHT):
                self.batter_x = min(SCREEN_WIDTH - 30, self.batter_x + 1)
            
            # CPU投球（時間経過で自動開始）
            self.cpu_timer += 1
            if self.cpu_timer > 60:
                self.start_pitch()
                # CPUの球種ランダム設定
                self.ball_vx = random.uniform(-0.1, 0.1)
                self.ball_z = random.uniform(2.5, 3.5)
        else:
            # CPUバッター（待機中は動かない）
            
            # プレイヤー投球開始
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.start_pitch()

    def start_pitch(self):
        self.game_state = STATE_PITCHING
        
        p_idx = 0 if self.is_player_attack else 1 # 守備側が投球
        pitcher = self.team_pitchers[p_idx]
        
        if self.current_stamina[p_idx] > 0:
            self.current_stamina[p_idx] -= 1
            
        stamina_ratio = max(0.0, self.current_stamina[p_idx] / pitcher["stamina"])
        self.ball_vx = 0 # 初期は直球
        self.ball_vy = pitcher["speed"] * (0.8 + 0.2 * stamina_ratio) # 球速
        self.ball_z = 3 # 投球の高さ
        pyxel.play(0, 1)

    def update_pitching(self):
        if self.is_player_attack:
            # プレイヤー攻撃：ボール変化はCPU任せ（単純な直球/変化球）
            pass
        else:
            # プレイヤー守備：変化球操作可能
            if pyxel.btn(pyxel.KEY_LEFT):
                self.ball_vx -= 0.08
            if pyxel.btn(pyxel.KEY_RIGHT):
                self.ball_vx += 0.08
            if pyxel.btn(pyxel.KEY_UP):
                self.ball_z += 0.1 # ホップ
            if pyxel.btn(pyxel.KEY_DOWN):
                self.ball_z -= 0.1 # ドロップ
            
            # CPUバッター思考（ボールを追いかける）
            target_x = self.ball_x - 14
            if self.batter_x < target_x - 2: self.batter_x += 1
            if self.batter_x > target_x + 2: self.batter_x -= 1

        # ボールの移動
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        # バッターのスイング
        swing_input = False
        if self.is_player_attack:
            if pyxel.btnp(pyxel.KEY_SPACE): swing_input = True
        else:
            # CPUスイング判定（ゾーン内なら確率で振る）
            if (85 < self.ball_y < 95 and not self.is_swinging and 
                abs((self.batter_x + 14) - self.ball_x) < 15):
                if random.random() < 0.2: swing_input = True
        
        if swing_input and not self.is_swinging:
            self.is_swinging = True
            self.swing_frame = 5 # スイングの持続時間

        if self.is_swinging:
            self.swing_frame -= 1
            if self.swing_frame <= 0:
                self.is_swinging = False

            # 当たり判定（簡易版）
            # バットの範囲とボールの範囲が重なったらヒット
            bat_rect = [self.batter_x + 8, self.batter_y, 12, 4] # バットの当たり判定
            if (bat_rect[0] < self.ball_x < bat_rect[0] + bat_rect[2] and
                bat_rect[1] - 5 < self.ball_y < bat_rect[1] + 5):
                
                # ジャストミート判定（中心に近いほどよく飛ぶ）
                offset = abs((self.batter_x + 14) - self.ball_x)
                
                if offset < 5:
                    self.game_state = STATE_HIT
                    self.message = "" # まだ結果は未確定
                    self.play_outs = 0
                    
                    team_idx = 1 if self.is_player_attack else 0
                    batter = self.team_batters[team_idx][self.current_batter[team_idx]]
                    
                    # 打率とホームラン率によるヒット性判定
                    is_good_hit = random.random() < batter["avg"] * 2.0
                    is_hr_course = random.random() < (batter["hr"] * 0.1)
                    
                    if offset < 2:
                        base_vy = -5.0
                        base_vz = random.uniform(2.5, 4.5)
                        if is_hr_course:
                            base_vy = -6.0
                            base_vz = random.uniform(4.0, 6.0)
                    elif offset < 3.5:
                        base_vy = -3.5
                        base_vz = random.uniform(1.5, 3.5)
                    else:
                        base_vy = -2.5
                        base_vz = 0.5 if random.random() < 0.5 else 5.0
                        
                    if not is_good_hit and not is_hr_course:
                        base_vy *= 0.6 # 打率判定に外れたら打球速度低下（内野ゴロ化）
                        if base_vz > 2.0:
                            base_vz = 4.5 # 打ち上げた場合はポップフライ化

                    self.ball_vy = base_vy * REBOUND_COEFFICIENT
                    self.ball_vz = base_vz * REBOUND_COEFFICIENT
                    self.ball_vx = (self.ball_x - (self.batter_x + 14)) * 0.5 * REBOUND_COEFFICIENT
                    if not is_good_hit and not is_hr_course: self.ball_vx *= 0.5
                    self.balls = 0
                    self.strikes = 0
                    
                    # ランナーアニメーション開始 (手動コントロール)
                    self.anim_runners = []
                    base_pos = [[130, 60], [80, 20], [26, 60]] # 1B, 2B, 3B
                    
                    # 塁上の走者を待機状態でanim_runnersに追加
                    if self.runners[0]: self.anim_runners.append([base_pos[0][0], base_pos[0][1], base_pos[0][0], base_pos[0][1]])
                    if self.runners[1]: self.anim_runners.append([base_pos[1][0], base_pos[1][1], base_pos[1][0], base_pos[1][1]])
                    if self.runners[2]: self.anim_runners.append([base_pos[2][0], base_pos[2][1], base_pos[2][0], base_pos[2][1]])
                    
                    # バッターを追加
                    self.anim_runners.append([80, 100, 130, 60]) # バッター -> 1塁
                    
                    
                    pyxel.play(0, 0)
                else:
                    self.game_state = STATE_FOUL
                    self.message = "FOUL"
                    self.ball_vy = -2
                    self.ball_vx = -3 if self.ball_x < self.batter_x + 14 else 3
                    self.ball_vz = 1.0 # 低い弾道
        
        # キャッチャー到達（ストライク判定）
        if self.ball_y > 100:
            # ストライクゾーン判定（幅+/-8、高さ1.0~6.0）
            is_strike_x = abs(self.ball_x - SCREEN_WIDTH // 2) < 8
            is_strike_z = 1.0 < self.ball_z < 6.0

            if is_strike_x and is_strike_z:
                self.game_state = STATE_STRIKE
                self.message = "STRIKE!"
                self.strikes += 1
                # 3ストライクでアウト
                if self.strikes >= 3:
                    self.outs += 1
                    self.strikes = 0
                    self.balls = 0
                    self.message = "BATTER OUT!"
                    if self.outs >= 3:
                        self.message = "3 OUT CHANGE"
            else:
                self.game_state = STATE_BALL
                self.message = "BALL"
                self.balls += 1
                if self.balls >= 4:
                    self.handle_walk()

            # ボール・ストライク判定後、ピッチャーへの返球をセット
            if self.game_state in [STATE_BALL, STATE_STRIKE]:
                dx = (SCREEN_WIDTH // 2) - self.ball_x
                dy = 40 - self.ball_y
                self.ball_vx = dx / 20.0
                self.ball_vy = dy / 20.0
                self.ball_vz = 2.5 # 山なりに返球

    def handle_walk(self):
        self.game_state = STATE_WALK
        self.message = "WALK"
        self.balls = 0
        self.strikes = 0
        
        team = 1 if self.is_player_attack else 0
        
        # 押し出し処理
        if self.runners[0]:
            if self.runners[1]:
                if self.runners[2]:
                    self.scores[team] += 1
                else:
                    self.runners[2] = 1
            else:
                self.runners[1] = 1
        else:
            self.runners[0] = 1

    def register_out(self, msg):
        self.game_state = STATE_OUT
        self.message = msg
        self.outs += 1
        self.balls = 0
        self.strikes = 0
        if self.outs >= 3:
            self.message = "3 OUT CHANGE"
        pyxel.play(0, 1) # 捕球音(仮)

    def start_throw(self):
        self.game_state = STATE_THROW
        self.message = "THROWING"

        # Map base coordinates to the primary covering fielder index
        # NOTE: Using tuples for dictionary keys
        base_to_fielder_map = {
            (80, 100): 7, # Home -> Catcher
            (130, 60): 3, # 1B -> 1st Baseman
            (80, 20):  1, # 2B -> Shortstop (or 2B, index 2. SS is usually more athletic)
            (26, 60):  0  # 3B -> 3rd Baseman
        }

        target_base_coord = None
        # 送球先の決定 (ホーム > 3塁 > 2塁 > 1塁 の優先順位でフォースアウトを狙う)
        # ランナーがいない場合は、バッターランナーをアウトにするため1塁へ
        if self.runners[0] and self.runners[1] and self.runners[2]:
            target_base_coord = (80, 100) # 満塁: ホームへ
        elif self.runners[0] and self.runners[1]:
            target_base_coord = (26, 60) # 1,2塁: 3塁へ
        elif self.runners[0]:
            target_base_coord = (80, 20) # 1塁: 2塁へ
        else:
            # 上記以外の場合（ランナー無し、またはフォースでない状況）、バッターランナーをアウトにしに1塁へ
            target_base_coord = (130, 60)

        # 上のロジックで target_base_coord は必ず設定される
        covering_fielder_idx = base_to_fielder_map[target_base_coord]
        target_fielder_pos = self.fielders[covering_fielder_idx]
        self.throw_targets = [target_fielder_pos]
            
        self.next_throw()

    def next_throw(self):
        if not self.throw_targets:
            self.finalize_play()
            return

        target_x, target_y = self.throw_targets.pop(0)
        self.throw_target = [target_x, target_y]
        
        dx = target_x - self.ball_x
        dy = target_y - self.ball_y
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 0:
            speed = 4.0
            self.ball_vx = (dx / dist) * speed
            self.ball_vy = (dy / dist) * speed
            self.ball_vz = 1.0 
            pyxel.play(0, 1) # 送球音
            
    def finalize_play(self):
        self.game_state = STATE_HIT
        self.balls = 0
        self.strikes = 0
        self.result_timer = 0
        
        new_runners = [0, 0, 0]
        team = 1 if self.is_player_attack else 0
        
        for r in self.anim_runners:
            tx, ty = r[2], r[3]
            if tx == 130 and ty == 60: new_runners[0] = 1 # 1塁
            elif tx == 80 and ty == 20: new_runners[1] = 1 # 2塁
            elif tx == 26 and ty == 60: new_runners[2] = 1 # 3塁
            elif tx == 80 and ty == 100: self.scores[team] += 1 # ホーム
            
        self.runners = new_runners
        
        if self.message not in ["OUT!", "SAFE", "3 OUT CHANGE", "DOUBLE PLAY!"]:
            self.message = "HIT"
            pyxel.play(0, 0)

    def update_throw(self):
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy
        
        self.update_runners()
        self.update_fielders_movement()
        
        # 目標到達判定
        if self.throw_target:
            tx, ty = self.throw_target
            if abs(self.ball_x - tx) < 5 and abs(self.ball_y - ty) < 5:
                # 誰かがベースカバーに入っているか確認（ベースから10px以内）
                cover_ready = False
                if math.sqrt((self.pitcher_x - tx)**2 + (self.pitcher_y - ty)**2) < 10:
                    cover_ready = True
                else:
                    for f in self.fielders:
                        if math.sqrt((f[0] - tx)**2 + (f[1] - ty)**2) < 10:
                            cover_ready = True
                            break
                
                if cover_ready:
                    target_runner = None
                    for r in self.anim_runners:
                        if r[2] == tx and r[3] == ty:
                            target_runner = r
                            break
                    
                    if target_runner:
                        rx, ry = target_runner[0], target_runner[1]
                        dist_runner = math.sqrt((rx - tx)**2 + (ry - ty)**2)
                        if dist_runner < 15:
                            self.message = "SAFE"
                        else:
                            self.outs += 1
                            self.play_outs += 1
                            if self.play_outs == 2:
                                self.message = "DOUBLE PLAY!"
                            else:
                                self.message = "OUT!"
                            self.anim_runners.remove(target_runner)
                            pyxel.play(0, 1)
                            
                    if self.outs >= 3:
                        self.message = "3 OUT CHANGE"
                        self.throw_targets = []
                        self.finalize_play()
                        return
                        
                    # 連続送球をせず、一度でプレイを完了させる
                    self.throw_targets = []
                    self.finalize_play()
                else:
                    # ベースカバーが間に合っていない場合、ボールを止めて待つ
                    self.ball_x = tx
                    self.ball_y = ty
                    self.ball_vx = 0
                    self.ball_vy = 0

    def update_runners(self):
        for r in self.anim_runners:
            dx = r[2] - r[0]
            dy = r[3] - r[1]
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 1:
                speed = 1.5
                r[0] += (dx / dist) * speed
                r[1] += (dy / dist) * speed
                
    def update_fielders_movement(self):
        f_dists = []
        for i, f in enumerate(self.fielders):
            d_sq = (f[0] - self.ball_x)**2 + (f[1] - self.ball_y)**2
            
            # 内野手 (index 0-3) が外野 (y < 20) のボールを追う場合にペナルティ
            is_infielder = 0 <= i <= 3
            is_ball_in_outfield = self.ball_y < 20
            
            if is_infielder and is_ball_in_outfield:
                d_sq *= 2.0 # 距離の2乗にペナルティ
                
            f_dists.append((d_sq, i))
        
        f_dists.sort()
        catcher_idx = f_dists[0][1]

        # ヒット状態なら、送球が始まるまでボールを追い続ける
        if self.game_state == STATE_HIT:
            fielder = self.fielders[catcher_idx]
            dx = self.ball_x - fielder[0]
            dy = self.ball_y - fielder[1]
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 0:
                speed = 1.2 if dist > 1.2 else dist
                fielder[0] += (dx / dist) * speed
                fielder[1] += (dy / dist) * speed

            # 捕球判定
            if dist < 6 and self.ball_z < 10:
                pyxel.play(0, 1)
                if self.is_grounder: self.start_throw()
                else: self.check_tag_up()
                return

        # ベースカバーと帰塁のロジック
        cover_targets = {
            0: (26, 60),  # 3B -> 3塁
            1: (80, 20),  # SS -> 2塁
            2: (80, 20),  # 2B -> 2塁
            3: (130, 60), # 1B -> 1塁
            7: (80, 100), # C -> ホーム
        }
        for i, f in enumerate(self.fielders):
            if i == catcher_idx and self.game_state == STATE_HIT: continue
            
            target_pos = None
            if i in cover_targets:
                target_pos = cover_targets[i]
            # ベースカバー担当でない野手（主に外野手）は定位置に戻る
            elif hasattr(self, 'fielders_initial_pos'):
                target_pos = self.fielders_initial_pos[i]

            if target_pos:
                tx, ty = target_pos
                cdx = tx - f[0]
                cdy = ty - f[1]
                cdist = math.sqrt(cdx*cdx + cdy*cdy)
                if cdist > 1: # 完全に止まるように閾値を設定
                    speed = 0.8 if cdist > 0.8 else cdist
                    f[0] += (cdx / cdist) * speed
                    f[1] += (cdy / cdist) * speed
        
        # ピッチャーのカバーリング
        if self.throw_target: 
            ptx, pty = self.throw_target
        else: 
            if self.runners[0] and self.runners[1] and self.runners[2]:
                ptx, pty = 80, 100 # 満塁ならホーム
            elif self.runners[0] and self.runners[1]:
                ptx, pty = 26, 60  # 1,2塁なら3塁
            elif self.runners[1]:
                ptx, pty = 26, 60  # 2塁がいれば3塁
            else:
                ptx, pty = 130, 60 # それ以外は1塁
                
        pdx, pdy = ptx - self.pitcher_x, pty - self.pitcher_y
        pdist = math.sqrt(pdx*pdx + pdy*pdy)
        if pdist > 0:
            speed = 0.9 if pdist > 0.9 else pdist
            self.pitcher_x += (pdx / pdist) * speed
            self.pitcher_y += (pdy / pdist) * speed

    def check_tag_up(self):
        self.outs += 1
        self.balls = 0
        self.strikes = 0
        self.anim_runners = []
        
        if self.outs >= 3:
            self.game_state = STATE_OUT
            self.message = "3 OUT CHANGE"
            return

        # タッチアップ判定 (3塁ランナーのみ)
        dist_home = math.sqrt((self.ball_x - 80)**2 + (self.ball_y - 100)**2)
        
        if self.runners[2] and dist_home > 60:
            team = 1 if self.is_player_attack else 0
            self.scores[team] += 1
            self.runners[2] = 0
            self.game_state = STATE_OUT
            self.message = "SACRIFICE FLY"
        else:
            self.game_state = STATE_OUT
            self.message = "OUT!"

    def advance_runners_manual(self):
        base_coords = {
            0: (130, 60), # 1B
            1: (80, 20),  # 2B
            2: (26, 60),  # 3B
            3: (80, 100)  # Home
        }
        coords_to_base = { (130, 60): 0, (80, 20): 1, (26, 60): 2, (80, 100): 3 }

        for runner in self.anim_runners:
            dest_coord = (runner[2], runner[3])
            
            if dest_coord in coords_to_base:
                dest_base_idx = coords_to_base[dest_coord]

                dist_to_dest = math.sqrt((runner[0] - dest_coord[0])**2 + (runner[1] - dest_coord[1])**2)

                if dist_to_dest < 1.5:
                    if dest_base_idx < 3:
                        next_base_idx = dest_base_idx + 1
                        new_dest_coord = base_coords[next_base_idx]
                        
                        runner[2] = new_dest_coord[0]
                        runner[3] = new_dest_coord[1]

    def update_result(self):
        # ヒット時はボールを飛ばす
        if self.game_state in [STATE_HIT, STATE_FOUL, STATE_HOMERUN]:
            # カメラスクロール（ボールを追いかける）
            target_scroll = self.ball_y - SCREEN_HEIGHT * 0.6
            if target_scroll > 0: target_scroll = 0
            if target_scroll < FENCE_Y - 20: target_scroll = FENCE_Y - 20
            self.scroll_y += (target_scroll - self.scroll_y) * 0.1

        if self.game_state in [STATE_HIT, STATE_FOUL]:
            self.ball_x += self.ball_vx
            self.ball_y += self.ball_vy
            
            # 高さの処理（重力）
            self.ball_z += self.ball_vz
            self.ball_vz -= 0.15
            
            # フェンス判定（扇形）
            dist_home = math.sqrt((self.ball_x - 80)**2 + (self.ball_y - 100)**2)
            if dist_home > FENCE_R:
                if self.ball_z > 8:
                    # フェンス越え（ホームラン確定待ち）
                    pass 
                else:
                    # フェンス直撃（曲面反射）
                    # 法線ベクトル（中心からボールへの向き）
                    nx = (self.ball_x - 80) / dist_home
                    ny = (self.ball_y - 100) / dist_home
                    # 反射ベクトル計算: V = V - 2(V.N)N
                    dot = self.ball_vx * nx + self.ball_vy * ny
                    self.ball_vx = (self.ball_vx - 2 * dot * nx) * 0.5
                    self.ball_vy = (self.ball_vy - 2 * dot * ny) * 0.5
                    # 押し戻し
                    self.ball_x = 80 + nx * (FENCE_R - 1)
                    self.ball_y = 100 + ny * (FENCE_R - 1)
                    pyxel.play(2, 2)

            # バウンド時のファウル判定
            if self.ball_z < 0 and self.game_state == STATE_HIT and self.message == "":
                # ホーム(80, 100)からの広がりで判定
                # 1塁(130, 60)を通るライン -> dx=50, dy=40 -> ratio=1.25
                dy = 100 - self.ball_y
                limit_w = dy * 1.25
                if self.ball_x < 80 - limit_w or self.ball_x > 80 + limit_w:
                    self.game_state = STATE_FOUL
                    self.message = "FOUL"
                    self.ball_vx *= 0.5
                    self.ball_vy *= 0.5
                    pyxel.play(2, 2)

            # バウンド処理
            if self.ball_z < 0:
                if self.ball_vz < -1.0:
                    pyxel.play(1, 2)
                self.ball_z = 0
                self.ball_vz = -self.ball_vz * 0.2 # 跳ね返り
                self.ball_vx *= 0.9 # 地面摩擦
                self.is_grounder = True

        # 返球アニメーション
        if self.game_state in [STATE_BALL, STATE_STRIKE]:
            self.ball_x += self.ball_vx
            self.ball_y += self.ball_vy
            self.ball_z += self.ball_vz
            self.ball_vz -= 0.15 # 重力
            
            if self.ball_z < 0:
                self.ball_z = 0
                self.ball_vz = -self.ball_vz * 0.13
                
            if self.ball_y <= 40: # ピッチャーに到達
                self.ball_y = 40
                self.ball_x = SCREEN_WIDTH // 2
                self.ball_vx = 0
                self.ball_vy = 0
                self.ball_z = 0
                self.ball_vz = 0

        if self.game_state == STATE_HIT:
            if pyxel.btnp(pyxel.KEY_A):
                self.advance_runners_manual()
            self.update_runners()

        # ヒット中（未確定）の場合の処理
        if self.game_state == STATE_HIT:
            self.update_fielders_movement()

            # ホームラン判定（フェンス越えで一定距離または画面外）
            dist_home = math.sqrt((self.ball_x - 80)**2 + (self.ball_y - 100)**2)
            if (dist_home > FENCE_R + 30 and self.ball_z > 0):
                self.game_state = STATE_HOMERUN
                self.message = "HOMERUN!"
                team = 1 if self.is_player_attack else 0
                self.scores[team] += sum(self.runners) + 1
                self.runners = [0, 0, 0]
                self.balls = 0
                self.strikes = 0
                pyxel.play(0, 0)

        # ヒット（シングル）判定：ボールがまだ画面内にあり、捕球もされていない状態で時間が経った
        if self.game_state == STATE_HIT and self.message == "":
             self.result_timer += 1
             if self.result_timer > 60:
                 self.finalize_play()

        # 結果が出ている場合、リセットタイマーを進める
        if self.message != "":
            self.result_timer += 1
            wait_time = 45 if self.game_state in [STATE_BALL, STATE_STRIKE] else 90
            if self.result_timer > wait_time: # 待ってリセット
                self.advance_batter_if_needed()
                if self.outs >= 3:
                    self.game_state = STATE_CHANGE
                    self.change_timer = 0
                    self.message = ""
                else:
                    self.reset_game()

    def advance_batter_if_needed(self):
        finished_messages = [
            "HIT", "HOMERUN!", "BATTER OUT!", "OUT!", "SAFE",
            "DOUBLE PLAY!", "WALK", "SACRIFICE FLY", "3 OUT CHANGE"
        ]
        if self.message in finished_messages:
            team_idx = 1 if self.is_player_attack else 0
            self.current_batter[team_idx] = (self.current_batter[team_idx] + 1) % 9

    def update_change(self):
        self.change_timer += 1
        if self.change_timer > 60: # 1秒間演出
            # チェンジ処理
            self.is_player_attack = not self.is_player_attack
            self.outs = 0
            self.runners = [0, 0, 0]
            self.balls = 0
            self.strikes = 0
            
            if self.is_top:
                self.is_top = False
            else:
                self.is_top = True
                self.inning += 1
            
            if self.inning > 9:
                self.game_state = STATE_GAMEOVER
                self.message = "GAME SET"
            else:
                self.reset_game()

    def update_gameover(self):
        # スペースキーでリスタート
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.restart_game()

    def draw(self):
        pyxel.cls(COLOR_GRASS)
        
        # カメラ適用
        pyxel.camera(0, self.scroll_y)

        # フィールド描画
        self.draw_field()
        
        # ランナー描画（フィールド上）
        self.draw_field_runners()

        if self.game_state == STATE_TITLE:
            pass # タイトルでも背景としてフィールドを描画し、後で文字を重ねる

        # ピッチャー描画
        pyxel.rect(self.pitcher_x - 4, self.pitcher_y - 5, 8, 8, COLOR_PITCHER) # 体
        pyxel.rect(self.pitcher_x - 1, self.pitcher_y - 7, 2, 2, 0) # 帽子

        # 守備選手描画
        for f in self.fielders:
            pyxel.rect(f[0], f[1], 8, 8, COLOR_FIELDER)
            pyxel.rect(f[0]+2, f[1]-2, 4, 2, 0) # 帽子

        # バッター描画
        self.draw_batter()

        # ボール描画
        if self.ball_z > 0:
            # 高低差を明確にするため、低い位置では影を大きくする
            shadow_r = 2 if self.ball_z < 10 else 1
            pyxel.circ(self.ball_x, self.ball_y, shadow_r, COLOR_SHADOW) # 影
        
        pyxel.circ(self.ball_x, self.ball_y - self.ball_z, 2, COLOR_WHITE) # 本体

        # カメラリセット（UI描画のため）
        pyxel.camera()

        if self.game_state == STATE_TITLE:
            self.draw_title()
            return

        # UI描画
        score_str = f"CPU:{self.scores[0]} PLY:{self.scores[1]}"
        pyxel.text(5, 5, score_str, 7)
        pyxel.text(5, 12, f"B:{self.balls} S:{self.strikes} O:{self.outs}", 7)
        
        # イニング表示
        tb = "^" if self.is_top else "v"
        pyxel.text(130, 5, f"{self.inning}{tb}", 7)
        
        # バッター情報表示
        team_idx = 1 if self.is_player_attack else 0
        b_idx = self.current_batter[team_idx]
        batter = self.team_batters[team_idx][b_idx]
        avg_str = f".{int(batter['avg'] * 1000):03d}"
        pyxel.text(110, 12, f"BAT:{b_idx+1} {avg_str}", 10)
        
        p_idx = 0 if self.is_player_attack else 1
        stamina = self.current_stamina[p_idx]
        pyxel.text(70, 12, f"STM:{stamina}", 8 if stamina < 10 else 7)
        
        # ランナー表示
        self.draw_runners_ui()
        
        if self.game_state == STATE_CHANGE:
             # 攻守交代アニメーション
             pyxel.rect(0, 50, SCREEN_WIDTH, 20, 0)
             msg = "CHANGE"
             color = 7 if (pyxel.frame_count // 4) % 2 == 0 else 10
             pyxel.text(SCREEN_WIDTH // 2 - len(msg) * 2, 57, msg, color)

        if self.message != "":
             pyxel.text(SCREEN_WIDTH // 2 - len(self.message)*2, 60, self.message, 7)

        if self.game_state == STATE_GAMEOVER:
            pyxel.text(40, 80, "PRESS SPACE TO RESTART", pyxel.frame_count % 16)
        elif self.game_state == STATE_WAIT:
             pyxel.text(50, 100, "PRESS SPACE TO PITCH", 1)

    def draw_field_runners(self):
        # プレイ中のランナー
        if self.anim_runners:
            for r in self.anim_runners:
                pyxel.rect(r[0], r[1], 6, 8, COLOR_BATTER)
        # 待機中のランナー（塁上に表示）
        elif self.game_state in [STATE_WAIT, STATE_PITCHING, STATE_THROW]:
            base_pos = [[130, 60], [80, 20], [26, 60]] # 1塁, 2塁, 3塁
            for i, has_runner in enumerate(self.runners):
                if has_runner:
                    bx, by = base_pos[i]
                    pyxel.rect(bx, by, 6, 8, COLOR_BATTER)

    def draw_runners_ui(self):
        # 塁のダイヤモンド表示 (基準点 20, 25)
        base_color = [7, 8] # 白、赤
        # 2塁, 1塁, 3塁 の順で描画（頂点）
        pyxel.circ(20, 21, 1, base_color[self.runners[1]]) # 2nd
        pyxel.circ(24, 25, 1, base_color[self.runners[0]]) # 1st
        pyxel.circ(16, 25, 1, base_color[self.runners[2]]) # 3rd

    def draw_field(self):
        # マウンド
        pyxel.circ(SCREEN_WIDTH // 2, 40, 10, COLOR_DIRT)
        # ホームベース付近
        pyxel.circ(SCREEN_WIDTH // 2, 100, 15, COLOR_DIRT)
        pyxel.rect(SCREEN_WIDTH // 2 - 4, 100, 8, 4, COLOR_WHITE) # ホームベース
        # ファウルライン（外野まで拡張）
        # 左: (80, 100) -> (-120, -60)
        pyxel.line(80, 100, -120, FENCE_Y, COLOR_WHITE)
        # 右: (80, 100) -> (280, -60)
        pyxel.line(80, 100, 280, FENCE_Y, COLOR_WHITE)
        # 1塁ベース
        pyxel.rect(130, 60, 4, 4, COLOR_WHITE)
        # 3塁ベース
        pyxel.rect(26, 60, 4, 4, COLOR_WHITE)

        # 外野フェンス（扇形）
        # 中心(80, 100), 半径160
        for r in range(FENCE_R, FENCE_R + 10):
            pyxel.circb(80, 100, r, 6) # フェンス本体（太線）
        pyxel.circb(80, 100, FENCE_R, 7) # フェンスライン（白）

    def draw_title(self):
        s = "FAMISTA STYLE BASEBALL"
        pyxel.text(SCREEN_WIDTH // 2 - len(s) * 2, 40, s, 7)
        if pyxel.frame_count % 30 < 15:
            s = "PRESS SPACE TO START"
            pyxel.text(SCREEN_WIDTH // 2 - len(s) * 2, 80, s, 7)

    def draw_batter(self):
        if self.game_state in [STATE_HIT, STATE_THROW, STATE_HOMERUN, STATE_OUT]: return

        color = COLOR_BATTER
        bx, by = self.batter_x, self.batter_y
        
        # アイドルアニメーション（上下に揺れる）
        idle_offset = (pyxel.frame_count // 15) % 2
        if not self.is_swinging:
            by += idle_offset

        # 体
        pyxel.rect(bx, by, 6, 10, color)
        # 頭
        pyxel.rect(bx+1, by-3, 4, 3, 0)
        
        # バット
        if self.is_swinging:
            # スイングアニメーション
            if self.swing_frame >= 4:
                # 振り始め（斜め上）
                pyxel.line(bx + 6, by + 2, bx + 12, by - 4, 4)
                pyxel.line(bx + 5, by + 2, bx + 11, by - 4, 4)
            elif self.swing_frame >= 2:
                # インパクト（水平）
                pyxel.rect(bx + 6, by + 2, 12, 3, 4) # 茶色のバット
            else:
                # フォロースルー（斜め下）
                pyxel.line(bx + 6, by + 2, bx + 12, by + 8, 4)
                pyxel.line(bx + 5, by + 2, bx + 11, by + 8, 4)
        else:
            # 構え（縦向き）
            pyxel.rect(bx + 4, by - 4, 2, 8, 4)

App()
