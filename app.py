import os
import anthropic
import streamlit as st
from prompt import FORTUNE_METHODS, get_system_prompt, build_user_message, get_mashup_system_prompt, build_mashup_user_message

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

st.markdown('<div class="section-label">✦ 出目（任意）</div>', unsafe_allow_html=True)
raw_data = st.text_area("", placeholder="カード名・星の配置・サイコロの出目など", height=150, label_visibility="collapsed", key="raw_data")

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

# マッシュアップ用の追加入力（モード選択の直後）
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
    elif not raw_data.strip() and mode == "rewrite":
        st.error("リライトモードでは下書きを入力してください。")
    elif mode == "mashup" and not raw_data2.strip():
        st.error("占術２の生データを入力してください。")
    else:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            st.error("APIキーが設定されていません。Streamlit CloudのSecretsを確認してください。")
        else:
            if mode == "mashup":
                system_prompt = get_mashup_system_prompt(method_key, method_key2)
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
                system_prompt = get_system_prompt(method_key)
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

            # 入力サマリー表示
            summary_parts = []
            if consultation:
                summary_parts.append(f"📌 相談ジャンル：{consultation}")
            if consultation_text:
                summary_parts.append(f"💬 依頼文章：{consultation_text}")
            if raw_data:
                summary_parts.append(f"🎴 出目：{raw_data}")
            if memo:
                summary_parts.append(f"📝 補足メモ：{memo}")

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
    <div style="font-size:11px; letter-spacing:3px; color:rgba(196,164,255,0.4);">🍡 ODANGO ENGINE v1.1 ✦ Private Use Only</div>
</div>
""", unsafe_allow_html=True)
