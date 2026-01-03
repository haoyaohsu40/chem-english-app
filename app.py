import streamlit as st
import pandas as pd
import json
import base64
from io import BytesIO
import time
import random
import uuid
import urllib.parse # 新增這行，用來修復G翻譯帶入單字的問題

# ==========================================
# 1. 核心設定 (防止白屏，放最上面)
# ==========================================
st.set_page_config(page_title="職場英文生存術", layout="wide", page_icon="🏭")

VERSION = "v63.0 (V54 Base + Fixes)"

# ==========================================
# 2. 安全引用套件
# ==========================================
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    from gtts import gTTS
    from deep_translator import GoogleTranslator
    import eng_to_ipa
    PACKAGES_OK = True
except ImportError as e:
    st.error(f"❌ 缺少必要套件: {e}")
    PACKAGES_OK = False

# ==========================================
# 3. 核心功能函式
# ==========================================
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

@st.cache_data(ttl=60, show_spinner=False)
def get_google_sheet_data():
    if not PACKAGES_OK: return pd.DataFrame(columns=['User', 'Notebook', 'Word', 'IPA', 'Chinese', 'Date'])
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
    if not PACKAGES_OK: return
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
    if not PACKAGES_OK: return ""
    try:
        if not text: return ""
        tts = gTTS(text=str(text), lang=lang, tld=tld, slow=slow)
        fp = BytesIO(); tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        rand_id = f"audio_{uuid.uuid4()}"
        autoplay_attr = "autoplay" if autoplay else ""
        style = "width: 100%; height: 35px;" if visible else "width: 0; height: 0; display: none;"
        
        # 手機版自動播放增強腳本
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

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# ==========================================
# 4. CSS 樣式 (基於 V54，加入手機橫排修正)
# ==========================================
st.markdown("""
<style>
    /* 全域設定 */
    .main { background-color: #f8f9fa; }
    #MainMenu, footer { visibility: hidden; }

    /* --- [關鍵修正] 強制手機版按鈕橫排不換行 --- */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important; /* 禁止換行 */
        gap: 3px !important;         /* 縮小間距 */
        overflow-x: auto !important; /* 允許左右滑動以防切到 */
        align-items: center !important;
    }
    
    [data-testid="column"] {
        min-width: 0px !important; /* 允許欄位縮到很小 */
        padding: 0px 1px !important;
        flex: 1 !important;
    }

    /* --- 列表卡片 --- */
    .list-card {
        background: #ffffff;
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 12px;
        border-left: 6px solid #4CAF50;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    .word-row {
        display: flex;
        align-items: baseline;
        gap: 8px;
        margin-bottom: 8px;
        flex-wrap: wrap;
    }

    .list-word { font-size: 20px; font-weight: 900; color: #2e7d32; }
    .list-ipa { font-size: 14px; color: #888; font-family: monospace; }
    .list-mean { font-size: 16px; color: #1565C0; font-weight: bold; }

    /* --- 卡片與測驗 --- */
    .card-box {
        background-color: #ffffff; 
        padding: 30px 20px; 
        border-radius: 15px;
        text-align: center; 
        border: 3px solid #81C784; 
        min-height: 220px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
        margin-bottom: 15px;
        display: flex; 
        flex-direction: column; 
        justify-content: center;
        align-items: center;
    }
    
    .quiz-card {
        background-color: #fffde7;
        padding: 20px; 
        border-radius: 15px;
        text-align: center; 
        border: 2px dashed #fbc02d; 
        margin-bottom: 15px;
    }
    
    .card-word { font-size: 40px; font-weight: 900; color: #2E7D32; margin-bottom: 10px; }
    .card-ipa { font-size: 18px; color: #666; margin-bottom: 15px; }
    .quiz-word { font-size: 32px; font-weight: 900; color: #1565C0; margin: 10px 0; }
    
    /* 按鈕微調 (高度統一) */
    .stButton>button { 
        border-radius: 8px; 
        font-weight: bold; 
        width: 100%; 
        min-height: 38px; 
        height: 38px;
        padding: 0px !important;
        font-size: 13px !important;
    }
    
    /* 連結按鈕樣式 (模擬 Streamlit 按鈕) */
    a.custom-link-btn {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        height: 38px;
        background-color: #f0f2f6;
        color: #31333F;
        text-decoration: none;
        border-radius: 8px;
        border: 1px solid #d6d6d8;
        font-weight: 600;
        font-size: 13px;
        z-index: 10; 
        position: relative;
    }
    a.custom-link-btn:hover {
        border-color: #f63366;
        color: #f63366;
    }

    .version-tag { text-align: center; color: #aaa; font-size: 10px; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 5. 頁面邏輯
# ==========================================

def initialize_session_state():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'df' not in st.session_state: st.session_state.df = get_google_sheet_data()
    if 'current_page' not in st.session_state: st.session_state.current_page = "main"
    if 'play_order' not in st.session_state: st.session_state.play_order = ["英文", "中文"]
    if 'accent_tld' not in st.session_state: st.session_state.accent_tld = 'com'
    if 'is_slow' not in st.session_state: st.session_state.is_slow = False
    if 'nb_mode' not in st.session_state: st.session_state.nb_mode = "選擇現有"
    if 'is_sliding' not in st.session_state: st.session_state.is_sliding = False
    
    # 測驗/拼字變數
    for k in ['quiz_current', 'quiz_score', 'quiz_total', 'quiz_answered', 'quiz_options']:
        if k not in st.session_state: st.session_state[k] = None if 'current' in k or 'options' in k else 0
    for k in ['spell_current', 'spell_input', 'spell_checked', 'spell_correct', 'spell_score', 'spell_total']:
         if k not in st.session_state: st.session_state[k] = "" if 'input' in k else (None if 'current' in k else 0)

# --- 設定頁面 (已修復) ---
def settings_page():
    st.subheader("⚙️ 設定")
    if st.button("🔙 返回", use_container_width=True): st.session_state.current_page = "main"; safe_rerun()
    st.divider()
    
    st.write("**發音設定:**")
    acc = st.selectbox("口音", ["美式 (com)", "英式 (co.uk)"])
    st.session_state.accent_tld = "co.uk" if "英式" in acc else "com"
    
    st.divider()
    st.write("**輪播順序:**")
    c1, c2, c3 = st.columns(3)
    if c1.button("英文"): st.session_state.play_order.append("英文")
    if c2.button("中文"): st.session_state.play_order.append("中文")
    if c3.button("清空"): st.session_state.play_order = []
    st.info(f"目前順序: {st.session_state.play_order}")
    
    st.divider()
    if st.button("🚪 登出", type="secondary", use_container_width=True):
        st.session_state.logged_in = False; st.session_state.current_page = "main"; safe_rerun()

# --- 下載頁面 (已修復) ---
def download_page():
    st.subheader("📥 下載")
    if st.button("🔙 返回", use_container_width=True): st.session_state.current_page = "main"; safe_rerun()
    st.divider()
    
    df = st.session_state.df
    user_df = df[df['User'] == st.session_state.current_user]
    st.write(f"您的單字總數: {len(user_df)}")
    
    if not user_df.empty:
        # 下載 Excel
        st.download_button("📥 下載 Excel", data=to_excel(user_df), file_name="vocab.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.s
