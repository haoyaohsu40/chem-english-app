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
# 1. 頁面與 CSS 設定
# ==========================================
VERSION = "v52.0 (Layout Fix & Slide Stop)"
st.set_page_config(page_title="職場英文生存術", layout="wide", page_icon="🏭")

st.markdown("""
<style>
    .main { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f8f9fa; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* 登入區塊 */
    .login-container {
        background-color: white; padding: 30px 20px; border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;
        margin: 20px auto; max-width: 500px; border-top: 6px solid #1E88E5;
    }
    
    /* 輸入框優化 */
    .stTextInput>div>div>input { color: #333 !important; background-color: white !important; }

    /* 列表卡片 (優化間距) */
    .list-card {
        background: white; padding: 12px; margin-bottom: 8px;
        border-radius: 12px; border-left: 5px solid #4CAF50;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .list-word { font-size: 20px; font-weight: 900; color: #2e7d32; }
    .list-ipa { font-size: 14px; color: #757575; font-family: monospace; margin-left: 5px; }
    .list-mean { font-size: 16px; color: #1565C0; font-weight: bold; display: block; margin-top: 4px; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 8px;}
    
    /* 連結按鈕 (G/Y) */
    a.link-btn {
        text-decoration: none; display: flex; 
        align-items: center; justify-content: center;
        padding: 6px 0; border-radius: 8px; 
        font-weight: bold; border: 1px solid #ddd; 
        font-size: 13px; color: #555; background: #f1f3f4;
        width: 100%; height: 40px; /* 統一高度 */
        white-space: nowrap; 
    }

    /* 卡片模式 */
    .card-box {
        background-color: white; padding: 30px 20px; border-radius: 15px;
        text-align: center; border: 2px solid #81C784; min-height: 200px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 15px;
        display: flex; flex-direction: column; justify-content: center;
    }
    .card-word { font-size: 42px; font-weight: 900; color: #2E7D32; line-height: 1.1; margin-bottom: 5px; }
    .card-ipa { font-size: 16px; color: #666; margin-bottom: 15px; }
    
    /* 測驗/拼字卡片 */
    .quiz-card {
        background-color: #fffde7; padding: 20px; border-radius: 15px;
        text-align: center; border: 2px dashed #fbc02d; margin-bottom: 15px;
    }
    .quiz-word { font-size: 32px; font-weight: 900; color: #1565C0; margin: 10px 0; }

    /* 按鈕樣式 (統一高度) */
    .stButton>button { 
        border-radius: 8px; width: 100%; font-weight: bold; 
        height: auto; padding: 6px 0;
        min-height: 40px; 
    }
    
    /* 統計方塊 */
    .stat-box {
        background: white; border-radius: 10px; padding: 10px; text-align: center;
        border: 1px solid #e0e0e0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stat-num { font-size: 20px; font-weight: bold; color: #1976D2; }
    .stat-lbl { font-size: 12px; color: #666; }

    .version-tag { text-align: center; color: #ccc; font-size: 10px; margin-top: 50px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心功能函式
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
        for c in cols:
             if c not in df.columns: df[c] = ""
        df = df[cols].fillna("")
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

def get_audio_html(text, lang='en', tld='com', slow=False, autoplay=False, visible=True):
    try:
        if not text: return ""
        tts = gTTS(text=str(text), lang=lang, tld=tld, slow=slow)
        fp = BytesIO(); tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        rand_id = f"audio_{uuid.uuid4()}"
        autoplay_attr = "autoplay" if autoplay else ""
        # 使用 opacity:0 隱藏，確保手機瀏覽器能自動播放
        style = "width: 100%; margin-top: 5px;" if visible else "width: 1px; height: 1px; opacity: 0; position: absolute; left: -9999px;"
        return f"""<audio id="{rand_id}" controls {autoplay_attr} style="{style}"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>"""
    except: return ""

def generate_custom_audio(df, sequence, tld='com', slow=False):
    full_text = ""
    process_df = df.iloc[::-1].head(50) 
    for i, (index, row) in enumerate(process_df.iterrows(), start=1):
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

def add_word_callback():
    w_in = st.session_state.input_word
    if st.session_state.nb_mode == "建立新本":
        target_nb = st.session_state.new_nb_name
    else:
        target_nb = st.session_state.target_nb_key
    
    current_user = st.session_state.current_user
    df = st.session_state.df

    if w_in and target_nb:
        if check_duplicate(df, current_user, target_nb, w_in):
            st.session_state.msg_warning = f"⚠️ '{w_in}' 已經存在！"
        else:
            try:
                ipa = f"[{eng_to_ipa.convert(w_in)}]"
                trans = GoogleTranslator(source='auto', target='zh-TW').translate(w_in)
                new = {'User': current_user, 'Notebook': target_nb, 'Word': w_in, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                st.session_state.df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                save_to_google_sheet(st.session_state.df)
                st.session_state.msg_success = f"✅ 已加入：{w_in}"
                st.session_state.input_word = "" 
            except Exception as e:
                st.session_state.msg_warning = f"錯誤: {str(e)}"
    else:
         st.session_state.msg_warning = "⚠️ 請輸入單字並選擇筆記本"

def add_to_mistake_notebook(row, user):
    df = st.session_state.df
    mistake_nb_name = "🔥 錯題本 (Auto)"
    if not check_duplicate(df, user, mistake_nb_name, row['Word']):
        new_entry = row.to_dict()
        new_entry['Notebook'] = mistake_nb_name
        new_entry['User'] = user
        st.session_state.df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        save_to_google_sheet(st.session_state.df)
        return True
    return False

# ==========================================
# 3. 狀態初始化
# ==========================================

def initialize_session_state():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'df' not in st.session_state: st.session_state.df = get_google_sheet_data()
    if 'current_page' not in st.session_state: st.session_state.current_page = "main"
    
    # 設定
    if 'play_order' not in st.session_state: st.session_state.play_order = ["英文", "中文"]
    if 'accent_tld' not in st.session_state: st.session_state.accent_tld = 'com'
    if 'is_slow' not in st.session_state: st.session_state.is_slow = False
    if 'nb_mode' not in st.session_state: st.session_state.nb_mode = "選擇現有"
    
    # 輪播狀態 (新增: 是否正在運行)
    if 'is_sliding' not in st.session_state: st.session_state.is_sliding = False

    # 測驗/拼字狀態
    if 'quiz_current' not in st.session_state: st.session_state.quiz_current = None
    if 'quiz_score' not in st.session_state: st.session_state.quiz_score = 0
    if 'quiz_total' not in st.session_state: st.session_state.quiz_total = 0
    if 'quiz_answered' not in st.session_state: st.session_state.quiz_answered = False
    
    if 'spell_current' not in st.session_state: st.session_state.spell_current = None
    if 'spell_input' not in st.session_state: st.session_state.spell_input = ""
    if 'spell_checked' not in st.session_state: st.session_state.spell_checked = False
    if 'spell_correct' not in st.session_state: st.session_state.spell_correct = False
    if 'spell_score' not in st.session_state: st.session_state.spell_score = 0
    if 'spell_total' not in st.session_state: st.session_state.spell_total = 0

    if 'msg_success' not in st.session_state: st.session_state.msg_success = ""
    if 'msg_warning' not in st.session_state: st.session_state.msg_warning = ""

# ==========================================
# 4. 頁面佈局
# ==========================================

def login_page():
    st.markdown("""<div class="login-container"><div style="font-size:24px;font-weight:900;color:#1565C0;">🚀 職場英文生存術</div><div style="color:#666;font-size:14px;margin-bottom:20px;">輸入代號，立即開始</div></div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 8, 1])
    with c2:
        user_input = st.text_input("您的 英文ID / 姓名", placeholder="例如: Kevin", key="login_user")
        if st.button("🚀 登入", type="primary", use_container_width=True):
            if user_input:
                st.session_state.current_user = user_input.strip()
                st.session_state.logged_in = True
                st.rerun()

# --- 設定頁面 ---
def settings_page():
    st.markdown("### ⚙️ 設定與管理")
    if st.button("🔙 返回主畫面", type="secondary", use_container_width=True, key="btn_back_set"):
        st.session_state.current_page = "main"; st.rerun()
    st.divider()
    st.subheader("🔊 發音設定")
    accents = {'美式 (US)': 'com', '英式 (UK)': 'co.uk'}
    curr_acc = [k for k, v in accents.items() if v == st.session_state.accent_tld][0]
    st.session_state.accent_tld = accents[st.selectbox("口音", list(accents.keys()), index=list(accents.keys()).index(curr_acc))]
    spd_opts = ["正常", "慢速"]
    curr_spd = "慢速" if st.session_state.is_slow else "正常"
    sel_spd = st.radio("語速", spd_opts, index=spd_opts.index(curr_spd), horizontal=True)
    st.session_state.is_slow = (sel_spd == "慢速")
    st.divider()
    st.subheader("🎧 輪播順序")
    c1, c2, c3 = st.columns(3)
    with c1: 
        if st.button("➕ 英文"): st.session_state.play_order.append("英文")
    with c2: 
        if st.button("➕ 中文"): st.session_state.play_order.append("中文")
    with c3: 
        if st.button("❌ 清空"): st.session_state.play_order = []
    order_str = " ➝ ".join(st.session_state.play_order) if st.session_state.play_order else "(未設定)"
    st.info(f"目前順序：{order_str}")
    st.divider()
    st.subheader("✏️ 筆記本管理")
    df = st.session_state.df
    current_user = st.session_state.current_user
    notebooks = sorted(list(set(df[df['User']==current_user]['Notebook'].dropna().unique().tolist())))
    if notebooks:
        ren_target = st.selectbox("選擇要改名的本子", notebooks)
        ren_new = st.text_input("輸入新名稱")
        if st.button("確認更名"):
            if ren_new and ren_new != ren_target:
                df.loc[(df['User']==current_user) & (df['Notebook']==ren_target), 'Notebook'] = ren_new
                st.session_state.df = df; save_to_google_sheet(df)
                st.success("更名成功！"); time.sleep(1); st.rerun()
        st.write("")
        del_target = st.selectbox("選擇要刪除的本子", notebooks, key="del_nb")
        if st.button("🗑️ 刪除此本子", type="primary"):
             df_new = df[~((df['User']==current_user) & (df['Notebook']==del_target))]
             st.session_state.df = df_new; save_to_google_sheet(df_new)
             st.success("刪除成功"); st.rerun()
    st.divider()
    if st.button("🚪 登出", type="secondary", use_container_width=True, key="btn_logout"): 
        st.session_state.logged_in = False; st.session_state.current_page = "main"; st.rerun()

# --- 下載頁面 ---
def download_page():
    st.markdown("### 📥 下載中心")
    if st.button("🔙 返回主畫面", type="secondary", use_container_width=True, key="btn_back_dl"):
        st.session_state.current_page = "main"; st.rerun()
    df = st.session_state.df
    current_user = st.session_state.current_user
    st.divider()
    notebooks = sorted(list(set(df[df['User']==current_user]['Notebook'].dropna().unique().tolist())))
    target_nb = st.selectbox("選擇要下載的筆記本", ["全部"] + notebooks)
    dl_df = df[df['User'] == current_user]
    if target_nb != "全部": dl_df = dl_df[dl_df['Notebook'] == target_nb]
    st.info(f"已選擇: {len(dl_df)} 個單字")
    st.markdown("#### 1. 下載 Excel")
    if not dl_df.empty:
        st.download_button("📥 下載 Excel 檔案", to_excel(dl_df), f"Vocab_{target_nb}.xlsx", use_container_width=True, key="dl_xlsx")
    else: st.button("無資料可下載", disabled=True, use_container_width=True)
    st.markdown("#### 2. 下載 MP3 語音檔")
    st.caption("⚠️ 注意：單字量大時製作需等待約 10-30 秒")
    if not dl_df.empty:
        if st.button("🎵 開始製作 MP3", type="primary", use_container_width=True, key="gen_mp3"):
            with st.spinner("正在錄音中...請稍候"):
                mp3_data = generate_custom_audio(dl_df, st.session_state.play_order, st.session_state.accent_tld, st.session_state.is_slow)
                st.session_state.mp3_cache = mp3_data
                st.rerun()
        if 'mp3_cache' in st.session_state:
             st.download_button("⬇️ 下載製作好的 MP3", st.session_state.mp3_cache, f"Audio_{target_nb}.mp3", "audio/mp3", use_container_width=True, key="dl_mp3_final")

# --- 主功能頁面 ---
def main_page():
    if st.session_state.msg_success:
        st.toast(st.session_state.msg_success, icon="✅")
        st.session_state.msg_success = ""
    if st.session_state.msg_warning:
        st.toast(st.session_state.msg_warning, icon="⚠️")
        st.session_state.msg_warning = ""

    df_all = st.session_state.df
    current_user = st.session_state.current_user
    df = df_all[df_all['User'] == current_user]
    notebooks = sorted(list(set(df['Notebook'].dropna().unique().tolist())))
    if 'Default' not in notebooks: notebooks.append('Default')
    if "🔥 錯題本 (Auto)" not in notebooks: notebooks.append("🔥 錯題本 (Auto)")

    c_h1, c_h2, c_h3 = st.columns([5, 1, 1])
    with c_h1: st.markdown(f"**Hi, {current_user}**")
    with c_h2: 
        if st.button("⚙️", help="設定", key="go_settings"): st.session_state.current_page = "settings"; st.rerun()
    with c_h3:
        if st.button("📥", help="下載", key="go_download"): st.session_state.current_page = "download"; st.rerun()

    st.write("📝 **新增單字**")
    st.session_state.nb_mode = st.radio("來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed", index=0 if st.session_state.nb_mode=="選擇現有" else 1, key="nb_radio")
    st.session_state.nb_mode = st.session_state.nb_radio 
    if st.session_state.nb_mode == "選擇現有":
        st.selectbox("筆記本", notebooks, key="target_nb_key", label_visibility="collapsed")
    else:
        st.text_input("新筆記本名稱", placeholder="例如: 會議單字", key="new_nb_name", label_visibility="collapsed")
    w_in = st.text_input("輸入英文單字", placeholder="例如: Polymer", key="input_word")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("👀 翻譯", use_container_width=True, key="btn_trans"):
            if w_in: st.info(GoogleTranslator(source='auto', target='zh-TW').translate(w_in))
    with b2:
        if st.button("🔊 試聽", use_container_width=True, key="btn_listen"):
            if w_in: st.markdown(get_audio_html(w_in, tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
    st.button("➕ 加入單字庫", type="primary", use_container_width=True, on_click=add_word_callback, key="btn_add")

    st.divider()
    filter_nb = st.selectbox("複習筆記本", ["全部"] + notebooks, key="main_filter_nb")
    filtered_df = df if filter_nb == "全部" else df[df['Notebook'] == filter_nb]
    s1, s2 = st.columns(2)
    with s1: st.markdown(f"<div class='stat-box'><div class='stat-num'>{len(df)}</div><div class='stat-lbl'>雲端總數</div></div>", unsafe_allow_html=True)
    with s2: st.markdown(f"<div class='stat-box'><div class='stat-num'>{len(filtered_df)}</div><div class='stat-lbl'>本子字數</div></div>", unsafe_allow_html=True)
    st.write("")

    tabs = st.tabs(["列表", "卡片", "輪播", "測驗", "拼字"])
    
    # Tab 1: 列表 (版面修復)
    with tabs[0]:
        if not filtered_df.empty:
            for i, row in filtered_df.iloc[::-1].iterrows():
                st.markdown(f"""
                <div class="list-card">
                    <div><span class="list-word">{row['Word']}</span><span class="list-ipa">{row['IPA']}</span></div>
                    <span class="list-mean">{row['Chinese']}</span>
                </div>""", unsafe_allow_html=True)
                # 使用 columns 來控制橫排，並給予適當比例，避免擠壓
                ac1, ac2, ac3, ac4 = st.columns([0.9, 1.1, 1.1, 0.9])
                with ac1:
                    if st.button("🔊", key=f"l_play_{i}", use_container_width=True):
                        st.markdown(get_audio_html(row['Word'], tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
                with ac2:
                    st.markdown(f'<a href="https://translate.google.com/?sl=en&tl=zh-TW&text={row["Word"]}&op=translate" target="_blank" class="link-btn">G 翻譯</a>', unsafe_allow_html=True)
                with ac3:
                    st.markdown(f'<a href="https://tw.dictionary.search.yahoo.com/search?p={row["Word"]}" target="_blank" class="link-btn">Y 字典</a>', unsafe_allow_html=True)
                with ac4:
                    if st.button("🗑️", key=f"l_del_{i}", use_container_width=True):
                        st.session_state.df = st.session_state.df.drop(i)
                        save_to_google_sheet(st.session_state.df)
                        st.rerun()
        else: st.info("無資料")

    # Tab 2: 卡片
    with tabs[1]:
        if not filtered_df.empty:
            if 'card_idx' not in st.session_state: st.session_state.card_idx = 0
            idx = st.session_state.card_idx % len(filtered_df)
            row = filtered_df.iloc[idx]
            st.markdown(f"""<div class="card-box"><div class="card-word">{row['Word']}</div><div class="card-ipa">{row['IPA']}</div></div>""", unsafe_allow_html=True)
            cb1, cb2, cb3 = st.columns([1, 2, 1])
            with cb1: 
                if st.button("◀", key="c_prev", use_container_width=True): st.session_state.card_idx -= 1; st.rerun()
            with cb2:
                if st.button("👀 中文 / 發音", key="c_rev", use_container_width=True):
                    st.info(f"{row['Chinese']}")
                    st.markdown(get_audio_html(row['Word'], tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
            with cb3:
                if st.button("▶", key="c_next", use_container_width=True): st.session_state.card_idx += 1; st.rerun()
        else: st.warning("無資料")

    # Tab 3: 輪播 (加入停止鈕)
    with tabs[2]:
        ctrl_ph = st.empty()
        # 根據狀態顯示「開始」或「停止」按鈕
        if not st.session_state.is_sliding:
            if ctrl_ph.button("▶️ 開始輪播", type="primary", use_container_width=True, key="start_slide"):
                if not st.session_state.play_order: st.error("請先去設定播放順序！")
                else: st.session_state.is_sliding = True; st.rerun()
        else:
            if ctrl_ph.button("⏹️ 停止輪播", type="primary", use_container_width=True, key="stop_slide"):
                st.session_state.is_sliding = False; st.rerun()

        if st.session_state.is_sliding:
            ph = st.empty()
            slide_df = filtered_df.sample(frac=1)
            for r_idx, row in slide_df.iterrows():
                if not st.session_state.is_sliding: break # 檢查停止標記
                for step_idx, step in enumerate(st.session_state.play_order):
                    if not st.session_state.is_sliding: break # 檢查停止標記
                    ph.empty(); time.sleep(0.1)
                    txt, lang = (row['Word'], 'en') if step == "英文" else (row['Chinese'], 'zh-TW')
                    html = f"""<div class="card-box"><div class="card-word" style="font-size:36px;">{txt}</div></div>"""
                    with ph.container():
                        st.markdown(html, unsafe_allow_html=True)
                        st.markdown(get_audio_html(txt, lang, st.session_state.accent_tld, st.session_state.is_slow, autoplay=True, visible=False), unsafe_allow_html=True)
                    time.sleep(2.5)
            st.session_state.is_sliding = False; st.rerun() # 結束後重置狀態

    # Tab 4: 測驗
    with tabs[3]:
        if filtered_df.empty: st.warning("沒單字無法測驗")
        else:
            c_s, c_r = st.columns([3, 1])
            rate = (st.session_state.quiz_score/st.session_state.quiz_total)*100 if st.session_state.quiz_total>0 else 0
            c_s.caption(f"答對: {st.session_state.quiz_score}/{st.session_state.quiz_total} ({rate:.0f}%)")
            if c_r.button("歸零", key="reset_quiz"): st.session_state.quiz_score=0; st.session_state.quiz_total=0; st.rerun()
            if st.session_state.quiz_current is None or st.session_state.quiz_current['Word'] not in filtered_df['Word'].values:
                target = filtered_df.sample(1).iloc[0]
                st.session_state.quiz_current = target
                others = filtered_df[filtered_df['Chinese'] != target['Chinese']]
                distractors = others.sample(min(3, len(others)))['Chinese'].tolist()
                while len(distractors) < 3: distractors.append("無選項")
                opts = [target['Chinese']] + distractors; random.shuffle(opts)
                st.session_state.quiz_options = opts
                st.session_state.quiz_answered = False
                st.rerun()
            q = st.session_state.quiz_current
            st.markdown(f"""<div class="quiz-card"><div class="quiz-word">{q['Word']}</div></div>""", unsafe_allow_html=True)
            if st.button("🔊 題目發音", use_container_width=True, key="play_quiz_audio"):
                 st.markdown(get_audio_html(q['Word'], tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
            if not st.session_state.quiz_answered:
                for idx, opt in enumerate(st.session_state.quiz_options):
                    if st.button(opt, use_container_width=True, key=f"q_opt_{q['Word']}_{idx}"):
                        st.session_state.quiz_answered = True
                        st.session_state.quiz_total += 1
                        if opt == q['Chinese']: 
                            st.session_state.quiz_score += 1; st.toast("🎉 正確！", icon="✅")
                        else: 
                            st.toast(f"❌ 錯了，是 {q['Chinese']}", icon="❌"); add_to_mistake_notebook(q, current_user)
                        st.rerun()
            else:
                if st.button("➡️ 下一題", type="primary", use_container_width=True, key="next_quiz"):
                    st.session_state.quiz_current = None; st.rerun()

    # Tab 5: 拼字
    with tabs[4]:
        if filtered_df.empty: st.warning("沒單字無法測驗")
        else:
            if st.session_state.spell_current is None:
                st.session_state.spell_current = filtered_df.sample(1).iloc[0]
                st.session_state.spell_input = ""; st.session_state.spell_checked = False; st.rerun()
            sq = st.session_state.spell_current
            st.markdown(f"""<div class="quiz-card"><div style="color:#888;">請聽音拼字</div><div class="quiz-word" style="font-size:24px;">{sq['Chinese']}</div></div>""", unsafe_allow_html=True)
            if st.button("🔊 播放發音", use_container_width=True, key="play_spell_audio"):
                st.markdown(get_audio_html(sq['Word'], tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
            if not st.session_state.spell_checked:
                inp = st.text_input("輸入單字", key="sp_in")
                if st.button("送出", type="primary", use_container_width=True, key="submit_spell"):
                    st.session_state.spell_checked = True; st.session_state.spell_input = inp; st.session_state.spell_total += 1
                    if inp.strip().lower() == str(sq['Word']).strip().lower():
                        st.session_state.spell_score += 1; st.session_state.spell_correct = True
                    else:
                        st.session_state.spell_correct = False; add_to_mistake_notebook(sq, current_user)
                    st.rerun()
            else:
                if st.session_state.spell_correct: st.success(f"🎉 正確！ {sq['Word']}")
                else: st.error(f"❌ 錯誤。答案是：{sq['Word']}")
                if st.button("➡️ 下一題", type="primary", use_container_width=True, key="next_spell"):
                    st.session_state.spell_current = None; st.rerun()

    st.markdown(f'<div class="version-tag">{VERSION}</div>', unsafe_allow_html=True)

def main():
    initialize_session_state()
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.current_page == "settings": settings_page()
        elif st.session_state.current_page == "download": download_page()
        else: main_page()

if __name__ == "__main__":
    main()
