import streamlit as st
import pandas as pd
import json
import base64
from io import BytesIO
import time
import random
import uuid
import urllib.parse # 用於處理網址中的單字編碼

# ==========================================
# 0. 核心設定 (必須放最上面)
# ==========================================
st.set_page_config(page_title="職場英文生存術", layout="wide", page_icon="🏭")

VERSION = "v66.0 (V65 Layout + G-Trans URL Fix)"

def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ==========================================
# 1. CSS 樣式 (完全維持 V65/V54)
# ==========================================
st.markdown("""
<style>
    /* 全域設定 */
    .main { background-color: #f8f9fa; }
    #MainMenu, footer { visibility: hidden; }

    /* --- 強制手機版欄位「絕對不換行」 --- */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 3px !important;
        align-items: center !important;
        overflow-x: hidden !important;
    }
    
    /* 欄位縮小 */
    [data-testid="column"] {
        min-width: 0px !important;
        flex: 1 !important;
        padding: 0px 1px !important;
        overflow: visible !important;
    }

    /* --- 列表卡片 --- */
    .list-card {
        background: #ffffff;
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 12px;
        border-left: 6px solid #4CAF50;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    .word-row {
        display: flex;
        align-items: baseline;
        gap: 10px;
        margin-bottom: 10px;
        flex-wrap: wrap;
    }

    .list-word { font-size: 22px; font-weight: 900; color: #2e7d32; }
    .list-ipa { font-size: 15px; color: #888; font-family: monospace; }
    .list-mean { font-size: 18px; color: #1565C0; font-weight: bold; }

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
    
    /* 按鈕微調 */
    .stButton>button { border-radius: 8px; font-weight: bold; width: 100%; min-height: 45px; }
    
    /* 連結按鈕樣式 (模擬 Streamlit 按鈕) */
    a.custom-link-btn {
        display: inline-flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        height: 45px;
        background-color: #f0f2f6;
        color: #31333F;
        text-decoration: none;
        border-radius: 8px;
        border: 1px solid #d6d6d8;
        font-weight: 600;
        font-size: 14px;
        white-space: nowrap;
        position: relative;
        z-index: 10;
    }
    a.custom-link-btn:hover {
        border-color: #f63366;
        color: #f63366;
    }

    .version-tag { text-align: center; color: #aaa; font-size: 10px; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心功能
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
        style = "width: 100%; height: 40px;" if visible else "width: 0; height: 0; display: none;"
        
        return f"""
            <audio id="{rand_id}" controls {autoplay_attr} style="{style}" preload="auto">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            <script>
                var audio = document.getElementById("{rand_id}");
                if (audio) {{
                    audio.play().catch(function(error) {{
                        console.log("Autoplay blocked: " + error);
                    }});
                }}
            </script>
        """
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
    fp = BytesIO(); tts.write_to_fp(fp)
    return fp.getvalue()

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
# 3. 頁面邏輯
# ==========================================

def initialize_session_state():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'current_user' not in st.session_state: st.session_state.current_user = None
    if 'df' not in st.session_state: st.session_state.df = get_google_sheet_data()
    if 'current_page' not in st.session_state: st.session_state.current_page = "main"
    if 'play_order' not in st.session_state: st.session_state.play_order = ["英文", "中文"]
    if 'accent_tld' not in st.session_state: st.session_state.accent_tld = 'com'
    if 'is_slow' not in st.session_state: st.session_state.is_slow = False
    if 'is_sliding' not in st.session_state: st.session_state.is_sliding = False
    if 'card_idx' not in st.session_state: st.session_state.card_idx = 0
    
    # 測驗/拼字變數
    for k in ['quiz_current', 'quiz_score', 'quiz_total', 'quiz_answered', 'quiz_options']:
        if k not in st.session_state: st.session_state[k] = None if 'current' in k or 'options' in k else 0
    for k in ['spell_current', 'spell_input', 'spell_checked', 'spell_correct', 'spell_score', 'spell_total']:
         if k not in st.session_state: st.session_state[k] = "" if 'input' in k else (None if 'current' in k else 0)

# --- 設定頁面 (恢復) ---
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

# --- 下載頁面 (恢復) ---
def download_page():
    st.subheader("📥 下載")
    if st.button("🔙 返回", use_container_width=True): st.session_state.current_page = "main"; safe_rerun()
    st.divider()
    
    df = st.session_state.df
    user_df = df[df['User'] == st.session_state.current_user]
    st.write(f"您的單字總數: {len(user_df)}")
    
    if not user_df.empty:
        # Excel
        st.download_button("📥 下載 Excel", data=to_excel(user_df), file_name="vocab.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        # MP3
        st.markdown("---")
        if st.button("🎵 製作 MP3", use_container_width=True):
            with st.spinner("錄音中..."):
                mp3_data = generate_custom_audio(user_df, st.session_state.play_order, st.session_state.accent_tld, st.session_state.is_slow)
                st.session_state.mp3_cache = mp3_data
                safe_rerun()
        if 'mp3_cache' in st.session_state:
             st.download_button("⬇️ 下載 MP3", st.session_state.mp3_cache, file_name="vocab_audio.mp3", mime="audio/mp3", use_container_width=True)
    else:
        st.warning("無資料可下載")

# --- 主功能頁面 ---
def main_page():
    df_all = st.session_state.df
    current_user = st.session_state.current_user
    df = df_all[df_all['User'] == current_user]
    notebooks = sorted(list(set(df['Notebook'].dropna().unique().tolist())))
    if 'Default' not in notebooks: notebooks.append('Default')
    if "🔥 錯題本 (Auto)" not in notebooks: notebooks.append("🔥 錯題本 (Auto)")

    # 頂部導航
    c_title, c_controls = st.columns([6, 4])
    with c_title: st.markdown(f"**Hi, {current_user}**")
    with c_controls:
        b_set, b_dl = st.columns(2)
        with b_set:
            if st.button("⚙️ 設定", use_container_width=True): st.session_state.current_page = "settings"; safe_rerun()
        with b_dl:
            if st.button("📥 下載", use_container_width=True): st.session_state.current_page = "download"; safe_rerun()

    # --- 新增單字區塊 ---
    st.write("📝 **新增單字**")
    st.session_state.nb_mode = st.radio("來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed", index=0 if st.session_state.nb_mode=="選擇現有" else 1)
    
    if st.session_state.nb_mode == "選擇現有":
        target_nb = st.selectbox("筆記本", notebooks, label_visibility="collapsed")
    else:
        target_nb = st.text_input("新筆記本名稱", placeholder="例如: 會議單字", label_visibility="collapsed")

    w_in = st.text_input("輸入英文單字", placeholder="例如: Polymer")
    
    # 批量輸入
    with st.expander("📂 批量輸入 (自動翻譯)"):
        st.caption("請輸入英文單字，用逗號隔開。")
        batch_text = st.text_area("輸入範例：Apple, Banana", height=100)
        if st.button("批量加入", use_container_width=True):
            if not target_nb: st.error("請選擇筆記本"); st.stop()
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
                save_to_google_sheet(st.session_state.df); st.success(f"已加入 {cnt} 個！"); time.sleep(1); safe_rerun()

    # 單筆按鈕
    b1, b2 = st.columns(2)
    with b1:
        if st.button("👀 翻譯", use_container_width=True):
            if w_in: st.info(GoogleTranslator(source='auto', target='zh-TW').translate(w_in))
    with b2:
        if st.button("🔊 試聽", use_container_width=True):
            if w_in: st.markdown(get_audio_html(w_in, tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
    
    if st.button("➕ 加入單字庫", type="primary", use_container_width=True):
        if w_in and target_nb:
            if check_duplicate(st.session_state.df, current_user, target_nb, w_in):
                st.toast("⚠️ 單字已存在")
            else:
                try:
                    ipa = f"[{eng_to_ipa.convert(w_in)}]"
                    trans = GoogleTranslator(source='auto', target='zh-TW').translate(w_in)
                    new = {'User': current_user, 'Notebook': target_nb, 'Word': w_in, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new])], ignore_index=True)
                    save_to_google_sheet(st.session_state.df)
                    st.toast(f"✅ 已加入: {w_in}")
                except Exception as e: st.error(str(e))

    st.divider()
    filter_nb = st.selectbox("複習筆記本", ["全部"] + notebooks)
    filtered_df = df if filter_nb == "全部" else df[df['Notebook'] == filter_nb]
    st.info(f"📚 {filter_nb}: 共 {len(filtered_df)} 個單字")

    tabs = st.tabs(["列表", "卡片", "輪播", "測驗", "拼字"])
    
    # --- Tab 1: 列表 (V54排版 + G翻譯修復) ---
    with tabs[0]:
        if not filtered_df.empty:
            for i, row in filtered_df.iloc[::-1].iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="list-card">
                        <div class="word-row">
                            <span class="list-word">{row['Word']}</span>
                            <span class="list-ipa">{row['IPA']}</span>
                            <span class="list-mean">{row['Chinese']}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)
                    
                    # V54: 四個按鈕一行
                    c1, c2, c3, c4 = st.columns([1, 1, 1.5, 1.5])
                    with c1:
                        if st.button("🔊", key=f"p_{i}"):
                            st.markdown(get_audio_html(row['Word'], tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
                    with c2:
                        if st.button("🗑️", key=f"d_{i}"):
                            st.session_state.df = st.session_state.df.drop(i)
                            save_to_google_sheet(st.session_state.df)
                            safe_rerun()
                    with c3:
                        # 修正: 加入 urllib.parse.quote 確保單字正確帶入
                        safe_word = urllib.parse.quote(row['Word'])
                        st.markdown(f'''<a href="https://translate.google.com/?sl=en&tl=zh-TW&text={safe_word}&op=translate" target="_blank" class="custom-link-btn">G 翻譯</a>''', unsafe_allow_html=True)
                    with c4:
                        safe_word_y = urllib.parse.quote(row['Word'])
                        st.markdown(f'''<a href="https://tw.dictionary.search.yahoo.com/search?p={safe_word_y}" target="_blank" class="custom-link-btn">Y 字典</a>''', unsafe_allow_html=True)
        else: st.info("無資料")

    # --- Tab 2: 卡片 ---
    with tabs[1]:
        if not filtered_df.empty:
            idx = st.session_state.card_idx % len(filtered_df)
            row = filtered_df.iloc[idx]
            st.markdown(f"""<div class="card-box"><div class="card-word">{row['Word']}</div><div class="card-ipa">{row['IPA']}</div></div>""", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1: 
                if st.button("◀", key="c_prev"): st.session_state.card_idx -= 1; safe_rerun()
            with c2:
                if st.button("👀 中文 / 發音", key="c_rev", use_container_width=True):
                    st.info(f"{row['Chinese']}")
                    st.markdown(get_audio_html(row['Word'], tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
            with c3:
                if st.button("▶", key="c_next"): st.session_state.card_idx += 1; safe_rerun()

    # --- Tab 3: 輪播 ---
    with tabs[2]:
        if not st.session_state.is_sliding:
            if st.button("▶️ 開始輪播", type="primary", use_container_width=True):
                st.session_state.is_sliding = True; safe_rerun()
        else:
            if st.button("⏹️ 停止輪播", type="primary", use_container_width=True):
                st.session_state.is_sliding = False; safe_rerun()

        if st.session_state.is_sliding:
            ph = st.empty()
            slide_df = filtered_df.sample(frac=1)
            for r_idx, row in slide_df.iterrows():
                if not st.session_state.is_sliding: break
                for step in st.session_state.play_order:
                    if not st.session_state.is_sliding: break
                    ph.empty(); time.sleep(0.2)
                    txt = row['Word'] if step == "英文" else row['Chinese']
                    lang = 'en' if step == "英文" else 'zh-TW'
                    with ph.container():
                        st.markdown(f"""<div class="card-box"><div class="card-word" style="font-size:36px;">{txt}</div></div>""", unsafe_allow_html=True)
                        st.markdown(get_audio_html(txt, lang, st.session_state.accent_tld, st.session_state.is_slow, autoplay=True, visible=False), unsafe_allow_html=True)
                    time.sleep(2.5)
            st.session_state.is_sliding = False; safe_rerun()

    with tabs[3]: st.info("測驗功能請使用電腦版")
    with tabs[4]: st.info("拼字功能請使用電腦版")

    st.markdown(f'<div class="version-tag">{VERSION}</div>', unsafe_allow_html=True)

# 登入頁面
def login_page():
    st.markdown("<h1 style='text-align:center;'>🚀 職場英文生存術</h1>", unsafe_allow_html=True)
    user = st.text_input("輸入您的 ID", placeholder="Kevin")
    if st.button("登入", type="primary", use_container_width=True) and user:
        st.session_state.current_user = user.strip(); st.session_state.logged_in = True; safe_rerun()

def main():
    initialize_session_state()
    if not st.session_state.logged_in: login_page()
    elif st.session_state.current_page == "settings": settings_page()
    elif st.session_state.current_page == "download": download_page()
    else: main_page()

if __name__ == "__main__":
    main()
