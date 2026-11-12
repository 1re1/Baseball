# -*- coding: utf-8 -*-
"""チームと選手（すべて架空）。成績は乱数（種を固定）で作る"""
import random

# 名前, 略号, 主色(RGB 0-7), ユニフォーム色, 打撃の型, 投手の型
TEAMS = [
    ("ドルフィンズ", "DOL", (1, 2, 6), (7, 7, 7), "avg", "fast"),
    ("ファルコンズ", "FAL", (6, 0, 0), (7, 7, 7), "power", "even"),
    ("サンダース",   "THU", (7, 5, 0), (2, 2, 2), "power", "slow"),
    ("コメッツ",     "COM", (0, 1, 4), (5, 6, 7), "speed", "even"),
    ("ウルブズ",     "WOL", (2, 2, 2), (6, 6, 6), "even", "fast"),
    ("ロケッツ",     "ROC", (7, 3, 0), (7, 7, 5), "power", "even"),
    ("シャークス",   "SHA", (0, 4, 4), (7, 7, 7), "speed", "slow"),
    ("スターズ",     "STA", (5, 1, 6), (7, 7, 2), "star", "star"),
]

SURNAMES = """ヤマダ タナカ スズキ サトウ タカハシ イトウ ワタナベ ナカムラ コバヤシ カトウ ヨシダ ヤマモト
イノウエ キムラ ハヤシ シミズ ヤマグチ モリ アベ イケダ ハシモト ヤマシタ イシカワ ナカジマ マエダ フジタ
オガワ ゴトウ オカダ ハセガワ ムラカミ コンドウ イシイ サイトウ サカモト エンドウ アオキ フジイ ニシムラ
フクダ オオタ ミウラ フジワラ オカモト マツダ ナカガワ ナカノ ハラダ オノ タムラ タケウチ カネコ ワダ
ナカヤマ イシダ ウエダ モリタ ハラ シバタ サカイ クドウ ヨコヤマ ミヤザキ ミヤモト ウチダ タカギ アンドウ
タニグチ オオノ マルヤマ イマイ タカダ フジモト タケダ ムラタ ウエノ スギヤマ マスダ ヒラノ オオツカ チバ
クボ マツイ イワサキ サクライ キノシタ ノグチ マツオ キクチ ノムラ アライ ソノダ ホンダ カワグチ スガ
ミズノ ヒラタ コジマ ツジ オオシマ アキヤマ ヨシカワ ヤノ ミヤタ カワカミ ヒロセ ツチヤ ナガイ セキ""".split()

POS = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]


def make_teams(seed=1986):
    rnd = random.Random(seed)
    pool = SURNAMES[:]
    rnd.shuffle(pool)
    out = []
    pi = 0
    for name, abbr, pc, uc, bstyle, pstyle in TEAMS:
        batters = []
        for i in range(12):           # 8 人 + 控え 4 人
            nm = pool[pi % len(pool)]
            pi += 1
            star = bstyle == "star"
            core = i in (2, 3, 4)       # クリーンアップ
            avg = rnd.randint(235, 300) + (25 if core else 0) + (20 if star else 0)
            if i >= 8:
                avg -= 20
            pw = rnd.randint(2, 5) + (3 if core else 0) + (1 if bstyle == "power" else 0) + (2 if star else 0)
            if i in (0, 1):
                pw = max(1, pw - 2)
            sp = rnd.randint(3, 7) + (2 if i in (0, 1) else 0) + (1 if bstyle == "speed" else 0) - (1 if core else 0)
            hr = max(0, pw * pw // 2 + rnd.randint(-3, 4))
            lefty = rnd.random() < 0.35
            batters.append(dict(name=nm, avg=min(avg, 380), pow=max(1, min(9, pw)), spd=max(1, min(9, sp)),
                                hr=min(hr, 60), left=lefty))
        pitchers = []
        for i in range(5):
            nm = pool[pi % len(pool)]
            pi += 1
            base = {"fast": 146, "even": 142, "slow": 138, "star": 150}[pstyle]
            kmh = base + rnd.randint(-4, 6) - (3 if i else 0)
            cv = rnd.randint(3, 7) + (2 if pstyle == "slow" else 0) + (1 if pstyle == "star" else 0)
            st = rnd.randint(6, 9) if i == 0 else rnd.randint(2, 5)
            era = rnd.randint(18, 42)
            pitchers.append(dict(name=nm, kmh=min(kmh, 158), cv=max(1, min(9, cv)), st=st, era=era,
                                 left=rnd.random() < 0.3))
        out.append(dict(name=name, abbr=abbr, pc=pc, uc=uc, batters=batters, pitchers=pitchers))
    return out
