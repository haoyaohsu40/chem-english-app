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
.stButton>button { border-radius: 8px; cursor: pointer !important; }
div[data-baseweb="select"] { cursor: pointer !important; }
.word-text { font-size: 24px; font-weight: bold; color: #2E7D32; font-family: 'Arial Black', sans-serif; }
.ipa-text { font-size: 16px; color: #757575; font-family: 'Arial', sans-serif; }
.meaning-text { font-size: 20px; color: #1565C0; font-weight: bold;}
.quiz-card {
    background-color: #fff3e0;
    padding: 30px;
    border-radius: 15px;
    text-align: center;
    border: 2px dashed #ff9800;
    margin-bottom: 20px;
}
.quiz-word { font-size: 40px; color: #d84315; font-weight: bold; margin-bottom: 10px; }
div[data-testid="stMetricValue"] { font-size: 24px; color: #d32f2f; }
</style>
""", unsafe_allow_html=True)

# --- 核心：連接 Google Sheets ---
def get_google_sheet_data():
    """連接 Google Sheets 並回傳 DataFrame"""
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
    """將整個 DataFrame 覆寫回 Google Sheets"""
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
    """將 DataFrame 轉為 Excel Bytes"""
    output = BytesIO()
    # 使用 openpyxl 引擎寫入 Excel
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

    # --- 計算目前筆記本字數 (預先計算) ---
    # 這裡我們需要知道使用者選了哪個筆記本，才能在頂部顯示。
    # 利用 session_state.get 取值，如果還沒選預設是"全部"
    current_filter_nb = st.session_state.get('filter_nb_key', '全部')
    
    if current_filter_nb == "全部":
        current_book_count = len(df)
    else:
        current_book_count = len(df[df['Notebook'] == current_filter_nb])

    # --- 頂部顯示區 ---
    # 調整佈局：標題佔 2, 總字數佔 1, 該本字數佔 1
    col_title, col_total, col_current = st.columns([2, 1, 1])
    
    with col_title: 
        st.title("🚀 AI 智能單字速記通 (家庭版)")
    
    with col_total: 
        st.metric("☁️ 雲端總字數", f"{len(df)}")
    
    with col_current:
        # 顯示當前選中筆記本的字數
        label_text = "📖 目前本子字數" if current_filter_nb != "全部" else "📖 全部單字數"
        st.metric(label_text, f"{current_book_count}")

    # --- 側邊欄 ---
    with st.sidebar:
        st.header("📝 新增單字")
        notebooks = df['Notebook'].unique().tolist()
        if '預設筆記本' not in notebooks: notebooks.append('預設筆記本')
        
        nb_mode_opt = st.radio("筆記本來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed")
        if nb_mode_opt == "選擇現有": notebook = st.selectbox("選擇筆記本", notebooks)
        else: notebook = st.text_input("輸入新筆記本名稱", "我的單字本")

        st.markdown("---")
        input_mode = st.radio("輸入模式", ["🔤 單字輸入", "🚀 批次貼上"], horizontal=True)

        # 設定預設值
        accents = {'美式 (US)': 'com', '英式 (UK)': 'co.uk', '澳式 (AU)': 'com.au', '印度 (IN)': 'co.in'}
        speeds = {'正常 (Normal)': False, '慢速 (Slow)': True}
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
                    with st.spinner('同步到雲端中...'):
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
                        with st.spinner("正在寫入雲端..."):
                            df = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
                            st.session_state.df = df
                            save_to_google_sheet(df)
                            st.success(f"加入 {len(new_entries)} 筆")
                            time.sleep(1)
                            st.rerun()

    st.sidebar.markdown("---")
    with st.sidebar.expander("🔊 發音設定", expanded=False):
        selected_accent = st.selectbox("口音", list(accents.keys()))
        st.session_state.accent_tld = accents[selected_accent]
        selected_speed = st.radio("語速", list(speeds.keys()))
        st.session_state.is_slow = speeds[selected_speed]

    with st.sidebar.expander("🎧 播放順序", expanded=True):
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1: 
            if st.button("➕ 英文"): st.session_state.play_order.append("英文")
        with c2: 
            if st.button("➕ 中文"): st.session_state.play_order.append("中文")
        with c3: 
            if st.button("❌ 清空"): st.session_state.play_order = []
        order_str = " ➝ ".join(st.session_state.play_order)
        st.info(f"順序：\n**{order_str if order_str else '(未選)'}**")

    # --- 進階管理 ---
    with st.sidebar.expander("🛠️ 進階管理 (刪除筆記本)"):
        if st.button("🔄 強制雲端更新"):
            st.session_state.df = get_google_sheet_data()
            st.success("已更新！")
            st.rerun()
        
        manage_list = df['Notebook'].unique().tolist()
        if manage_list:
            target_nb = st.selectbox("選擇要刪除的筆記本", manage_list, key="m_nb")
            if st.button("🗑️ 刪除此筆記本"):
                if st.session_state.get('confirm_del') != True:
                    st.warning("請再按一次確認")
                    st.session_state.confirm_del = True
                else:
                    df = df[df['Notebook'] != target_nb]
                    st.session_state.df = df
                    save_to_google_sheet(df)
                    st.session_state.confirm_del = False
                    st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.caption("版本: v23.0 (Excel 下載修復版)")

    # --- 主畫面過濾區 & 下載區 ---
    col_filter, col_mp3 = st.columns([2, 1])
    
    with col_filter:
        # 這裡設定 key='filter_nb_key' 讓上面的程式碼可以抓到這個值
        filter_nb = st.selectbox("📖 我要複習哪一本？", ["全部"] + df['Notebook'].unique().tolist(), key='filter_nb_key')
    
    filtered_df = df if filter_nb == "全部" else df[df['Notebook'] == filter_nb]
    
    st.info(f"📊 篩選後共有 **{len(filtered_df)}** 個單字")

    with col_mp3:
        st.write("🎧 **工具區**")
        # 下載 Excel 按鈕 (移到這裡)
        if not filtered_df.empty:
             # Excel 下載
            excel_data = to_excel(filtered_df) # 這裡改為只下載篩選後的，或全部 df，看您需求。通常備份是備份全部。
            # 如果要備份全部，請將 filtered_df 改為 df。這裡假設您想下載看到的資料。
            # 為了備份安全，我們還是預設下載「全部資料」比較保險，或者您可以選擇下載 filtered_df
            # 這裡我們下載 "全部 (df)" 以便於備份，若只想下載該本，改為 filtered_df 即可
            
            c_down_1, c_down_2 = st.columns(2)
            with c_down_1:
                st.download_button(
                    label="📥 下載 Excel",
                    data=to_excel(df), # 下載完整資料庫
                    file_name=f'vocab_backup_{pd.Timestamp.now().strftime("%Y%m%d")}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    use_container_width=True
                )

            with c_down_2:
                if st.session_state.play_order:
                     # MP3 下載邏輯
                     # 注意：MP3 產生比較慢，使用 filtered_df (目前本子)
                    pass # 按鈕在下面渲染，這裡只是佔位
                else:
                    pass

            if not filtered_df.empty and st.session_state.play_order:
                if st.button("下載自訂順序 MP3", use_container_width=True):
                    with st.spinner("生成中..."):
                        audio_bytes = generate_custom_audio(filtered_df, st.session_state.play_order, tld=st.session_state.accent_tld, slow=st.session_state.is_slow)
                        st.download_button(label="📥 點擊下載 MP3", data=audio_bytes, file_name=f"vocab_custom.mp3", mime="audio/mp3", use_container_width=True)
        else:
            st.button("無資料", disabled=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📋 單字列表", "🃏 學習卡片", "🎬 學習卡撥放", "🏆 測驗挑戰"])

    with tab1:
        h1, h2, h3, h4 = st.columns([3, 2, 2, 1])
        h1.markdown('<h4>🇬🇧 English / 音標</h4>', unsafe_allow_html=True)
        h2.markdown("#### 🇹🇼 中文翻譯")
        h3.markdown("#### 發音 / 翻譯")
        h4.markdown("#### 操作")
        st.markdown("---")

        if not filtered_df.empty:
            for index, row in filtered_df.iloc[::-1].iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                with c1:
                    st.markdown(f"<div class='word-text'>{row['Word']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='ipa-text'>{row['IPA']}</div>", unsafe_allow_html=True)
                with c2: st.markdown(f"<div class='meaning-text'>{row['Chinese']}</div>", unsafe_allow_html=True)
                with c3:
                    if st.button("🔊 播放", key=f"l_p_{index}"):
                        st.markdown(text_to_speech_visible(row['Word'], 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow), unsafe_allow_html=True)
                    encoded_word = urllib.parse.quote(str(row['Word']))
                    google_url = f"https://translate.google.com/?sl=en&tl=zh-TW&text={encoded_word}&op=translate"
                    st.markdown(f"[G 翻譯]({google_url})")
                with c4:
                    if st.button("🗑️ 刪除", key=f"l_d_{index}"):
                        df = df[~((df['Word'] == row['Word']) & (df['Notebook'] == row['Notebook']))]
                        st.session_state.df = df
                        save_to_google_sheet(df)
                        st.rerun()
                st.markdown("---")
        else: st.info("無資料")

    with tab2:
        if not filtered_df.empty:
            if 'card_index' not in st.session_state: st.session_state.card_index = 0
            curr_idx = st.session_state.card_index % len(filtered_df)
            row = filtered_df.iloc[curr_idx]
            
            st.markdown("###")
            _, c_card, _ = st.columns([1, 2, 1])
            with c_card:
                st.markdown(f"""
                    <div style="border: 2px solid #4CAF50; border-radius: 15px; padding: 20px; text-align: center; background-color: #f9f9f9;">
                        <div style="font-size: 50px; color: #2E7D32; font-weight: bold;">{row['Word']}</div>
                        <div style="color: #666; font-size: 20px;">{row['IPA']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("###")
                encoded_img_word = urllib.parse.quote(str(row['Word']))
                st.link_button("🖼️ Google 圖片搜尋", f"https://www.google.com/search?tbm=isch&q={encoded_img_word}+image", use_container_width=True)

                c_show, c_aud = st.columns(2)
                with c_show:
                    if st.button("👀 看答案", use_container_width=True):
                        st.info(f"{row['Chinese']}")
                with c_aud:
                    if st.button("🔊 聽發音", use_container_width=True):
                        st.markdown(text_to_speech_visible(row['Word'], 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow), unsafe_allow_html=True)
            
            c_prev, c_next = st.columns(2)
            with c_prev: 
                if st.button("⬅️ 上一張", use_container_width=True): st.session_state.card_index -= 1; st.rerun()
            with c_next: 
                if st.button("下一張 ➡️", use_container_width=True): st.session_state.card_index += 1; st.rerun()

    with tab3:
        st.markdown("#### 🎬 學習卡撥放")
        col_ctrl, _ = st.columns([1, 2])
        with col_ctrl:
            delay_sec = st.slider("切換速度 (秒)", 2, 10, 3)
            start_btn = st.button("▶️ 開始播放", type="primary")
        
        slide_placeholder = st.empty()
        
        if start_btn:
            if filtered_df.empty: st.error("無單字！")
            elif not st.session_state.play_order: st.error("請先設定播放順序！")
            else:
                st.toast("播放中...")
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
        st.markdown("#### 🏆 測驗挑戰")
        if 'quiz_total' in st.session_state and st.session_state.quiz_total > 0:
            acc = (st.session_state.quiz_score / st.session_state.quiz_total) * 100
        else: acc = 0
        c_score, c_reset = st.columns([3, 1])
        with c_score: st.markdown(f"📊 答對 **{st.session_state.quiz_score}** / 總題數 **{st.session_state.quiz_total}** (正確率: {acc:.1f}%)")
        with c_reset:
            if st.button("🔄 重置分數"):
                st.session_state.quiz_score = 0; st.session_state.quiz_total = 0; st.rerun()
        st.divider()

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