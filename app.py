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
VERSION = "v48.0 (Mobile Layout Refined)"
st.set_page_config(page_title="職場英文生存術", layout="wide", page_icon="🏭")

# ==========================================
# 2. CSS 樣式 (針對手機優化)
# ==========================================
st.markdown("""
<style>
    .main { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f8f9fa; }
    
    /* 隱藏預設選單 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* 登入畫面樣式 */
    .login-container {
        background-color: white; padding: 40px 20px; border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center;
        margin: 20px auto; max-width: 600px; border-top: 8px solid #1E88E5;
    }
    .login-slogan { font-size: 24px; font-weight: 900; color: #1565C0; margin-bottom: 10px; }
    .login-sub { font-size: 16px; color: #555; margin-bottom: 30px; }
    
    /* 輸入框樣式優化 (解決白底白字問題) */
    .stTextInput>div>div>input {
        color: #333 !important;
        background-color: #ffffff !important;
        border: 1px solid #ddd;
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
    .card-word { font-size: 42px; font-weight: bold; color: #2E7D32; margin-bottom: 5px; line-height: 1.1; } /* 字體改小 */
    .card-ipa { font-size: 18px; color: #666; margin-bottom: 20px; }

    /* 按鈕樣式 */
    .stButton>button {
        border-radius: 20px; font-weight: bold; width: 100%;
    }
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
        cols = ['User', 'Notebook', 'Word', 'IPA', 'Chinese', 'Date']
        if not data: return pd.DataFrame(columns=cols)
        df = pd.DataFrame(data)
        # 補齊欄位
        for c in cols:
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
        cols = ['User', 'Notebook', 'Word', 'IPA', 'Chinese', 'Date']
        # 移除不需要的欄位 (如 Password)
        for c in cols:
             if c not in df.columns: df[c] = ""
        df = df[cols].fillna("")
        update_data = [df.columns.values.tolist()] + df.values.tolist()
        sheet.update(update_data)
        get_google_sheet_data.clear()
    except Exception as e: st.error(f"儲存失敗：{e}")

def check_duplicate(df, user, notebook, word):
    if df.empty: return False
    user_str = str(user).strip()
    nb_str = str(notebook).strip()
    word_str = str(word).strip().lower()
    temp_df = df.copy()
    temp_df['norm_user'] = temp_df['User'].astype(str).str.strip()
    temp_df['norm_nb'] = temp_df['Notebook'].astype(str).str.strip()
    temp_df['norm_word'] = temp_df['Word'].astype(str).str.strip().str.lower()
    mask = ((temp_df['norm_user'] == user_str) & (temp_df['norm_nb'] == nb_str) & (temp_df['norm_word'] == word_str))
    return not temp_df[mask].empty

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

def is_contains_chinese(string):
    for char in str(string):
        if '\u4e00' <= char <= '\u9fff': return True
    return False

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

def add_words_callback():
    final_text = st.session_state.ocr_editor
    target_nb = st.session_state.target_nb_key
    current_user = str(st.session_state.current_user).strip()
    df = st.session_state.df
    
    words_to_add = [w.strip() for w in re.split(r'[,\n ]', final_text) if w.strip()]
    new_entries = []
    skipped = 0
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
        df_all = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
        st.session_state.df = df_all; save_to_google_sheet(df_all)
        st.session_state.msg_success = f"✅ 成功加入 {len(new_entries)} 筆！(略過 {skipped} 重複)"
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
    
    # 功能狀態
    if 'show_settings' not in st.session_state: st.session_state.show_settings = False
    if 'show_download' not in st.session_state: st.session_state.show_download = False
    if 'input_word' not in st.session_state: st.session_state.input_word = ""
    
    if 'msg_success' not in st.session_state: st.session_state.msg_success = ""
    if 'msg_warning' not in st.session_state: st.session_state.msg_warning = ""

# ==========================================
# 5. 頁面佈局
# ==========================================

def login_page():
    st.markdown("""
        <div class="login-container">
            <div class="login-slogan">💼 職場英文生存術</div>
            <div class="login-sub">聽懂主管在說什麼，不再鴨子聽雷</div>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 6, 1])
    with c2:
        user_input = st.text_input("請輸入您的 英文ID / 姓名", placeholder="例如: Tony, Alex...", key="login_user")
        if st.button("🚀 進入我的單字庫", type="primary", use_container_width=True):
            if user_input:
                st.session_state.current_user = user_input.strip()
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("請輸入 ID")

def main_app():
    # 顯示訊息
    if st.session_state.msg_success:
        st.toast(st.session_state.msg_success, icon="✅")
        st.session_state.msg_success = "" 
    if st.session_state.msg_warning:
        st.toast(st.session_state.msg_warning, icon="⚠️")
        st.session_state.msg_warning = ""

    df_all = st.session_state.df
    current_user = st.session_state.current_user
    df = df_all[df_all['User'] == current_user]

    # --- Header Area (新增單字 + 設定 + 下載) ---
    with st.container():
        st.markdown('<div class="header-box">', unsafe_allow_html=True)
        
        # Top Row: Title & Icons
        h1, h2, h3 = st.columns([6, 1, 1])
        with h1: st.write(f"👋 Hi, **{current_user}**")
        with h2: 
            if st.button("⚙️", help="設定"): st.session_state.show_settings = not st.session_state.show_settings
        with h3: 
            if st.button("📥", help="下載"): st.session_state.show_download = not st.session_state.show_download
        
        # Settings Panel (Toggle)
        if st.session_state.show_settings:
            with st.expander("⚙️ 進階設定", expanded=True):
                accents = {'美式 (US)': 'com', '英式 (UK)': 'co.uk'}
                st.session_state.accent_tld = accents[st.selectbox("口音", list(accents.keys()))]
                st.session_state.is_slow = st.checkbox("慢速發音", value=st.session_state.is_slow)
                if st.button("🚪 登出", type="secondary"): st.session_state.logged_in = False; st.rerun()
        
        # Download Panel (Toggle)
        if st.session_state.show_download:
             with st.expander("📥 下載資料", expanded=True):
                 if not df.empty:
                     st.download_button("下載 Excel", to_excel(df), "vocab.xlsx", use_container_width=True)
                 else: st.info("無資料可下載")

        # --- Input Area (依照手繪稿) ---
        input_mode = st.radio("模式", ["單字", "批次"], horizontal=True, label_visibility="collapsed")
        
        # 筆記本選擇 (放在輸入區附近)
        notebooks = df['Notebook'].unique().tolist()
        if 'Default' not in notebooks: notebooks.append('Default')
        target_nb = st.selectbox("存入筆記本", notebooks, key="target_nb_key")

        if input_mode == "單字":
            w_in = st.text_input("輸入英文單字 (如: Coordinate)", key="input_word")
            
            b1, b2, b3 = st.columns([1, 1, 2])
            with b1: 
                if st.button("👀 翻譯", use_container_width=True):
                    if w_in: st.info(GoogleTranslator(source='auto', target='zh-TW').translate(w_in))
            with b2:
                if st.button("🔊 試聽", use_container_width=True):
                    if w_in: st.markdown(get_audio_html(w_in, tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
            with b3:
                if st.button("➕ 加入", type="primary", use_container_width=True):
                    if w_in and target_nb:
                        if check_duplicate(df, current_user, target_nb, w_in):
                            st.session_state.msg_warning = f"'{w_in}' 已經有了！"
                        else:
                            ipa = f"[{eng_to_ipa.convert(w_in)}]"
                            trans = GoogleTranslator(source='auto', target='zh-TW').translate(w_in)
                            new = {'User': current_user, 'Notebook': target_nb, 'Word': w_in, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                            st.session_state.df = pd.concat([df_all, pd.DataFrame([new])], ignore_index=True)
                            save_to_google_sheet(st.session_state.df)
                            st.session_state.msg_success = f"已加入：{w_in}"
                            st.session_state.input_word = ""; st.rerun()
        else:
            st.text_area("批次貼上 (空格分隔)", key="ocr_editor")
            if st.button("🚀 批次加入", type="primary", on_click=add_words_callback): pass
            
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Stats & Notebook Filter ---
    c_s1, c_s2 = st.columns(2)
    with c_s1: 
        st.markdown(f'<div class="stat-box"><div class="stat-num">{len(df_all)}</div><div class="stat-label">☁️ 雲端總數</div></div>', unsafe_allow_html=True)
    with c_s2:
        filter_nb = st.selectbox("複習筆記本", ["全部"] + notebooks, label_visibility="collapsed")
        filtered_df = df if filter_nb == "全部" else df[df['Notebook'] == filter_nb]
        st.caption(f"目前顯示: {len(filtered_df)} 字")

    st.divider()

    # --- Main Tabs ---
    tabs = st.tabs(["列表", "卡片", "輪播", "測驗", "拼字"])
    
    # 1. 列表 (單行簡潔版)
    with tabs[0]:
        if not filtered_df.empty:
            # 反轉順序顯示最新的在上面
            for i, row in filtered_df.iloc[::-1].iterrows():
                # 使用 Flexbox 模擬單行
                col_w, col_btn = st.columns([5, 1])
                with col_w:
                     st.markdown(f"""
                     <div class="list-row">
                        <div>
                            <span class="list-word">{row['Word']}</span>
                            <span class="list-ipa">{row['IPA']}</span>
                            <span class="list-mean">{row['Chinese']}</span>
                        </div>
                     </div>
                     """, unsafe_allow_html=True)
                with col_btn:
                    if st.button("🗑️", key=f"del_{i}"):
                        st.session_state.df = df_all.drop(i)
                        save_to_google_sheet(st.session_state.df)
                        st.rerun()
        else: st.info("目前沒有單字")

    # 2. 卡片 (字體縮小)
    with tabs[1]:
        if not filtered_df.empty:
            if 'card_idx' not in st.session_state: st.session_state.card_idx = 0
            idx = st.session_state.card_idx % len(filtered_df)
            row = filtered_df.iloc[idx]
            
            st.markdown(f"""
            <div class="card-box">
                <div class="card-word">{row['Word']}</div>
                <div class="card-ipa">{row['IPA']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1: 
                if st.button("◀", use_container_width=True): st.session_state.card_idx -= 1; st.rerun()
            with c2:
                if st.button("👀 看中文 / 🔊 聽發音", use_container_width=True):
                    st.info(f"{row['Chinese']}")
                    st.markdown(get_audio_html(row['Word'], tld=st.session_state.accent_tld, autoplay=True), unsafe_allow_html=True)
            with c3:
                if st.button("▶", use_container_width=True): st.session_state.card_idx += 1; st.rerun()

    # 其他功能保留基本邏輯
    with tabs[2]: st.info("輪播功能開發中...")
    with tabs[3]: st.info("測驗功能開發中...")
    with tabs[4]: st.info("拼字功能開發中...")

def main():
    initialize_session_state()
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
