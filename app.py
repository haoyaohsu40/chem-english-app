import streamlit as st
import pandas as pd
import json
import base64
from io import BytesIO
import time
import random
import uuid

# --- 安全引用第三方套件 ---
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    from gtts import gTTS
    from deep_translator import GoogleTranslator
    import eng_to_ipa
except ImportError as e:
    st.error(f"❌ 缺少必要套件: {e}")
    st.stop()

# ==========================================
# 0. 核心設定與相容性
# ==========================================
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

VERSION = "v53.0 (Mobile Fix & Batch Input)"
st.set_page_config(page_title="職場英文生存術", layout="wide", page_icon="🏭")

# ==========================================
# 1. CSS 樣式 (強制修正跑版與深色模式衝突)
# ==========================================
st.markdown("""
<style>
    /* 全域設定 */
    .main { background-color: #f8f9fa; }
    #MainMenu, footer { visibility: hidden; }

    /* --- 列表卡片優化 (手機版橫排關鍵) --- */
    .list-card {
        background: #ffffff !important;
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 12px;
        border-left: 6px solid #4CAF50;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        gap: 5px;
    }
    
    .list-header {
        display: flex;
        align-items: baseline;
        gap: 8px;
        flex-wrap: wrap;
    }

    .list-word { font-size: 20px; font-weight: 900; color: #2e7d32; }
    .list-ipa { font-size: 14px; color: #888; font-family: monospace; }
    .list-mean { font-size: 16px; color: #1565C0; font-weight: bold; }

    /* --- 按鈕橫排容器 (Action Row) --- */
    .action-row {
        display: flex;
        flex-direction: row; /* 強制橫向 */
        align-items: center;
        gap: 12px; /* 按鈕間距 */
        margin-top: 5px;
        padding-top: 5px;
        border-top: 1px solid #eee;
    }

    /* 圖示按鈕樣式 */
    .icon-btn {
        text-decoration: none;
        background-color: #f1f3f4;
        color: #555 !important;
        padding: 6px 15px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: bold;
        border: 1px solid #ddd;
        display: flex;
        align-items: center;
        justify-content: center;
        min-width: 40px;
    }
    .icon-btn:hover { background-color: #e8f0fe; color: #1967d2 !important; border-color: #1967d2; }

    /* --- 卡片與測驗 (強制白底黑字，修復深色模式看不見的問題) --- */
    .card-box {
        background-color: #ffffff !important; 
        padding: 30px 20px; 
        border-radius: 15px;
        text-align: center; 
        border: 3px solid #81C784; 
        min-height: 200px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
        margin-bottom: 15px;
        display: flex; 
        flex-direction: column; 
        justify-content: center;
        align-items: center;
    }
    
    .quiz-card {
        background-color: #fffde7 !important; /* 強制亮黃底 */
        padding: 20px; 
        border-radius: 15px;
        text-align: center; 
        border: 2px dashed #fbc02d; 
        margin-bottom: 15px;
    }
    
    /* 強制文字顏色 */
    .card-word { font-size: 38px; font-weight: 900; color: #2E7D32 !important; margin-bottom: 10px; }
    .card-ipa { font-size: 16px; color: #666 !important; margin-bottom: 15px; }
    .quiz-word { font-size: 32px; font-weight: 900; color: #1565C0 !important; margin: 10px 0; }
    .quiz-hint { color: #888 !important; font-size: 14px; }

    /* --- 統計數據橫排 --- */
    .stats-row {
        display: flex;
        justify-content: center;
        gap: 15px;
        margin-bottom: 15px;
        background: #e3f2fd;
        padding: 10px;
        border-radius: 10px;
    }
    .stat-item { font-size: 15px; color: #0277bd; font-weight: bold; }

    /* Streamlit 元件微調 */
    .stButton>button { border-radius: 8px; font-weight: bold; width: 100%; }
    .stTextInput>div>div>input { background-color: #ffffff !important; color: #333 !important; }
    
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
        # 如果 invisible，我們將其設為隱藏但保留 DOM
        style = "width: 100%; height: 30px;" if visible else "width: 0; height: 0; overflow: hidden; display: none;"
        return f"""<audio id="{rand_id}" controls {autoplay_attr} style="{style}" preload="auto"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>"""
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
    if 'nb_mode' not in st.session_state: st.session_state.nb_mode = "選擇現有"
    if 'is_sliding' not in st.session_state: st.session_state.is_sliding = False
    
    # 測驗變數
    for k in ['quiz_current', 'quiz_score', 'quiz_total', 'quiz_answered', 'quiz_options']:
        if k not in st.session_state: st.session_state[k] = None if 'current' in k or 'options' in k else 0
    # 拼字變數
    for k in ['spell_current', 'spell_input', 'spell_checked', 'spell_correct', 'spell_score', 'spell_total']:
         if k not in st.session_state: st.session_state[k] = "" if 'input' in k else (None if 'current' in k else 0)

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

    # --- 新增單字區塊 (含批量輸入) ---
    st.write("📝 **新增單字**")
    st.session_state.nb_mode = st.radio("來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed", index=0 if st.session_state.nb_mode=="選擇現有" else 1)
    
    if st.session_state.nb_mode == "選擇現有":
        target_nb = st.selectbox("筆記本", notebooks, label_visibility="collapsed")
    else:
        target_nb = st.text_input("新筆記本名稱", placeholder="例如: 會議單字", label_visibility="collapsed")

    # 單筆輸入
    w_in = st.text_input("輸入英文單字", placeholder="例如: Polymer")
    
    # 2. 批量輸入 (修正需求)
    with st.expander("📂 批量輸入 (多個單字)"):
        batch_text = st.text_area("格式：英文,中文 (每一行一個)", placeholder="Apple,蘋果\nBanana,香蕉")
        if st.button("批量加入"):
            if not target_nb: st.error("請選擇筆記本"); st.stop()
            lines = batch_text.strip().split('\n')
            added_count = 0
            for line in lines:
                if "," in line:
                    parts = line.split(",", 1)
                    w, m = parts[0].strip(), parts[1].strip()
                    if w and m and not check_duplicate(st.session_state.df, current_user, target_nb, w):
                        try:
                            ipa = f"[{eng_to_ipa.convert(w)}]"
                            new = {'User': current_user, 'Notebook': target_nb, 'Word': w, 'IPA': ipa, 'Chinese': m, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new])], ignore_index=True)
                            added_count += 1
                        except: pass
            if added_count > 0:
                save_to_google_sheet(st.session_state.df)
                st.success(f"成功加入 {added_count} 個單字！"); time.sleep(1); safe_rerun()
            else: st.warning("未加入任何單字，請檢查格式或是否重複。")

    # 單筆操作按鈕
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
        else: st.toast("請輸入單字與選擇筆記本")

    st.divider()
    filter_nb = st.selectbox("複習筆記本", ["全部"] + notebooks)
    filtered_df = df if filter_nb == "全部" else df[df['Notebook'] == filter_nb]
    
    # 統計數據
    st.markdown(f"""<div class="stats-row"><div class="stat-item">☁️ 雲端總數: {len(df)}</div><div class="stat-item">📖 本子字數: {len(filtered_df)}</div></div>""", unsafe_allow_html=True)

    tabs = st.tabs(["列表", "卡片", "輪播", "測驗", "拼字"])
    
    # --- Tab 1: 列表 (修正: 按鈕強制橫向) ---
    with tabs[0]:
        if not filtered_df.empty:
            for i, row in filtered_df.iloc[::-1].iterrows():
                # 生成不顯示的音訊 HTML 供按鈕調用
                audio_html = get_audio_html(row['Word'], tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True, visible=False)
                
                # HTML 結構：上方是文字，下方是按鈕列 (Action Row)
                # 使用 HTML <a> 標籤製作圖示按鈕，保證永遠橫向
                html_block = f"""
                <div class="list-card">
                    <div class="list-header">
                        <span class="list-word">{row['Word']}</span>
                        <span class="list-ipa">{row['IPA']}</span>
                        <span class="list-mean">{row['Chinese']}</span>
                    </div>
                    <div class="action-row">
                        <a href="https://translate.google.com/?sl=en&tl=zh-TW&text={row['Word']}&op=translate" target="_blank" class="icon-btn">G</a>
                        <a href="https://tw.dictionary.search.yahoo.com/search?p={row['Word']}" target="_blank" class="icon-btn">Y</a>
                    </div>
                </div>
                """
                st.markdown(html_block, unsafe_allow_html=True)
                
                # 為了讓刪除按鈕和發音按鈕能運作，我們使用 Streamlit 的 columns 放在卡片下方
                # 但為了視覺上的「同一排」，我們調整 marginTop
                c_act1, c_act2, c_space = st.columns([1, 1, 3])
                with c_act1:
                     if st.button("🔊 發音", key=f"play_{i}"):
                         st.markdown(audio_html, unsafe_allow_html=True)
                with c_act2:
                     if st.button("🗑️ 刪除", key=f"del_{i}"):
                         st.session_state.df = st.session_state.df.drop(i)
                         save_to_google_sheet(st.session_state.df)
                         safe_rerun()
        else: st.info("無資料")

    # --- Tab 2: 卡片 ---
    with tabs[1]:
        if not filtered_df.empty:
            if 'card_idx' not in st.session_state: st.session_state.card_idx = 0
            idx = st.session_state.card_idx % len(filtered_df)
            row = filtered_df.iloc[idx]
            # 強制樣式，修復深色模式
            st.markdown(f"""
            <div class="card-box">
                <div class="card-word">{row['Word']}</div>
                <div class="card-ipa">{row['IPA']}</div>
            </div>""", unsafe_allow_html=True)
            
            cb1, cb2, cb3 = st.columns([1, 2, 1])
            with cb1: 
                if st.button("◀", key="c_prev"): st.session_state.card_idx -= 1; safe_rerun()
            with cb2:
                if st.button("👀 中文 / 發音", key="c_rev", use_container_width=True):
                    st.info(f"{row['Chinese']}")
                    st.markdown(get_audio_html(row['Word'], tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
            with cb3:
                if st.button("▶", key="c_next"): st.session_state.card_idx += 1; safe_rerun()

    # --- Tab 3: 輪播 (修正聲音) ---
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
                    
                    # 生成 HTML
                    html = f"""<div class="card-box"><div class="card-word" style="font-size:36px;">{txt}</div></div>"""
                    
                    with ph.container():
                        st.markdown(html, unsafe_allow_html=True)
                        # 自動播放 (嘗試)
                        st.markdown(get_audio_html(txt, lang, st.session_state.accent_tld, st.session_state.is_slow, autoplay=True, visible=False), unsafe_allow_html=True)
                        # 手動播放備案 (修正需求 3)
                        st.caption("若無聲音請點下方按鈕:")
                        if st.button("🔊 手動播放", key=f"slide_man_{r_idx}_{step}"):
                            st.markdown(get_audio_html(txt, lang, st.session_state.accent_tld, st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
                    
                    time.sleep(2.5)
            st.session_state.is_sliding = False; safe_rerun()

    # --- Tab 4: 測驗 (修復顯示問題) ---
    with tabs[3]:
        if filtered_df.empty: st.warning("沒單字無法測驗")
        else:
            c1, c2 = st.columns([3,1])
            rate = (st.session_state.quiz_score/st.session_state.quiz_total)*100 if st.session_state.quiz_total>0 else 0
            c1.caption(f"答對: {st.session_state.quiz_score}/{st.session_state.quiz_total} ({rate:.0f}%)")
            if c2.button("歸零"): st.session_state.quiz_score=0; st.session_state.quiz_total=0; safe_rerun()

            if st.session_state.quiz_current is None:
                target = filtered_df.sample(1).iloc[0]
                st.session_state.quiz_current = target
                others = filtered_df[filtered_df['Chinese'] != target['Chinese']]
                distractors = others.sample(min(3, len(others)))['Chinese'].tolist()
                while len(distractors) < 3: distractors.append("無選項")
                opts = [target['Chinese']] + distractors; random.shuffle(opts)
                st.session_state.quiz_options = opts
                st.session_state.quiz_answered = False
                safe_rerun()
            
            q = st.session_state.quiz_current
            # 強制背景色樣式
            st.markdown(f"""<div class="quiz-card"><div class="quiz-word">{q['Word']}</div><div class="quiz-hint">請選擇正確中文</div></div>""", unsafe_allow_html=True)
            
            if st.button("🔊 播放讀音", use_container_width=True):
                st.markdown(get_audio_html(q['Word'], tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)

            if not st.session_state.quiz_answered:
                for idx, opt in enumerate(st.session_state.quiz_options):
                    if st.button(opt, use_container_width=True, key=f"q_{idx}"):
                        st.session_state.quiz_answered = True
                        st.session_state.quiz_total += 1
                        if opt == q['Chinese']: st.session_state.quiz_score += 1; st.toast("✅ 正確")
                        else: st.toast(f"❌ 錯誤! 是 {q['Chinese']}");
                        safe_rerun()
            else:
                if st.button("➡️ 下一題", type="primary", use_container_width=True):
                    st.session_state.quiz_current = None; safe_rerun()

    # --- Tab 5: 拼字 (修復顯示問題) ---
    with tabs[4]:
        if filtered_df.empty: st.warning("沒單字")
        else:
            if st.session_state.spell_current is None:
                st.session_state.spell_current = filtered_df.sample(1).iloc[0]
                st.session_state.spell_input = ""; st.session_state.spell_checked = False; safe_rerun()
            
            sq = st.session_state.spell_current
            st.markdown(f"""<div class="quiz-card"><div class="quiz-hint">請聽音拼寫出單字</div><div class="quiz-word">{sq['Chinese']}</div></div>""", unsafe_allow_html=True)
            
            if st.button("🔊 播放單字", use_container_width=True, key="sp_play"):
                st.markdown(get_audio_html(sq['Word'], tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)

            if not st.session_state.spell_checked:
                inp = st.text_input("輸入拼寫", key="spell_in_box")
                if st.button("送出"):
                    st.session_state.spell_checked = True; st.session_state.spell_input = inp
                    st.session_state.spell_total += 1
                    if inp.strip().lower() == str(sq['Word']).strip().lower():
                        st.session_state.spell_score += 1; st.session_state.spell_correct = True
                    else: st.session_state.spell_correct = False
                    safe_rerun()
            else:
                if st.session_state.spell_correct: st.success(f"🎉 正確! {sq['Word']}")
                else: st.error(f"❌ 錯誤，正確是: {sq['Word']}")
                if st.button("➡️ 下一題", type="primary", use_container_width=True):
                    st.session_state.spell_current = None; safe_rerun()
    
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
    elif st.session_state.current_page == "settings": 
        st.button("🔙 返回", on_click=lambda: setattr(st.session_state, 'current_page', 'main')); st.title("設定 (開發中)")
    elif st.session_state.current_page == "download":
        st.button("🔙 返回", on_click=lambda: setattr(st.session_state, 'current_page', 'main')); st.title("下載 (開發中)")
        st.download_button("下載 Excel", data=pd.DataFrame().to_csv(), file_name="vocab.csv")
    else: main_page()

if __name__ == "__main__":
    main()
