import streamlit as st
import pandas as pd
import json
import base64
from io import BytesIO
import time
import random
import uuid

# --- 0. 檢查套件 (防止白屏) ---
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    from gtts import gTTS
    from deep_translator import GoogleTranslator
    import eng_to_ipa
except ImportError as e:
    st.error(f"❌ 程式無法執行，因為缺少套件: {e}")
    st.stop()

# ==========================================
# 1. 核心設定
# ==========================================
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

VERSION = "v57.0 (Mobile Final Fix)"
st.set_page_config(page_title="職場英文生存術", layout="wide", page_icon="🏭")

# ==========================================
# 2. CSS 樣式 (請勿刪除任何引號)
# ==========================================
st.markdown("""
<style>
    /* --- 全域強制設定 (解決深色模式黑屏問題) --- */
    .stApp {
        background-color: #f0f2f6; /* 強制淺灰背景 */
    }
    
    /* 隱藏選單 */
    #MainMenu, footer { visibility: hidden; }

    /* --- 關鍵：強制手機版欄位「絕對不換行」 --- */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important; /* 禁止換行 */
        gap: 2px !important;         /* 縮小間距 */
        overflow-x: hidden !important;
    }
    
    /* 強制縮小欄位寬度，讓4個按鈕能擠在手機畫面 */
    [data-testid="column"] {
        min-width: 0px !important;
        padding: 0px 1px !important;
        flex: 1 !important;
    }

    /* --- 按鈕樣式優化 --- */
    .stButton > button {
        padding: 0px !important;
        font-size: 12px !important;
        height: 35px !important;
        min-height: 35px !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        border: 1px solid #ccc !important;
        background-color: #ffffff !important;
        color: #333 !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        border-color: #4CAF50 !important;
        color: #4CAF50 !important;
    }

    /* --- 連結按鈕 (G翻譯/Y字典) --- */
    a.custom-link-btn {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        height: 35px;
        background-color: #ffffff;
        color: #333333;
        text-decoration: none;
        border-radius: 8px;
        border: 1px solid #ccc;
        font-weight: bold;
        font-size: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        white-space: nowrap; /* 文字不換行 */
        z-index: 10;
        position: relative;
    }
    a.custom-link-btn:hover {
        border-color: #2196F3;
        color: #2196F3;
        background-color: #f8faff;
    }

    /* --- 列表卡片 (強制白底黑字) --- */
    .list-card {
        background-color: #ffffff !important;
        padding: 10px;
        margin-bottom: 5px;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* 單字排版 */
    .word-row {
        display: flex;
        align-items: baseline;
        gap: 5px;
        margin-bottom: 5px;
        flex-wrap: wrap;
    }
    .list-word { font-size: 18px; font-weight: 900; color: #2e7d32 !important; margin-right: 5px; }
    .list-ipa { font-size: 13px; color: #666 !important; font-family: monospace; }
    .list-mean { font-size: 16px; color: #1565C0 !important; font-weight: bold; }

    /* --- 卡片模式 --- */
    .card-box {
        background-color: #ffffff !important; 
        padding: 20px; 
        border-radius: 15px;
        text-align: center; 
        border: 3px solid #81C784; 
        min-height: 200px;
        margin-bottom: 15px;
    }
    .card-word { font-size: 32px; font-weight: 900; color: #2E7D32 !important; margin-bottom: 10px; }
    
    /* 解決輸入框在深色模式看不見的問題 */
    .stTextInput input {
        color: #333 !important;
        background-color: #fff !important;
    }

    .version-tag { text-align: center; color: #aaa; font-size: 10px; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 核心功能函式
# ==========================================
@st.cache_data(ttl=60, show_spinner=False)
def get_google_sheet_data():
    try:
        if "service_account" not in st.secrets: return pd.DataFrame(columns=['User', 'Notebook', 'Word', 'IPA', 'Chinese', 'Date'])
        creds_json = json.loads(st.secrets["service_account"]["info"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        sheet = client.open("vocab_db").sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return pd.DataFrame(columns=['User', 'Notebook', 'Word', 'IPA', 'Chinese', 'Date'])
        return df.fillna("")
    except: return pd.DataFrame(columns=['User', 'Notebook', 'Word', 'IPA', 'Chinese', 'Date'])

def save_to_google_sheet(df):
    try:
        creds_json = json.loads(st.secrets["service_account"]["info"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        sheet = client.open("vocab_db").sheet1
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        get_google_sheet_data.clear()
    except Exception as e: st.error(f"儲存失敗: {e}")

def get_audio_html(text, lang='en', tld='com', slow=False, autoplay=False, visible=True):
    try:
        if not text: return ""
        tts = gTTS(text=str(text), lang=lang, tld=tld, slow=slow)
        fp = BytesIO(); tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        rand_id = f"audio_{uuid.uuid4()}"
        autoplay_attr = "autoplay" if autoplay else ""
        style = "width: 100%; height: 30px;" if visible else "width: 0; height: 0; display: none;"
        # 手機版自動播放腳本
        js = f"""<script>
            setTimeout(function() {{
                var audio = document.getElementById("{rand_id}");
                if (audio) {{ audio.play().catch(e => console.log(e)); }}
            }}, 100);
        </script>""" if autoplay else ""
        
        return f"""
            <audio id="{rand_id}" controls {autoplay_attr} style="{style}" preload="auto">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            {js}
        """
    except: return ""

def check_duplicate(df, user, notebook, word):
    if df.empty: return False
    mask = ((df['User'].astype(str).str.strip() == str(user).strip()) & 
            (df['Notebook'].astype(str).str.strip() == str(notebook).strip()) & 
            (df['Word'].astype(str).str.strip().str.lower() == str(word).strip().lower()))
    return not df[mask].empty

# ==========================================
# 4. 主程式邏輯
# ==========================================

def initialize_session_state():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'df' not in st.session_state: st.session_state.df = get_google_sheet_data()
    if 'play_order' not in st.session_state: st.session_state.play_order = ["英文", "中文"]
    if 'accent_tld' not in st.session_state: st.session_state.accent_tld = 'com'
    if 'is_slow' not in st.session_state: st.session_state.is_slow = False
    if 'is_sliding' not in st.session_state: st.session_state.is_sliding = False
    if 'card_idx' not in st.session_state: st.session_state.card_idx = 0

def main_page():
    df_all = st.session_state.df
    current_user = st.session_state.current_user
    df = df_all[df_all['User'] == current_user]
    notebooks = sorted(list(set(df['Notebook'].dropna().unique().tolist())))
    if 'Default' not in notebooks: notebooks.append('Default')

    # 頂部導航
    c1, c2 = st.columns([6, 4])
    with c1: st.markdown(f"**Hi, {current_user}**")
    with c2:
        b1, b2 = st.columns(2)
        with b1: 
            if st.button("設定"): st.toast("功能開發中")
        with b2: 
            if st.button("下載"): st.toast("功能開發中")

    # --- 新增單字 ---
    st.write("📝 **新增單字**")
    nb_mode = st.radio("來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed")
    
    if nb_mode == "選擇現有":
        target_nb = st.selectbox("筆記本", notebooks, label_visibility="collapsed")
    else:
        target_nb = st.text_input("新筆記本", placeholder="例如: 會議")

    w_in = st.text_input("單字", placeholder="例如: Polymer")
    
    # 批量輸入
    with st.expander("📂 批量輸入 (英文,逗號隔開)"):
        batch_text = st.text_area("例如: apple, banana, dog", height=80)
        if st.button("批量加入", use_container_width=True):
            if not target_nb: st.error("請選筆記本"); st.stop()
            words = batch_text.replace('\n', ',').split(',')
            cnt = 0
            for w in words:
                w = w.strip()
                if w and not check_duplicate(st.session_state.df, current_user, target_nb, w):
                    try:
                        ipa = f"[{eng_to_ipa.convert(w)}]"
                        trans = GoogleTranslator(source='auto', target='zh-TW').translate(w)
                        new = {'User': current_user, 'Notebook': target_nb, 'Word': w, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new])], ignore_index=True)
                        cnt += 1
                    except: pass
            if cnt > 0:
                save_to_google_sheet(st.session_state.df)
                st.success(f"已加入 {cnt} 個！"); time.sleep(1); safe_rerun()

    # 按鈕列
    b_trans, b_listen = st.columns(2)
    with b_trans:
        if st.button("👀 翻譯"):
            if w_in: st.info(GoogleTranslator(source='auto', target='zh-TW').translate(w_in))
    with b_listen:
        if st.button("🔊 試聽"):
            if w_in: st.markdown(get_audio_html(w_in, autoplay=True), unsafe_allow_html=True)
            
    if st.button("➕ 加入單字庫", type="primary"):
        if w_in and target_nb:
            if check_duplicate(st.session_state.df, current_user, target_nb, w_in):
                st.toast("已存在")
            else:
                ipa = f"[{eng_to_ipa.convert(w_in)}]"
                trans = GoogleTranslator(source='auto', target='zh-TW').translate(w_in)
                new = {'User': current_user, 'Notebook': target_nb, 'Word': w_in, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new])], ignore_index=True)
                save_to_google_sheet(st.session_state.df)
