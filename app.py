import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from gtts import gTTS
import base64
from io import BytesIO
from deep_translator import GoogleTranslator
import eng_to_ipa
import time
import re
import uuid
import random

# ==========================================
# 1. 頁面設定
# ==========================================
VERSION = "v48.1 (Fix Error & Restore Features)"
st.set_page_config(page_title="職場英文生存術", layout="wide", page_icon="🏭")

# ==========================================
# 2. CSS 樣式 (維持不變)
# ==========================================
st.markdown("""
<style>
    .main { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f8f9fa; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* 登入畫面 */
    .login-container {
        background-color: white; padding: 40px 20px; border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center;
        margin: 20px auto; max-width: 600px; border-top: 8px solid #1E88E5;
    }
    .login-slogan { font-size: 24px; font-weight: 900; color: #1565C0; margin-bottom: 10px; }
    .login-sub { font-size: 16px; color: #555; margin-bottom: 30px; }
    
    /* 輸入框優化 */
    .stTextInput>div>div>input {
        color: #333 !important; background-color: #ffffff !important; border: 1px solid #ddd;
    }

    /* 頂部標題區 */
    .header-box {
        background: white; padding: 15px; border-radius: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px;
    }

    /* 統計數字卡 */
    .stat-box {
        background: #e3f2fd; border-radius: 10px; padding: 10px;
        text-align: center; border: 1px solid #bbdefb;
    }
    .stat-num { font-size: 24px; font-weight: bold; color: #1565C0; }
    .stat-label { font-size: 12px; color: #555; }

    /* 列表模式：單行顯示 */
    .list-row {
        background: white; padding: 12px 15px; margin-bottom: 8px;
        border-radius: 10px; border-left: 5px solid #4CAF50;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        display: flex; align-items: center; justify-content: space-between;
    }
    .list-word { font-size: 18px; font-weight: bold; color: #2e7d32; margin-right: 8px; }
    .list-ipa { font-size: 14px; color: #757575; font-family: monospace; margin-right: 15px; }
    .list-mean { font-size: 16px; color: #1565C0; font-weight: 500; flex-grow: 1; }

    /* 卡片模式 */
    .card-box {
        background-color: white; padding: 30px 20px; border-radius: 20px;
        text-align: center; border: 3px solid #81C784; min-height: 250px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .card-word { font-size: 42px; font-weight: bold; color: #2E7D32; margin-bottom: 5px; line-height: 1.1; }
    .card-ipa { font-size: 18px; color: #666; margin-bottom: 20px; }

    /* 按鈕樣式 */
    .stButton>button { border-radius: 20px; font-weight: bold; width: 100%; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 核心功能函式
# ==========================================

@st.cache_data(ttl=60, show_spinner=False)
def get_google_sheet_data():
    try:
        creds_json = json.loads(st.secrets["service_account"]["info"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        sheet = client.open("vocab_db").sheet1
        data = sheet.get_all_records()
        if not data: return pd.DataFrame(columns=['User', 'Notebook', 'Word', 'IPA', 'Chinese', 'Date'])
        df = pd.DataFrame(data)
        for c in ['User', 'Notebook', 'Word', 'IPA', 'Chinese', 'Date']:
            if c not in df.columns: df[c] = ""
        df['User'] = df['User'].astype(str).str.strip()
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
        if 'User' in df.columns: df['User'] = df['User'].astype(str).str.strip()
        df = df[['User', 'Notebook', 'Word', 'IPA', 'Chinese', 'Date']].fillna("")
        update_data = [df.columns.values.tolist()] + df.values.tolist()
        sheet.update(update_data)
        get_google_sheet_data.clear()
    except Exception as e: st.error(f"儲存失敗：{e}")

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

@st.cache_data(show_spinner=False)
def get_audio_base64(text, lang='en', tld='com', slow=False):
    try:
        if not text: return None
        tts = gTTS(text=str(text), lang=lang, tld=tld, slow=slow)
        fp = BytesIO()
        tts.write_to_fp(fp)
        return base64.b64encode(fp.getvalue()).decode()
    except: return None

def get_audio_html(text, lang='en', tld='com', slow=False, autoplay=False, visible=True):
    b64 = get_audio_base64(text, lang, tld, slow)
    if not b64: return ""
    rand_id = f"audio_{uuid.uuid4()}" 
    display_style = "display:none;" if (not visible) else "width: 100%; margin-top: 5px;"
    autoplay_attr = "autoplay" if autoplay else ""
    return f"""<audio id="{rand_id}" controls {autoplay_attr} style="{display_style}"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>"""

# ★★★ 關鍵修正：使用 Callback 處理加入單字，避免紅字錯誤 ★★★
def save_word_callback():
    w_in = st.session_state.input_word
    
    # 決定筆記本
    if st.session_state.nb_mode == "✨ 建立新本":
        target_nb = st.session_state.new_nb_name
    else:
        target_nb = st.session_state.exist_nb_name
        
    current_user = st.session_state.current_user
    df = st.session_state.df

    if w_in and target_nb:
        if check_duplicate(df, current_user, target_nb, w_in):
            st.session_state.msg_warning = f"'{w_in}' 已經在 [{target_nb}] 裡面囉！"
        else:
            try:
                ipa = f"[{eng_to_ipa.convert(w_in)}]"
                trans = GoogleTranslator(source='auto', target='zh-TW').translate(w_in)
                new = {'User': current_user, 'Notebook': target_nb, 'Word': w_in, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                st.session_state.df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                save_to_google_sheet(st.session_state.df)
                st.session_state.msg_success = f"✅ 已加入：{w_in} (到 {target_nb})"
                st.session_state.input_word = "" # 清空輸入框
            except Exception as e:
                st.session_state.msg_warning = f"錯誤: {e}"
    else:
        st.session_state.msg_warning = "請輸入單字和筆記本名稱"

def batch_add_callback():
    final_text = st.session_state.ocr_editor
    
    # 決定筆記本
    if st.session_state.nb_mode == "✨ 建立新本":
        target_nb = st.session_state.new_nb_name
    else:
        target_nb = st.session_state.exist_nb_name

    current_user = st.session_state.current_user
    df = st.session_state.df
    
    words_to_add = [w.strip() for w in re.split(r'[,\n ]', final_text) if w.strip()]
    new_entries = []
    skipped = 0
    
    if not target_nb:
        st.session_state.msg_warning = "請選擇或建立筆記本"
        return

    for w in words_to_add:
        if not w or not re.match(r'^[a-zA-Z]+$', w): continue
        if check_duplicate(df, current_user, target_nb, w): skipped += 1
        else:
            try:
                ipa = f"[{eng_to_ipa.convert(w)}]"
                trans = GoogleTranslator(source='auto', target='zh-TW').translate(w)
                new_entries.append({'User': current_user, 'Notebook': target_nb, 'Word': w, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')})
            except: pass
    
    if new_entries:
        st.session_state.df = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
        save_to_google_sheet(st.session_state.df)
        st.session_state.msg_success = f"✅ 批次加入 {len(new_entries)} 筆！(略過 {skipped} 重複)"
        st.session_state.ocr_editor = ""
    elif skipped > 0: st.session_state.msg_warning = f"⚠️ 所有 {skipped} 筆都重複了"
    else: st.session_state.msg_warning = "⚠️ 無有效單字"

# ==========================================
# 4. 狀態管理
# ==========================================

def initialize_session_state():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'df' not in st.session_state: st.session_state.df = get_google_sheet_data()
    if 'play_order' not in st.session_state: st.session_state.play_order = ["英文", "中文", "英文"] 
    if 'accent_tld' not in st.session_state: st.session_state.accent_tld = 'com'
    if 'is_slow' not in st.session_state: st.session_state.is_slow = False
    
    if 'show_settings' not in st.session_state: st.session_state.show_settings = False
    if 'show_download' not in st.session_state: st.session_state.show_download = False
    if 'input_word' not in st.session_state: st.session_state.input_word = ""
    
    if 'msg_success' not in st.session_state: st.session_state.msg_success = ""
    if 'msg_warning' not in st.session_state: st.session_state.msg_warning = ""

# ======
