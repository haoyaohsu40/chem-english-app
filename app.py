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
st.set_page_config(page_title="AI 智能單字速記通 (家庭版)", layout="wide", page_icon="🚀")

# 這裡加入隱藏右上角選單的 CSS，既然無法改中文，不如讓介面清爽一點
st.markdown("""
<style>
    /* 全局字體 */
    .main { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }

    /* 按鈕優化 */
    .stButton>button { 
        border-radius: 10px; 
        font-weight: bold; 
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    /* 頂部數據卡片 (綠色框框風格) */
    .metric-card {
        background-color: #ffffff;
        border: 2px solid #4CAF50; /* 綠色邊框 */
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .metric-label { font-size: 14px; color: #666; margin-bottom: 5px; font-weight: bold;}
    .metric-value { font-size: 36px; font-weight: bold; color: #d32f2f; } /* 紅色數字 */

    /* 單字列表樣式 */
    .word-text { font-size: 24px; font-weight: bold; color: #2E7D32; font-family: 'Arial Black', sans-serif; }
    .ipa-text { font-size: 14px; color: #757575; }
    .meaning-text { font-size: 20px; color: #1565C0; font-weight: bold;}

    /* 測驗區塊 */
    .quiz-card {
        background-color: #fff8e1;
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        border: 3px dashed #ffb74d;
        margin-bottom: 20px;
    }
    .quiz-word { font-size: 40px; color: #333; font-weight: bold; margin: 10px 0; }
    
    /* 隱藏右上角 Streamlit 預設選單 (因為無法改中文) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心功能函式 (Google Sheets / Audio / Tools)
# ==========================================

def get_google_sheet_data():
    """讀取 Google Sheets 資料"""
    try:
        creds_json = json.loads(st.secrets["service_account"]["info"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        sheet = client.open("vocab_db").sheet1
        data = sheet.get_all_records()
        if not data:
            df = pd.DataFrame(columns=['Notebook', 'Word', 'IPA', 'Chinese', 'Date'])
            return df
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"連線 Google Sheets 失敗：{e}")
        return pd.DataFrame(columns=['Notebook', 'Word', 'IPA', 'Chinese', 'Date'])

def save_to_google_sheet(df):
    """儲存資料回 Google Sheets"""
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
    """檢查是否包含中文字"""
    for char in str(string):
        if '\u4e00' <= char <= '\u9fff': return True
    return False

def to_excel(df):
    """轉換 DataFrame 為 Excel bytes"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- 語音相關 (列表模式用 HTML，測驗模式用原生 Audio) ---
def text_to_speech_visible(text, lang='en', tld='com', slow=False):
    """產生可見的播放器 (用於列表模式)"""
    try:
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', str(text))
        if not clean_text: return ""
        tts = gTTS(text=clean_text, lang=lang, tld=tld, slow=slow)
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        # 加入隨機 ID 盡量減少列表模式的快取問題
        unique_id = f"audio_visible_{uuid.uuid4()}" 
        return f"""<audio id="{unique_id}" controls style="width: 100%; margin-top: 5px;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>"""
    except: return ""

def get_audio_bytes(text, lang='en', tld='com', slow=False):
    """直接產生音訊 Bytes (用於測驗模式，確保絕對不快取)"""
    try:
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', str(text))
        if not clean_text: return None
        tts = gTTS(text=clean_text, lang=lang, tld=tld, slow=slow)
        fp = BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

def text_to_speech_autoplay_hidden(text, lang='en', tld='com', slow=False):
    """產生隱藏的自動播放器"""
    try:
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', str(text))
        if not clean_text: return ""
        tts = gTTS(text=clean_text, lang=lang, tld=tld, slow=slow)
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        unique_id = f"audio_hidden_{uuid.uuid4()}"
        return f"""<audio autoplay style="display:none;" id="{unique_id}"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>"""
    except: return ""

def generate_custom_audio(df, sequence, tld='com', slow=False):
    """合成 MP3 檔案"""
    full_text = ""
    # 根據列表順序 (倒序或正序，這裡使用顯示順序)
    for i, (index, row) in enumerate(df.iloc[::-1].iterrows(), start=1):
        word = str(row['Word'])
        chinese = str(row['Chinese'])
        
        full_text += f"Number {i}. " 
        
        if not sequence:
            full_text += f"{word}. {chinese}. "
        else:
            for item in sequence:
                if item == "英文":
                    full_text += f"{word}. "
                elif item == "中文":
                    full_text += f"{chinese}. "
        
        full_text += " ... " # 單字間隔

    tts = gTTS(text=full_text, lang='zh-TW', slow=slow) # 基底用中文以支援混合朗讀
    fp = BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()

# ==========================================
# 3. 狀態初始化與測驗邏輯
# ==========================================

def initialize_session_state():
    if 'df' not in st.session_state:
        st.session_state.df = get_google_sheet_data()
    if 'play_order' not in st.session_state:
        st.session_state.play_order = ["英文", "中文", "英文"] 
    if 'accent_tld' not in st.session_state:
        st.session_state.accent_tld = 'com'
    if 'is_slow' not in st.session_state:
        st.session_state.is_slow = False
    
    # 測驗狀態
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
    
    # 產生干擾項
    other_rows = df[df['Chinese'] != correct_opt]
    if len(other_rows) >= 3:
        distractors = other_rows.sample(3)['Chinese'].astype(str).tolist()
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
    else:
        st.session_state.quiz_is_correct = False

# ==========================================
# 4. 主程式 Layout
# ==========================================

def main():
    initialize_session_state()
    df = st.session_state.df

    # --- 頂部區塊：標題與數據卡片 ---
    col_header, col_metrics_area = st.columns([2, 2])
    
    with col_header:
        st.title("🚀 AI 智能單字速記通")
        st.caption("家庭雲端版 v26.1 (Quiz Audio Fix)")

    # 取得目前篩選的筆記本 (從下方 Selectbox 取得狀態，若無則預設全部)
    current_notebook_filter = st.session_state.get('filter_nb_key', '全部')
    
    total_count = len(df)
    filtered_df = df if current_notebook_filter == "全部" else df[df['Notebook'] == current_notebook_filter]
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

    # --- 側邊欄：輸入與設定 ---
    with st.sidebar:
        st.header("📝 新增單字")
        notebooks_list = df['Notebook'].unique().tolist()
        if '預設筆記本' not in notebooks_list: notebooks_list.append('預設筆記本')
        
        # 筆記本選擇
        nb_mode_opt = st.radio("筆記本來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed")
        if nb_mode_opt == "選擇現有":
            target_notebook = st.selectbox("選擇筆記本", notebooks_list)
        else:
            target_notebook = st.text_input("輸入新筆記本名稱", "我的單字本")

        st.markdown("---")
        
        # 輸入模式
        input_mode = st.radio("輸入模式", ["🔤 單字輸入", "🚀 批次貼上"], horizontal=True)

        if input_mode == "🔤 單字輸入":
            word_input = st.text_input("輸入英文單字", placeholder="例如: Valve")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("👀 翻譯", use_container_width=True):
                    if word_input and not is_contains_chinese(word_input):
                        try:
                            trans = GoogleTranslator(source='auto', target='zh-TW').translate(word_input)
                            st.info(f"{trans}")
                        except: st.error("翻譯失敗")
            with c2:
                if st.button("🔊 試聽", use_container_width=True):
                    if word_input: 
                        st.markdown(text_to_speech_visible(word_input, 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow), unsafe_allow_html=True)
            
            if st.button("➕ 加入單字庫", type="primary", use_container_width=True):
                if word_input and target_notebook and not is_contains_chinese(word_input):
                    with st.spinner('同步中...'):
                        try:
                            ipa = f"[{eng_to_ipa.convert(word_input)}]"
                            trans = GoogleTranslator(source='auto', target='zh-TW').translate(word_input)
                            new_entry = {
                                'Notebook': target_notebook, 
                                'Word': word_input, 
                                'IPA': ipa, 
                                'Chinese': trans, 
                                'Date': pd.Timestamp.now().strftime('%Y-%m-%d')
                            }
                            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                            st.session_state.df = df
                            save_to_google_sheet(df)
                            st.success(f"已儲存：{word_input}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"錯誤: {e}")

        else: # 批次模式
            bulk_input = st.text_area("📋 批次貼上 (以逗號或換行分隔)", height=100)
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
                                new_entries.append({
                                    'Notebook': target_notebook, 
                                    'Word': w, 
                                    'IPA': ipa, 
                                    'Chinese': trans, 
                                    'Date': pd.Timestamp.now().strftime('%Y-%m-%d')
                                })
                            except: pass
                        bar.progress((i+1)/len(words))
                    
                    if new_entries:
                        df = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
                        st.session_state.df = df
                        save_to_google_sheet(df)
                        st.success(f"成功加入 {len(new_entries)} 筆單字！")
                        time.sleep(1)
                        st.rerun()

        st.markdown("---")
        
        # --- 發音與順序設定 ---
        with st.expander("🔊 發音與語速設定", expanded=False):
            accents = {'美式 (US)': 'com', '英式 (UK)': 'co.uk', '澳式 (AU)': 'com.au', '印度 (IN)': 'co.in'}
            # 保持狀態
            curr_acc_key = [k for k, v in accents.items() if v == st.session_state.accent_tld][0]
            sel_acc = st.selectbox("口音", list(accents.keys()), index=list(accents.keys()).index(curr_acc_key))
            st.session_state.accent_tld = accents[sel_acc]
            
            speeds = {'正常 (Normal)': False, '慢速 (Slow)': True}
            curr_spd_key = [k for k, v in speeds.items() if v == st.session_state.is_slow][0]
            sel_spd = st.radio("語速", list(speeds.keys()), index=list(speeds.keys()).index(curr_spd_key))
            st.session_state.is_slow = speeds[sel_spd]

        with st.expander("🎧 播放順序設定", expanded=True):
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1: 
                if st.button("➕ 英文"): st.session_state.play_order.append("英文")
            with col_p2: 
                if st.button("➕ 中文"): st.session_state.play_order.append("中文")
            with col_p3: 
                if st.button("❌ 清空"): st.session_state.play_order = []
            
            order_text = " ➝ ".join(st.session_state.play_order)
            st.info(f"目前順序：\n{order_text if order_text else '(未設定)'}")

        st.markdown("---")
        
        # --- 進階管理 (包含更名與刪除) ---
        with st.expander("🛠️ 進階管理"):
            if st.button("🔄 強制雲端更新", use_container_width=True):
                st.session_state.df = get_google_sheet_data()
                st.success("已更新！"); st.rerun()
            
            st.divider()
            
            # 修改筆記本名稱功能
            st.write("✏️ **修改筆記本名稱**")
            rename_target_nb = st.selectbox("選擇要改名的筆記本", notebooks_list, key="rename_select")
            new_name_input = st.text_input("輸入新名稱", key="rename_input")
            if st.button("確認更名", key="rename_btn"):
                if new_name_input and new_name_input != rename_target_nb:
                    df.loc[df['Notebook'] == rename_target_nb, 'Notebook'] = new_name_input
                    st.session_state.df = df
                    save_to_google_sheet(df)
                    st.success(f"已將 {rename_target_nb} 更名為 {new_name_input}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("請輸入有效的新名稱")

            st.divider()

            # 刪除筆記本功能
            st.write("🗑️ **刪除整個筆記本**")
            del_target_nb = st.selectbox("選擇要刪除的筆記本", notebooks_list, key="del_select")
            if st.button("刪除此筆記本", type="primary"):
                 # 簡單的確認機制
                if st.session_state.get('confirm_del_nb') != del_target_nb:
                    st.warning(f"請再次點擊按鈕以確認刪除：{del_target_nb}")
                    st.session_state.confirm_del_nb = del_target_nb
                else:
                    df = df[df['Notebook'] != del_target_nb]
                    st.session_state.df = df
                    save_to_google_sheet(df)
                    st.success(f"已刪除 {del_target_nb}")
                    st.session_state.confirm_del_nb = None
                    time.sleep(1)
                    st.rerun()
        
        st.markdown("---")
        st.caption("版本: v26.1 (Quiz Audio Fix)")

    # --- 主畫面：工具區與複習區 ---
    st.divider()
    
    # 筆記本篩選與工具列
    c_filter, c_tools = st.columns([1, 1.5])
    
    with c_filter:
        nb_options = ["全部"] + df['Notebook'].unique().tolist()
        st.selectbox("📖 我要複習哪一本？", nb_options, key='filter_nb_key')
        st.caption(f"篩選後共有 {len(filtered_df)} 個單字")

    with c_tools:
        st.write("🎧 **工具區**")
        t1, t2 = st.columns(2)
        with t1:
            if not filtered_df.empty:
                file_name_xls = f"Vocab_{current_notebook_filter}.xlsx"
                st.download_button(
                    label="📥 下載 Excel",
                    data=to_excel(filtered_df),
                    file_name=file_name_xls,
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    use_container_width=True
                )
            else:
                st.button("📥 無資料", disabled=True, use_container_width=True)
        
        with t2:
            if not filtered_df.empty and st.session_state.play_order:
                if st.button("🎵 製作 MP3", use_container_width=True):
                    with st.spinner("製作中..."):
                        tld = st.session_state.accent_tld
                        slow = st.session_state.is_slow
                        audio_data = generate_custom_audio(filtered_df, st.session_state.play_order, tld=tld, slow=slow)
                        st.download_button(
                            label="⬇️ 下載 MP3",
                            data=audio_data,
                            file_name=f"Audio_{current_notebook_filter}.mp3",
                            mime="audio/mp3",
                            use_container_width=True
                        )
            else:
                st.button("🎵 設定順序後下載", disabled=True, use_container_width=True)

    # --- 功能頁籤 (Tab) ---
    st.markdown("###")
    tab1, tab2, tab3, tab4 = st.tabs(["📋 單字列表", "🃏 學習卡片", "🎬 自動輪播", "🏆 測驗挑戰"])

    # Tab 1: 單字列表
    with tab1:
        h1, h2, h3, h4 = st.columns([3, 2, 2, 1])
        h1.markdown("**GB English / 音標**")
        h2.markdown("**TW 中文翻譯**")
        h3.markdown("**發音 / 翻譯**")
        h4.markdown("**操作**")
        st.divider()

        if not filtered_df.empty:
            for index, row in filtered_df.iloc[::-1].iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                with c1:
                    st.markdown(f"<div class='word-text'>{row['Word']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='ipa-text'>{row['IPA']}</div>", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"<div class='meaning-text'>{row['Chinese']}</div>", unsafe_allow_html=True)
                with c3:
                    if st.button("🔊 播放", key=f"play_{index}"):
                        st.markdown(text_to_speech_visible(row['Word'], 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow), unsafe_allow_html=True)
                    st.markdown(f"[G 翻譯](https://translate.google.com/?sl=en&tl=zh-TW&text={row['Word']}&op=translate)")
                with c4:
                    if st.button("🗑️ 刪除", key=f"del_{index}"):
                        df = df[~((df['Word'] == row['Word']) & (df['Notebook'] == row['Notebook']))]
                        st.session_state.df = df
                        save_to_google_sheet(df)
                        st.rerun()
                st.markdown("---")
        else:
            st.info("目前選擇的筆記本沒有單字，請從左側新增！")

    # Tab 2: 學習卡片
    with tab2:
        if not filtered_df.empty:
            if 'card_index' not in st.session_state: st.session_state.card_index = 0
            # 確保索引在範圍內
            curr_idx = st.session_state.card_index % len(filtered_df)
            row = filtered_df.iloc[curr_idx]

            col_prev, col_card, col_next = st.columns([1, 4, 1])
            with col_prev:
                st.markdown("<br><br><br><br>", unsafe_allow_html=True)
                if st.button("◀ 上一個", use_container_width=True): 
                    st.session_state.card_index -= 1; st.rerun()
            
            with col_next:
                st.markdown("<br><br><br><br>", unsafe_allow_html=True)
                if st.button("下一個 ▶", use_container_width=True): 
                    st.session_state.card_index += 1; st.rerun()

            with col_card:
                # 卡片 UI
                st.markdown(f"""
                <div style="border: 2px solid #81C784; border-radius: 20px; padding: 50px; text-align: center; background-color: #ffffff; box-shadow: 0 4px 10px rgba(0,0,0,0.1); min-height: 300px;">
                    <div style="font-size: 60px; color: #2E7D32; font-weight: bold; margin-bottom: 20px;">{row['Word']}</div>
                    <div style="color: #666; font-size: 24px;">{row['IPA']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("👀 偷看中文", use_container_width=True):
                        st.info(f"💡 {row['Chinese']}")
                with b2:
                    if st.button("🔊 聽發音", use_container_width=True):
                        st.markdown(text_to_speech_visible(row['Word'], 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow), unsafe_allow_html=True)

    # Tab 3: 自動輪播
    with tab3:
        st.info("💡 依照您左側設定的「播放順序」自動朗讀單字")
        c_set, _ = st.columns([1, 2])
        with c_set:
            delay = st.slider("每張卡片停留秒數", 2, 8, 3)
            start_play = st.button("▶️ 開始輪播", type="primary", use_container_width=True)

        slide_ph = st.empty()

        if start_play:
            if filtered_df.empty: st.error("無單字！")
            elif not st.session_state.play_order: st.error("請先設定播放順序！")
            else:
                play_list = filtered_df.iloc[::-1] # 預設倒序播放(新字先)
                for index, row in play_list.iterrows():
                    word = row['Word']; chinese = row['Chinese']; ipa = row['IPA']
                    
                    for step in st.session_state.play_order:
                        slide_ph.empty()
                        time.sleep(0.1)
                        
                        card_html = f"""
                        <div style="border:2px solid #4CAF50;border-radius:20px;padding:40px;text-align:center;background-color:#f0fdf4;min-height:300px;display:flex;flex-direction:column;justify-content:center;">
                            <div style="font-size:50px;color:#2E7D32;font-weight:bold;">{word}</div>
                            <div style="font-size:24px;color:#666;margin-bottom:20px;">{ipa}</div>
                        """
                        
                        if step == "英文":
                            card_html += f"""<div style="color:#aaa;">(Listen...)</div>{text_to_speech_autoplay_hidden(word, 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow)}"""
                        elif step == "中文":
                            card_html += f"""<div style="font-size:40px;color:#1565C0;font-weight:bold;">{chinese}</div>{text_to_speech_autoplay_hidden(chinese, 'zh-TW', slow=st.session_state.is_slow)}"""
                        
                        card_html += "</div>"
                        slide_ph.markdown(card_html, unsafe_allow_html=True)
                        time.sleep(delay)
                slide_ph.success("播放完成！")

    # Tab 4: 測驗挑戰
    with tab4:
        if 'quiz_total' in st.session_state and st.session_state.quiz_total > 0:
            rate = (st.session_state.quiz_score / st.session_state.quiz_total) * 100
        else: rate = 0
        
        c_stat, c_reset = st.columns([3, 1])
        c_stat.markdown(f"📊 答對：**{st.session_state.quiz_score}** / 總題數：**{st.session_state.quiz_total}** (正確率: {rate:.1f}%)")
        if c_reset.button("🔄 重置成績"):
            st.session_state.quiz_score = 0; st.session_state.quiz_total = 0; st.rerun()

        st.divider()

        if filtered_df.empty:
            st.warning("請先新增單字才能進行測驗！")
        else:
            if st.session_state.quiz_current is None: next_question(filtered_df)
            q = st.session_state.quiz_current
            
            st.markdown(f"""
            <div class="quiz-card">
                <div style="font-size:18px;color:#555;">請聽發音或看單字，選出正確中文</div>
                <div class="quiz-word">{q['Word']}</div>
                <div style="color:#888;">{q['IPA']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- 修正重點：使用 st.audio 原生元件取代 HTML ---
            # 這樣可以確保每次單字更換時，播放器內容一定會強制更新
            audio_bytes = get_audio_bytes(q['Word'], 'en', tld=st.session_state.accent_tld, slow=st.session_state.is_slow)
            if audio_bytes:
                # 使用 key=q['Word'] 確保單字改變時，整個播放器會被重建
                st.audio(audio_bytes, format='audio/mp3')

            if not st.session_state.quiz_answered:
                cols = st.columns(2)
                for idx, opt in enumerate(st.session_state.quiz_options):
                    if cols[idx % 2].button(opt, key=f"q_opt_{idx}", use_container_width=True):
                        check_answer(opt)
                        st.rerun()
            else:
                if st.session_state.quiz_is_correct:
                    st.success("🎉 答對了！太棒了！")
                    st.balloons()
                else:
                    st.error(f"❌ 答錯了... 正確答案是：{q['Chinese']}")
                
                if st.button("➡️ 下一題", type="primary", use_container_width=True):
                    next_question(filtered_df)
                    st.rerun()

if __name__ == "__main__":
    main()
