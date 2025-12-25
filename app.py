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
# 1. 頁面設定與 CSS 樣式 (極致美化版)
# ==========================================
st.set_page_config(page_title="AI 智能單字速記通 (備考衝刺版)", layout="wide", page_icon="🎓")

st.markdown("""
<style>
    .main { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    
    /* 1. 隱藏預設選單 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* 2. 標題區塊美化 */
    .title-container {
        text-align: center;
        padding: 20px 0 40px 0;
        background: linear-gradient(to bottom, #ffffff, #f8f9fa);
        border-radius: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .main-title {
        font-size: 42px;
        font-weight: 900;
        background: -webkit-linear-gradient(45deg, #1565C0, #42A5F5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        padding: 0;
        font-family: 'Arial Black', sans-serif;
    }
    .sub-title {
        font-size: 16px;
        color: #78909c;
        margin-top: 8px;
        font-weight: 600;
        letter-spacing: 1.5px;
    }

    /* 3. 數據卡片 */
    .metric-card {
        background: #ffffff;
        border-left: 6px solid #4CAF50;
        border-radius: 12px;
        padding: 15px 10px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-3px); }
    .metric-label { font-size: 16px; color: #546e7a; font-weight: bold; margin-bottom: 4px; }
    .metric-value { font-size: 36px; font-weight: 800; color: #2e7d32; }

    /* 4. 按鈕優化 */
    .stButton>button { 
        border-radius: 12px; font-weight: bold; border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.08); transition: all 0.2s;
        font-size: 18px !important; padding: 12px 20px; height: auto;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }

    /* 5. 字體放大區 */
    .stRadio label p, .stCheckbox label p, .stSelectbox label p, .stTextInput label p { font-size: 18px !important; }
    .stMarkdown p { font-size: 18px; }

    /* 6. 卡片樣式 */
    .word-text { font-size: 28px; font-weight: bold; color: #2E7D32; font-family: 'Arial Black', sans-serif; }
    .ipa-text { font-size: 18px; color: #757575; }
    .meaning-text { font-size: 24px; color: #1565C0; font-weight: bold;}
    
    .quiz-card {
        background-color: #fff8e1; padding: 40px; border-radius: 20px;
        text-align: center; border: 4px dashed #ffb74d; margin-bottom: 20px;
    }
    .mistake-mode { border: 4px solid #ef5350 !important; background-color: #ffebee !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心功能函式
# ==========================================

def get_google_sheet_data():
    try:
        creds_json = json.loads(st.secrets["service_account"]["info"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        sheet = client.open("vocab_db").sheet1
        data = sheet.get_all_records()
        if not data: return pd.DataFrame(columns=['Notebook', 'Word', 'IPA', 'Chinese', 'Date'])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"連線失敗：{e}")
        return pd.DataFrame(columns=['Notebook', 'Word', 'IPA', 'Chinese', 'Date'])

def save_to_google_sheet(df):
    try:
        creds_json = json.loads(st.secrets["service_account"]["info"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        sheet = client.open("vocab_db").sheet1
        sheet.clear()
        update_data = [df.columns.values.tolist()] + df.values.tolist()
        sheet.update(update_data)
    except Exception as e:
        st.error(f"儲存失敗：{e}")

def is_contains_chinese(string):
    for char in str(string):
        if '\u4e00' <= char <= '\u9fff': return True
    return False

def check_duplicate(df, notebook, word):
    if df.empty: return False
    mask = (df['Notebook'] == notebook) & (df['Word'].str.lower() == str(word).lower().strip())
    return not df[mask].empty

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- 語音功能 ---
def text_to_speech_visible(text, lang='en', tld='com', slow=False):
    try:
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', str(text))
        if not clean_text: return ""
        tts = gTTS(text=clean_text, lang=lang, tld=tld, slow=slow)
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        unique_id = f"audio_vis_{uuid.uuid4()}" 
        return f"""<audio id="{unique_id}" controls style="width: 100%; margin-top: 5px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>"""
    except: return ""

def get_audio_bytes(text, lang='en', tld='com', slow=False):
    try:
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', str(text))
        if not clean_text: return None
        tts = gTTS(text=clean_text, lang=lang, tld=tld, slow=slow)
        fp = BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

def text_to_speech_autoplay_hidden(text, lang='en', tld='com', slow=False):
    try:
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', str(text))
        if not clean_text: return ""
        tts = gTTS(text=clean_text, lang=lang, tld=tld, slow=slow)
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        unique_id = f"audio_hide_{uuid.uuid4()}"
        return f"""<audio autoplay style="display:none;" id="{unique_id}"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>"""
    except: return ""

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

def add_to_mistake_notebook(row):
    df = st.session_state.df
    mistake_nb_name = "🔥 錯題本 (Auto)"
    if not check_duplicate(df, mistake_nb_name, row['Word']):
        new_entry = {'Notebook': mistake_nb_name,'Word': row['Word'],'IPA': row['IPA'],'Chinese': row['Chinese'],'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        st.session_state.df = df; save_to_google_sheet(df)
        return True
    return False

# ==========================================
# 3. 狀態初始化
# ==========================================

def initialize_session_state():
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

# --- 測驗邏輯 ---
def next_question(df):
    if df.empty: return
    target_row = df.sample(1).iloc[0]
    st.session_state.quiz_current = target_row
    correct_opt = str(target_row['Chinese'])
    all_df = st.session_state.df 
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
        st.session_state.quiz_score += 1
        st.session_state.quiz_is_correct = True
    else:
        st.session_state.quiz_is_correct = False
        if add_to_mistake_notebook(current): st.toast(f"已加入錯題本: {current['Word']}", icon="🔥")

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
            st.session_state.spell_score += 1
            st.session_state.spell_correct = True
        else:
            st.session_state.spell_correct = False
            if add_to_mistake_notebook(st.session_state.spell_current): st.toast(f"已加入錯題本: {st.session_state.spell_current['Word']}", icon="🔥")

# ==========================================
# 4. 主程式 Layout
# ==========================================

def main():
    initialize_session_state()
    df = st.session_state.df

    # 1. 標題區
    st.markdown("""
        <div class="title-container">
            <h1 class="main-title">🚀 AI 智能單字速記通 🎓</h1>
            <div class="sub-title">打造您的專屬英文單字庫 • 智慧記憶 • 效率學習</div>
        </div>
    """, unsafe_allow_html=True)

    # 2. 數據卡片
    notebooks = df['Notebook'].unique().tolist()
    if "🔥 錯題本 (Auto)" not in notebooks: notebooks.append("🔥 錯題本 (Auto)")
    
    if 'filter_nb_key' not in st.session_state: st.session_state.filter_nb_key = '全部'
    if st.session_state.filter_nb_key not in ["全部"] + notebooks: st.session_state.filter_nb_key = "全部"

    current_nb = st.session_state.filter_nb_key
    filtered_df = df if current_nb == "全部" else df[df['Notebook'] == current_nb]
    
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">☁️ 雲端總字數</div><div class="metric-value">{len(df)}</div></div>""", unsafe_allow_html=True)
    with c_m2:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">📖 目前本子字數</div><div class="metric-value">{len(filtered_df)}</div></div>""", unsafe_allow_html=True)

    # 3. 側邊欄
    with st.sidebar:
        st.header("📝 新增單字")
        if '預設筆記本' not in notebooks: notebooks.append('預設筆記本')
        
        nb_mode = st.radio("筆記本來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed")
        target_nb = st.selectbox("選擇筆記本", notebooks) if nb_mode == "選擇現有" else st.text_input("輸入新筆記本名稱", "我的單字本")

        st.divider()
        input_type = st.radio("輸入模式", ["🔤 單字輸入", "🚀 批次貼上"], horizontal=True)

        if input_type == "🔤 單字輸入":
            w_in = st.text_input("輸入英文單字", placeholder="例如: Valve")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("👀 翻譯", use_container_width=True):
                    if w_in and not is_contains_chinese(w_in):
                        try: st.info(f"{GoogleTranslator(source='auto', target='zh-TW').translate(w_in)}")
                        except: st.error("失敗")
            with c2:
                if st.button("🔊 試聽", use_container_width=True):
                    if w_in: st.markdown(text_to_speech_visible(w_in, 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow), unsafe_allow_html=True)
            
            if st.button("➕ 加入單字庫", type="primary", use_container_width=True):
                if w_in and target_nb:
                    if check_duplicate(df, target_nb, w_in):
                        st.warning(f"⚠️ 單字 '{w_in}' 已經在 '{target_nb}' 裡面囉！")
                    else:
                        try:
                            ipa = f"[{eng_to_ipa.convert(w_in)}]"
                            trans = GoogleTranslator(source='auto', target='zh-TW').translate(w_in)
                            new = {'Notebook': target_nb, 'Word': w_in, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                            df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                            st.session_state.df = df
                            save_to_google_sheet(df)
                            st.success(f"已儲存：{w_in}")
                            time.sleep(0.5); st.rerun()
                        except Exception as e: st.error(f"錯誤: {e}")
        else:
            bulk_in = st.text_area("📋 批次貼上 (逗號或換行分隔)", height=150)
            if st.button("🚀 批次加入", type="primary"):
                if bulk_in and target_nb:
                    words = re.split(r'[,\n，]', bulk_in)
                    new_entries = []
                    skipped_count = 0
                    
                    bar = st.progress(0)
                    for i, w in enumerate(words):
                        w = w.strip()
                        if w and not is_contains_chinese(w):
                            if check_duplicate(df, target_nb, w):
                                skipped_count += 1
                            else:
                                try:
                                    ipa = f"[{eng_to_ipa.convert(w)}]"
                                    trans = GoogleTranslator(source='auto', target='zh-TW').translate(w)
                                    new_entries.append({'Notebook': target_nb, 'Word': w, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')})
                                except: pass
                        bar.progress((i+1)/len(words))
                    
                    if new_entries:
                        df = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
                        st.session_state.df = df
                        save_to_google_sheet(df)
                        st.success(f"✅ 成功加入 {len(new_entries)} 筆 (已自動過濾 {skipped_count} 筆重複)")
                        time.sleep(2); st.rerun()
                    elif skipped_count > 0:
                        st.warning(f"⚠️ 所有 {skipped_count} 筆單字都重複了，沒有新增任何資料。")

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
                    df.loc[df['Notebook'] == ren_target, 'Notebook'] = ren_new
                    st.session_state.df = df; save_to_google_sheet(df)
                    st.success(f"已更名為 {ren_new}"); time.sleep(1); st.rerun()
            
            st.write("🗑️ **刪除筆記本**")
            del_target = st.selectbox("選擇刪除對象", notebooks, key="del_sel")
            if st.button("刪除此本", type="primary"):
                if st.session_state.get('confirm_del') != del_target:
                    st.warning("再按一次確認"); st.session_state.confirm_del = del_target
                else:
                    df = df[df['Notebook'] != del_target]
                    st.session_state.df = df; save_to_google_sheet(df); st.success("已刪除"); st.rerun()
        
        # 這裡加回版本號
        st.markdown("---")
        st.caption("版本: v31.0 (Spelling Feedback)")

    # 4. 主畫面控制區
    st.divider()
    c_filt, c_tool = st.columns([1, 1.5])
    with c_filt:
        st.selectbox("📖 我要複習哪一本？", ["全部"] + notebooks, key='filter_nb_key')
        if current_nb == "🔥 錯題本 (Auto)": st.warning("🔥 這是您的錯題本，請重點複習！")

    with c_tool:
        st.markdown("**🎧 工具區**")
        t1, t2 = st.columns(2)
        with t1:
            if not filtered_df.empty:
                st.download_button("📥 下載 Excel", to_excel(filtered_df), f"Vocab_{current_nb}.xlsx", use_container_width=True)
            else: st.button("📥 無資料", disabled=True, use_container_width=True)
        with t2:
            if not filtered_df.empty and st.session_state.play_order:
                if st.button("🎵 製作 MP3", use_container_width=True):
                    with st.spinner("製作中..."):
                        mp3 = generate_custom_audio(filtered_df, st.session_state.play_order, st.session_state.accent_tld, st.session_state.is_slow)
                        st.download_button("⬇️ 下載 MP3", mp3, f"Audio_{current_nb}.mp3", "audio/mp3", use_container_width=True)
            else: st.button("🎵 設定順序後下載", disabled=True, use_container_width=True)

    # 5. 導航按鈕
    st.markdown("###")
    n1, n2, n3, n4, n5 = st.columns(5)
    def btn_type(mode_name): return "primary" if st.session_state.current_mode == mode_name else "secondary"

    if n1.button("📋 列表", type=btn_type('list'), use_container_width=True): st.session_state.current_mode = 'list'; st.rerun()
    if n2.button("🃏 卡片", type=btn_type('card'), use_container_width=True): st.session_state.current_mode = 'card'; st.rerun()
    if n3.button("🎬 輪播", type=btn_type('slide'), use_container_width=True): st.session_state.current_mode = 'slide'; st.rerun()
    if n4.button("🏆 測驗", type=btn_type('quiz'), use_container_width=True): st.session_state.current_mode = 'quiz'; st.rerun()
    if n5.button("✍️ 拼字", type=btn_type('spell'), use_container_width=True): st.session_state.current_mode = 'spell'; st.rerun()
    
    st.divider()

    # 6. 內容區
    mode = st.session_state.current_mode

    if mode == 'list':
        if not filtered_df.empty:
            for i, row in filtered_df.iloc[::-1].iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                with c1: st.markdown(f"<div class='word-text'>{row['Word']}</div><div class='ipa-text'>{row['IPA']}</div>", unsafe_allow_html=True)
                with c2: st.markdown(f"<div class='meaning-text'>{row['Chinese']}</div>", unsafe_allow_html=True)
                with c3: 
                    if st.button("🔊", key=f"p{i}"): st.markdown(text_to_speech_visible(row['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow), unsafe_allow_html=True)
                with c4:
                    if st.button("🗑️", key=f"d{i}"):
                        df = df[~((df['Word'] == row['Word']) & (df['Notebook'] == row['Notebook']))]
                        st.session_state.df = df; save_to_google_sheet(df); st.rerun()
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
                    if st.button("🔊 聽發音", use_container_width=True): st.markdown(text_to_speech_visible(row['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow), unsafe_allow_html=True)
        else: st.info("無單字")

    elif mode == 'slide':
        delay = st.slider("每張卡片停留秒數", 2, 8, 3)
        ph = st.empty()
        if st.button("▶️ 開始輪播", type="primary"):
            if not st.session_state.play_order: st.error("請先設定播放順序")
            else:
                for _, row in filtered_df.iloc[::-1].iterrows():
                    for step in st.session_state.play_order:
                        ph.empty(); time.sleep(0.1)
                        html = f"""<div style="border:3px solid #4CAF50;border-radius:20px;padding:50px;text-align:center;background:#f0fdf4;min-height:350px;"><div style="font-size:60px;color:#2E7D32;font-weight:bold;">{row['Word']}</div><div style="color:#666;font-size:24px;">{row['IPA']}</div>"""
                        if step == "英文": html += f"""<div style="color:#aaa;">Listening...</div>{text_to_speech_autoplay_hidden(row['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow)}"""
                        elif step == "中文": html += f"""<div style="font-size:50px;color:#1565C0;font-weight:bold;">{row['Chinese']}</div>{text_to_speech_autoplay_hidden(row['Chinese'], 'zh-TW', slow=st.session_state.is_slow)}"""
                        html += "</div>"
                        ph.markdown(html, unsafe_allow_html=True); time.sleep(delay)
                ph.success("輪播結束")

    elif mode == 'quiz':
        q_mode = st.radio("🎯 測驗範圍", ["📖 當前筆記本", "🔥 錯題本"], horizontal=True, key="qm")
        target_df = df[df['Notebook'] == "🔥 錯題本 (Auto)"] if q_mode == "🔥 錯題本" else filtered_df

        c_s, c_r = st.columns([3, 1])
        rate = (st.session_state.quiz_score/st.session_state.quiz_total)*100 if st.session_state.quiz_total>0 else 0
        c_s.markdown(f"📊 答對：**{st.session_state.quiz_score}** / **{st.session_state.quiz_total}** ({rate:.1f}%)")
        if c_r.button("🔄 重置"): st.session_state.quiz_score=0; st.session_state.quiz_total=0; st.rerun()

        if target_df.empty:
            st.success("錯題本是空的！") if q_mode == "🔥 錯題本" else st.warning("無單字")
        else:
            if st.session_state.quiz_current is None or st.session_state.quiz_current['Word'] not in target_df['Word'].values:
                next_question(target_df); st.rerun()
            q = st.session_state.quiz_current
            card_cls = "quiz-card mistake-mode" if q_mode == "🔥 錯題本" else "quiz-card"
            st.markdown(f"""<div class="{card_cls}"><div style="color:#555;">選出正確中文 (答錯自動加入錯題本)</div><div class="quiz-word">{q['Word']}</div><div>{q['IPA']}</div></div>""", unsafe_allow_html=True)
            
            ab = get_audio_bytes(q['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow)
            if ab: st.audio(ab, format='audio/mp3')

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

        if target_df.empty:
            st.success("錯題本是空的！") if s_mode == "🔥 錯題本" else st.warning("無單字")
        else:
            if st.session_state.spell_current is None or st.session_state.spell_current['Word'] not in target_df['Word'].values:
                next_spelling(target_df); st.rerun()
            
            sq = st.session_state.spell_current
            card_cls = "quiz-card mistake-mode" if s_mode == "🔥 錯題本" else "quiz-card"
            st.markdown(f"""<div class="{card_cls}"><div style="color:#555;">聽發音輸入英文 (答錯自動加入錯題本)</div><div style="font-size:18px;color:#666;">(中文意思)</div><div style="font-size:36px;color:#1565C0;font-weight:bold;margin:10px 0;">{sq['Chinese']}</div></div>""", unsafe_allow_html=True)
            
            sab = get_audio_bytes(sq['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow)
            if sab: st.audio(sab, format='audio/mp3')

            if not st.session_state.spell_checked:
                inp = st.text_input("輸入單字", key="spin")
                if st.button("✅ 送出", type="primary"):
                    st.session_state.spell_input = inp; check_spelling(); st.rerun()
            else:
                if st.session_state.spell_correct: st.success(f"🎉 拼對了！ {sq['Word']}"); st.balloons()
                else: 
                    # 這裡加入了詳細的錯誤反饋
                    st.error(f"❌ 拼錯了...\n\n您的輸入：**{st.session_state.spell_input}**\n\n正確答案：**{sq['Word']}**")
                
                if st.button("➡️ 下一題", type="primary"): next_spelling(target_df); st.rerun()

if __name__ == "__main__":
    main()
