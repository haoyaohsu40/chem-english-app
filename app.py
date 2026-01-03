import streamlit as st
import pandas as pd
import json
import base64
from io import BytesIO
import time
import random
import uuid
import urllib.parse

# ==========================================
# 1. 核心設定 (必須放最上面，防止白屏)
# ==========================================
st.set_page_config(page_title="職場英文生存術", layout="wide", page_icon="🏭")

VERSION = "v63.0 (V54 Logic + V58 Layout + Fixes)"

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

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# ==========================================
# 4. CSS 樣式 (基於 V58 手機橫排技術)
# ==========================================
st.markdown("""
<style>
    /* 全域設定 */
    .stApp { background-color: #f8f9fa; }
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
        st.download_button("📥 下載 Excel", data=to_excel(user_df), file_name="vocab.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
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
            if st.button("⚙️", use_container_width=True): st.session_state.current_page = "settings"; safe_rerun()
        with b_dl:
            if st.button("📥", use_container_width=True): st.session_state.current_page = "download"; safe_rerun()

    # --- 新增單字區塊 ---
    with st.expander("📝 新增單字", expanded=True):
        st.session_state.nb_mode = st.radio("來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed")
        
        if st.session_state.nb_mode == "選擇現有":
            target_nb = st.selectbox("筆記本", notebooks, label_visibility="collapsed")
        else:
            target_nb = st.text_input("新筆記本名稱", placeholder="例如: 會議單字", label_visibility="collapsed")

        w_in = st.text_input("輸入英文單字", placeholder="例如: Polymer")
        
        # 批量輸入 (自動翻譯版)
        st.caption("📂 批量輸入 (英文,逗號隔開)")
        batch_text = st.text_area("批量", height=60, label_visibility="collapsed", placeholder="apple, banana, dog")
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

        # 單筆按鈕
        b1, b2 = st.columns(2)
        with b1:
            if st.button("👀 翻譯", use_container_width=True):
                if w_in and PACKAGES_OK: st.info(GoogleTranslator(source='auto', target='zh-TW').translate(w_in))
        with b2:
            if st.button("🔊 試聽", use_container_width=True):
                if w_in: st.markdown(get_audio_html(w_in, autoplay=True), unsafe_allow_html=True)
        
        if st.button("➕ 加入單字庫", type="primary", use_container_width=True):
            if w_in and target_nb and PACKAGES_OK:
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
    filter_nb = st.selectbox("📖 選擇筆記本", ["全部"] + notebooks)
    filtered_df = df if filter_nb == "全部" else df[df['Notebook'] == filter_nb]
    
    st.info(f"📚 {filter_nb}: 共 {len(filtered_df)} 個單字")

    tabs = st.tabs(["列表", "卡片", "輪播", "測驗", "拼字"])
    
    # --- Tab 1: 列表 (修正: 4個按鈕同一排) ---
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
                    
                    # 使用 4 欄位，比例調整以適應手機
                    # 順序: [發音] [刪除] [G翻譯] [Y字典]
                    c1, c2, c3, c4 = st.columns([0.8, 0.8, 1.2, 1.2])
                    
                    with c1:
                        if st.button("🔊", key=f"p_{i}"):
                            st.markdown(get_audio_html(row['Word'], tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True, visible=False), unsafe_allow_html=True)
                    
                    with c2:
                        if st.button("🗑️", key=f"d_{i}"):
                            st.session_state.df = st.session_state.df.drop(i)
                            save_to_google_sheet(st.session_state.df)
                            safe_rerun()
                    
                    with c3:
                        # 修正: sl=auto 確保偵測, text=帶入單字
                        st.markdown(f'''<a href="https://translate.google.com/?sl=auto&tl=zh-TW&text={row['Word']}&op=translate" target="_blank" class="custom-link-btn">G翻譯</a>''', unsafe_allow_html=True)

                    with c4:
                        st.markdown(f'''<a href="https://tw.dictionary.search.yahoo.com/search?p={row['Word']}" target="_blank" class="custom-link-btn">Y字典</a>''', unsafe_allow_html=True)
        else: st.info("無資料")

    # --- Tab 2: 卡片 ---
    with tabs[1]:
        if not filtered_df.empty:
            if 'card_idx' not in st.session_state: st.session_state.card_idx = 0
            idx = st.session_state.card_idx % len(filtered_df)
            row = filtered_df.iloc[idx]
            
            st.markdown(f"""
            <div class="card-box">
                <div class="card-word">{row['Word']}</div>
                <div class="card-ipa">{row['IPA']}</div>
            </div>""", unsafe_allow_html=True)
            
            cb1, cb2, cb3 = st.columns([1, 2, 1])
            with cb1: 
                if st.button("◀", key="c_prev"): st.session_state.card_idx -= 1; safe_rerun()
            with cb2:
                if st.button("👀 中文", key="c_rev", use_container_width=True):
                    st.info(f"{row['Chinese']}")
                    st.markdown(get_audio_html(row['Word'], tld=st.session_state.accent_tld, slow=st.session_state.is_slow, autoplay=True), unsafe_allow_html=True)
            with cb3:
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

    # --- Tab 4: 測驗 ---
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
            st.markdown(f"""<div class="quiz-card"><div class="quiz-word">{q['Word']}</div></div>""", unsafe_allow_html=True)
            
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

    # --- Tab 5: 拼字 ---
    with tabs[4]:
        if filtered_df.empty: st.warning("沒單字")
        else:
            if st.session_state.spell_current is None:
                st.session_state.spell_current = filtered_df.sample(1).iloc[0]
                st.session_state.spell_input = ""; st.session_state.spell_checked = False; safe_rerun()
            
            sq = st.session_state.spell_current
            st.markdown(f"""<div class="quiz-card"><div style="color:#666;">請聽音拼寫出單字</div><div class="quiz-word">{sq['Chinese']}</div></div>""", unsafe_allow_html=True)
            
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
    elif st.session_state.current_page == "settings": settings_page()
    elif st.session_state.current_page == "download": download_page()
    else: main_page()

if __name__ == "__main__":
    main()
