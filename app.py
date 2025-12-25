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
# 1. 頁面設定與 CSS 樣式
# ==========================================
st.set_page_config(page_title="AI 智能單字速記通 (學生備考版)", layout="wide", page_icon="🎓")

# 隱藏右上角選單 + 自定義樣式
st.markdown("""
<style>
    .main { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    .stButton>button { 
        border-radius: 10px; font-weight: bold; border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: all 0.2s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
    
    .metric-card {
        background-color: #ffffff; border: 2px solid #4CAF50; border-radius: 15px;
        padding: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 10px;
    }
    .metric-label { font-size: 14px; color: #666; margin-bottom: 5px; font-weight: bold;}
    .metric-value { font-size: 36px; font-weight: bold; color: #d32f2f; }

    .word-text { font-size: 24px; font-weight: bold; color: #2E7D32; font-family: 'Arial Black', sans-serif; }
    .ipa-text { font-size: 14px; color: #757575; }
    .meaning-text { font-size: 20px; color: #1565C0; font-weight: bold;}

    .quiz-card {
        background-color: #fff8e1; padding: 30px; border-radius: 20px;
        text-align: center; border: 3px dashed #ffb74d; margin-bottom: 20px;
    }
    .quiz-word { font-size: 40px; color: #333; font-weight: bold; margin: 10px 0; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
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

# --- 錯題本邏輯 ---
def add_to_mistake_notebook(row):
    """將答錯的題目加入錯題本"""
    df = st.session_state.df
    mistake_nb_name = "🔥 錯題本 (Auto)"
    
    # 檢查是否已經在錯題本中
    exists = df[(df['Notebook'] == mistake_nb_name) & (df['Word'] == row['Word'])]
    if exists.empty:
        new_entry = {
            'Notebook': mistake_nb_name,
            'Word': row['Word'],
            'IPA': row['IPA'],
            'Chinese': row['Chinese'],
            'Date': pd.Timestamp.now().strftime('%Y-%m-%d')
        }
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        st.session_state.df = df
        save_to_google_sheet(df)
        return True # 新增成功
    return False # 已經存在

# ==========================================
# 3. 狀態初始化
# ==========================================

def initialize_session_state():
    if 'df' not in st.session_state: st.session_state.df = get_google_sheet_data()
    if 'play_order' not in st.session_state: st.session_state.play_order = ["英文", "中文", "英文"] 
    if 'accent_tld' not in st.session_state: st.session_state.accent_tld = 'com'
    if 'is_slow' not in st.session_state: st.session_state.is_slow = False
    
    # 選擇題測驗狀態
    if 'quiz_score' not in st.session_state: st.session_state.quiz_score = 0
    if 'quiz_total' not in st.session_state: st.session_state.quiz_total = 0
    if 'quiz_current' not in st.session_state: st.session_state.quiz_current = None
    if 'quiz_options' not in st.session_state: st.session_state.quiz_options = []
    if 'quiz_answered' not in st.session_state: st.session_state.quiz_answered = False
    if 'quiz_is_correct' not in st.session_state: st.session_state.quiz_is_correct = False

    # 拼字測驗狀態
    if 'spell_current' not in st.session_state: st.session_state.spell_current = None
    if 'spell_input' not in st.session_state: st.session_state.spell_input = ""
    if 'spell_checked' not in st.session_state: st.session_state.spell_checked = False
    if 'spell_correct' not in st.session_state: st.session_state.spell_correct = False
    if 'spell_score' not in st.session_state: st.session_state.spell_score = 0
    if 'spell_total' not in st.session_state: st.session_state.spell_total = 0

# --- 選擇題邏輯 ---
def next_question(df):
    if df.empty: return
    target_row = df.sample(1).iloc[0]
    st.session_state.quiz_current = target_row
    correct_opt = str(target_row['Chinese'])
    other_rows = df[df['Chinese'] != correct_opt]
    
    if len(other_rows) >= 3: distractors = other_rows.sample(3)['Chinese'].astype(str).tolist()
    else:
        placeholders = ["蘋果", "閥門", "幫浦", "螺絲", "溫度", "壓力", "反應器"]
        candidates = [p for p in placeholders if p != correct_opt]
        needed = 3 - len(other_rows)
        distractors = other_rows['Chinese'].astype(str).tolist() + random.sample(candidates, min(len(candidates), needed))
        while len(distractors) < 3: distractors.append("未知單字")
    
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
        # 自動加入錯題本
        added = add_to_mistake_notebook(current)
        if added: st.toast(f"已將 '{current['Word']}' 加入錯題本", icon="🔥")

# --- 拼字測驗邏輯 ---
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
        
        correct_word = str(st.session_state.spell_current['Word']).strip().lower()
        user_input = str(st.session_state.spell_input).strip().lower()
        
        if correct_word == user_input:
            st.session_state.spell_score += 1
            st.session_state.spell_correct = True
        else:
            st.session_state.spell_correct = False
            # 自動加入錯題本
            added = add_to_mistake_notebook(st.session_state.spell_current)
            if added: st.toast(f"已將 '{st.session_state.spell_current['Word']}' 加入錯題本", icon="🔥")

# ==========================================
# 4. 主程式 Layout
# ==========================================

def main():
    initialize_session_state()
    df = st.session_state.df

    col_header, col_metrics_area = st.columns([2, 2])
    with col_header:
        st.title("🎓 AI 智能單字速記通")
        st.caption("學生備考版 v27.0 (Spelling + MistakeBook)")

    # 筆記本篩選 (特別標註錯題本)
    notebooks = df['Notebook'].unique().tolist()
    if "🔥 錯題本 (Auto)" not in notebooks: notebooks.append("🔥 錯題本 (Auto)")
    
    current_notebook_filter = st.session_state.get('filter_nb_key', '全部')
    filtered_df = df if current_notebook_filter == "全部" else df[df['Notebook'] == current_notebook_filter]
    
    with col_metrics_area:
        m1, m2 = st.columns(2)
        with m1:
            st.markdown(f"""<div class="metric-card"><div class="metric-label">☁️ 雲端總字數</div><div class="metric-value">{len(df)}</div></div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div class="metric-card"><div class="metric-label">📖 目前本子字數</div><div class="metric-value">{len(filtered_df)}</div></div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("📝 新增單字")
        if '預設筆記本' not in notebooks: notebooks.append('預設筆記本')
        
        nb_mode_opt = st.radio("筆記本來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed")
        if nb_mode_opt == "選擇現有": target_notebook = st.selectbox("選擇筆記本", notebooks)
        else: target_notebook = st.text_input("輸入新筆記本名稱", "我的單字本")

        st.markdown("---")
        input_mode = st.radio("輸入模式", ["🔤 單字輸入", "🚀 批次貼上"], horizontal=True)

        if input_mode == "🔤 單字輸入":
            word_input = st.text_input("輸入英文單字", placeholder="例如: Valve")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("👀 翻譯", use_container_width=True):
                    if word_input and not is_contains_chinese(word_input):
                        try: st.info(f"{GoogleTranslator(source='auto', target='zh-TW').translate(word_input)}")
                        except: st.error("失敗")
            with c2:
                if st.button("🔊 試聽", use_container_width=True):
                    if word_input: st.markdown(text_to_speech_visible(word_input, 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow), unsafe_allow_html=True)
            
            if st.button("➕ 加入單字庫", type="primary", use_container_width=True):
                if word_input and target_notebook:
                    try:
                        ipa = f"[{eng_to_ipa.convert(word_input)}]"
                        trans = GoogleTranslator(source='auto', target='zh-TW').translate(word_input)
                        new_entry = {'Notebook': target_notebook, 'Word': word_input, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                        st.session_state.df = df
                        save_to_google_sheet(df)
                        st.success(f"已儲存：{word_input}"); time.sleep(0.5); st.rerun()
                    except Exception as e: st.error(f"錯誤: {e}")
        else:
            bulk_input = st.text_area("📋 批次貼上", height=100)
            if st.button("🚀 批次加入", type="primary"):
                if bulk_input and target_notebook:
                    words = re.split(r'[,\n，]', bulk_input)
                    new_entries = []
                    bar = st.progress(0)
                    for i, w in enumerate(words):
                        w = w.strip()
                        if w and not is_contains_chinese(w):
                            try:
                                ipa = f"[{eng_to_ipa.convert(w)}]"
                                trans = GoogleTranslator(source='auto', target='zh-TW').translate(w)
                                new_entries.append({'Notebook': target_notebook, 'Word': w, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')})
                            except: pass
                        bar.progress((i+1)/len(words))
                    if new_entries:
                        df = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
                        st.session_state.df = df
                        save_to_google_sheet(df)
                        st.success(f"加入 {len(new_entries)} 筆"); time.sleep(1); st.rerun()

        st.markdown("---")
        with st.expander("🔊 發音與語速", expanded=False):
            accents = {'美式 (US)': 'com', '英式 (UK)': 'co.uk', '澳式 (AU)': 'com.au', '印度 (IN)': 'co.in'}
            curr_acc = [k for k, v in accents.items() if v == st.session_state.accent_tld][0]
            st.session_state.accent_tld = accents[st.selectbox("口音", list(accents.keys()), index=list(accents.keys()).index(curr_acc))]
            
            speeds = {'正常': False, '慢速': True}
            curr_spd = [k for k, v in speeds.items() if v == st.session_state.is_slow][0]
            st.session_state.is_slow = speeds[st.radio("語速", list(speeds.keys()), index=list(speeds.keys()).index(curr_spd))]

        with st.expander("🎧 播放順序", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1: 
                if st.button("➕ 英文"): st.session_state.play_order.append("英文")
            with c2: 
                if st.button("➕ 中文"): st.session_state.play_order.append("中文")
            with c3: 
                if st.button("❌ 清空"): st.session_state.play_order = []
            st.info(f"順序：{' ➝ '.join(st.session_state.play_order) if st.session_state.play_order else '(未設定)'}")

        st.markdown("---")
        with st.expander("🛠️ 進階管理"):
            if st.button("🔄 強制更新"): st.session_state.df = get_google_sheet_data(); st.success("已更新"); st.rerun()
            st.divider()
            st.write("🗑️ **刪除筆記本**")
            del_nb = st.selectbox("選擇刪除對象", notebooks, key="del_sel")
            if st.button("刪除此本", type="primary"):
                if st.session_state.get('confirm_del') != del_nb:
                    st.warning("再按一次確認"); st.session_state.confirm_del = del_nb
                else:
                    df = df[df['Notebook'] != del_nb]
                    st.session_state.df = df; save_to_google_sheet(df); st.success("已刪除"); st.rerun()
        st.markdown("---"); st.caption("v27.0 Student Edition")

    st.divider()
    c_filt, c_tool = st.columns([1, 1.5])
    with c_filt:
        st.selectbox("📖 我要複習哪一本？", ["全部"] + notebooks, key='filter_nb_key')
        if current_notebook_filter == "🔥 錯題本 (Auto)":
            st.warning("🔥 這是您的錯題本，請重點複習！")

    with c_tool:
        st.write("🎧 **工具區**")
        t1, t2 = st.columns(2)
        with t1:
            if not filtered_df.empty:
                st.download_button("📥 下載 Excel", to_excel(filtered_df), f"Vocab_{current_notebook_filter}.xlsx", use_container_width=True)
            else: st.button("📥 無資料", disabled=True, use_container_width=True)
        with t2:
            if not filtered_df.empty and st.session_state.play_order:
                if st.button("🎵 製作 MP3", use_container_width=True):
                    with st.spinner("製作中..."):
                        mp3 = generate_custom_audio(filtered_df, st.session_state.play_order, st.session_state.accent_tld, st.session_state.is_slow)
                        st.download_button("⬇️ 下載 MP3", mp3, f"Audio_{current_notebook_filter}.mp3", "audio/mp3", use_container_width=True)
            else: st.button("🎵 設定順序後下載", disabled=True, use_container_width=True)

    st.markdown("###")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 列表", "🃏 卡片", "🎬 輪播", "🏆 測驗", "✍️ 拼字"])

    # Tab 1: 列表
    with tab1:
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
        else: st.info("無單字")

    # Tab 2: 卡片
    with tab2:
        if not filtered_df.empty:
            if 'card_idx' not in st.session_state: st.session_state.card_idx = 0
            idx = st.session_state.card_idx % len(filtered_df)
            row = filtered_df.iloc[idx]
            c_p, c_c, c_n = st.columns([1,4,1])
            with c_p: 
                st.write(""); st.write(""); st.write("")
                if st.button("◀"): st.session_state.card_idx -= 1; st.rerun()
            with c_n: 
                st.write(""); st.write(""); st.write("")
                if st.button("▶"): st.session_state.card_idx += 1; st.rerun()
            with c_c:
                st.markdown(f"""<div style="border:2px solid #81C784;border-radius:20px;padding:50px;text-align:center;min-height:300px;"><div style="font-size:60px;color:#2E7D32;font-weight:bold;">{row['Word']}</div><div style="color:#666;font-size:24px;">{row['IPA']}</div></div>""", unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                with b1: 
                    if st.button("👀 看中文", use_container_width=True): st.info(f"{row['Chinese']}")
                with b2: 
                    if st.button("🔊 聽發音", use_container_width=True): st.markdown(text_to_speech_visible(row['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow), unsafe_allow_html=True)

    # Tab 3: 輪播
    with tab3:
        delay = st.slider("秒數", 2, 8, 3)
        ph = st.empty()
        if st.button("▶️ 開始", type="primary"):
            if not st.session_state.play_order: st.error("請設順序")
            else:
                for _, row in filtered_df.iloc[::-1].iterrows():
                    for step in st.session_state.play_order:
                        ph.empty(); time.sleep(0.1)
                        html = f"""<div style="border:2px solid #4CAF50;border-radius:20px;padding:40px;text-align:center;background:#f0fdf4;min-height:300px;"><div style="font-size:50px;color:#2E7D32;font-weight:bold;">{row['Word']}</div><div style="color:#666;">{row['IPA']}</div>"""
                        if step == "英文": html += f"""<div style="color:#aaa;">Listening...</div>{text_to_speech_autoplay_hidden(row['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow)}"""
                        elif step == "中文": html += f"""<div style="font-size:40px;color:#1565C0;font-weight:bold;">{row['Chinese']}</div>{text_to_speech_autoplay_hidden(row['Chinese'], 'zh-TW', slow=st.session_state.is_slow)}"""
                        html += "</div>"
                        ph.markdown(html, unsafe_allow_html=True); time.sleep(delay)
                ph.success("結束")

    # Tab 4: 選擇測驗
    with tab4:
        c_s, c_r = st.columns([3, 1])
        rate = (st.session_state.quiz_score/st.session_state.quiz_total)*100 if st.session_state.quiz_total>0 else 0
        c_s.markdown(f"📊 答對：**{st.session_state.quiz_score}** / **{st.session_state.quiz_total}** ({rate:.1f}%)")
        if c_r.button("🔄 重置"): st.session_state.quiz_score=0; st.session_state.quiz_total=0; st.rerun()
        st.divider()

        if filtered_df.empty: st.warning("無單字")
        else:
            if st.session_state.quiz_current is None: next_question(filtered_df)
            q = st.session_state.quiz_current
            st.markdown(f"""<div class="quiz-card"><div style="color:#555;">請選出正確中文 (答錯將自動加入錯題本)</div><div class="quiz-word">{q['Word']}</div><div>{q['IPA']}</div></div>""", unsafe_allow_html=True)
            
            ab = get_audio_bytes(q['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow)
            if ab: st.audio(ab, format='audio/mp3')

            if not st.session_state.quiz_answered:
                cols = st.columns(2)
                for i, opt in enumerate(st.session_state.quiz_options):
                    if cols[i%2].button(opt, key=f"qo{i}", use_container_width=True): check_answer(opt); st.rerun()
            else:
                if st.session_state.quiz_is_correct: st.success("🎉 正確！"); st.balloons()
                else: st.error(f"❌ 錯誤。正確：{q['Chinese']}")
                if st.button("➡️ 下一題", type="primary", use_container_width=True): next_question(filtered_df); st.rerun()

    # Tab 5: 拼字測驗 (新功能)
    with tab5:
        c_ss, c_sr = st.columns([3, 1])
        s_rate = (st.session_state.spell_score/st.session_state.spell_total)*100 if st.session_state.spell_total>0 else 0
        c_ss.markdown(f"✍️ 拼寫：**{st.session_state.spell_score}** / **{st.session_state.spell_total}** ({s_rate:.1f}%)")
        if c_sr.button("🔄 重置拼寫"): st.session_state.spell_score=0; st.session_state.spell_total=0; st.rerun()
        st.divider()

        if filtered_df.empty: st.warning("無單字")
        else:
            if st.session_state.spell_current is None: next_spelling(filtered_df)
            sq = st.session_state.spell_current
            
            st.markdown(f"""<div class="quiz-card"><div style="color:#555;">請聽發音並輸入英文 (答錯自動加入錯題本)</div><div style="font-size:30px;color:#1565C0;font-weight:bold;">{sq['Chinese']}</div></div>""", unsafe_allow_html=True)
            
            sab = get_audio_bytes(sq['Word'], 'en', st.session_state.accent_tld, st.session_state.is_slow)
            if sab: st.audio(sab, format='audio/mp3')

            if not st.session_state.spell_checked:
                spell_val = st.text_input("輸入單字", key="spell_in")
                if st.button("✅ 送出答案", type="primary"):
                    st.session_state.spell_input = spell_val
                    check_spelling()
                    st.rerun()
            else:
                if st.session_state.spell_correct: st.success(f"🎉 拼對了！ {sq['Word']}"); st.balloons()
                else: st.error(f"❌ 拼錯了... 正確是：{sq['Word']}")
                if st.button("➡️ 下一題拼寫", type="primary"): next_spelling(filtered_df); st.rerun()

if __name__ == "__main__":
    main()
