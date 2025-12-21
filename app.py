import streamlit as st
import pandas as pd
import os
from gtts import gTTS
import base64
from io import BytesIO
from deep_translator import GoogleTranslator
import eng_to_ipa
import time
import re

# 設定檔案名稱
CSV_FILE = 'vocab.csv'

def load_data():
    """載入或建立資料庫"""
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=['Notebook', 'Word', 'IPA', 'Chinese', 'Date'])
        df.to_csv(CSV_FILE, index=False)
    return pd.read_csv(CSV_FILE)

def save_data(df):
    """儲存資料"""
    df.to_csv(CSV_FILE, index=False)

def text_to_speech_autoplay(text):
    """回傳自動播放的 HTML"""
    try:
        clean_text = re.sub(r'[^\w\s]', '', text)
        tts = gTTS(text=clean_text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        md = f"""
            <audio controls style="height: 30px; width: 100%;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        return md
    except Exception as e:
        return f"無法產生語音"

def generate_long_audio(df):
    """生成通勤用的長音訊 (加入報數與停頓優化)"""
    full_text = ""
    for i, (index, row) in enumerate(df.iterrows(), start=1):
        word = str(row['Word'])
        chinese = str(row['Chinese'])
        segment = f"第{i}個... ... {word}. ... ... {chinese}. ... ... {word}. ... ... ... "
        full_text += segment
    
    tts = gTTS(text=full_text, lang='zh-TW')
    fp = BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()

def is_contains_chinese(string):
    """檢查字串是否包含中文"""
    for char in string:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False

def main():
    st.set_page_config(page_title="化工英語通 v8.0", layout="wide", page_icon="⚗️")

    # CSS 美化與【強制防翻譯】設定
    st.markdown("""
    <meta name="google" content="notranslate">
    <style>
    .stButton>button { border-radius: 8px; }
    /* 英文單字樣式 - 防止翻譯 */
    .word-text { font-size: 24px; font-weight: bold; color: #2E7D32; font-family: 'Arial Black', sans-serif; }
    .ipa-text { font-size: 16px; color: #757575; font-family: 'Arial', sans-serif; }
    .meaning-text { font-size: 20px; color: #1565C0; font-weight: bold;}
    div[data-testid="stVerticalBlock"] > div { gap: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("⚗️ 化工英語單字卡 (v8.0 批次極速版)")

    # 載入資料
    df = load_data()

    # --- 側邊欄：新增單字區 ---
    with st.sidebar:
        st.header("📝 新增單字")
        
        # 1. 筆記本選擇 (共用)
        notebooks = df['Notebook'].unique().tolist()
        if '預設筆記本' not in notebooks:
            notebooks.append('預設筆記本')
        
        # 筆記本選擇區塊
        nb_mode_opt = st.radio("筆記本來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed")
        if nb_mode_opt == "選擇現有":
            notebook = st.selectbox("選擇筆記本", notebooks)
        else:
            notebook = st.text_input("輸入新筆記本名稱", "ABS製程")

        st.markdown("---")
        
        # 2. 切換輸入模式 (單字 vs 批次)
        input_mode = st.radio("輸入模式", ["🔤 單字輸入 (單筆)", "🚀 批次貼上 (多筆)"], horizontal=True)

        if input_mode == "🔤 單字輸入 (單筆)":
            # --- 舊的單筆輸入模式 ---
            word_input = st.text_input("輸入英文單字", placeholder="例如: Valve (請勿輸入中文)")

            if st.button("🔊 試聽發音 (免存檔)"):
                if word_input:
                    clean_word = word_input.split('[')[0].split('/')[0].strip()
                    if is_contains_chinese(clean_word):
                        st.warning("⚠️ 請輸入英文進行試聽")
                    else:
                        st.markdown(text_to_speech_autoplay(clean_word), unsafe_allow_html=True)
                else:
                    st.warning("請先輸入單字")

            if st.button("➕ 加入單字庫", type="primary"):
                if word_input and notebook:
                    if is_contains_chinese(word_input) and '[' not in word_input:
                        st.error("❌ 錯誤：請輸入英文 (如 Valve)，不要輸入中文！")
                    else:
                        with st.spinner('AI 正在查詢翻譯與音標...'):
                            if '[' in word_input or '/' in word_input:
                                ipa_match = re.search(r'[\[\/](.*?)[\]\/]', word_input)
                                ipa = f"[{ipa_match.group(1)}]" if ipa_match else ""
                                word_clean = re.sub(r'[\[\/].*?[\]\/]', '', word_input).strip()
                            else:
                                word_clean = word_input.strip()
                                try:
                                    ipa = f"[{eng_to_ipa.convert(word_clean)}]"
                                except:
                                    ipa = ""
                            
                            if is_contains_chinese(word_clean):
                                st.error("❌ 錯誤：輸入框偵測到中文！請只輸入英文。")
                            else:
                                try:
                                    translator = GoogleTranslator(source='auto', target='zh-TW')
                                    chinese_trans = translator.translate(word_clean)
                                except:
                                    chinese_trans = "請手動輸入中文"

                                new_entry = {
                                    'Notebook': notebook,
                                    'Word': word_clean,
                                    'IPA': ipa,
                                    'Chinese': chinese_trans,
                                    'Date': pd.Timestamp.now().strftime('%Y-%m-%d')
                                }
                                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                                save_data(df)
                                st.success(f"已加入：{word_clean}")
                                time.sleep(0.5)
                                st.rerun()

        else:
            # --- 新的批次輸入模式 ---
            st.info("請將 NotebookLM 整理好的單字貼在下方，用逗號隔開。")
            st.caption("例如：apple, valve, pump, viscosity")
            bulk_input = st.text_area("📋 貼上區", height=150)
            
            if st.button("🚀 開始批次加入", type="primary"):
                if bulk_input and notebook:
                    # 使用 regex 同時處理：英文逗號、中文逗號、換行符號
                    words = re.split(r'[,\n，]', bulk_input)
                    
                    added_count = 0
                    progress_bar = st.progress(0)
                    total_words = len([w for w in words if w.strip()])
                    
                    if total_words == 0:
                        st.warning("沒有偵測到有效單字")
                    else:
                        new_entries = []
                        processed = 0
                        
                        for w in words:
                            word_clean = w.strip()
                            if not word_clean: continue
                            
                            processed += 1
                            progress_bar.progress(processed / total_words)
                            
                            # 簡單過濾：如果有中文或是數字開頭(例如 1. apple)就跳過或處理
                            # 這裡我們只過濾純中文
                            if is_contains_chinese(word_clean):
                                continue 
                                
                            # 開始處理單字
                            try:
                                ipa = f"[{eng_to_ipa.convert(word_clean)}]"
                                translator = GoogleTranslator(source='auto', target='zh-TW')
                                chinese_trans = translator.translate(word_clean)
                                
                                new_entry = {
                                    'Notebook': notebook,
                                    'Word': word_clean,
                                    'IPA': ipa,
                                    'Chinese': chinese_trans,
                                    'Date': pd.Timestamp.now().strftime('%Y-%m-%d')
                                }
                                new_entries.append(new_entry)
                                added_count += 1
                            except Exception as e:
                                st.error(f"處理 {word_clean} 時發生錯誤: {e}")

                        if new_entries:
                            df = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
                            save_data(df)
                            progress_bar.empty()
                            st.success(f"🎉 成功加入 {added_count} 個單字！")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.warning("沒有成功加入任何單字，請檢查格式。")


    # --- 側邊欄：通勤模式 ---
    st.sidebar.markdown("---")
    with st.sidebar.expander("🎧 通勤模式 (MP3下載)"):
        st.write("打包下載目前的列表。")
        st.caption("順序：第N個 ➝ 英文 ➝ 中文 ➝ 英文")
        
    # --- 側邊欄：進階管理 ---
    with st.sidebar.expander("🛠️ 進階管理"):
        manage_list = df['Notebook'].unique().tolist()
        if manage_list:
            target_nb = st.selectbox("選擇要管理的筆記本", manage_list, key="manage_nb_select")
            new_nb_name = st.text_input("新名稱:", value=target_nb, key="rename_input")
            if st.button("確認改名"):
                if new_nb_name and new_nb_name != target_nb:
                    df.loc[df['Notebook'] == target_nb, 'Notebook'] = new_nb_name
                    save_data(df)
                    st.success("已更新")
                    st.rerun()
            
            confirm_del = st.checkbox("確認刪除", key="del_check")
            if st.button("🗑️ 刪除筆記本"):
                if confirm_del:
                    df = df[df['Notebook'] != target_nb]
                    save_data(df)
                    st.success("已刪除")
                    st.rerun()
        
        if st.button("💥 重置所有資料"):
            if os.path.exists(CSV_FILE):
                os.remove(CSV_FILE)
                st.rerun()

    # --- 主畫面 ---
    col_filter, col_mp3 = st.columns([2, 1])
    with col_filter:
        filter_nb = st.selectbox("📖 我要複習哪一本？", ["全部"] + df['Notebook'].unique().tolist())
    
    if filter_nb != "全部":
        filtered_df = df[df['Notebook'] == filter_nb]
    else:
        filtered_df = df

    # --- 在主畫面顯示下載按鈕 ---
    with col_mp3:
        st.write("🎧 **通勤下載**")
        if not filtered_df.empty:
            if st.button("下載此列表 MP3"):
                with st.spinner(f"正在生成優化音訊 (加入停頓與報數)..."):
                    audio_bytes = generate_long_audio(filtered_df.iloc[::-1])
                    st.download_button(
                        label="📥 點擊下載優化版 MP3",
                        data=audio_bytes,
                        file_name=f"vocab_{filter_nb}_slow.mp3",
                        mime="audio/mp3"
                    )
        else:
            st.button("無資料可下載", disabled=True)

    tab1, tab2 = st.tabs(["📋 單字列表 (速查)", "🃏 學習卡片 (背誦)"])

    with tab1:
        # 標題加入 translate="no"
        h1, h2, h3, h4 = st.columns([3, 2, 2, 1])
        h1.markdown('<h4 translate="no">🇬🇧 English Word / 音標</h4>', unsafe_allow_html=True)
        h2.markdown("#### 🇹🇼 中文翻譯")
        h3.markdown("#### 發音 / 字典")
        h4.markdown("#### 操作")
        st.markdown("---")

        if filtered_df.empty:
            st.info("目前清單是空的，請從左側新增！")
        
        for index, row in filtered_df.iloc[::-1].iterrows():
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            with c1:
                st.markdown(f"<div class='word-text notranslate' translate='no'>{row['Word']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='ipa-text'>{row['IPA']}</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='meaning-text'>{row['Chinese']}</div>", unsafe_allow_html=True)
            with c3:
                if st.button("🔊 播放", key=f"play_{index}"):
                    st.markdown(text_to_speech_autoplay(row['Word']), unsafe_allow_html=True)
                yahoo_url = f"https://tw.dictionary.yahoo.com/dictionary?p={row['Word']}"
                st.markdown(f"[📖 Yahoo 詳解]({yahoo_url})")
            with c4:
                if st.button("🗑️ 刪除", key=f"del_{index}"):
                    df = df[~((df['Word'] == row['Word']) & (df['Notebook'] == row['Notebook']))]
                    save_data(df)
                    st.rerun()
            st.markdown("---")

    with tab2:
        if filtered_df.empty:
            st.info("請先新增單字")
        else:
            if 'card_index' not in st.session_state:
                st.session_state.card_index = 0
            if st.session_state.card_index >= len(filtered_df):
                st.session_state.card_index = 0
            
            current_row = filtered_df.iloc[st.session_state.card_index]
            
            st.markdown("###")
            card_col1, card_col2, card_col3 = st.columns([1, 2, 1])
            with card_col2:
                st.markdown(
                    f"""
                    <div style="border: 2px solid #4CAF50; border-radius: 15px; padding: 30px; text-align: center; background-color: #f9f9f9;">
                        <div class="notranslate" translate="no" style="font-size: 40px; color: #2E7D32; font-weight: bold; margin-bottom: 10px;">{current_row['Word']}</div>
                        <div style="color: #666; margin-bottom: 20px;">{current_row['IPA']}</div>
                    </div>
                    """, unsafe_allow_html=True
                )
                st.markdown("###")
                col_show, col_audio = st.columns(2)
                with col_show:
                    if st.button("👀 看中文解釋", key="show_card_ans", use_container_width=True):
                        st.info(f"中文: {current_row['Chinese']}")
                        yahoo_url = f"https://tw.dictionary.yahoo.com/dictionary?p={current_row['Word']}"
                        st.markdown(f"[📖 Yahoo 字典]({yahoo_url})")
                with col_audio:
                    if st.button("🔊 聽發音", key="play_card_audio", use_container_width=True):
                        st.markdown(text_to_speech_autoplay(current_row['Word']), unsafe_allow_html=True)

            st.markdown("---")
            nav1, nav2 = st.columns(2)
            with nav1:
                if st.button("⬅️ 上一張", use_container_width=True):
                    st.session_state.card_index = (st.session_state.card_index - 1) % len(filtered_df)
                    st.rerun()
            with nav2:
                if st.button("下一張 ➡️", use_container_width=True):
                    st.session_state.card_index = (st.session_state.card_index + 1) % len(filtered_df)
                    st.rerun()

if __name__ == "__main__":
    main()