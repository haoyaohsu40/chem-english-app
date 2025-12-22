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
import uuid

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

def text_to_speech_visible(text, lang='en'):
    """回傳【可見】的音訊播放器 (v8.0 風格)"""
    try:
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        if not clean_text: return ""
        
        tts = gTTS(text=clean_text, lang=lang)
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        
        # 關鍵：controls=顯示播放條, autoplay=自動播一次
        md = f"""
            <audio controls autoplay style="width: 100%; margin-top: 5px;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        return md
    except Exception as e:
        return ""

def text_to_speech_autoplay_hidden(text, lang='en'):
    """(保留給自動播放模式用) 回傳隱藏的自動播放音訊"""
    try:
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        if not clean_text: return ""
        tts = gTTS(text=clean_text, lang=lang)
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        unique_id = f"audio_{uuid.uuid4()}_{time.time_ns()}"
        md = f"""
            <audio autoplay style="width:0;height:0;opacity:0;" id="{unique_id}">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        return md
    except: return ""

def generate_custom_audio(df, sequence):
    """生成客製化順序的長音訊"""
    full_text = ""
    for i, (index, row) in enumerate(df.iloc[::-1].iterrows(), start=1):
        word = str(row['Word'])
        chinese = str(row['Chinese'])
        full_text += f"第{i}個... "
        if not sequence: 
            full_text += f"{word}... "
        else:
            for item in sequence:
                if item == "英文": full_text += f"{word}... "
                elif item == "中文": full_text += f"{chinese}... "
        full_text += "... ... "
    tts = gTTS(text=full_text, lang='zh-TW')
    fp = BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()

def is_contains_chinese(string):
    for char in string:
        if '\u4e00' <= char <= '\u9fff': return True
    return False

def main():
    st.set_page_config(page_title="化工英語通 v14.0", layout="wide", page_icon="⚗️")

    # CSS
    st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; }
    .word-text { font-size: 24px; font-weight: bold; color: #2E7D32; font-family: 'Arial Black', sans-serif; }
    .ipa-text { font-size: 16px; color: #757575; font-family: 'Arial', sans-serif; }
    .meaning-text { font-size: 20px; color: #1565C0; font-weight: bold;}
    .slide-card {
        border: 2px solid #4CAF50;
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        background-color: #f0fdf4;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        min-height: 300px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .slide-word { font-size: 60px; color: #2E7D32; font-weight: bold; margin-bottom: 10px; }
    .slide-ipa { font-size: 28px; color: #666; margin-bottom: 20px; }
    .slide-meaning { font-size: 50px; color: #1565C0; font-weight: bold; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("⚗️ 化工英語單字卡 (v14.0 經典回歸版)")

    df = load_data()

    if 'play_order' not in st.session_state:
        st.session_state.play_order = ["英文", "中文", "英文"] 

    # --- 側邊欄 ---
    with st.sidebar:
        st.header("📝 新增單字")
        notebooks = df['Notebook'].unique().tolist()
        if '預設筆記本' not in notebooks: notebooks.append('預設筆記本')
        
        nb_mode_opt = st.radio("筆記本來源", ["選擇現有", "建立新本"], horizontal=True, label_visibility="collapsed")
        if nb_mode_opt == "選擇現有": notebook = st.selectbox("選擇筆記本", notebooks)
        else: notebook = st.text_input("輸入新筆記本名稱", "ABS製程")

        st.markdown("---")
        input_mode = st.radio("輸入模式", ["🔤 單字輸入", "🚀 批次貼上"], horizontal=True)

        if input_mode == "🔤 單字輸入":
            word_input = st.text_input("輸入英文單字", placeholder="例如: Valve")
            # 試聽也改用可見播放器，方便確認
            if st.button("🔊 試聽"):
                if word_input and not is_contains_chinese(word_input):
                    st.markdown(text_to_speech_visible(word_input, 'en'), unsafe_allow_html=True)
            if st.button("➕ 加入", type="primary"):
                if word_input and notebook and not is_contains_chinese(word_input):
                    with st.spinner('處理中...'):
                        try:
                            ipa = f"[{eng_to_ipa.convert(word_input)}]"
                            trans = GoogleTranslator(source='auto', target='zh-TW').translate(word_input)
                            new_entry = {'Notebook': notebook, 'Word': word_input, 'IPA': ipa, 'Chinese': trans, 'Date': pd.Timestamp.now().strftime('%Y-%m-%d')}
                            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                            save_data(df)
                            st.success(f"已加入：{word_input}")
                            time.sleep(0.5)
                            st.rerun()
                        except: st.error("錯誤")
        else:
            bulk_input = st.text_area("📋 批次貼上區", height=100)
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
                        df = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
                        save_data(df)
                        st.success(f"加入 {len(new_entries)} 筆")
                        time.sleep(1)
                        st.rerun()

    # --- 通勤模式設定 ---
    st.sidebar.markdown("---")
    with st.sidebar.expander("🎧 通勤模式 (設定)", expanded=True):
        st.write("自訂播放順序：")
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
    with st.sidebar.expander("🛠️ 進階管理"):
        manage_list = df['Notebook'].unique().tolist()
        if manage_list:
            target_nb = st.selectbox("管理筆記本", manage_list, key="m_nb")
            new_nb_name = st.text_input("新名稱:", value=target_nb, key="rename_input")
            if st.button("確認改名"):
                if new_nb_name and new_nb_name != target_nb:
                    df.loc[df['Notebook'] == target_nb, 'Notebook'] = new_nb_name
                    save_data(df)
                    st.success("已更新")
                    st.rerun()
            if st.button("🗑️ 刪除此筆記本"):
                df = df[df['Notebook'] != target_nb]
                save_data(df)
                st.rerun()
        if st.button("💥 重置所有資料"):
            if os.path.exists(CSV_FILE): os.remove(CSV_FILE)
            st.rerun()

    # --- 主畫面 ---
    col_filter, col_mp3 = st.columns([2, 1])
    with col_filter:
        filter_nb = st.selectbox("📖 我要複習哪一本？", ["全部"] + df['Notebook'].unique().tolist())
    filtered_df = df if filter_nb == "全部" else df[df['Notebook'] == filter_nb]

    with col_mp3:
        st.write("🎧 **通勤下載**")
        if not filtered_df.empty and st.session_state.play_order:
            if st.button("下載自訂順序 MP3"):
                with st.spinner("生成中..."):
                    audio_bytes = generate_custom_audio(filtered_df, st.session_state.play_order)
                    st.download_button(label="📥 下載 MP3", data=audio_bytes, file_name=f"vocab_custom.mp3", mime="audio/mp3")
        else:
            st.button("無資料/未設順序", disabled=True)

    tab1, tab2, tab3 = st.tabs(["📋 單字列表", "🃏 學習卡片", "🎬 自動播放"])

    with tab1:
        # 列表標題
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
                    # 1. 按鈕加上文字
                    if st.button("🔊 播放", key=f"l_p_{index}"):
                        # 2. 顯示可見的播放器 (HTML audio controls)
                        st.markdown(text_to_speech_visible(row['Word'], 'en'), unsafe_allow_html=True)
                    
                    st.markdown(f"[G 翻譯](https://translate.google.com/?sl=en&tl=zh-TW&text={row['Word']}&op=translate)")
                with c4:
                    # 1. 按鈕加上文字
                    if st.button("🗑️ 刪除", key=f"l_d_{index}"):
                        df = df[~((df['Word'] == row['Word']) & (df['Notebook'] == row['Notebook']))]
                        save_data(df)
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
                st.link_button("🖼️ Google 圖片搜尋", f"https://www.google.com/search?tbm=isch&q={row['Word']}+chemical", use_container_width=True)

                c_show, c_aud = st.columns(2)
                with c_show:
                    if st.button("👀 看答案", use_container_width=True):
                        st.info(f"{row['Chinese']}")
                with c_aud:
                    if st.button("🔊 聽發音", use_container_width=True):
                        st.markdown(text_to_speech_visible(row['Word'], 'en'), unsafe_allow_html=True)
            
            c_prev, c_next = st.columns(2)
            with c_prev: 
                if st.button("⬅️ 上一張", use_container_width=True): st.session_state.card_index -= 1; st.rerun()
            with c_next: 
                if st.button("下一張 ➡️", use_container_width=True): st.session_state.card_index += 1; st.rerun()

    with tab3:
        st.markdown("#### 🎬 像看影片一樣背單字")
        st.caption("如需停止，請重新整理網頁。")
        
        col_ctrl, _ = st.columns([1, 2])
        with col_ctrl:
            delay_sec = st.slider("切換速度 (秒)", 2, 10, 3)
            start_btn = st.button("▶️ 開始播放", type="primary")
        
        slide_placeholder = st.empty()
        
        if start_btn:
            if filtered_df.empty:
                st.error("無單字！")
            else:
                st.toast("播放中... (停止請按 F5)")
                play_list = filtered_df.iloc[::-1]
                
                for index, row in play_list.iterrows():
                    word = row['Word']
                    chinese = row['Chinese']
                    ipa = row['IPA']
                    
                    slide_placeholder.empty()
                    time.sleep(0.1)
                    
                    # 這裡還是用隱藏的自動播放，為了視覺乾淨
                    # 英文
                    slide_placeholder.markdown(f"""
                    <div class="slide-card">
                        <div class="slide-word">{word}</div>
                        <div class="slide-ipa">{ipa}</div>
                        <div style="height: 50px; color: #aaa;">(思考中...)</div>
                        {text_to_speech_autoplay_hidden(word, 'en')}
                    </div>
                    """, unsafe_allow_html=True)
                    time.sleep(delay_sec)
                    
                    # 中文
                    slide_placeholder.markdown(f"""
                    <div class="slide-card">
                        <div class="slide-word">{word}</div>
                        <div class="slide-ipa">{ipa}</div>
                        <div class="slide-meaning">{chinese}</div>
                        {text_to_speech_autoplay_hidden(chinese, 'zh-TW')}
                    </div>
                    """, unsafe_allow_html=True)
                    time.sleep(delay_sec)
                
                slide_placeholder.success("播放結束！")

if __name__ == "__main__":
    main()