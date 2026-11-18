import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import random

# --- ページ設定 ---
st.set_page_config(page_title="魔改造チェス オンライン", page_icon="♟️", layout="wide")

# --- Googleスプレッドシート接続（ユーザーシート＆対戦ロビーシート） ---
@st.cache_resource
def get_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(st.secrets["spreadsheet_url"])
    user_sheet = spreadsheet.sheet1
    
    # 2枚目のシート「battles」がなければ自動作成
    try:
        battle_sheet = spreadsheet.worksheet("battles")
    except gspread.WorksheetNotFound:
        battle_sheet = spreadsheet.add_worksheet(title="battles", rows=100, cols=10)
        battle_sheet.append_row(["room_id", "p1", "p2", "turn", "board", "status", "winner"])
    return user_sheet, battle_sheet

# --- 全キャラクターマスタデータ（初期6種 + ガチャ32体） ---
CHARACTERS = {
    # 初期デッキ（ゴールドリアル）
    "GR_P": {"name": "ゴールド・ポーン", "rarity": "初期", "gender": "無", "piece": "ポーン", "icon": "♙", "hp": 100, "atk": 30, "skill": "基本の歩兵。前方に進む。"},
    "GR_R": {"name": "ゴールド・ルーク", "rarity": "初期", "gender": "無", "piece": "ルーク", "icon": "♖", "hp": 180, "atk": 50, "skill": "縦横に直線移動。"},
    "GR_N": {"name": "ゴールド・ナイト", "rarity": "初期", "gender": "無", "piece": "ナイト", "icon": "♘", "hp": 140, "atk": 45, "skill": "トリッキーな跳躍攻撃。"},
    "GR_B": {"name": "ゴールド・ビショップ", "rarity": "初期", "gender": "無", "piece": "ビショップ", "icon": "♗", "hp": 130, "atk": 45, "skill": "斜めラインからの攻撃。"},
    "GR_Q": {"name": "ゴールド・クイーン", "rarity": "初期", "gender": "無", "piece": "クイーン", "icon": "♕", "hp": 200, "atk": 70, "skill": "縦横斜め全方位の万能駒。"},
    "GR_K": {"name": "ゴールド・キング", "rarity": "初期", "gender": "無", "piece": "キング", "icon": "♔", "hp": 250, "atk": 40, "skill": "【キング枠】倒されると敗北。"},

    # コモン（9体）
    "C01": {"name": "見習い鉄砲足軽", "rarity": "コモン", "gender": "男", "piece": "ポーン", "icon": "🔫", "hp": 90, "atk": 35, "skill": "【ジャイアントキリング】相手がレジェンダリー以上なら2回攻撃。"},
    "C02": {"name": "路地裏のスリ少女", "rarity": "コモン", "gender": "女", "piece": "ポーン", "icon": "🗡️", "hp": 85, "atk": 30, "skill": "相手のスキルクールタイムを+2ターン延長。"},
    "C03": {"name": "量産型お掃除ロボ", "rarity": "コモン", "gender": "男", "piece": "ポーン", "icon": "🤖", "hp": 110, "atk": 25, "skill": "倒されるとオイル溜まりを残し敵を1ターン行動不能に。"},
    "C04": {"name": "爆弾魔の妹分", "rarity": "コモン", "gender": "女", "piece": "ポーン", "icon": "💣", "hp": 80, "atk": 40, "skill": "【道連れ】エピック以上に倒されると相打ちにする。"},
    "C05": {"name": "宅配バイク便の兄ちゃん", "rarity": "コモン", "gender": "男", "piece": "ナイト", "icon": "🛵", "hp": 120, "atk": 40, "skill": "1ターンに2回連続移動が可能。"},
    "C06": {"name": "保健室の養護教諭", "rarity": "コモン", "gender": "女", "piece": "ビショップ", "icon": "💉", "hp": 130, "atk": 25, "skill": "ターン終了時、隣接する味方コモン・アンコモンを全回復。"},
    "C07": {"name": "工事現場のバリケード男", "rarity": "コモン", "gender": "男", "piece": "ルーク", "icon": "🚧", "hp": 260, "atk": 10, "skill": "攻撃できないが超耐久で高レアの突進を止める壁役。"},
    "C08": {"name": "占いカフェのバイト娘", "rarity": "コモン", "gender": "女", "piece": "ビショップ", "icon": "🔮", "hp": 110, "atk": 35, "skill": "相手の次の行動を1つ封じる。"},
    "C09": {"name": "悪の組織の下っぱ女", "rarity": "コモン", "gender": "女", "piece": "ポーン", "icon": "🦹‍♀️", "hp": 95, "atk": 35, "skill": "【団結の作戦】味方コモンが4体以上いると攻撃力3倍＆装甲貫通。"},

    # アンコモン（5体）
    "U01": {"name": "忍者ハンゾウ", "rarity": "アンコモン", "gender": "男", "piece": "ナイト", "icon": "🥷", "hp": 135, "atk": 55, "skill": "【変わり身】攻撃された時1度だけ味方コモンと入れ替わり回避。"},
    "U02": {"name": "サイバーハッカー・ミカ", "rarity": "アンコモン", "gender": "女", "piece": "ビショップ", "icon": "💻", "hp": 125, "atk": 50, "skill": "機械・現代系キャラを1ターン自分の駒として操る。"},
    "U03": {"name": "マグマ料理長", "rarity": "アンコモン", "gender": "男", "piece": "ルーク", "icon": "🍳", "hp": 170, "atk": 55, "skill": "通った跡を3ターン炎上床にし高レアの進軍を塞ぐ。"},
    "U04": {"name": "スケボー女子高生", "rarity": "アンコモン", "gender": "女", "piece": "ナイト", "icon": "🛹", "hp": 130, "atk": 50, "skill": "味方を飛び越えるたび攻撃力UP。3体飛び越えるとミシックも一撃。"},
    "U05": {"name": "カレー好き少女", "rarity": "アンコモン", "gender": "女", "piece": "ポーン", "icon": "🍛", "hp": 115, "atk": 45, "skill": "【激辛スパイス】相手を3ターン激辛状態（毎ターンHP減少＋混乱）に。"},

    # レア（4体）
    "R01": {"name": "蒸気機関の重装騎士", "rarity": "レア", "gender": "男", "piece": "ルーク", "icon": "🚂", "hp": 210, "atk": 65, "skill": "直線上の敵を吹き飛ばし、盤面端にぶつけると即死ダメージ。"},
    "R02": {"name": "雪原の狙撃手・レイナ", "rarity": "レア", "gender": "女", "piece": "ビショップ", "icon": "❄️", "hp": 150, "atk": 75, "skill": "斜め一直線上のどこからでも移動せず遠距離狙撃。"},
    "R03": {"name": "陰陽師・アベノ", "rarity": "レア", "gender": "男", "piece": "ビショップ", "icon": "☯️", "hp": 160, "atk": 60, "skill": "倒された味方コモンを式神として自分の隣に復活させる。"},
    "R04": {"name": "重力の魔女・ノア", "rarity": "レア", "gender": "女", "piece": "クイーン", "icon": "🌌", "hp": 185, "atk": 70, "skill": "周囲2マスの敵を引き寄せ、移動スキルを封じる。"},

    # エピック（8体）
    "E01": {"name": "剣豪・ムサシ", "rarity": "エピック", "gender": "男", "piece": "ナイト", "icon": "⚔️", "hp": 200, "atk": 90, "skill": "周囲1マスの敵を同時に薙ぎ払う（遠距離攻撃に弱い）。"},
    "E02": {"name": "吸血姫・カーミラ", "rarity": "エピック", "gender": "女", "piece": "クイーン", "icon": "🧛‍♀️", "hp": 210, "atk": 85, "skill": "敵を倒すたびに最大HPと攻撃力を吸収して強化。"},
    "E03": {"name": "軌道衛星レーザー艦", "rarity": "エピック", "gender": "男", "piece": "ルーク", "icon": "🛰️", "hp": 240, "atk": 110, "skill": "2ターンチャージ後、縦1列を敵味方問わず消滅。"},
    "E04": {"name": "時空の踊り子・ルナ", "rarity": "エピック", "gender": "女", "piece": "ビショップ", "icon": "⏳", "hp": 175, "atk": 65, "skill": "味方1体をもう1回行動させる。"},
    "E05": {"name": "深海のクラーケン使い", "rarity": "エピック", "gender": "男", "piece": "ルーク", "icon": "🐙", "hp": 230, "atk": 80, "skill": "盤面の半分を水没させ、移動範囲をクイーン並みに拡大。"},
    "E06": {"name": "AIアイドル・ステラ", "rarity": "エピック", "gender": "女", "piece": "クイーン", "icon": "🎤", "hp": 195, "atk": 75, "skill": "周囲2マスの敵を魅了し1ターン攻撃不能にする。"},
    "E07": {"name": "煉獄のバーサーカー", "rarity": "エピック", "gender": "男", "piece": "ナイト", "icon": "🔥", "hp": 220, "atk": 95, "skill": "HPが減るほど攻撃力激増（味方も攻撃範囲に入ると殴る）。"},
    "E08": {"name": "死霊術師・ヘレナ", "rarity": "エピック", "gender": "女", "piece": "キング", "icon": "💀", "hp": 280, "atk": 60, "skill": "【キング枠】倒されても味方コモンがいれば魂を移して生存！"},

    # レジェンダリー（4体）
    "L01": {"name": "雷帝・ゼウス", "rarity": "レジェンダリー", "gender": "男", "piece": "キング", "icon": "⚡", "hp": 320, "atk": 85, "skill": "【キング枠】3ターンに1度、ランダムな敵2体に落雷ダメージ。"},
    "L02": {"name": "星屑の戦乙女・ヴァルキリー", "rarity": "レジェンダリー", "gender": "女", "piece": "クイーン", "icon": "🪽", "hp": 270, "atk": 115, "skill": "全方位移動＆攻撃。味方が4体以下で真の力を発揮。"},
    "L03": {"name": "機甲神・オメガ", "rarity": "レジェンダリー", "gender": "男", "piece": "ルーク", "icon": "🦾", "hp": 380, "atk": 100, "skill": "全攻撃を半減する超装甲（ただし1マスずつしか動けない）。"},
    "L04": {"name": "九尾の狐・タマモ", "rarity": "レジェンダリー", "gender": "女", "piece": "クイーン", "icon": "🦊", "hp": 260, "atk": 105, "skill": "分身を2体作り出す（本体を倒されない限り復活）。"},

    # ミシック（2体）
    "M01": {"name": "終焉の魔王・アビス", "rarity": "ミシック", "gender": "男", "piece": "クイーン", "icon": "👿", "hp": 340, "atk": 140, "skill": "【黒の覇王】移動先周囲を即死させる（移動後1ターン硬直）。"},
    "M02": {"name": "創世の女神・アテナ", "rarity": "ミシック", "gender": "女", "piece": "キング", "icon": "👑", "hp": 360, "atk": 0, "skill": "【キング枠】味方全体強化＆1度だけ致命傷無効（自身は攻撃不可）。"}
}

RARITY_COLORS = {
    "初期": "🟫", "コモン": "⚪", "アンコモン": "🟢",
    "レア": "🔵", "エピック": "🟣", "レジェンダリー": "🟡", "ミシック": "🌈"
}

DEFAULT_DECK = [
    "GR_K", "GR_Q", "GR_R", "GR_R", "GR_B", "GR_B", "GR_N", "GR_N",
    "GR_P", "GR_P", "GR_P", "GR_P", "GR_P", "GR_P", "GR_P", "GR_P"
]

# --- ユーザーデータ読み書き ---
def load_user(username, password=None):
    user_sheet, _ = get_sheets()
    records = user_sheet.get_all_records()
    for idx, row in enumerate(records, start=2):
        if str(row["username"]) == username:
            if password is None or str(row["password"]) == password:
                return idx, {
                    "username": username,
                    "password": str(row["password"]),
                    "coins": int(row["coins"]),
                    "items": json.loads(row["items"]) if row["items"] else {"exp_book": 5},
                    "units": json.loads(row["units"]) if row["units"] else {},
                    "deck": json.loads(row["deck"]) if row["deck"] else DEFAULT_DECK.copy(),
                    "quests": json.loads(row["quests"]) if row["quests"] else {"wins": 0, "gacha": 0}
                }
            else:
                return -1, None
    return None, None

def get_all_usernames():
    user_sheet, _ = get_sheets()
    records = user_sheet.get_all_records()
    return [str(r["username"]) for r in records if r.get("username")]

def create_user(username, password):
    user_sheet, _ = get_sheets()
    init_units = {
        "GR_K": {"count": 1, "lv": 1}, "GR_Q": {"count": 1, "lv": 1},
        "GR_R": {"count": 2, "lv": 1}, "GR_B": {"count": 2, "lv": 1},
        "GR_N": {"count": 2, "lv": 1}, "GR_P": {"count": 8, "lv": 1}
    }
    new_row = [
        username, password, 1000,
        json.dumps({"exp_book": 10}), json.dumps(init_units),
        json.dumps(DEFAULT_DECK), json.dumps({"wins": 0, "gacha": 0})
    ]
    user_sheet.append_row(new_row)
    return load_user(username, password)

def save_user():
    if "row_idx" in st.session_state and "user" in st.session_state:
        user_sheet, _ = get_sheets()
        u = st.session_state.user
        row = st.session_state.row_idx
        user_sheet.update(f"C{row}:G{row}", [[
            u["coins"], json.dumps(u["items"]), json.dumps(u["units"]),
            json.dumps(u["deck"]), json.dumps(u["quests"])
        ]])

def get_stats(cid, lv):
    base = CHARACTERS[cid]
    mult = 1 + (lv - 1) * 0.08
    return int(base["hp"] * mult), int(base["atk"] * mult)

# --- 8x8盤面初期化ヘルパー ---
def init_board(p1_deck, p1_units, p2_deck, p2_units):
    board = [[None for _ in range(8)] for _ in range(8)]
    # P2（上側: 0行目=主力8体, 1行目=前衛8体）
    for c in range(8):
        cid0 = p2_deck[c]
        hp0, atk0 = get_stats(cid0, p2_units.get(cid0, {"lv": 1})["lv"])
        board[0][c] = {"owner": "P2", "cid": cid0, "hp": hp0, "max_hp": hp0, "atk": atk0}
        
        cid1 = p2_deck[8 + c]
        hp1, atk1 = get_stats(cid1, p2_units.get(cid1, {"lv": 1})["lv"])
        board[1][c] = {"owner": "P2", "cid": cid1, "hp": hp1, "max_hp": hp1, "atk": atk1}

    # P1（下側: 7行目=主力8体, 6行目=前衛8体）
    for c in range(8):
        cid7 = p1_deck[c]
        hp7, atk7 = get_stats(cid7, p1_units.get(cid7, {"lv": 1})["lv"])
        board[7][c] = {"owner": "P1", "cid": cid7, "hp": hp7, "max_hp": hp7, "atk": atk7}
        
        cid6 = p1_deck[8 + c]
        hp6, atk6 = get_stats(cid6, p1_units.get(cid6, {"lv": 1})["lv"])
        board[6][c] = {"owner": "P1", "cid": cid6, "hp": hp6, "max_hp": hp6, "atk": atk6}
    return board

# --- ログイン画面 ---
if "user" not in st.session_state:
    st.title("♟️ 魔改造チェス オンライン")
    st.caption("友達とオンライン対戦可能！全32体＋初期6種の戦略バトル！")
    tab1, tab2 = st.tabs(["ログイン", "新規アカウント作成"])
    
    with tab1:
        u_in = st.text_input("ユーザー名", key="l_u")
        p_in = st.text_input("パスワード", type="password", key="l_p")
        if st.button("ログイン", type="primary"):
            idx, data = load_user(u_in, p_in)
            if idx == -1:
                st.error("パスワードが違います！")
            elif idx is None:
                st.error("ユーザーが見つかりません。新規作成してください。")
            else:
                st.session_state.row_idx = idx
                st.session_state.user = data
                st.rerun()

    with tab2:
        nu_in = st.text_input("希望のユーザー名", key="r_u")
        np_in = st.text_input("パスワード", type="password", key="r_p")
        if st.button("はじめる（初期1000コイン獲得！）"):
            if not nu_in or not np_in:
                st.warning("名前とパスワードを入力してください。")
            else:
                idx, _ = load_user(nu_in, np_in)
                if idx is not None:
                    st.error("そのユーザー名は既に使われています。")
                else:
                    idx, data = create_user(nu_in, np_in)
                    st.session_state.row_idx = idx
                    st.session_state.user = data
                    st.success("アカウント作成完了！")
                    st.rerun()
    st.stop()

# --- メインゲーム画面 ---
u = st.session_state.user
st.sidebar.title(f"👤 {u['username']}")
st.sidebar.metric("💰 所持コイン", f"{u['coins']} G")
st.sidebar.metric("📘 経験値の書", f"{u['items'].get('exp_book', 0)} 冊")
if st.sidebar.button("ログアウト"):
    del st.session_state.user
    st.rerun()

menu = st.tabs([
    "🌐 友達とオンライン対戦",
    "⚔️ CPU練習バトル",
    "🎰 魔改造ガチャ",
    "⬆️ 育成（Lv.50）",
    "🃏 16体デッキ編成",
    "📖 全キャラ図鑑"
])

# 1. 友達とオンライン対戦
with menu[0]:
    st.header("🌐 友達とオンライン対戦")
    pvp_mode = st.radio("対戦スタイルを選択", ["⚔️ リアルタイム8×8盤面バトル（合言葉で対戦）", "🔥 友達の最新デッキと模擬戦（いつでも対戦）"], horizontal=True)

    if "リアルタイム" in pvp_mode:
        st.info("同じ合言葉（例: `1234`）を入力して、1人が「部屋を作る」、もう1人が「参加する」を押すと8×8盤面がスタート！")
        room_code = st.text_input("対戦の合言葉（ルームID）", value="1234")
        _, battle_sheet = get_sheets()

        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            if st.button("🏠 部屋を作る（P1・先攻）", type="primary"):
                records = battle_sheet.get_all_records()
                found_row = None
                for idx, r in enumerate(records, start=2):
                    if str(r["room_id"]) == room_code:
                        found_row = idx
                        break
                row_data = [room_code, u["username"], "", "P1", "", "waiting", ""]
                if found_row:
                    battle_sheet.update(f"A{found_row}:G{found_row}", [row_data])
                else:
                    battle_sheet.append_row(row_data)
                st.success(f"部屋「{room_code}」を作成！友達が参加したら「盤面を更新」を押してね。")

        with col_r2:
            if st.button("🚪 部屋に参加する（P2・後攻）"):
                records = battle_sheet.get_all_records()
                joined = False
                for idx, r in enumerate(records, start=2):
                    if str(r["room_id"]) == room_code:
                        _, p1_data = load_user(str(r["p1"]))
                        if p1_data:
                            board = init_board(p1_data["deck"], p1_data["units"], u["deck"], u["units"])
                            battle_sheet.update(f"C{idx}:G{idx}", [[u["username"], "P1", json.dumps(board), "playing", ""]])
                            st.success("マッチング成立！バトル開始だ！")
                            joined = True
                        break
                if not joined:
                    st.error("その合言葉の部屋が見つかりません。先に友達に部屋を作ってもらおう！")

        with col_r3:
            if st.button("🔄 盤面を最新に更新"):
                st.rerun()

        # 現在の部屋状態を表示
        records = battle_sheet.get_all_records()
        room_info, room_row = None, None
        for idx, r in enumerate(records, start=2):
            if str(r["room_id"]) == room_code:
                room_info, room_row = r, idx
                break

        if room_info:
            st.divider()
            st.subheader(f"ルーム [{room_code}] ： 🔵 {room_info['p1']} (P1) VS 🔴 {room_info['p2'] or '募集中...'} (P2)")
            
            if room_info["status"] == "waiting":
                st.warning("⏳ 対戦相手の入室を待っています…（相手が入ったら「盤面を最新に更新」を押してください）")
            elif room_info["status"] == "finished":
                st.success(f"🏆 **決着！ 勝者： {room_info['winner']} ！！**")
                if room_info["winner"] == u["username"]:
                    st.balloons()
            elif room_info["status"] == "playing" and room_info["board"]:
                board = json.loads(room_info["board"])
                my_side = "P1" if room_info["p1"] == u["username"] else ("P2" if room_info["p2"] == u["username"] else "SPEC")
                turn = room_info["turn"]

                if turn == my_side:
                    st.success(f"🔥 **あなたのターンです！（あなたは {my_side}）**")
                else:
                    st.info(f"⏳ **相手のターンです（現在: {turn} の手番）** 相手が動かしたら「盤面を最新に更新」を押そう！")

                # 8x8 盤面描画
                my_pieces = []
                for r_i in range(8):
                    cols = st.columns(8)
                    for c_i in range(8):
                        cell = board[r_i][c_i]
                        coord = f"{r_i},{c_i}"
                        if cell:
                            c_info = CHARACTERS[cell["cid"]]
                            tag = "🔵" if cell["owner"] == "P1" else "🔴"
                            cols[c_i].markdown(f"**{tag}{c_info['icon']}**\n\n`({r_i},{c_i})`\n\nHP:{cell['hp']}")
                            if cell["owner"] == my_side:
                                my_pieces.append((coord, f"{c_info['icon']}{c_info['name']} ({r_i},{c_i}) HP:{cell['hp']}"))
                        else:
                            cols[c_i].markdown(f"⬜\n\n`({r_i},{c_i})`")

                # 行動コマンド（自分のターンのみ）
                if turn == my_side and my_pieces:
                    st.divider()
                    st.write("### 🎮 コマンド入力（移動 / 攻撃）")
                    sc1, sc2, sc3 = st.columns(3)
                    with sc1:
                        from_choice = st.selectbox("動かす自分の駒", my_pieces, format_func=lambda x: x[1])
                    with sc2:
                        to_r = st.number_input("移動先の縦座標（行 0〜7）", min_value=0, max_value=7, value=3)
                    with sc3:
                        to_c = st.number_input("移動先の横座標（列 0〜7）", min_value=0, max_value=7, value=3)

                    if st.button("このマスへ移動・攻撃する！", type="primary"):
                        fr, fc = map(int, from_choice[0].split(","))
                        mover = board[fr][fc]
                        target = board[to_r][to_c]
                        
                        if fr == to_r and fc == to_c:
                            st.error("同じマスには移動できません！")
                        elif target and target["owner"] == my_side:
                            st.error("味方の駒がいるマスには移動できません！")
                        else:
                            # 攻撃・下剋上ダメージ判定
                            win_game = False
                            if target:
                                dmg = mover["atk"]
                                m_cid = mover["cid"]
                                t_rar = CHARACTERS[target["cid"]]["rarity"]
                                # 下剋上スキル補正
                                if m_cid == "C01" and t_rar in ["レジェンダリー", "ミシック"]:
                                    dmg *= 2
                                if m_cid == "C09":
                                    c_allies = sum(1 for row in board for x in row if x and x["owner"] == my_side and CHARACTERS[x["cid"]]["rarity"] == "コモン")
                                    if c_allies >= 4:
                                        dmg *= 3
                                
                                target["hp"] -= dmg
                                if target["hp"] <= 0:
                                    # 撃破！
                                    if CHARACTERS[target["cid"]]["piece"] == "キング":
                                        win_game = True
                                    board[to_r][to_c] = mover
                                    board[fr][fc] = None
                                else:
                                    # 耐えた場合はその場でダメージのみ
                                    board[to_r][to_c] = target
                            else:
                                board[to_r][to_c] = mover
                                board[fr][fc] = None

                            next_turn = "P2" if my_side == "P1" else "P1"
                            if win_game:
                                battle_sheet.update(f"D{room_row}:G{room_row}", [[next_turn, json.dumps(board), "finished", u["username"]]])
                                u["coins"] += 500
                                save_user()
                            else:
                                battle_sheet.update(f"D{room_row}:E{room_row}", [[next_turn, json.dumps(board)]])
                            st.rerun()

    else:
        # 友達の最新デッキと模擬戦
        st.write("友達が育てた最新の16体デッキをスプレッドシートから呼び出して対戦しよう！")
        all_users = [name for name in get_all_usernames() if name != u["username"]]
        if not all_users:
            st.warning("まだ他のプレイヤーが登録されていません！友達にこのURLを送ってアカウントを作ってもらおう！")
        else:
            rival_name = st.selectbox("対戦する友達を選ぶ", all_users)
            if st.button(f"🔥 {rival_name} のデッキと対戦！", type="primary"):
                _, rival = load_user(rival_name)
                def calc_army(deck_list, units_dict):
                    hp_sum, atk_sum, c_cnt, ud = 0, 0, 0, False
                    for cid in deck_list:
                        lv = units_dict.get(cid, {"lv": 1})["lv"]
                        h, a = get_stats(cid, lv)
                        hp_sum += h
                        atk_sum += a
                        if CHARACTERS[cid]["rarity"] == "コモン": c_cnt += 1
                        if cid in ["C01", "C04", "C09", "U04", "U05"]: ud = True
                    if c_cnt >= 4: atk_sum = int(atk_sum * 1.4)
                    if ud: atk_sum += 350
                    return hp_sum + atk_sum * 2 + random.randint(-150, 250)

                my_pow = calc_army(u["deck"], u["units"])
                rv_pow = calc_army(rival["deck"], rival["units"])

                c1, c2 = st.columns(2)
                c1.metric(f"あなた ({u['username']}) の総戦力", my_pow)
                c2.metric(f"友達 ({rival_name}) の総戦力", rv_pow)

                if my_pow >= rv_pow:
                    st.success(f"🎉 **{rival_name} の軍勢に勝利！！** 報酬 200 G 獲得！")
                    u["coins"] += 200
                    save_user()
                else:
                    st.error(f"💀 **{rival_name} に敗北…** デッキを見直してリベンジしよう！")

# 2. CPU練習バトル
with menu[1]:
    st.header("⚔️ CPU練習バトル（コイン＆経験値の書稼ぎ）")
    enemy_lv = st.selectbox("対戦相手のランク", ["初級（報酬: 150G + 書2冊）", "中級（報酬: 350G + 書4冊）", "上級・魔王級（報酬: 800G + 書8冊）"])
    if st.button("CPUバトル開始！", type="primary"):
        total_hp, total_atk, common_count, has_underdog = 0, 0, 0, False
        for cid in u["deck"]:
            lv = u["units"].get(cid, {"lv": 1})["lv"]
            hp, atk = get_stats(cid, lv)
            total_hp += hp
            total_atk += atk
            if CHARACTERS[cid]["rarity"] == "コモン": common_count += 1
            if cid in ["C01", "C04", "C09", "U04", "U05"]: has_underdog = True

        if common_count >= 4: total_atk = int(total_atk * 1.4)
        if has_underdog: total_atk += 350

        if "初級" in enemy_lv: e_score, r_coin, r_book = 2800, 150, 2
        elif "中級" in enemy_lv: e_score, r_coin, r_book = 5700, 350, 4
        else: e_score, r_coin, r_book = 10900, 800, 8

        p_score = total_hp + total_atk * 2 + random.randint(-200, 300)
        st.write(f"あなたの戦力: **{p_score}** vs 敵戦力: **{e_score}**")
        if p_score >= e_score:
            st.success(f"🎉 **勝利！** {r_coin} G と経験値の書 {r_book} 冊を獲得！")
            u["coins"] += r_coin
            u["items"]["exp_book"] = u["items"].get("exp_book", 0) + r_book
            save_user()
        else:
            st.error("💀 敗北… 育成して再挑戦しよう！")

# 3. ガチャ
with menu[2]:
    st.header("🎰 魔改造ガチャ（全32体実装）")
    st.write("1回 **100 G** / 10連 **900 G**（ミシック 1% / レジェンダリー 4% / エピック 15% / レア 20% / アンコモン 25% / コモン 35%）")
    def pull_gacha(times):
        pools = {
            "ミシック": ["M01", "M02"], "レジェンダリー": ["L01", "L02", "L03", "L04"],
            "エピック": [f"E0{i}" for i in range(1, 9)], "レア": ["R01", "R02", "R03", "R04"],
            "アンコモン": ["U01", "U02", "U03", "U04", "U05"], "コモン": [f"C0{i}" for i in range(1, 10)]
        }
        results = []
        for _ in range(times):
            r = random.random() * 100
            if r < 1: rar = "ミシック"
            elif r < 5: rar = "レジェンダリー"
            elif r < 20: rar = "エピック"
            elif r < 40: rar = "レア"
            elif r < 65: rar = "アンコモン"
            else: rar = "コモン"
            cid = random.choice(pools[rar])
            results.append(cid)
            if cid in u["units"]: u["units"][cid]["count"] += 1
            else: u["units"][cid] = {"count": 1, "lv": 1}
        save_user()
        return results

    c1, c2 = st.columns(2)
    with c1:
        if st.button("単発ガチャ（100 G）"):
            if u["coins"] >= 100:
                u["coins"] -= 100
                for cid in pull_gacha(1):
                    c = CHARACTERS[cid]
                    st.success(f"{RARITY_COLORS[c['rarity']]} **[{c['rarity']}] {c['name']}**（{c['piece']}）を獲得！")
            else: st.error("コイン不足！")
    with c2:
        if st.button("10連ガチャ（900 G）", type="primary"):
            if u["coins"] >= 900:
                u["coins"] -= 900
                for cid in pull_gacha(10):
                    c = CHARACTERS[cid]
                    st.write(f"{RARITY_COLORS[c['rarity']]} **[{c['rarity']}] {c['name']}**（{c['piece']}）")
            else: st.error("コイン不足！")

# 4. 育成
with menu[3]:
    st.header("⬆️ キャラクター強化（最大 Lv.50）")
    owned = list(u["units"].keys())
    selected_cid = st.selectbox("強化するキャラ", owned, format_func=lambda x: f"{RARITY_COLORS[CHARACTERS[x]['rarity']]} {CHARACTERS[x]['name']} (Lv.{u['units'][x]['lv']})")
    cur_lv = u["units"][selected_cid]["lv"]
    hp, atk = get_stats(selected_cid, cur_lv)
    st.write(f"**Lv.{cur_lv} / 50** ｜ HP: **{hp}** ｜ ATK: **{atk}**")
    st.info(f"スキル：{CHARACTERS[selected_cid]['skill']}")
    if cur_lv < 50 and st.button("経験値の書を1冊使ってレベルアップ！", type="primary"):
        if u["items"].get("exp_book", 0) >= 1:
            u["items"]["exp_book"] -= 1
            u["units"][selected_cid]["lv"] += 1
            save_user()
            st.rerun()
        else: st.error("経験値の書が足りません！")

# 5. デッキ編成
with menu[4]:
    st.header("🃏 マイデッキ編成（16体）")
    st.write("枠1〜8が盤面の後列（主力）、枠9〜16が前列（前衛）に配置されます！キング枠は必ず1体入れてね。")
    new_deck = []
    cols = st.columns(4)
    for i in range(16):
        with cols[i % 4]:
            default_val = u["deck"][i] if i < len(u["deck"]) else "GR_P"
            choice = st.selectbox(
                f"枠 {i+1}", owned,
                index=owned.index(default_val) if default_val in owned else 0,
                key=f"deck_slot_{i}",
                format_func=lambda x: f"{RARITY_COLORS[CHARACTERS[x]['rarity']]}{CHARACTERS[x]['name'][:7]}"
            )
            new_deck.append(choice)
    if st.button("この16体でデッキを保存する", type="primary"):
        kings = [c for c in new_deck if CHARACTERS[c]["piece"] == "キング"]
        if len(kings) != 1:
            st.error(f"キング枠のキャラは必ず1体だけ入れてください！（現在: {len(kings)}体）")
        else:
            u["deck"] = new_deck
            save_user()
            st.success("✅ デッキを保存しました！")

# 6. 図鑑
with menu[5]:
    st.header("📖 全38体（初期6種＋ガチャ32体）キャラクター図鑑")
    for cid, info in CHARACTERS.items():
        owned_mark = "✅ 所持" if cid in u["units"] else "🔒 未所持"
        with st.expander(f"{RARITY_COLORS[info['rarity']]} [{info['rarity']}] {info['name']} ({info['piece']}) - {owned_mark}"):
            st.write(f"**基本HP:** {info['hp']} ｜ **基本ATK:** {info['atk']}")
            st.write(f"**特殊スキル:** {info['skill']}")
