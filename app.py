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
VERSION = "v44.1 (Fix Error & Font)"
st.set_page_config(page_title=f"AI 智能單字速記通 ({VERSION})", layout="wide", page_icon="🎓")

# ==========================================
# 2. CSS 樣式
# ==========================================
st.markdown("""
<style>
    .main { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    
    .title-container {
        text-align: center; padding: 20px 0 40px 0;
        background: linear-gradient(to bottom, #ffffff, #f8f9fa);
        border-radius: 20px; margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .main-title {
        font-size: 42px; font-weight: 900;
        background: -webkit-linear-gradient(45deg, #1565C0, #42A5F5);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin: 0; padding: 0; font-family: 'Arial Black', sans-serif;
    }
    .sub-title { font-size: 16px; color: #78909c; margin-top: 8px; font-weight: 600; letter-spacing: 1.5px; }

    /* --- 數據卡片 (恢復大字體) --- */
    .metric-card {
        background: #ffffff; border-left: 6px solid #4CAF50; border-radius: 12px;
        padding: 15px 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 10px; transition: transform 0.2s;
    }
    .metric-label { font-size: 18px; color: #546e7a; font-weight: bold; margin-bottom: 4px; }
    .metric-value { font-size: 42px; font-weight: 900; color: #2e7d32; }

    .stButton>button { 
        border-radius: 12px; font-weight: bold; border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.08); transition: all 0.2s;
        font-size: 18px !important; padding: 12px 20px; height: auto;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }
    .word-text { font-size: 28px; font-weight: bold; color: #2E7D32; font-family: 'Arial Black', sans-serif; }
    .ipa-text { font-size: 18px; color: #757575; }
    .meaning-text { font-size: 24px; color: #1565C0; font-weight: bold;}
    
    a.link-btn {
        text-decoration: none; display: inline-block; padding: 6px 10px;
        border-radius: 8px; font-weight: bold; border: 1px solid #ddd; 
        transition: all 0.2s; margin-right: 5px; font-size: 16px;
    }
    a.google-btn { background-color: #f1f3f4; color: #1a73e8; border-color: #dadce0; }
    a.yahoo-btn { background-color: #f3e5f5; color: #720e9e; border-color: #e1bee7; }

    .quiz-card {
        background-color: #fff8e1; padding: 40px; border-radius: 20px;
        text-align: center; border: 4px dashed #ffb74d; margin-bottom: 20px;
    }
    .quiz-word { font-size: 60px; font-weight: 900; color: #1565C0; margin: 20px 0; }
    .mistake-mode { border: 4px solid #ef5350 !important; background-color: #ffebee !important; }
    
    .login-container {
        background-color: white; padding: 60px; border-radius: 25px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.1); text-align: center;
        max-width: 800px; margin: 50px auto; border-top: 12px solid #4CAF50;
    }
    .welcome-text { font-size: 28px; color: #666; margin-bottom: 10px; font-weight: bold; }
    .login-title { color: #2E7D32; margin-top: 0; font-size: 48px; font-weight: 900; white-space: nowrap; }
    .version-tag { position: fixed; bottom: 10px; left: 15px; color: #aaa; font-size: 14px; font-family: monospace; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心功能
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
        cols = ['User', 'Password', 'Notebook', 'Word', 'IPA', 'Chinese', 'Date']
        if not data: return pd.DataFrame(columns=cols)
        df = pd.DataFrame(data)
        if 'Password' not in df.columns: df['Password'] = ""
        for c in cols:
            if c not in df.columns: df[c] = ""
        df['User'] = df['User'].astype(str).str.strip()
        df['Password'] = df['Password'].astype(str).str.strip()
        return df.fillna("")
    except: return pd.DataFrame(columns=['User', 'Password', 'Notebook', 'Word', 'IPA', 'Chinese', 'Date'])

def save_to_google_sheet(df):
    try:
        creds_json = json.loads(st.secrets["service_account"]["info"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        sheet = client.open("vocab_db").sheet1
        sheet.clear()
        if 'User' in df.columns: df['User'] = df['User'].astype(str).str.strip()
        if 'Password' in df.columns: df['Password'] = df['Password'].astype(str).str.strip()
        cols = ['User', 'Password', 'Notebook', 'Word', 'IPA', 'Chinese', 'Date']
        for c in cols:
            if c not in df.columns: df[c] = ""
        df = df[cols].fillna("")
        update_data = [df.columns.values.tolist()] + df.values.tolist()
        sheet.update(update_data)
        get_google_sheet_data.clear()
    except Exception as e: st.error(f"儲存失敗：{e}")

def check_duplicate(df, user, notebook, word):
    if df.empty: return False
    mask = (df['User'] == str(user).strip()) & (df['Notebook'] == notebook) & (df['Word'].str.lower() == str(word).lower().strip())
    return not df[mask].empty

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

def is_contains_chinese(string):
    for char in str(string):
        if '\u4e00' <= char <= '\u9fff': return True
    return False

# --- 語音核心 (快取優化) ---
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
    return f"""
    <audio id="{rand_id}" controls {autoplay_attr} style="{display_style}">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>
    """

def generate_custom_audio(df, sequence, tld='com', slow=False):
    full_text = ""
    for i, (index, row) in enumerate(df.iloc[::-1].iterrows(), start=1):
        word = str(row['Word']); chinese = str(row['Chinese'])
        full_text += f"Number {i}. " 
        if not sequence: full_text += f"{word}. {chinese}. "
        else:
            for item in sequence:
                if item == "英文": full_text += f"{word}. "
                elif item == "中文": full_text += f"{chinese}. "
        full_text += " ... "
    tts = gTTS(text=full_text, lang='zh-TW', slow=slow)
    fp = BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()

def add_to_mistake_notebook(row, user):
    df = st.session_state.df
    mistake_nb_name = "🔥 錯題本 (Auto)"
    if not check_duplicate(df, user, mistake_nb_name, row['Word']):
        user_rows = df[df['User'] == user]
        user_pwd = user_rows.iloc[0]['Password'] if not user_rows.empty else ""
        new_entry = {'User': str(user).strip(), 'Password': user_pwd, 'Notebook': mistake_nb_name, 'Word': row['Word'], 'IPA': row['IPA'], 'Chinese': row['Chinese'], 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        st.session_state.df = df; save_to_google_sheet(df)
        return True
    return False

# ==========================================
# 4. 狀態初始化
# ==========================================

def initialize_session_state():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'df' not in st.session_state: st.session_state.df = get_google_sheet_data()
    if 'play_order' not in st.session_state: st.session_state.play_order = ["英文", "中文", "英文"] 
    if 'accent_tld' not in st.session_state: st.session_state.accent_tld = 'com'
    if 'is_slow' not in st.session_state: st.session_state.is_slow = False
    if 'current_mode' not in st.session_state: st.session_state.current_mode = 'list'
    
    if 'quiz_score' not in st.session_state: st.session_state.quiz_score = 0
    if 'quiz_total' not in st.session_state: st.session_state.quiz_total = 0
    if 'quiz_current' not in st.session_state: st.session_state.quiz_current = None
    if 'quiz_options' not in st.session_state: st.session_state.quiz_options = []
    if 'quiz_answered' not in st.session_state: st.session_state.quiz_answered = False
    if 'quiz_is_correct' not in st.session_state: st.session_state.quiz_is_correct = False

    if 'spell_current' not in st.session_state: st.session_state.spell_current = None
    if 'spell_input' not in st.session_state: st.session_state.spell_input = ""
    if 'spell_checked' not in st.session_state: st.session_state.spell_checked = False
    if 'spell_correct' not in st.session_state: st.session_state.spell_correct = False
    if 'spell_score' not in st.session_state: st.session_state.spell_score = 0
    if 'spell_total' not in st.session_state: st.session_state.spell_total = 0
    
    if 'msg_success' not in st.session_state: st.session_state.msg_success = ""
    if 'msg_warning' not in st.session_state: st.session_state.msg_warning = ""

def add_words_callback():
    final_text = st.session_state.ocr_editor
    target_nb = st.session_state.target_nb_key
    current_user = str(st.session_state.current_user).strip()
    df = st.session_state.df
    user_pwd = ""
    if not df.empty:
        user_rows = df[df['User'] == current_user]
        if not user_rows.empty: user_pwd = user_rows.iloc[0]['Password']
    
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
                new_entries.append({'User': current_user, 'Password': user_pwd, 'Notebook': target_nb, 'Word': w, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')})
            except: pass
    if new_entries:
        df_all = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
        st.session_state.df = df_all; save_to_google_sheet(df_all)
        st.session_state.msg_success = f"✅ 成功加入 {len(new_entries)} 筆單字！"
        st.session_state.ocr_editor = ""
    elif skipped > 0: st.session_state.msg_warning = "⚠️ 所有單字都重複了！"
    else: st.session_state.msg_warning = "⚠️ 沒有有效的英文單字可加入。"

def next_question(df):
    if df.empty: return
    target_row = df.sample(1).iloc[0]
    st.session_state.quiz_current = target_row
    correct_opt = str(target_row['Chinese'])
    all_df = df 
    other_rows = all_df[all_df['Chinese'] != correct_opt]
    if len(other_rows) >= 3: distractors = other_rows.sample(3)['Chinese'].astype(str).tolist()
    else:
        placeholders = ["蘋果", "閥門", "幫浦", "螺絲", "溫度", "壓力", "反應器"]
        candidates = [p for p in placeholders if p != correct_opt]
        needed = 3 - len(other_rows)
        distractors = other_rows['Chinese'].astype(str).tolist() + random.sample(candidates, min(len(candidates), needed))
    options = [correct_opt] + distractors
    random.shuffle(options)
    st.session_state.quiz_options = options
    st.session_state.quiz_answered = False
    st.session_state.quiz_is_correct = False

def check_answer(user_choice):
    st.session_state.quiz_answered = True
    st.session_state.quiz_total += 1
    current = st.session_state.quiz_current
    if user_choice == str(current['Chinese']):
        st.session_state.quiz_score += 1; st.session_state.quiz_is_correct = True
    else:
        st.session_state.quiz_is_correct = False
        if add_to_mistake_notebook(current, st.session_state.current_user): st.toast(f"已加入錯題本: {current['Word']}", icon="🔥")

def next_spelling(df):
    if df.empty: return
    target_row = df.sample(1).iloc[0]
    st.session_state.spell_current = target_row
    st.session_state.spell_input = ""
    st.session_state.spell_checked = False
    st.session_state.spell_correct = False

def check_spelling():
    if not st.session_state.spell_current.empty:
        st.session_state.spell_checked = True
        st.session_state.spell_total += 1
        correct = str(st.session_state.spell_current['Word']).strip().lower()
        user = str(st.session_state.spell_input).strip().lower()
        if correct == user:
            st.session_state.spell_score += 1; st.session_state.spell_correct = True
        else:
            st.session_state.spell_correct = False
            if add_to_mistake_notebook(st.session_state.spell_current, st.session_state.current_user): st.toast(f"已加入錯題本: {st.session_state.spell_current['Word']}", icon="🔥")

# ==========================================
# 5. 主程式 Layout
# ==========================================

def login_page():
    login_ph = st.empty()
    with login_ph.container():
        st.markdown("""<div class="login-container"><div class="welcome-text">歡迎來到</div><h1 class="login-title">🚀 AI 智能單字速記通 🎓</h1><p style="color: #666; font-size: 18px; margin-top: 20px;">請輸入您的帳號與密碼</p></div>""", unsafe_allow_html=True)
        df = st.session_state.df
        
        with st.form("login_form"):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                user_input = st.text_input("學號 / 姓名 / 英文ID", placeholder="例如: s12345, 王小明, or Tony", key="login_user")
                pwd_input = st.text_input("密碼 (若新用戶請設定新密碼)", type="password", autocomplete="current-password")
                submit_val = st.form_submit_button("🚀 登入 / 註冊", type="primary", use_container_width=True)
                
                if submit_val:
                    if user_input and pwd_input:
                        user_data = df[df['User'] == user_input.strip()]
                        is_new_user = True
                        stored_password = ""
                        if not user_data.empty:
                            pwd_rows = user_data[user_data['Password'] != ""]
                            if not pwd_rows.empty:
                                stored_password = pwd_rows.iloc[0]['Password']
                                is_new_user = False
                        if is_new_user:
                            st.session_state.current_user = user_input.strip()
                            st.session_state.logged_in = True
                            if not user_data.empty:
                                df.loc[df['User'] == user_input.strip(), 'Password'] = pwd_input
                                save_to_google_sheet(df)
                            else:
                                dummy_entry = {'User': user_input.strip(), 'Password': pwd_input, 'Notebook': '預設筆記本', 'Word': 'Welcome', 'IPA': '', 'Chinese': '歡迎使用', 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                                df_new = pd.concat([df, pd.DataFrame([dummy_entry])], ignore_index=True)
                                st.session_state.df = df_new; save_to_google_sheet(df_new)
                            login_ph.empty(); st.rerun()
                        else:
                            if pwd_input == stored_password:
                                st.session_state.current_user = user_input.strip()
                                st.session_state.logged_in = True
                                if (user_data['Password'] == "").any():
                                    df.loc[df['User'] == user_input.strip(), 'Password'] = stored_password
                                    save_to_google_sheet(df)
                                login_ph.empty(); st.rerun()
                            else: st.error("密碼錯誤，請再試一次")
                    else: st.error("請輸入帳號和密碼")

    st.markdown(f'<div class="version-tag">{VERSION}</div>', unsafe_allow_html=True)

def main_app():
    if st.session_state.msg_success:
        st.success(st.session_state.msg_success)
        st.session_state.msg_success = "" 
    if st.session_state.msg_warning:
        st.warning(st.session_state.msg_warning)
        st.session_state.msg_warning = ""

    df_all = st.session_state.df
    current_user = str(st.session_state.current_user).strip()
    if 'User' not in df_all.columns: df_all['User'] = ""
    else: df_all['User'] = df_all['User'].astype(str).str.strip()
    df = df_all[(df_all['User'] == current_user) | (df_all['User'] == "") | (df_all['User'] == "nan")]

    st.markdown(f"""<div class="title-container"><h1 class="main-title">🚀 AI 智能單字速記通 🎓</h1><div class="sub-title">歡迎回來，{current_user}！ • 您的專屬學習空間</div></div>""", unsafe_allow_html=True)

    notebooks = df['Notebook'].unique().tolist()
    if "🔥 錯題本 (Auto)" not in notebooks: notebooks.append("🔥 錯題本 (Auto)")
    if 'filter_nb_key' not in st.session_state: st.session_state.filter_nb_key = '全部'
    if st.session_state.filter_nb_key not in ["全部"] + notebooks: st.session_state.filter_nb_key = "全部"
    current_nb = st.session_state.filter_nb_key
    filtered_df = df if current_nb == "全部" else df[df['Notebook'] == current_nb]
    
    # --- 恢復大字體 ---
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">☁️ 雲端總字數</div><div class="metric-value">{len(df)}</div></div>""", unsafe_allow_html=True)
    with c_m2:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">📖 目前本子字數</div><div class="metric-value">{len(filtered_df)}</div></div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.info(f"👤 目前使用者：**{current_user}**")
        if st.button("🚪 登出"): st.session_state.logged_in = False; st.rerun()
        st.divider()
        st.header("📝 新增單字")
        if '預設筆記本' not in notebooks: notebooks.append('預設筆記本')
        nb_mode = st.radio("筆記本來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed")
        target_nb = st.selectbox("選擇筆記本", notebooks, key="target_nb_key") if nb_mode == "選擇現有" else st.text_input("輸入新筆記本名稱", "我的單字本", key="target_nb_key")
        st.divider()
        
        ocr_opts = ["🔤 單字輸入", "🚀 批次貼上"]
        input_type = st.radio("輸入模式", ocr_opts, horizontal=True)

        if input_type == "🔤 單字輸入":
            w_in = st.text_input("輸入英文單字", placeholder="例如: Valve")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("👀 翻譯", use_container_width=True):
                    if w_in and not is_contains_chinese(w_in):
                        try: st.info(f"{GoogleTranslator(source='auto', target='zh-TW').translate(w_in)}")
                        except: st.error("翻譯失敗")
            with c2:
                if st.button("🔊 試聽", use_container_width=True):
                    if w_in:
                        st.markdown(get_audio_html(w_in, 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)

            if st.button("➕ 加入單字庫", type="primary", use_container_width=True):
                if w_in and target_nb:
                    if check_duplicate(df, current_user, target_nb, w_in): st.warning(f"⚠️ 重複單字")
                    else:
                        try:
                            user_rows = df[df['User'] == current_user]
                            user_pwd = user_rows.iloc[0]['Password'] if not user_rows.empty else ""
                            ipa = f"[{eng_to_ipa.convert(w_in)}]"
                            trans = GoogleTranslator(source='auto', target='zh-TW').translate(w_in)
                            new = {'User': current_user, 'Password': user_pwd, 'Notebook': target_nb, 'Word': w_in, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                            df_all = pd.concat([df_all, pd.DataFrame([new])], ignore_index=True)
                            st.session_state.df = df_all; save_to_google_sheet(df_all); st.success(f"已儲存：{w_in}"); time.sleep(0.5); st.rerun()
                        except Exception as e: st.error(f"錯誤: {e}")
        
        elif input_type == "🚀 批次貼上":
            st.info("💡 提示：請將其他來源 (如 Gemini) 產生的單字複製到下方。")
            bulk_in = st.text_area("📋 貼上單字區", height=150, key="ocr_editor")
            if st.button("🚀 批次加入", type="primary", on_click=add_words_callback): pass

        st.divider()
        with st.expander("🔊 發音與語速", expanded=False):
            accents = {'美式 (US)': 'com', '英式 (UK)': 'co.uk', '澳式 (AU)': 'com.au', '印度 (IN)': 'co.in'}
            curr_acc = [k for k, v in accents.items() if v == st.session_state.accent_tld][0]
            st.session_state.accent_tld = accents[st.selectbox("口音", list(accents.keys()), index=list(accents.keys()).index(curr_acc))]
            speeds = {'正常': False, '慢速': True}
            curr_spd = [k for k, v in speeds.items() if v == st.session_state.is_slow][0]
            st.session_state.is_slow = speeds[st.radio("語速", list(speeds.keys()), index=list(speeds.keys()).index(curr_spd))]

        with st.expander("🎧 播放順序", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1: 
                if st.button("➕ 英文"): st.session_state.play_order.append("英文")
            with c2: 
                if st.button("➕ 中文"): st.session_state.play_order.append("中文")
            with c3: 
                if st.button("❌ 清空"): st.session_state.play_order = []
            st.info(f"順序：{' ➝ '.join(st.session_state.play_order) if st.session_state.play_order else '(未設定)'}")

        with st.expander("🛠️ 進階管理 (含更名)", expanded=False):
            if st.button("🔄 強制更新"): st.session_state.df = get_google_sheet_data(); st.success("已更新"); st.rerun()
            st.write("✏️ **更名筆記本**")
            ren_target = st.selectbox("選擇對象", notebooks, key='ren_sel')
            ren_new = st.text_input("輸入新名稱", key='ren_val')
            if st.button("確認更名"):
                if ren_new and ren_new != ren_target:
                    df_all.loc[(df_all['User'].astype(str) == current_user) & (df_all['Notebook'] == ren_target), 'Notebook'] = ren_new
                    st.session_state.df = df_all; save_to_google_sheet(df_all); st.success("已更名"); time.sleep(1); st.rerun()
            st.write("🗑️ **刪除筆記本**")
            del_target = st.selectbox("選擇刪除對象", notebooks, key="del_sel")
            if st.button("刪除此本", type="primary"):
                if st.session_state.get('confirm_del') != del_target: st.warning("再按一次確認"); st.session_state.confirm_del = del_target
                else:
                    df_all = df_all[~((df_all['User'].astype(str) == current_user) & (df_all['Notebook'] == del_target))]
                    st.session_state.df = df_all; save_to_google_sheet(df_all); st.success("已刪除"); st.rerun()
        st.markdown("---"); st.caption(f"版本: {VERSION}")

    st.divider()
    c_filt, c_tool = st.columns([1, 1.5])
    with c_filt:
        st.selectbox("📖 我要複習哪一本？", ["全部"] + notebooks, key='filter_nb_key')
        if current_nb == "🔥 錯題本 (Auto)": st.warning("🔥 這是您的錯題本，請重點複習！")
    with c_tool:
        st.markdown("**🎧 工具區**")
        t1, t2 = st.columns(2)
        with t1:
            if not filtered_df.empty: st.download_button("📥 下載 Excel", to_excel(filtered_df), f"Vocab_{current_nb}.xlsx", use_container_width=True)
            else: st.button("📥 無資料", disabled=True, use_container_width=True)
        with t2:
            if not filtered_df.empty and st.session_state.play_order:
                if st.button("🎵 製作 MP3", use_container_width=True):
                    with st.spinner("製作中..."):
                        mp3 = generate_custom_audio(filtered_df, st.session_state.play_order, st.session_state.accent_tld, st.session_state.is_slow)
                        st.download_button("⬇️ 下載 MP3", mp3, f"Audio_{current_nb}.mp3", "audio/mp3", use_container_width=True)
            else: st.button("🎵 設定順序後下載", disabled=True, use_container_width=True)

    st.markdown("###")
    n1, n2, n3, n4, n5 = st.columns(5)
    def btn_type(mode_name): return "primary" if st.session_state.current_mode == mode_name else "secondary"
    if n1.button("📋 列表", type=btn_type('list'), use_container_width=True): st.session_state.current_mode = 'list'; st.rerun()
    if n2.button("🃏 卡片", type=btn_type('card'), use_container_width=True): st.session_state.current_mode = 'card'; st.rerun()
    if n3.button("🎬 輪播", type=btn_type('slide'), use_container_width=True): st.session_state.current_mode = 'slide'; st.rerun()
    if n4.button("🏆 測驗", type=btn_type('quiz'), use_container_width=True): st.session_state.current_mode = 'quiz'; st.rerun()
    if n5.button("✍️ 拼字", type=btn_type('spell'), use_container_width=True): st.session_state.current_mode = 'spell'; st.rerun()
    st.divider()

    mode = st.session_state.current_mode

    if mode == 'list':
        if not filtered_df.empty:
            for i, row in filtered_df.iloc[::-1].iterrows():
                c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])
                with c1: st.markdown(f"<div class='word-text'>{row['Word']}</div><div class='ipa-text'>{row['IPA']}</div>", unsafe_allow_html=True)
                with c2: st.markdown(f"<div class='meaning-text'>{row['Chinese']}</div>", unsafe_allow_html=True)
                with c3: 
                    if st.button("🔊", key=f"p{i}"):
                        st.markdown(get_audio_html(row['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)

                with c4:
                    g_url = f"https://translate.google.com/?sl=en&tl=zh-TW&text={row['Word']}&op=translate"
                    y_url = f"https://tw.dictionary.search.yahoo.com/search?p={row['Word']}"
                    st.markdown(f'''<div style="display: flex;"><a href="{g_url}" target="_blank" class="link-btn google-btn">G</a><a href="{y_url}" target="_blank" class="link-btn yahoo-btn">Y!</a></div>''', unsafe_allow_html=True)
                with c5:
                    if st.button("🗑️", key=f"d{i}"):
                        df_all = df_all[~((df_all['User'].astype(str) == current_user) & (df_all['Word'] == row['Word']) & (df_all['Notebook'] == row['Notebook']))]
                        st.session_state.df = df_all; save_to_google_sheet(df_all); st.rerun()
                st.divider()
        else: st.info("目前無單字")

    elif mode == 'card':
        if not filtered_df.empty:
            if 'card_idx' not in st.session_state: st.session_state.card_idx = 0
            idx = st.session_state.card_idx % len(filtered_df)
            row = filtered_df.iloc[idx]
            c_p, c_c, c_n = st.columns([1, 4, 1])
            with c_p: 
                st.write(""); st.write(""); st.write("") 
                if st.button("◀ 上一個", use_container_width=True): st.session_state.card_idx -= 1; st.rerun()
            with c_n: 
                st.write(""); st.write(""); st.write("") 
                if st.button("下一個 ▶", use_container_width=True): st.session_state.card_idx += 1; st.rerun()
            with c_c:
                st.markdown(f"""<div style="border:3px solid #81C784;border-radius:20px;padding:60px;text-align:center;min-height:350px;"><div style="font-size:70px;color:#2E7D32;font-weight:bold;">{row['Word']}</div><div style="color:#666;font-size:28px;">{row['IPA']}</div></div>""", unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                with b1: 
                    if st.button("👀 看中文", use_container_width=True): st.info(f"{row['Chinese']}")
                with b2: 
                    if st.button("🔊 聽發音", use_container_width=True): 
                        st.markdown(get_audio_html(row['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
        else: st.info("無單字")

    elif mode == 'slide':
        delay = st.slider("每張卡片停留秒數", 2, 8, 3)
        ph = st.empty()
        if st.button("▶️ 開始輪播", type="primary"):
            if not st.session_state.play_order: st.error("請先設定播放順序")
            else:
                for _, row in filtered_df.iloc[::-1].iterrows():
                    for step in st.session_state.play_order:
                        ph.empty() 
                        time.sleep(0.1)
                        text = ""
                        lang = 'en'
                        tld = st.session_state.accent_tld
                        if step == "英文": text = row['Word']; lang = 'en'
                        elif step == "中文": text = row['Chinese']; lang = 'zh-TW'; tld = 'com'
                        
                        html_audio = get_audio_html(text, lang, tld, st.session_state.is_slow, autoplay=True, visible=False)
                        
                        with ph.container():
                            html_content = f"""<div style="border:3px solid #4CAF50;border-radius:20px;padding:50px;text-align:center;background:#f0fdf4;min-height:350px;margin-bottom:10px;"><div style="font-size:60px;color:#2E7D32;font-weight:bold;">{row['Word']}</div><div style="color:#666;font-size:24px;margin-bottom:20px;">{row['IPA']}</div>"""
                            if step == "中文": html_content += f"""<div style="font-size:50px;color:#1565C0;font-weight:bold;">{row['Chinese']}</div>"""
                            elif step == "英文": html_content += f"""<div style="color:#aaa;">Listening...</div>"""
                            html_content += "</div>"
                            st.markdown(html_content + html_audio, unsafe_allow_html=True)
                        time.sleep(delay)
                ph.success("輪播結束")

    elif mode == 'quiz':
        q_mode = st.radio("🎯 測驗範圍", ["📖 當前筆記本", "🔥 錯題本"], horizontal=True, key="qm")
        target_df = df[df['Notebook'] == "🔥 錯題本 (Auto)"] if q_mode == "🔥 錯題本" else filtered_df
        c_s, c_r = st.columns([3, 1])
        rate = (st.session_state.quiz_score/st.session_state.quiz_total)*100 if st.session_state.quiz_total>0 else 0
        c_s.markdown(f"📊 答對：**{st.session_state.quiz_score}** / **{st.session_state.quiz_total}** ({rate:.1f}%)")
        if c_r.button("🔄 重置"): st.session_state.quiz_score=0; st.session_state.quiz_total=0; st.rerun()

        if target_df.empty: st.success("錯題本是空的！") if q_mode == "🔥 錯題本" else st.warning("無單字")
        else:
            if st.session_state.quiz_current is None or st.session_state.quiz_current['Word'] not in target_df['Word'].values:
                next_question(target_df); st.rerun()
            q = st.session_state.quiz_current
            card_cls = "quiz-card mistake-mode" if q_mode == "🔥 錯題本" else "quiz-card"
            st.markdown(f"""<div class="{card_cls}"><div style="color:#555;">選出正確中文 (答錯自動加入錯題本)</div><div class="quiz-word">{q['Word']}</div><div>{q['IPA']}</div></div>""", unsafe_allow_html=True)
            
            if st.button("🔊 播放題目發音", use_container_width=True):
                st.markdown(get_audio_html(q['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow, autoplay=True, visible=True), unsafe_allow_html=True)

            if not st.session_state.quiz_answered:
                cols = st.columns(2)
                for i, opt in enumerate(st.session_state.quiz_options):
                    if cols[i%2].button(opt, key=f"qo{i}", use_container_width=True): check_answer(opt); st.rerun()
            else:
                if st.session_state.quiz_is_correct: st.success("🎉 正確！"); st.balloons()
                else: st.error(f"❌ 錯誤。正確：{q['Chinese']}")
                if st.button("➡️ 下一題", type="primary", use_container_width=True): next_question(target_df); st.rerun()

    elif mode == 'spell':
        s_mode = st.radio("🎯 拼寫範圍", ["📖 當前筆記本", "🔥 錯題本"], horizontal=True, key="sm")
        target_df = df[df['Notebook'] == "🔥 錯題本 (Auto)"] if s_mode == "🔥 錯題本" else filtered_df
        c_s, c_r = st.columns([3, 1])
        rate = (st.session_state.spell_score/st.session_state.spell_total)*100 if st.session_state.spell_total>0 else 0
        c_s.markdown(f"✍️ 拼寫：**{st.session_state.spell_score}** / **{st.session_state.spell_total}** ({rate:.1f}%)")
        if c_r.button("🔄 重置"): st.session_state.spell_score=0; st.session_state.spell_total=0; st.rerun()

        if target_df.empty: st.success("錯題本是空的！") if s_mode == "🔥 錯題本" else st.warning("無單字")
        else:
            if st.session_state.spell_current is None or st.session_state.spell_current['Word'] not in target_df['Word'].values:
                next_spelling(target_df); st.rerun()
            
            sq = st.session_state.spell_current
            card_cls = "quiz-card mistake-mode" if s_mode == "🔥 錯題本" else "quiz-card"
            st.markdown(f"""<div class="{card_cls}"><div style="color:#555;">聽發音輸入英文 (答錯自動加入錯題本)</div><div style="font-size:18px;color:#666;">(中文意思)</div><div style="font-size:36px;color:#1565C0;font-weight:bold;margin:10px 0;">{sq['Chinese']}</div></div>""", unsafe_allow_html=True)
            
            if st.button("🔊 重聽發音", use_container_width=True):
                st.markdown(get_audio_html(sq['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow, autoplay=True, visible=True), unsafe_allow_html=True)
            
            if not st.session_state.spell_checked and st.session_state.spell_input == "":
                 st.markdown(get_audio_html(sq['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow, autoplay=True, visible=False), unsafe_allow_html=True)

            if not st.session_state.spell_checked:
                inp = st.text_input("輸入單字", key="spin")
                if st.button("✅ 送出", type="primary"):
                    st.session_state.spell_input = inp; check_spelling(); st.rerun()
            else:
                if st.session_state.spell_correct: st.success(f"🎉 拼對了！ {sq['Word']}"); st.balloons()
                else: st.error(f"❌ 拼錯了...\n\n您的輸入：**{st.session_state.spell_input}**\n\n正確答案：**{sq['Word']}**")
                if st.button("➡️ 下一題", type="primary"): next_spelling(target_df); st.rerun()

def main():
    initialize_session_state()
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
