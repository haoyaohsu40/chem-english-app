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
import urllib.parse
import random

# --- 設定頁面 ---
st.set_page_config(page_title="AI 智能單字速記通 (家庭版)", layout="wide", page_icon="🚀")

# --- CSS 美化 ---
st.markdown("""
<style>
/* 全局字體優化 */
.main { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }

/* 按鈕樣式 */
.stButton>button { 
    border-radius: 12px; 
    height: 3em; 
    font-weight: bold; 
    border: none;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    transition: all 0.2s;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

/* 頂部數據卡片樣式 */
.metric-card {
    background-color: #f0fdf4; /* 淺綠色背景 */
    border: 2px solid #a5d6a7;
    border-radius: 15px;
    padding: 10px;
    text-align: center;
    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}
.metric-label { font-size: 14px; color: #555; margin-bottom: 5px; }
.metric-value { font-size: 32px; font-weight: bold; color: #2E7D32; }

/* 單字卡樣式 */
.word-text { font-size: 26px; font-weight: bold; color: #2E7D32; font-family: 'Arial Black', sans-serif; }
.ipa-text { font-size: 16px; color: #757575; }
.meaning-text { font-size: 22px; color: #1565C0; font-weight: bold;}

/* 測驗區塊 */
.quiz-card {
    background-color: #fff8e1;
    padding: 40px;
    border-radius: 20px;
    text-align: center;
    border: 3px dashed #ffb74d;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# --- 核心：連接 Google Sheets ---
def get_google_sheet_data():
    try:
        creds_json = json.loads(st.secrets["service_account"]["info"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        sheet = client.open("vocab_db").sheet1
        data = sheet.get_all_records()
        if not data:
            df = pd.DataFrame(columns=['Notebook', 'Word', 'IPA', 'Chinese', 'Date'])
            sheet.append_row(['Notebook', 'Word', 'IPA', 'Chinese', 'Date'])
            return df
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"連線 Google Sheets 失敗：{e}")
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

# --- 輔助函數 ---
def text_to_speech_visible(text, lang='en', tld='com', slow=False):
    try:
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', str(text))
        if not clean_text: return ""
        tts = gTTS(text=clean_text, lang=lang, tld=tld, slow=slow)
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        return f"""<audio controls autoplay style="width: 100%; margin-top: 10px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>"""
    except: return ""

def text_to_speech_autoplay_hidden(text, lang='en', tld='com', slow=False):
    try:
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', str(text))
        if not clean_text: return ""
        tts = gTTS(text=clean_text, lang=lang, tld=tld, slow=slow)
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        unique_id = f"audio_{uuid.uuid4()}_{time.time_ns()}"
        return f"""<audio autoplay style="width:0;height:0;opacity:0;" id="{unique_id}"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>"""
    except: return ""

def generate_custom_audio(df, sequence, tld='com', slow=False):
    full_text = ""
    for i, (index, row) in enumerate(df.iloc[::-1].iterrows(), start=1):
        word = str(row['Word']); chinese = str(row['Chinese'])
        full_text += f"第{i}個... "
        if not sequence: full_text += f"{word}... "
        else:
            for item in sequence:
                if item == "英文": full_text += f"{word}... "
                elif item == "中文": full_text += f"{chinese}... "
        full_text += "... ... "
    tts = gTTS(text=full_text, lang='zh-TW', slow=slow)
    fp = BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()

def is_contains_chinese(string):
    for char in str(string):
        if '\u4e00' <= char <= '\u9fff': return True
    return False

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- 測驗函數 ---
def initialize_quiz_state():
    if 'quiz_score' not in st.session_state: st.session_state.quiz_score = 0
    if 'quiz_total' not in st.session_state: st.session_state.quiz_total = 0
    if 'quiz_current' not in st.session_state: st.session_state.quiz_current = None
    if 'quiz_options' not in st.session_state: st.session_state.quiz_options = []
    if 'quiz_answered' not in st.session_state: st.session_state.quiz_answered = False
    if 'quiz_is_correct' not in st.session_state: st.session_state.quiz_is_correct = False

def next_question(df):
    if df.empty: return
    target_row = df.sample(1).iloc[0]
    st.session_state.quiz_current = target_row
    correct_opt = str(target_row['Chinese'])
    other_rows = df[df['Chinese'] != correct_opt]
    distractors = []
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
    if user_choice == str(st.session_state.quiz_current['Chinese']):
        st.session_state.quiz_score += 1
        st.session_state.quiz_is_correct = True
    else: st.session_state.quiz_is_correct = False

# --- 主程式 ---
def main():
    if 'df' not in st.session_state:
        with st.spinner('正在連線雲端資料庫...'):
            st.session_state.df = get_google_sheet_data()
    
    df = st.session_state.df
    initialize_quiz_state()
    if 'play_order' not in st.session_state: st.session_state.play_order = ["英文", "中文", "英文"] 

    # --- 1. 頂部佈局：標題 (左) + 數據卡片 (右) ---
    col_header, col_metrics_area = st.columns([2, 2])
    
    with col_header:
        st.title("🚀 AI 智能單字速記通")
        st.caption("家庭雲端版 v24.2")

    # --- 2. 篩選邏輯 ---
    current_notebook = st.session_state.get('filter_nb_key', '全部')
    
    total_count = len(df)
    filtered_df = df if current_notebook == "全部" else df[df['Notebook'] == current_notebook]
    current_count = len(filtered_df)

    with col_metrics_area:
        m1, m2 = st.columns(2)
        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">☁️ 雲端總字數</div>
                <div class="metric-value">{total_count}</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">📖 目前本子字數</div>
                <div class="metric-value">{current_count}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # --- 3. 側邊欄 (修復：加回設定功能) ---
    with st.sidebar:
        st.header("📝 新增單字")
        notebooks = df['Notebook'].unique().tolist()
        if '預設筆記本' not in notebooks: notebooks.append('預設筆記本')
        
        nb_mode_opt = st.radio("筆記本來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed")
        if nb_mode_opt == "選擇現有": notebook = st.selectbox("選擇筆記本", notebooks)
        else: notebook = st.text_input("輸入新筆記本名稱", "我的單字本")

        st.markdown("---")
        input_mode = st.radio("輸入模式", ["🔤 單字輸入", "🚀 批次貼上"], horizontal=True)

        # 設定預設值 (確保狀態存在)
        if 'accent_tld' not in st.session_state: st.session_state.accent_tld = 'com'
        if 'is_slow' not in st.session_state: st.session_state.is_slow = False

        if input_mode == "🔤 單字輸入":
            word_input = st.text_input("輸入英文單字", placeholder="例如: Valve")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("👀 翻譯", use_container_width=True):
                    if word_input and not is_contains_chinese(word_input):
                        try:
                            with st.spinner("..."):
                                trans = GoogleTranslator(source='auto', target='zh-TW').translate(word_input)
                                st.info(f"{trans}")
                        except: st.error("失敗")
            with c2:
                if st.button("🔊 試聽", use_container_width=True):
                    if word_input: st.markdown(text_to_speech_visible(word_input, 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow), unsafe_allow_html=True)

            if st.button("➕ 加入單字庫", type="primary", use_container_width=True):
                if word_input and notebook and not is_contains_chinese(word_input):
                    with st.spinner('同步中...'):
                        try:
                            ipa = f"[{eng_to_ipa.convert(word_input)}]"
                            trans = GoogleTranslator(source='auto', target='zh-TW').translate(word_input)
                            new_entry = {'Notebook': notebook, 'Word': word_input, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                            st.session_state.df = df
                            save_to_google_sheet(df)
                            st.success(f"已儲存：{word_input}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"錯誤: {e}")
        else:
            bulk_input = st.text_area("📋 批次貼上", height=100)
            if st.button("🚀 批次加入", type="primary"):
                if bulk_input and notebook:
                    words = re.split(r'[,\n，]', bulk_input)
                    new_entries = []
                    bar = st.progress(0)
                    for i, w in enumerate(words):
                        w = w.strip()
                        if w and not is_contains_chinese(w):
                            try:
                                ipa = f"[{eng_to_ipa.convert(w)}]"
                                trans = GoogleTranslator(source='auto', target='zh-TW').translate(w)
                                new_entries.append({'Notebook': notebook, 'Word': w, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')})
                            except: pass
                        bar.progress((i+1)/len(words))
                    
                    if new_entries:
                        with st.spinner("寫入中..."):
                            df = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
                            st.session_state.df = df
                            save_to_google_sheet(df)
                            st.success(f"加入 {len(new_entries)} 筆")
                            time.sleep(1)
                            st.rerun()

        # --- 補回：發音與順序設定 ---
        st.markdown("---")
        with st.expander("🔊 發音與語速設定", expanded=False):
            accents = {'美式 (US)': 'com', '英式 (UK)': 'co.uk', '澳式 (AU)': 'com.au', '印度 (IN)': 'co.in'}
            # 找出目前設定的 index
            curr_acc_val = st.session_state.accent_tld
            # 反查 key
            default_acc_key = [k for k, v in accents.items() if v == curr_acc_val]
            default_acc_key = default_acc_key[0] if default_acc_key else '美式 (US)'
            
            selected_accent = st.selectbox("口音", list(accents.keys()), index=list(accents.keys()).index(default_acc_key))
            st.session_state.accent_tld = accents[selected_accent]
            
            speeds = {'正常 (Normal)': False, '慢速 (Slow)': True}
            # 反查 speed index
            curr_speed_val = st.session_state.is_slow
            default_spd_key = [k for k, v in speeds.items() if v == curr_speed_val]
            default_spd_key = default_spd_key[0] if default_spd_key else '正常 (Normal)'

            selected_speed = st.radio("語速", list(speeds.keys()), index=list(speeds.keys()).index(default_spd_key))
            st.session_state.is_slow = speeds[selected_speed]

        with st.expander("🎧 播放順序設定", expanded=True):
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1: 
                if st.button("➕ 英文"): st.session_state.play_order.append("英文")
            with c2: 
                if st.button("➕ 中文"): st.session_state.play_order.append("中文")
            with c3: 
                if st.button("❌ 清空"): st.session_state.play_order = []
            
            order_str = " ➝ ".join(st.session_state.play_order)
            st.caption(f"目前順序：\n{order_str if order_str else '(未設定)'}")

        st.markdown("---")
        with st.expander("🛠️ 進階管理"):
            if st.button("🔄 強制雲端更新"):
                st.session_state.df = get_google_sheet_data()
                st.success("已更新！"); st.rerun()
            manage_list = df['Notebook'].unique().tolist()
            if manage_list:
                target_nb = st.selectbox("刪除筆記本", manage_list)
                if st.button("🗑️ 刪除此本"):
                    if st.session_state.get('confirm_del') != True:
                        st.warning("確認刪除？")
                        st.session_state.confirm_del = True
                    else:
                        df = df[df['Notebook'] != target_nb]
                        st.session_state.df = df
                        save_to_google_sheet(df)
                        st.session_state.confirm_del = False
                        st.rerun()

    # --- 4. 主畫面工具區 ---
    st.subheader("📚 複習與工具區")
    
    nb_options = ["全部"] + df['Notebook'].unique().tolist()
    sel_nb = st.selectbox("請選擇要複習的筆記本：", nb_options, key='filter_nb_key')

    col_tool_1, col_tool_2 = st.columns(2)
    
    with col_tool_1:
        if not filtered_df.empty:
            file_name_xls = f"Vocab_{current_notebook if current_notebook != '全部' else 'All'}.xlsx"
            st.download_button(
                label="📥 下載 Excel (目前清單)",
                data=to_excel(filtered_df),
                file_name=file_name_xls,
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True
            )
        else:
            st.button("無資料可下載", disabled=True, use_container_width=True)

    with col_tool_2:
        if not filtered_df.empty and st.session_state.play_order:
            if st.button("🎧 製作並下載 MP3", use_container_width=True):
                with st.spinner("正在合成語音 (請稍候)..."):
                    tld = st.session_state.get('accent_tld', 'com')
                    slow = st.session_state.get('is_slow', False)
                    audio_bytes = generate_custom_audio(filtered_df, st.session_state.play_order, tld=tld, slow=slow)
                    st.download_button(
                        label="⬇️ 點擊下載 MP3 檔案", 
                        data=audio_bytes, 
                        file_name=f"Audio_{current_notebook}.mp3", 
                        mime="audio/mp3", 
                        use_container_width=True
                    )
        else:
            if not st.session_state.play_order:
                st.warning("⚠️ 請先在左側設定「播放順序」")
            else:
                st.button("無資料可下載", disabled=True, use_container_width=True)

    # --- 5. 功能頁籤區 ---
    st.markdown("###")
    tab1, tab2, tab3, tab4 = st.tabs(["📋 單字列表", "🃏 翻卡學習", "🎬 自動播放", "🏆 測驗挑戰"])

    with tab1:
        st.markdown(f"**目前顯示：{current_notebook} ({len(filtered_df)} 字)**")
        h1, h2, h3, h4 = st.columns([3, 2, 2, 1])
        h1.markdown("**🇬🇧 單字 / 音標**")
        h2.markdown("**🇹🇼 中文**")
        h3.markdown("**功能**")
        h4.markdown("**刪除**")
        st.divider()

        if not filtered_df.empty:
            for index, row in filtered_df.iloc[::-1].iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                with c1:
                    st.markdown(f"<div class='word-text'>{row['Word']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='ipa-text'>{row['IPA']}</div>", unsafe_allow_html=True)
                with c2: st.markdown(f"<div class='meaning-text'>{row['Chinese']}</div>", unsafe_allow_html=True)
                with c3:
                    if st.button("🔊", key=f"l_p_{index}"):
                        st.markdown(text_to_speech_visible(row['Word'], 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow), unsafe_allow_html=True)
                with c4:
                    if st.button("🗑️", key=f"l_d_{index}"):
                        df = df[~((df['Word'] == row['Word']) & (df['Notebook'] == row['Notebook']))]
                        st.session_state.df = df
                        save_to_google_sheet(df)
                        st.rerun()
                st.markdown("---")
        else: st.info("這裡還沒有單字喔！")

    with tab2:
        if not filtered_df.empty:
            if 'card_index' not in st.session_state: st.session_state.card_index = 0
            curr_idx = st.session_state.card_index % len(filtered_df)
            row = filtered_df.iloc[curr_idx]
            
            c_prev, c_card, c_next = st.columns([1, 4, 1])
            with c_prev: 
                st.markdown("<br><br><br>", unsafe_allow_html=True)
                if st.button("◀", use_container_width=True): st.session_state.card_index -= 1; st.rerun()
            with c_next: 
                st.markdown("<br><br><br>", unsafe_allow_html=True)
                if st.button("▶", use_container_width=True): st.session_state.card_index += 1; st.rerun()
            
            with c_card:
                st.markdown(f"""
                    <div style="border: 2px solid #81C784; border-radius: 20px; padding: 40px; text-align: center; background-color: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="font-size: 60px; color: #2E7D32; font-weight: bold;">{row['Word']}</div>
                        <div style="color: #666; font-size: 24px; margin-top: 10px;">{row['IPA']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("👀 顯示中文", use_container_width=True):
                        st.info(f"💡 {row['Chinese']}")
                with b2:
                    if st.button("🔊 播放發音", use_container_width=True):
                        st.markdown(text_to_speech_visible(row['Word'], 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow), unsafe_allow_html=True)

    with tab3:
        st.info("自動輪播您目前的單字列表")
        col_ctrl, _ = st.columns([1, 2])
        with col_ctrl:
            delay_sec = st.slider("每張卡片停留秒數", 2, 10, 3)
            start_btn = st.button("▶️ 開始播放", type="primary", use_container_width=True)
        
        slide_placeholder = st.empty()
        
        if start_btn:
            if filtered_df.empty: st.error("無單字！")
            elif not st.session_state.play_order: st.error("請先在左側設定播放順序！")
            else:
                play_list = filtered_df.iloc[::-1]
                for index, row in play_list.iterrows():
                    word = str(row['Word']); chinese = str(row['Chinese']); ipa = str(row['IPA'])
                    for step in st.session_state.play_order:
                        slide_placeholder.empty(); time.sleep(0.1)
                        if step == "英文":
                            slide_placeholder.markdown(f"""<div style="border:2px solid #4CAF50;border-radius:20px;padding:40px;text-align:center;background-color:#f0fdf4;min-height:350px;"><div style="font-size:60px;color:#2E7D32;font-weight:bold;">{word}</div><div style="font-size:28px;color:#666;">{ipa}</div><div style="height:50px;color:#aaa;">(Listen...)</div>{text_to_speech_autoplay_hidden(word, 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow)}</div>""", unsafe_allow_html=True)
                        elif step == "中文":
                            slide_placeholder.markdown(f"""<div style="border:2px solid #4CAF50;border-radius:20px;padding:40px;text-align:center;background-color:#f0fdf4;min-height:350px;"><div style="font-size:60px;color:#2E7D32;font-weight:bold;">{word}</div><div style="font-size:28px;color:#666;">{ipa}</div><div style="font-size:50px;color:#1565C0;font-weight:bold;margin-top:20px;">{chinese}</div>{text_to_speech_autoplay_hidden(chinese, 'zh-TW', slow=st.session_state.is_slow)}</div>""", unsafe_allow_html=True)
                        time.sleep(delay_sec)
                slide_placeholder.success("播放結束！")

    with tab4:
        if 'quiz_total' in st.session_state and st.session_state.quiz_total > 0:
            acc = (st.session_state.quiz_score / st.session_state.quiz_total) * 100
        else: acc = 0
        c_score, c_reset = st.columns([3, 1])
        with c_score: st.markdown(f"📊 答對 **{st.session_state.quiz_score}** / 總題數 **{st.session_state.quiz_total}** (正確率: {acc:.1f}%)")
        with c_reset:
            if st.button("🔄 重置"):
                st.session_state.quiz_score = 0; st.session_state.quiz_total = 0; st.rerun()
        
        if filtered_df.empty: st.info("請先新增單字！")
        else:
            if st.session_state.quiz_current is None: next_question(filtered_df)
            current_q = st.session_state.quiz_current
            
            st.markdown(f"""<div class="quiz-card"><div style="font-size:20px;color:#666;">請聽發音並選出正確中文：</div><div class="quiz-word">{current_q['Word']}</div><div style="color:#888;">{current_q['IPA']}</div></div>""", unsafe_allow_html=True)
            st.markdown(text_to_speech_visible(current_q['Word'], 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow), unsafe_allow_html=True)

            if not st.session_state.quiz_answered:
                cols = st.columns(2)
                for idx, option in enumerate(st.session_state.quiz_options):
                    if cols[idx % 2].button(option, key=f"opt_{idx}", use_container_width=True):
                        check_answer(option); st.rerun()
            else:
                if st.session_state.quiz_is_correct: st.success("🎉 答對了！"); st.balloons()
                else: st.error(f"❌ 答錯了... 正確答案是：{current_q['Chinese']}")
                if st.button("➡️ 下一題", type="primary", use_container_width=True):
                    next_question(filtered_df); st.rerun()

if __name__ == "__main__":
    main()
