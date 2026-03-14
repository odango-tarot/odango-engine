import os
import random
import requests
import anthropic
import streamlit as st
from prompt import FORTUNE_METHODS, get_system_prompt, build_user_message, get_mashup_system_prompt, build_mashup_user_message

# アストロダイスの面
ASTRO_PLANETS = ["太陽", "月", "水星", "金星", "火星", "木星", "土星", "天王星", "海王星", "冥王星", "キロン", "ドラゴンヘッド"]
ASTRO_SIGNS = ["おひつじ座", "おうし座", "ふたご座", "かに座", "しし座", "おとめ座", "てんびん座", "さそり座", "いて座", "やぎ座", "みずがめ座", "うお座"]
ASTRO_HOUSES = ["1ハウス", "2ハウス", "3ハウス", "4ハウス", "5ハウス", "6ハウス", "7ハウス", "8ハウス", "9ハウス", "10ハウス", "11ハウス", "12ハウス"]

SIGN_NAMES = {
    1:"おひつじ座", 2:"おうし座", 3:"ふたご座", 4:"かに座",
    5:"しし座", 6:"おとめ座", 7:"てんびん座", 8:"さそり座",
    9:"いて座", 10:"やぎ座", 11:"みずがめ座", 12:"うお座"
}
PLANET_NAMES = {
    "Sun":"太陽", "Moon":"月", "Mercury":"水星", "Venus":"金星",
    "Mars":"火星", "Jupiter":"木星", "Saturn":"土星",
    "Uranus":"天王星", "Neptune":"海王星", "Pluto":"冥王星",
    "Ascendant":"アセンダント", "Rahu":"ドラゴンヘッド（ラーフ）", "Ketu":"ドラゴンテイル（ケートゥ）",
}

CITY_COORDS = {
    "東京": (35.6762, 139.6503),
    "大阪": (34.6937, 135.5023),
    "名古屋": (35.1815, 136.9066),
    "札幌": (43.0618, 141.3545),
    "福岡": (33.5904, 130.4017),
    "仙台": (38.2688, 140.8721),
    "広島": (34.3853, 132.4553),
    "京都": (35.0116, 135.7681),
    "神戸": (34.6901, 135.1956),
    "秋田": (39.7186, 140.1023),
    "横浜": (35.4437, 139.6380),
    "さいたま": (35.8617, 139.6455),
}

# ルノルマン36枚カードリスト
LENORMAND_CARDS = [
    "（未選択）",
    "騎士", "クローバー", "船", "家", "木", "雲", "蛇", "棺",
    "花束", "鎌", "鞭", "鳥", "子供", "狐", "熊", "星",
    "コウノトリ", "犬", "塔", "庭園", "山", "十字路", "鼠", "ハート",
    "指輪", "本", "手紙", "紳士", "淑女", "百合", "太陽", "月",
    "鍵", "魚", "錨", "十字架",
]

def get_coords(place_str):
    for city, coords in CITY_COORDS.items():
        if city in place_str:
            return coords
    return (35.6762, 139.6503)

# ─────────────────────────────────────────────
# ネイタルチャート自動計算
# ─────────────────────────────────────────────
def fetch_natal_chart(year, month, day, hour, minute, lat, lon, tzone):
    api_key = st.secrets.get("ASTROLOGY_API_KEY", "")
    url = "https://json.freeastrologyapi.com/planets"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }
    payload = {
        "year": year, "month": month, "date": day,
        "hours": hour, "minutes": minute, "seconds": 0,
        "latitude": lat, "longitude": lon, "timezone": tzone,
        "config": {"observation_point": "topocentric", "ayanamsha": "tropical"}
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        planets_dict = data["output"][1]
        lines = []
        order = ["Ascendant", "Sun", "Moon", "Mercury", "Venus", "Mars",
                 "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Rahu", "Ketu"]
        for key in order:
            if key not in planets_dict:
                continue
            p = planets_dict[key]
            name = PLANET_NAMES.get(key, key)
            sign = SIGN_NAMES.get(p.get("current_sign", 0), "不明")
            degree = round(p.get("normDegree", 0), 1)
            house = p.get("house_number", "")
            retro = "（逆行）" if p.get("isRetro") == "true" else ""
            house_str = f"　{house}ハウス" if house else ""
            lines.append(f"{name}：{sign} {degree}度{house_str}{retro}")
        return "\n".join(lines)
    except Exception as e:
        return f"取得エラー：{e}"

# ─────────────────────────────────────────────
# グラン・タブロー配置からプロンプト用テキストを生成
# ─────────────────────────────────────────────
def build_grand_tableau_text(grid, person_setting):
    """
    grid: list of 36 strings (行1×8 + 行2×8 + 行3×8 + 行4×8 + 最終行×4)
    配置情報を構造化テキストに変換してプロンプトに渡す
    """
    row1 = grid[0:8]
    row2 = grid[8:16]
    row3 = grid[16:24]
    row4 = grid[24:32]
    row5 = grid[32:36]

    # 依頼者カードを特定
    client_gender = person_setting.get("client_gender", "女性")
    seeker_card = "淑女" if client_gender == "女性" else "紳士"

    # 淑女・紳士の位置を特定
    all_rows = [row1, row2, row3, row4, row5]
    seeker_pos = None
    lady_pos = None
    knight_pos = None

    for row_idx, row in enumerate(all_rows):
        for col_idx, card in enumerate(row):
            if card == "淑女":
                lady_pos = (row_idx + 1, col_idx + 1)
            if card == "紳士":
                knight_pos = (row_idx + 1, col_idx + 1)

    if seeker_card == "淑女":
        seeker_pos = lady_pos
    else:
        seeker_pos = knight_pos

    lines = []
    lines.append("【グラン・タブロー配置】")
    lines.append("※ 配置は「段数（上から）× 列数（左から）」で表します")
    lines.append("")

    row_labels = ["1段目（最上段）", "2段目", "3段目", "4段目", "最終行（中央4枚）"]
    for i, (label, row) in enumerate(zip(row_labels, all_rows)):
        filled = [c if c != "（未選択）" else "？" for c in row]
        lines.append(f"{label}：{' | '.join(filled)}")

    lines.append("")

    # 位置情報サマリー
    if lady_pos:
        row_name = ["最上段", "2段目", "3段目", "4段目", "最終行"][lady_pos[0]-1]
        bottom = lady_pos[0] == 4 or (lady_pos[0] == 5)
        top = lady_pos[0] == 1
        lines.append(f"▼ 淑女の位置：{row_name} / 左から{lady_pos[1]}列目")
        if top:
            lines.append("　→ 淑女は最上段：頭上の外部影響カードなし（内面・水面下に意識を向けるとき）")
        elif bottom:
            lines.append("　→ 淑女は最下段：下のカードなし（思考・気持ちを表す余裕がない状態）")

        # 過去・未来の列数
        past_cols = lady_pos[1] - 1
        future_cols = 8 - lady_pos[1] if lady_pos[0] <= 4 else 0
        lines.append(f"　→ 過去エリア：{past_cols}列 / 未来エリア：{future_cols}列")

    if knight_pos:
        row_name = ["最上段", "2段目", "3段目", "4段目", "最終行"][knight_pos[0]-1]
        lines.append(f"▼ 紳士の位置：{row_name} / 左から{knight_pos[1]}列目")

    lines.append("")

    # 4隅
    corner_tl = row1[0] if row1[0] != "（未選択）" else "？"
    corner_tr = row1[7] if row1[7] != "（未選択）" else "？"
    corner_bl = row4[0] if row4[0] != "（未選択）" else "？"
    corner_br = row4[7] if row4[7] != "（未選択）" else "？"
    lines.append(f"▼ 4隅：左上＝{corner_tl} / 右上＝{corner_tr} / 左下＝{corner_bl} / 右下＝{corner_br}")
    lines.append(f"　→ 対角ルート①：{corner_tl}→{corner_br}")
    lines.append(f"　→ 対角ルート②：{corner_tr}→{corner_bl}")

    lines.append("")

    # 最下段4枚（アドバイスエリア）
    bottom4 = [c if c != "（未選択）" else "？" for c in row5]
    lines.append(f"▼ 最終行4枚（アドバイスメッセージ）：{' | '.join(bottom4)}")

    lines.append("")

    # 依頼者周辺カード（頭上・真下・両脇）
    if seeker_pos and seeker_pos[0] <= 4:
        r, c = seeker_pos
        rows = [row1, row2, row3, row4]

        above = rows[r-2][c-1] if r >= 2 else "（なし）"
        below = rows[r][c-1] if r <= 3 else "（なし）"
        left = rows[r-1][c-2] if c >= 2 else "（なし）"
        right = rows[r-1][c] if c <= 7 else "（なし）"

        above2 = rows[r-3][c-1] if r >= 3 else "（なし）"
        above3 = rows[r-4][c-1] if r >= 4 else "（なし）"

        left2 = rows[r-1][c-3] if c >= 3 else "（なし）"
        right2 = rows[r-1][c+1] if c <= 6 else "（なし）"

        lines.append(f"▼ {seeker_card}の周辺カード")
        lines.append(f"　真上：{above}　（その上：{above2}　さらに上：{above3}）")
        lines.append(f"　真下：{below}")
        lines.append(f"　左：{left}　左2：{left2}")
        lines.append(f"　右：{right}　右2：{right2}")

        # 未来ルート（右へ1枚ずつ）
        future_route = []
        for fc in range(c, 8):  # c列目（現在）の右
            card = rows[r-1][fc]
            if card and card != "（未選択）" and card != seeker_card:
                col_above = rows[r-2][fc] if r >= 2 else "（なし）"
                col_above2 = rows[r-3][fc] if r >= 3 else "（なし）"
                future_route.append(f"　{len(future_route)+1}ヶ月後：{card}（縦上：{col_above} / さらに上：{col_above2}）")
        if future_route:
            lines.append("")
            lines.append(f"▼ {seeker_card}の未来ルート（右へ1枚＝1ヶ月）")
            lines.extend(future_route)

    return "\n".join(lines)

# ─────────────────────────────────────────────
# ページ設定
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🍡 ODANGO ENGINE",
    page_icon="🍡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# カスタムCSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@300;400&display=swap');
    html, body, [class*="css"] {
        font-family: 'Noto Serif JP', Georgia, serif;
        background-color: #0d0d1a;
        color: #e8d5b7;
    }
    .stApp {
        background: linear-gradient(160deg, #0d0d1a 0%, #13102b 50%, #0d0d1a 100%);
    }
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(196,164,255,0.25) !important;
        border-radius: 8px !important;
        color: #e8d5b7 !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, rgba(196,164,255,0.15), rgba(232,213,183,0.1));
        border: 1px solid rgba(196,164,255,0.4);
        border-radius: 10px;
        color: #e8d5b7;
        font-family: 'Noto Serif JP', Georgia, serif;
        letter-spacing: 0.15em;
        font-size: 15px;
        width: 100%;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(196,164,255,0.3), rgba(232,213,183,0.2));
        border-color: rgba(196,164,255,0.7);
    }
    .output-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(232,213,183,0.15);
        border-radius: 16px;
        padding: 32px;
        margin-top: 24px;
        line-height: 2;
        font-size: 15px;
        color: #e8d5b7;
        white-space: pre-wrap;
        font-family: 'Noto Serif JP', Georgia, serif;
    }
    .section-label {
        font-size: 11px;
        letter-spacing: 4px;
        color: #c4a4ff;
        margin-bottom: 8px;
    }
    .divider {
        width: 100%;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(196,164,255,0.3), transparent);
        margin: 24px 0;
    }
    .dice-result {
        background: rgba(196,164,255,0.08);
        border: 1px solid rgba(196,164,255,0.3);
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 14px;
        color: #e8d5b7;
        margin-bottom: 8px;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# パスワード認証
# ─────────────────────────────────────────────
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    st.markdown("""
    <div style="text-align:center; padding: 60px 0 32px 0;">
        <div style="font-size:11px; letter-spacing:6px; color:#c4a4ff; margin-bottom:12px;">✦ PRIVATE SYSTEM ✦</div>
        <h1 style="font-size:2rem; background: linear-gradient(90deg, #e8d5b7, #c4a4ff); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">🍡 ODANGO ENGINE</h1>
    </div>
    """, unsafe_allow_html=True)
    pw = st.text_input("パスワード", type="password", key="pw_input")
    if st.button("ログイン"):
        correct = st.secrets.get("APP_PASSWORD", "")
        if pw == correct:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います")
    return False

if not check_password():
    st.stop()

# ─────────────────────────────────────────────
# セッション初期化
# ─────────────────────────────────────────────
if "dice_sets" not in st.session_state:
    st.session_state.dice_sets = []
if "natal_result" not in st.session_state:
    st.session_state.natal_result = ""
if "natal_result2" not in st.session_state:
    st.session_state.natal_result2 = ""

# ─────────────────────────────────────────────
# ヘッダー
# ─────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 32px 0 8px 0;">
    <div style="font-size:11px; letter-spacing:6px; color:#c4a4ff; margin-bottom:12px;">✦ ODANGO GHOST WRITER SYSTEM ✦</div>
    <h1 style="font-size:2.2rem; margin:0; background: linear-gradient(90deg, #e8d5b7, #c4a4ff, #e8d5b7); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">🍡 ODANGO ENGINE</h1>
    <div style="font-size:13px; color:rgba(232,213,183,0.5); margin-top:12px; letter-spacing:2px;">占い鑑定ゴーストライティングシステム</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ネイタルチャートUIコンポーネント
# ─────────────────────────────────────────────
def natal_chart_ui(expander_key, result_key):
    with st.expander("🌟 生年月日・出生時刻から自動計算する"):
        nc1, nc2, nc3 = st.columns([1, 1, 1])
        with nc1:
            birth_year = st.number_input("生年", min_value=1900, max_value=2100, value=1990, step=1, key=f"birth_year_{expander_key}")
        with nc2:
            birth_month = st.number_input("生月", min_value=1, max_value=12, value=1, step=1, key=f"birth_month_{expander_key}")
        with nc3:
            birth_day = st.number_input("生日", min_value=1, max_value=31, value=1, step=1, key=f"birth_day_{expander_key}")
        nt1, nt2 = st.columns([1, 1])
        with nt1:
            birth_hour = st.number_input("時（24時間）", min_value=0, max_value=23, value=12, step=1, key=f"birth_hour_{expander_key}")
        with nt2:
            birth_minute = st.number_input("分", min_value=0, max_value=59, value=0, step=1, key=f"birth_minute_{expander_key}")
        birth_place = st.text_input("出生地（例：秋田県秋田市）", key=f"birth_place_{expander_key}")
        st.caption("※ 緯度経度は主要都市を自動設定します。不明な場合は東京（35.68, 139.69）を使用します。")
        if st.button("🌟 ネイタルチャートを計算する", key=f"calc_btn_{expander_key}"):
            lat, lon = get_coords(birth_place)
            result = fetch_natal_chart(birth_year, birth_month, birth_day, birth_hour, birth_minute, lat, lon, tzone=9.0)
            st.session_state[result_key] = result
            st.rerun()
        if st.session_state.get(result_key, ""):
            st.markdown(
                f'<div class="dice-result">🌟 計算結果：<br>{st.session_state[result_key].replace(chr(10), "<br>")}</div>',
                unsafe_allow_html=True
            )
            if st.button("🔄 計算結果をリセット", key=f"reset_btn_{expander_key}"):
                st.session_state[result_key] = ""
                st.rerun()

# ─────────────────────────────────────────────
# ルノルマン人物設定UIコンポーネント
# ─────────────────────────────────────────────
def lenormand_person_setting_ui(key_suffix="main"):
    st.markdown('<div class="section-label">✦ 人物カード設定（ルノルマン）</div>', unsafe_allow_html=True)
    with st.container(border=True):
        client_gender = st.radio(
            "依頼者の性別",
            options=["女性", "男性"],
            horizontal=True,
            key=f"lenormand_gender_{key_suffix}",
        )
        st.markdown("---")
        ROLE_OPTIONS = ["依頼者本人", "恋人・配偶者", "片想いの相手", "友人・知人", "その他"]
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("🌹 **淑女（29番）の役割**")
            lady_role = st.selectbox(
                "", options=ROLE_OPTIONS,
                index=0 if client_gender == "女性" else 1,
                label_visibility="collapsed",
                key=f"lenormand_lady_role_{key_suffix}",
            )
            lady_custom = ""
            if lady_role == "その他":
                lady_custom = st.text_input("具体的に入力", placeholder="例：娘、姉", key=f"lenormand_lady_custom_{key_suffix}")
        with col_r:
            st.markdown("🎩 **紳士（28番）の役割**")
            knight_role = st.selectbox(
                "", options=ROLE_OPTIONS,
                index=1 if client_gender == "女性" else 0,
                label_visibility="collapsed",
                key=f"lenormand_knight_role_{key_suffix}",
            )
            knight_custom = ""
            if knight_role == "その他":
                knight_custom = st.text_input("具体的に入力", placeholder="例：息子、弟", key=f"lenormand_knight_custom_{key_suffix}")
        lady_desc = lady_custom if lady_role == "その他" and lady_custom else lady_role
        knight_desc = knight_custom if knight_role == "その他" and knight_custom else knight_role
        st.caption(f"📌 淑女＝{lady_desc}　／　紳士＝{knight_desc}　／　依頼者：{client_gender}")
    return {
        "client_gender": client_gender,
        "lady_role": lady_role,
        "lady_custom": lady_custom,
        "knight_role": knight_role,
        "knight_custom": knight_custom,
    }

# ─────────────────────────────────────────────
# グラン・タブローグリッドUIコンポーネント
# ─────────────────────────────────────────────
def grand_tableau_grid_ui(key_suffix="main"):
    """36枚のドロップダウングリッドUI。gridリスト（36要素）を返す。"""
    st.markdown('<div class="section-label">✦ グラン・タブロー配置入力</div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.caption("左上から右へ、1段目→2段目→3段目→4段目→最終行（中央4枚）の順に選択してください")

        grid = []

        # 1〜4段目（各8枚）
        row_labels = ["1段目（最上段）", "2段目", "3段目", "4段目"]
        for row_idx, label in enumerate(row_labels):
            st.markdown(f"**{label}**")
            cols = st.columns(8)
            for col_idx, col in enumerate(cols):
                with col:
                    card = st.selectbox(
                        f"{col_idx+1}",
                        options=LENORMAND_CARDS,
                        index=0,
                        label_visibility="visible",
                        key=f"gt_{key_suffix}_r{row_idx}_c{col_idx}",
                    )
                    grid.append(card)

        # 最終行（4枚・中央寄せ）
        st.markdown("**最終行（中央4枚）**")
        _, c1, c2, c3, c4, _ = st.columns([2, 1, 1, 1, 1, 2])
        final_cols = [c1, c2, c3, c4]
        for i, col in enumerate(final_cols):
            with col:
                card = st.selectbox(
                    f"{i+1}",
                    options=LENORMAND_CARDS,
                    index=0,
                    label_visibility="visible",
                    key=f"gt_{key_suffix}_r4_c{i}",
                )
                grid.append(card)

        # 入力済み枚数を表示
        filled = sum(1 for c in grid if c != "（未選択）")
        st.caption(f"📌 入力済み：{filled} / 36枚")

    return grid

# ─────────────────────────────────────────────
# 入力フォーム
# ─────────────────────────────────────────────
col1, col2 = st.columns([1, 1])
with col1:
    st.markdown('<div class="section-label">✦ クライアント名</div>', unsafe_allow_html=True)
    client_name = st.text_input("", placeholder="例：山田花子", label_visibility="collapsed", key="client_name")
with col2:
    st.markdown('<div class="section-label">✦ 占術１</div>', unsafe_allow_html=True)
    method_key = st.selectbox(
        "",
        options=list(FORTUNE_METHODS.keys()),
        format_func=lambda x: {
            "astrology": "🌟 西洋占星術",
            "tarot": "🃏 タロット",
            "zen_tarot": "🪷 禅タロット（OSHOゼン）",
            "lenormand": "🌹 ルノルマン",
            "astrodice": "🎲 アストロダイス",
            "thoth": "🔮 トートタロット",
        }[x],
        label_visibility="collapsed",
        key="method",
    )

st.markdown('<div class="section-label">✦ ご相談内容（任意）</div>', unsafe_allow_html=True)
consultation = st.text_input("", placeholder="例：仕事の転職について", label_visibility="collapsed", key="consultation")

st.markdown('<div class="section-label">✦ クライアントの依頼文章（任意）</div>', unsafe_allow_html=True)
consultation_text = st.text_area("", placeholder="クライアントから届いた相談文をそのまま貼り付けてください", height=120, label_visibility="collapsed", key="consultation_text")

# ─────────────────────────────────────────────
# 占術別UI
# ─────────────────────────────────────────────
person_setting = {}
grand_tableau_grid = []

if method_key == "astrodice":
    st.markdown('<div class="section-label">✦ アストロダイス</div>', unsafe_allow_html=True)
    for i, dice in enumerate(st.session_state.dice_sets):
        st.markdown(f'<div class="dice-result">🎲 第{i+1}投｜{dice["label"] or "（ラベルなし）"}　→　{dice["planet"]} × {dice["sign"]} × {dice["house"]}</div>', unsafe_allow_html=True)
    if len(st.session_state.dice_sets) < 3:
        new_label = st.text_input(
            "", placeholder=f"第{len(st.session_state.dice_sets)+1}投のテーマ（例：現状、課題、アドバイス）",
            label_visibility="collapsed", key=f"dice_label_{len(st.session_state.dice_sets)}",
        )
        if st.button(f"🎲 第{len(st.session_state.dice_sets)+1}投を振る"):
            st.session_state.dice_sets.append({
                "label": new_label,
                "planet": random.choice(ASTRO_PLANETS),
                "sign": random.choice(ASTRO_SIGNS),
                "house": random.choice(ASTRO_HOUSES),
            })
            st.rerun()
    if st.session_state.dice_sets:
        if st.button("🔄 サイコロをリセット"):
            st.session_state.dice_sets = []
            st.rerun()
    raw_data = "\n".join([
        f"第{i+1}投（{d['label'] or 'テーマなし'}）：{d['planet']} × {d['sign']} × {d['house']}"
        for i, d in enumerate(st.session_state.dice_sets)
    ]) if st.session_state.dice_sets else ""

elif method_key == "astrology":
    st.markdown('<div class="section-label">✦ ネイタルチャート自動計算（任意）</div>', unsafe_allow_html=True)
    natal_chart_ui("main", "natal_result")
    st.markdown('<div class="section-label">✦ 出目（任意）</div>', unsafe_allow_html=True)
    raw_data = st.text_area("", value=st.session_state.get("natal_result", ""), placeholder="ネイタルチャートの情報を貼り付けてください", height=150, label_visibility="collapsed", key="raw_data")

elif method_key == "lenormand":
    person_setting = lenormand_person_setting_ui("main")
    grand_tableau_grid = grand_tableau_grid_ui("main")
    # グリッドからraw_dataを自動生成（補足テキストエリアも残す）
    raw_data = ""
    st.markdown('<div class="section-label">✦ 補足・追記（任意）</div>', unsafe_allow_html=True)
    raw_data_extra = st.text_area("", placeholder="グリッド以外の補足情報があれば", height=80, label_visibility="collapsed", key="raw_data_lenormand_extra")

else:
    st.markdown('<div class="section-label">✦ 出目（任意）</div>', unsafe_allow_html=True)
    raw_data = st.text_area("", placeholder="カード名・星の配置・サイコロの出目など", height=150, label_visibility="collapsed", key="raw_data")
    raw_data_extra = ""

st.markdown('<div class="section-label">✦ 補足メモ（任意）</div>', unsafe_allow_html=True)
memo = st.text_area("", placeholder="占い師の直感・クライアントの背景など", height=80, label_visibility="collapsed", key="memo")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# モード選択
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">✦ モード</div>', unsafe_allow_html=True)
mode = st.radio("", options=["generate", "rewrite", "mashup"],
    format_func=lambda x: {"generate": "✨ 出目から生成", "rewrite": "✏️ 下書きをリライト", "mashup": "🔀 マッシュアップ"}[x],
    horizontal=True, label_visibility="collapsed", key="mode")

if mode == "mashup":
    st.markdown('<div class="section-label">✦ 占術２</div>', unsafe_allow_html=True)
    method_key2 = st.selectbox(
        "",
        options=list(FORTUNE_METHODS.keys()),
        format_func=lambda x: {
            "astrology": "🌟 西洋占星術",
            "tarot": "🃏 タロット",
            "zen_tarot": "🪷 禅タロット（OSHOゼン）",
            "lenormand": "🌹 ルノルマン",
            "astrodice": "🎲 アストロダイス",
            "thoth": "🔮 トートタロット",
        }[x],
        label_visibility="collapsed",
        key="method2",
    )
    if method_key2 == "astrology":
        st.markdown('<div class="section-label">✦ ネイタルチャート自動計算（占術２）</div>', unsafe_allow_html=True)
        natal_chart_ui("mashup2", "natal_result2")
        st.markdown('<div class="section-label">✦ 占術２の生データ</div>', unsafe_allow_html=True)
        raw_data2 = st.text_area("", value=st.session_state.get("natal_result2", ""), placeholder="ネイタルチャートの情報を貼り付けてください", height=150, label_visibility="collapsed", key="raw_data2")
    elif method_key2 == "lenormand":
        person_setting = lenormand_person_setting_ui("mashup2")
        grand_tableau_grid = grand_tableau_grid_ui("mashup2")
        raw_data2 = ""
    else:
        st.markdown('<div class="section-label">✦ 占術２の生データ</div>', unsafe_allow_html=True)
        raw_data2 = st.text_area("", placeholder="占術２の出目を貼り付けてください", height=150, label_visibility="collapsed", key="raw_data2")
else:
    method_key2 = None
    raw_data2 = ""

st.markdown('<div class="section-label">✦ 目標文字数</div>', unsafe_allow_html=True)
char_preset = st.select_slider("", options=[500, 1000, 2000, 3000, 5000, 8000, 10000], value=8000, label_visibility="collapsed")
char_count = st.number_input("カスタム文字数（スライダーより優先）", min_value=500, max_value=15000, value=char_preset, step=500)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 生成ボタン
# ─────────────────────────────────────────────
if mode == "mashup":
    btn_label = "🔀 マッシュアップ鑑定を生成する"
elif mode == "rewrite":
    btn_label = "✏️ おだんご節にリライトする"
else:
    btn_label = "✨ おだんご節で執筆する"

if st.button(btn_label):
    if not client_name.strip():
        st.error("クライアント名を入力してください。")
    else:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            st.error("APIキーが設定されていません。")
        else:
            # ルノルマンのグリッドからraw_dataを生成
            if method_key == "lenormand" and grand_tableau_grid:
                tableau_text = build_grand_tableau_text(grand_tableau_grid, person_setting)
                extra = st.session_state.get("raw_data_lenormand_extra", "")
                raw_data = tableau_text + ("\n\n【追記】\n" + extra if extra else "")
            elif mode == "mashup" and method_key2 == "lenormand" and grand_tableau_grid:
                tableau_text = build_grand_tableau_text(grand_tableau_grid, person_setting)
                raw_data2 = tableau_text

            if mode == "mashup":
                system_prompt = get_mashup_system_prompt(method_key, method_key2, person_setting if person_setting else None)
                user_message = build_mashup_user_message(
                    client_name=client_name,
                    consultation=consultation,
                    method_label1=FORTUNE_METHODS[method_key],
                    method_label2=FORTUNE_METHODS[method_key2],
                    raw_data1=raw_data,
                    raw_data2=raw_data2,
                    memo=memo,
                    char_count=char_count,
                )
            else:
                system_prompt = get_system_prompt(method_key, person_setting if person_setting else None)
                user_message = build_user_message(
                    client_name=client_name,
                    consultation=consultation,
                    consultation_text=consultation_text,
                    method_label=FORTUNE_METHODS[method_key],
                    raw_data=raw_data,
                    memo=memo,
                    char_count=char_count,
                    mode=mode,
                )

            client = anthropic.Anthropic(api_key=api_key)

            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-label">✦ 生成原稿</div>', unsafe_allow_html=True)

            summary_parts = []
            if consultation:
                summary_parts.append(f"📌 相談ジャンル：{consultation}")
            if consultation_text:
                summary_parts.append(f"💬 依頼文章：{consultation_text}")
            if grand_tableau_grid:
                filled = sum(1 for c in grand_tableau_grid if c != "（未選択）")
                summary_parts.append(f"🌹 グラン・タブロー：{filled}枚入力済み")
            elif raw_data:
                summary_parts.append(f"🎴 出目：{raw_data}")
            if memo:
                summary_parts.append(f"📝 補足メモ：{memo}")
            if person_setting:
                lady_desc = person_setting.get("lady_custom") if person_setting.get("lady_role") == "その他" else person_setting.get("lady_role", "")
                knight_desc = person_setting.get("knight_custom") if person_setting.get("knight_role") == "その他" else person_setting.get("knight_role", "")
                summary_parts.append(f"🌹 人物設定：淑女＝{lady_desc}　紳士＝{knight_desc}　依頼者：{person_setting.get('client_gender', '')}")

            if summary_parts:
                summary_text = "\n".join(summary_parts)
                st.markdown(
                    f'<div style="background:rgba(196,164,255,0.07);border:1px solid rgba(196,164,255,0.2);border-radius:10px;padding:16px;margin-bottom:16px;font-size:13px;line-height:1.8;color:rgba(232,213,183,0.7);white-space:pre-wrap;">{summary_text}</div>',
                    unsafe_allow_html=True,
                )

            output_placeholder = st.empty()
            full_output = ""

            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                for text in stream.text_stream:
                    full_output += text
                    output_placeholder.markdown(
                        f'<div class="output-box">{full_output.replace(chr(10), "<br>")}</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown('<div class="section-label" style="margin-top:16px;">✦ コピー用</div>', unsafe_allow_html=True)
            st.text_area("", value=full_output, height=300, label_visibility="collapsed", key="copy_area")
            st.caption(f"📝 文字数：{len(full_output)}字")

# ─────────────────────────────────────────────
# フッター
# ─────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; margin-top:48px; padding-bottom:32px;">
    <div style="font-size:11px; letter-spacing:3px; color:rgba(196,164,255,0.4);">🍡 ODANGO ENGINE v1.6 ✦ Private Use Only</div>
</div>
""", unsafe_allow_html=True)
