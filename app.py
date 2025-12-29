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
VERSION = "v48.1 (Mobile Fixes)"
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
    .login-title { font-size: 22px; font-weight: 900; color: #1565C0; margin-bottom: 5px; }
    
    /* 頂部 Header */
    .header-row {
        background: white; padding: 10px 15px; border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 10px;
        display: flex; align-items: center; justify-content: space-between;
    }
    
    /* 輸入框優化 */
    .stTextInput>div>div>input { color: #333 !important; background-color: white !important; }

    /* 列表模式 */
    .list-row {
        background: white; padding: 10px 12px; margin-bottom: 6px;
        border-radius: 8px; border-left: 4px solid #4CAF50;
        box-shadow: 0 1px 2px rgba(0,0,0,0.08);
        display: flex; align-items: center;
    }
    .list-word { font-size: 17px; font-weight: bold; color: #2e7d32; margin-right: 8px; }
    .list-ipa { font-size: 13px; color: #757575; font-family: monospace; margin-right: 10px; }
    .list-mean { font-size: 15px; color: #1565C0; flex-grow: 1; }

    /* 卡片模式 */
    .card-box {
        background-color: white; padding: 20px; border-radius: 15px;
        text-align: center; border: 2px solid #81C784; min-height: 200px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 15px;
    }
    .card-word { font-size: 36px; font-weight: bold; color: #2E7D32; line-height: 1.2; margin-bottom: 5px; }
    .card-ipa { font-size: 16px; color: #666; margin-bottom: 15px; }
    
    /* 按鈕樣式 */
    .stButton>button { border-radius: 15px; width: 100%; font-weight: bold; }
    
    /* 版本號 */
    .version-tag { text-align: center; color: #aaa; font-size: 12px; margin-top: 30px; }
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

def get_audio_html(text, lang='en', tld='com', slow=False, autoplay=False):
    try:
        if not text: return ""
        tts = gTTS(text=str(text), lang=lang, tld=tld, slow=slow)
        fp = BytesIO(); tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        rand_id = f"audio_{uuid.uuid4()}"
        autoplay_attr = "autoplay" if autoplay else ""
        return f"""<audio id="{rand_id}" controls {autoplay_attr} style="width: 100%; margin-top: 5px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>"""
    except: return ""

# --- 關鍵修正：使用 Callback 來處理加入單字，避免報錯 ---
def add_word_callback():
    w_in = st.session_state.input_word
    # 決定筆記本名稱
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
                st.session_state.input_word = "" # 在 Callback 中清空是安全的
            except Exception as e:
                st.session_state.msg_warning = f"錯誤: {str(e)}"
    else:
         st.session_state.msg_warning = "⚠️ 請輸入單字並選擇筆記本"

# ==========================================
# 3. 狀態初始化
# ==========================================

def initialize_session_state():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'df' not in st.session_state: st.session_state.df = get_google_sheet_data()
    
    # 設定相關
    if 'play_order' not in st.session_state: st.session_state.play_order = ["英文", "中文"]
    if 'accent_tld' not in st.session_state: st.session_state.accent_tld = 'com'
    if 'is_slow' not in st.session_state: st.session_state.is_slow = False
    
    # 介面狀態
    if 'show_settings' not in st.session_state: st.session_state.show_settings = False
    if 'nb_mode' not in st.session_state: st.session_state.nb_mode = "選擇現有"
    
    # 訊息
    if 'msg_success' not in st.session_state: st.session_state.msg_success = ""
    if 'msg_warning' not in st.session_state: st.session_state.msg_warning = ""

# ==========================================
# 4. 頁面佈局
# ==========================================

def login_page():
    st.markdown("""<div class="login-container"><div class="login-title">🚀 職場英文生存術</div><div style="color:#666;font-size:14px;">輸入代號，立即開始</div></div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 8, 1])
    with c2:
        user_input = st.text_input("您的 英文ID / 姓名", placeholder="例如: Kevin", key="login_user")
        st.write("")
        if st.button("🚀 登入", type="primary", use_container_width=True):
            if user_input:
                st.session_state.current_user = user_input.strip()
                st.session_state.logged_in = True
                st.rerun()

def main_app():
    # 訊息通知
    if st.session_state.msg_success:
        st.toast(st.session_state.msg_success, icon="✅")
        st.session_state.msg_success = ""
    if st.session_state.msg_warning:
        st.toast(st.session_state.msg_warning, icon="⚠️")
        st.session_state.msg_warning = ""

    df_all = st.session_state.df
    current_user = st.session_state.current_user
    df = df_all[df_all['User'] == current_user]
    
    # 取得筆記本列表
    notebooks = sorted(list(set(df['Notebook'].dropna().unique().tolist())))
    if 'Default' not in notebooks: notebooks.append('Default')

    # --- Header (Logo + Settings + Download) ---
    c_h1, c_h2, c_h3 = st.columns([6, 1.5, 1.5]) # 調整比例讓按鈕在同一列
    with c_h1: st.markdown(f"**👋 Hi, {current_user}**")
    with c_h2: 
        if st.button("⚙️", help="設定"): st.session_state.show_settings = not st.session_state.show_settings
    with c_h3:
        if not df.empty:
            st.download_button("📥", to_excel(df), "vocab.xlsx", help="下載 Excel")

    # --- Settings Expander (補回功能) ---
    if st.session_state.show_settings:
        with st.expander("⚙️ 設定與管理", expanded=True):
            st.caption("🔊 發音設定")
            accents = {'美式 (US)': 'com', '英式 (UK)': 'co.uk'}
            st.session_state.accent_tld = accents[st.selectbox("口音", list(accents.keys()))]
            st.session_state.is_slow = st.checkbox("慢速發音", value=st.session_state.is_slow)
            
            st.divider()
            st.caption("🎧 播放順序")
            po = st.multiselect("順序 (拖拉排序)", ["英文", "中文"], default=st.session_state.play_order)
            st.session_state.play_order = po

            st.divider()
            st.caption("✏️ 筆記本管理 (更名)")
            if notebooks:
                ren_target = st.selectbox("選擇要改名的本子", notebooks, key="ren_sel")
                ren_new = st.text_input("新名稱", key="ren_val")
                if st.button("確認更名"):
                    if ren_new and ren_new != ren_target:
                        df_all.loc[(df_all['User']==current_user) & (df_all['Notebook']==ren_target), 'Notebook'] = ren_new
                        st.session_state.df = df_all; save_to_google_sheet(df_all)
                        st.success("更名成功！"); time.sleep(1); st.rerun()
            
            st.divider()
            if st.button("🚪 登出", type="secondary"): st.session_state.logged_in = False; st.rerun()

    st.markdown("---")

    # --- Input Area (加入筆記本選擇) ---
    st.write("📝 **新增單字**")
    
    # 筆記本選擇模式 (Radio)
    nb_mode = st.radio("筆記本來源", ["選擇現有", "建立新本"], horizontal=True, key="nb_mode", label_visibility="collapsed")
    
    if nb_mode == "選擇現有":
        st.selectbox("存入筆記本", notebooks, key="target_nb_key")
    else:
        st.text_input("輸入新筆記本名稱", placeholder="例如: 會議單字", key="new_nb_name")

    w_in = st.text_input("輸入英文單字", placeholder="例如: Polymer", key="input_word")
    
    b1, b2 = st.columns(2)
    with b1:
        if st.button("👀 翻譯", use_container_width=True):
            if w_in: st.info(GoogleTranslator(source='auto', target='zh-TW').translate(w_in))
    with b2:
        if st.button("🔊 試聽", use_container_width=True):
            if w_in: st.markdown(get_audio_html(w_in, tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
    
    # ★★★ 加入按鈕 (綁定 Callback) ★★★
    st.button("➕ 加入單字庫", type="primary", use_container_width=True, on_click=add_word_callback)

    # --- Filter & Stats ---
    st.divider()
    f1, f2 = st.columns([1, 1])
    with f1:
        st.markdown(f"<div style='text-align:center;color:#666;'>雲端總字數<br><b style='font-size:20px;color:#1565C0;'>{len(df)}</b></div>", unsafe_allow_html=True)
    with f2:
        filter_nb = st.selectbox("複習筆記本", ["全部"] + notebooks, label_visibility="collapsed")
    
    filtered_df = df if filter_nb == "全部" else df[df['Notebook'] == filter_nb]
    st.caption(f"目前顯示: {len(filtered_df)} 字")

    # --- Tabs ---
    tabs = st.tabs(["列表", "卡片", "輪播", "測驗", "拼字"])
    
    # Tab 1: 列表
    with tabs[0]:
        if not filtered_df.empty:
            for i, row in filtered_df.iloc[::-1].iterrows():
                c_txt, c_btn = st.columns([5, 1])
                with c_txt:
                    st.markdown(f"""
                    <div class="list-row">
                        <div>
                            <span class="list-word">{row['Word']}</span>
                            <span class="list-ipa">{row['IPA']}</span>
                            <span class="list-mean">{row['Chinese']}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)
                with c_btn:
                    if st.button("🗑️", key=f"del_{i}"):
                        st.session_state.df = df_all.drop(i)
                        save_to_google_sheet(st.session_state.df)
                        st.rerun()
        else: st.info("尚無單字")

    # Tab 2: 卡片
    with tabs[1]:
        if not filtered_df.empty:
            if 'card_idx' not in st.session_state: st.session_state.card_idx = 0
            idx = st.session_state.card_idx % len(filtered_df)
            row = filtered_df.iloc[idx]
            
            st.markdown(f"""<div class="card-box"><div class="card-word">{row['Word']}</div><div class="card-ipa">{row['IPA']}</div></div>""", unsafe_allow_html=True)
            
            cb1, cb2, cb3 = st.columns([1, 2, 1])
            with cb1: 
                if st.button("◀", key="prev", use_container_width=True): st.session_state.card_idx -= 1; st.rerun()
            with cb2:
                if st.button("中文 / 發音", key="reveal", use_container_width=True):
                    st.info(f"{row['Chinese']}")
                    st.markdown(get_audio_html(row['Word'], tld=st.session_state.accent_tld, autoplay=True), unsafe_allow_html=True)
            with cb3:
                if st.button("▶", key="next", use_container_width=True): st.session_state.card_idx += 1; st.rerun()
        else: st.warning("無資料")

    with tabs[2]: st.info("🚧 輪播功能建置中")
    with tabs[3]: st.info("🚧 測驗功能建置中")
    with tabs[4]: st.info("🚧 拼字功能建置中")

    st.markdown(f'<div class="version-tag">{VERSION}</div>', unsafe_allow_html=True)

def main():
    initialize_session_state()
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
