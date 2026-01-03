import streamlit as st
import pandas as pd
import json
import base64
from io import BytesIO
import time
import random
import uuid
import urllib.parse  # 新增: 用於處理網址參數

# ==========================================
# 1. 核心設定
# ==========================================
st.set_page_config(page_title="職場英文生存術", layout="wide", page_icon="🏭")

VERSION = "v62.0 (MP3 Restore & G-Trans Fix)"

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
# 3. CSS 樣式 (維持手機橫排優化)
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    #MainMenu, footer { visibility: hidden; }

    /* 強制手機版欄位絕對不換行 */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 3px !important;
        align-items: center !important;
        overflow-x: hidden !important;
    }
    
    [data-testid="column"] {
        min-width: 0px !important;
        flex: 1 !important;
        padding: 0px 1px !important;
        overflow: visible !important;
    }

    /* 按鈕樣式 */
    .stButton > button {
        padding: 0px !important;
        font-size: 12px !important;
        height: 36px !important;
        min-height: 36px !important;
        border-radius: 6px !important;
        font-weight: bold !important;
        border: 1px solid #ccc !important;
        background-color: #ffffff !important;
        color: #333 !important;
        width: 100% !important;
    }
    .stButton > button:active { background-color: #e3f2fd !important; }

    /* 連結按鈕 (G翻譯/Y字典) */
    a.custom-link-btn {
        display: flex; justify-content: center; align-items: center;
        width: 100%; height: 36px;
        background-color: #ffffff; color: #333333 !important;
        text-decoration: none; border-radius: 6px;
        border: 1px solid #ccc; font-weight: bold; font-size: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        white-space: nowrap; z-index: 99; position: relative;
    }
    a.custom-link-btn:hover { border-color: #2196F3; color: #2196F3 !important; background-color: #f0f8ff; }

    /* 列表卡片 */
    .list-card {
        background-color: #ffffff !important;
        padding: 10px; margin-bottom: 5px;
        border-radius: 10px; border-left: 5px solid #4CAF50;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .word-row { display: flex; align-items: baseline; gap: 5px; margin-bottom: 5px; flex-wrap: wrap; }
    .list-word { font-size: 18px; font-weight: 900; color: #2e7d32 !important; margin-right: 5px; }
    .list-ipa { font-size: 13px; color: #666 !important; font-family: monospace; }
    .list-mean { font-size: 16px; color: #1565C0 !important; font-weight: bold; }

    /* 卡片模式 */
    .card-box {
        background-color: #ffffff !important; padding: 20px; border-radius: 15px;
        text-align: center; border: 3px solid #81C784; min-height: 200px;
        margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .card-word { font-size: 36px; font-weight: 900; color: #2E7D32 !important; margin-bottom: 10px; }
    
    .stTextInput input { color: #333 !important; background-color: #fff !important; }
    .version-tag { text-align: center; color: #aaa; font-size: 10px; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. 核心功能函式
# ==========================================
def safe_rerun():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()

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
        style = "width: 100%; height: 30px;" if visible else "width: 0; height: 0; display: none;"
        
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

def generate_custom_audio(df, sequence, tld='com', slow=False):
    """產生整本筆記本的 MP3"""
    try:
        full_text = ""
        # 取倒序前 50 個字 (避免生成太久)
        process_df = df.iloc[::-1].head(50) 
        for i, (index, row) in enumerate(process_df.iterrows(), start=1):
            word = str(row['Word'])
            chinese = str(row['Chinese'])
            full_text += f"Number {i}. " 
            if not sequence: 
                full_text += f"{word}. {chinese}. "
            else:
                for item in sequence:
                    if item == "英文": full_text += f"{word}. "
                    elif item == "中文": full_text += f"{chinese}. "
            full_text += " ... " # 暫停
        
        tts = gTTS(text=full_text, lang='zh-TW', slow=slow) # 使用中文引擎混讀
        fp = BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except: return None

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
# 5. 頁面邏輯
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
    if 'current_page' not in st.session_state: st.session_state.current_page = "main"

# --- 設定頁面 ---
def settings_page():
    st.subheader("⚙️ 設定")
    if st.button("🔙 返回", use_container_width=True): st.session_state.current_page = "main"; safe_rerun()
    st.divider()
    
    st.write("**發音設定:**")
    acc = st.selectbox("口音選擇", ["美式 (com)", "英式 (co.uk)"])
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

# --- 下載頁面 (MP3 功能回復) ---
def download_page():
    st.subheader("📥 下載")
    if st.button("🔙 返回", use_container_width=True): st.session_state.current_page = "main"; safe_rerun()
    st.divider()
    
    df = st.session_state.df
    user_df = df[df['User'] == st.session_state.current_user]
    st.write(f"您的單字總數: {len(user_df)}")
    
    if not user_df.empty:
        st.markdown("#### 1. Excel 檔案")
        st.download_button("📥 下載 Excel", data=to_excel(user_df), file_name="vocab.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        
        st.markdown("#### 2. MP3 音訊檔 (前50字)")
        if st.button("🎵 製作並下載 MP3", use_container_width=True):
            with st.spinner("正在錄製中...請稍候"):
                mp3_data = generate_custom_audio(user_df, st.session_state.play_order, st.session_state.accent_tld, st.session_state.is_slow)
                if mp3_data:
                    st.download_button("⬇️ 點擊下載 MP3", data=mp3_data, file_name="vocab_audio.mp3", mime="audio/mp3", use_container_width=True)
                else:
                    st.error("製作失敗")
    else:
        st.warning("無資料可下載")

# --- 主功能頁面 ---
def main_page():
    df_all = st.session_state.df
    current_user = st.session_state.current_user
    df = df_all[df_all['User'] == current_user]
    notebooks = sorted(list(set(df['Notebook'].dropna().unique().tolist())))
    if 'Default' not in notebooks: notebooks.append('Default')

    # 頂部
    c1, c2 = st.columns([6, 4])
    with c1: st.markdown(f"**Hi, {current_user}**")
    with c2:
        b1, b2 = st.columns(2)
        with b1: 
            if st.button("⚙️"): st.session_state.current_page = "settings"; safe_rerun()
        with b2: 
            if st.button("📥"): st.session_state.current_page = "download"; safe_rerun()

    # 新增單字
    with st.expander("📝 新增單字", expanded=True):
        nb_mode = st.radio("來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed")
        if nb_mode == "選擇現有":
            target_nb = st.selectbox("筆記本", notebooks, label_visibility="collapsed")
        else:
            target_nb = st.text_input("新筆記本", placeholder="例如: 會議")

        w_in = st.text_input("單字", placeholder="例如: Polymer")
        
        c_tr, c_ls = st.columns(2)
        with c_tr:
            if st.button("👀 翻譯", use_container_width=True):
                if w_in and PACKAGES_OK: st.info(GoogleTranslator(source='auto', target='zh-TW').translate(w_in))
        with c_ls:
            if st.button("🔊 試聽", use_container_width=True):
                if w_in: st.markdown(get_audio_html(w_in, autoplay=True), unsafe_allow_html=True)
                
        if st.button("➕ 加入單字庫", type="primary", use_container_width=True):
            if w_in and target_nb and PACKAGES_OK:
                if check_duplicate(st.session_state.df, current_user, target_nb, w_in):
                    st.toast("已存在")
                else:
                    try:
                        ipa = f"[{eng_to_ipa.convert(w_in)}]"
                        trans = GoogleTranslator(source='auto', target='zh-TW').translate(w_in)
                        new = {'User': current_user, 'Notebook': target_nb, 'Word': w_in, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new])], ignore_index=True)
                        save_to_google_sheet(st.session_state.df)
                        st.toast(f"✅ 加入: {w_in}"); safe_rerun()
                    except: st.error("加入失敗")

        st.markdown("---")
        st.caption("📂 批量輸入 (英文,逗號隔開)")
        batch_text = st.text_area("批量", placeholder="apple, banana, dog", height=60, label_visibility="collapsed")
        if st.button("批量加入", use_container_width=True):
            if not target_nb: st.error("請選筆記本"); st.stop()
            words = batch_text.replace('\n', ',').split(',')
            cnt = 0
            for w in words:
                w = w.strip()
                if w and not check_duplicate(st.session_state.df, current_user, target_nb, w) and PACKAGES_OK:
                    try:
                        ipa = f"[{eng_to_ipa.convert(w)}]"
                        trans = GoogleTranslator(source='auto', target='zh-TW').translate(w)
                        new = {'User': current_user, 'Notebook': target_nb, 'Word': w, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new])], ignore_index=True)
                        cnt += 1
                    except: pass
            if cnt > 0:
                save_to_google_sheet(st.session_state.df); st.success(f"已加入 {cnt} 個！"); time.sleep(1); safe_rerun()

    st.divider()
    filter_nb = st.selectbox("📖 選擇筆記本", ["全部"] + notebooks)
    filtered_df = df if filter_nb == "全部" else df[df['Notebook'] == filter_nb]
    st.info(f"📚 {filter_nb}: {len(filtered_df)} 字")

    tabs = st.tabs(["列表", "卡片", "輪播", "測驗", "拼字"])
    
    # --- Tab 1: 列表 ---
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
                    
                    c1, c2, c3, c4 = st.columns([0.8, 0.8, 1.2, 1.2])
                    with c1:
                        if st.button("🔊", key=f"play_{i}"):
                            st.markdown(get_audio_html(row['Word'], autoplay=True, visible=False), unsafe_allow_html=True)
                    with c2:
                        if st.button("🗑️", key=f"del_{i}"):
                            st.session_state.df = st.session_state.df.drop(i)
                            save_to_google_sheet(st.session_state.df)
                            safe_rerun()
                    with c3:
                        # 修正: 帶入單字
                        word_encoded = urllib.parse.quote(row['Word'])
                        st.markdown(f'''<a href="https://translate.google.com/?sl=auto&tl=zh-TW&text={word_encoded}&op=translate" target="_blank" class="custom-link-btn">G翻譯</a>''', unsafe_allow_html=True)
                    with c4:
                        st.markdown(f'''<a href="https://tw.dictionary.search.yahoo.com/search?p={row['Word']}" target="_blank" class="custom-link-btn">Y字典</a>''', unsafe_allow_html=True)
        else: st.info("無資料")

    # --- Tab 2: 卡片 ---
    with tabs[1]:
        if not filtered_df.empty:
            idx = st.session_state.card_idx % len(filtered_df)
            row = filtered_df.iloc[idx]
            st.markdown(f"""<div class="card-box"><div class="card-word">{row['Word']}</div><div class="list-ipa">{row['IPA']}</div></div>""", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1,2,1])
            with c1: 
                if st.button("◀"): st.session_state.card_idx -= 1; safe_rerun()
            with c2: 
                if st.button("👀 中文"): 
                    st.info(row['Chinese']); st.markdown(get_audio_html(row['Word'], autoplay=True), unsafe_allow_html=True)
            with c3: 
                if st.button("▶"): st.session_state.card_idx += 1; safe_rerun()

    # --- Tab 3: 輪播 ---
    with tabs[2]:
        if not st.session_state.is_sliding:
            if st.button("▶️ 開始", type="primary", use_container_width=True): st.session_state.is_sliding = True; safe_rerun()
        else:
            if st.button("⏹️ 停止", type="primary", use_container_width=True): st.session_state.is_sliding = False; safe_rerun()
        
        if st.session_state.is_sliding:
            ph = st.empty()
            slide_df = filtered_df.sample(frac=1)
            for _, row in slide_df.iterrows():
                if not st.session_state.is_sliding: break
                for step in st.session_state.play_order:
                    if not st.session_state.is_sliding: break
                    ph.empty(); time.sleep(0.2)
                    txt = row['Word'] if step=="英文" else row['Chinese']
                    lang = 'en' if step=="英文" else 'zh-TW'
                    with ph.container():
                        st.markdown(f"""<div class="card-box"><div class="card-word">{txt}</div></div>""", unsafe_allow_html=True)
                        st.markdown(get_audio_html(txt, lang, autoplay=True, visible=False), unsafe_allow_html=True)
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
