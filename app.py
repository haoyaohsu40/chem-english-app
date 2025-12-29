<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>單字學習卡 - 修正版</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary-color: #4a90e2;
            --bg-color: #f5f7fa;
            --card-bg: #ffffff;
            --text-color: #333;
            --border-radius: 12px;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
        }

        .container {
            width: 100%;
            max-width: 800px; /* 稍微加寬以容納橫向排列 */
            background-color: var(--card-bg);
            border-radius: var(--border-radius);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        /* --- 修正點 1 & 5: 頂部區域與統計數據 --- */
        .header-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }

        .stats-container {
            display: flex;
            gap: 20px; /* 讓兩個統計數據分開一點但同一排 */
            font-size: 0.9em;
            color: #666;
            background: #f0f0f0;
            padding: 5px 15px;
            border-radius: 20px;
        }

        .header-controls {
            display: flex;
            gap: 10px; /* 設定與下載按鈕之間的間距 */
        }

        .btn {
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s;
            font-size: 0.9em;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .btn-primary { background-color: var(--primary-color); color: white; }
        .btn-secondary { background-color: #6c757d; color: white; }
        .btn-danger { background-color: #dc3545; color: white; }
        .btn:hover { opacity: 0.9; }

        /* --- 修正點 7: 輸入區塊 --- */
        .input-group {
            display: flex;
            gap: 10px;
            background: #eef2f7;
            padding: 15px;
            border-radius: var(--border-radius);
            flex-wrap: wrap; /* 手機版自動換行 */
        }

        .input-group input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            min-width: 150px;
        }

        /* --- 修正點 4: 導航分頁平均分散 --- */
        .nav-tabs {
            display: flex;
            width: 100%;
            border-bottom: 2px solid #ddd;
            margin-bottom: 10px;
        }

        .nav-tab {
            flex: 1; /* 每一個分頁佔據相同寬度 */
            text-align: center;
            padding: 10px 5px;
            cursor: pointer;
            color: #666;
            transition: 0.3s;
            white-space: nowrap; /* 防止文字換行 */
        }

        .nav-tab.active {
            color: var(--primary-color);
            border-bottom: 2px solid var(--primary-color);
            font-weight: bold;
        }

        /* 內容顯示區 */
        .content-section { display: none; }
        .content-section.active { display: block; }

        /* --- 修正點 2 & 3: 列表模式排版 --- */
        .word-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .word-item {
            display: flex;
            justify-content: space-between; /* 左右推開 */
            align-items: center;
            padding: 12px;
            border-bottom: 1px solid #eee;
        }

        .word-info {
            display: flex;
            align-items: center;
            gap: 10px; /* 單字、音標、中文之間的間距 */
            flex-wrap: nowrap; /* 強制不換行 */
            overflow: hidden;
            flex: 1; /* 佔據左側剩餘空間 */
        }

        .word-text { font-weight: bold; color: var(--primary-color); font-size: 1.1em; }
        .word-phonetic { color: #888; font-family: 'Arial', sans-serif; font-size: 0.9em; }
        .word-meaning { color: #333; }
        
        /* 確保中文不會掉下去，如果太長顯示... */
        .word-meaning span {
             white-space: nowrap;
             overflow: hidden;
             text-overflow: ellipsis;
        }

        /* 修正點 3: 操作按鈕同一排 */
        .word-actions {
            display: flex;
            gap: 8px; /* 按鈕間距 */
            flex-shrink: 0; /* 防止按鈕被壓縮 */
        }

        .action-btn {
            background: none;
            border: none;
            cursor: pointer;
            color: #666;
            font-size: 1.1em;
            padding: 4px;
        }
        .action-btn:hover { color: var(--primary-color); }
        .action-btn.delete:hover { color: #dc3545; }

        /* 卡片模式 */
        .card-display {
            text-align: center;
            padding: 40px;
            border: 2px dashed #ddd;
            border-radius: 20px;
            margin-top: 20px;
            position: relative;
        }
        .card-word { font-size: 2.5em; margin-bottom: 10px; color: var(--primary-color); }
        .card-phonetic { font-size: 1.2em; color: #888; margin-bottom: 20px; }
        .card-meaning { font-size: 1.5em; font-weight: bold; display: none; } /* 預設隱藏中文 */
        .card-display.show-meaning .card-meaning { display: block; }

        /* 輪播模式 */
        .carousel-container {
            text-align: center;
            padding: 30px;
            background: #333;
            color: #fff;
            border-radius: 15px;
            min-height: 200px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .carousel-word { font-size: 3em; margin-bottom: 10px; }
        .carousel-meaning { font-size: 1.5em; color: #ffd700; margin-top: 10px; opacity: 0; transition: opacity 0.5s; }
        .carousel-meaning.visible { opacity: 1; }
        
        .carousel-controls {
            margin-top: 20px;
            display: flex;
            gap: 10px;
            justify-content: center;
        }

    </style>
</head>
<body>

<div class="container">
    <div class="header-top">
        <h2><i class="fas fa-book-open"></i> 單字本</h2>
        
        <div class="stats-container">
            <span id="cloudCount">☁️ 雲端總數: 0</span>
            <span id="localCount">📖 本子字數: 0</span>
        </div>

        <div class="header-controls">
            <button class="btn btn-secondary" onclick="alert('設定功能開發中...')"><i class="fas fa-cog"></i> 設定</button>
            <button class="btn btn-primary" onclick="downloadData()"><i class="fas fa-download"></i> 下載</button>
        </div>
    </div>

    <div class="input-group">
        <input type="text" id="newWord" placeholder="輸入英文單字 (例如: apple)">
        <input type="text" id="newMeaning" placeholder="輸入中文意思 (例如: 蘋果)">
        <button class="btn btn-primary" onclick="addWord()">加入單字</button>
        <button class="btn btn-secondary" onclick="batchAdd()">拼次加入(批量)</button>
    </div>

    <div class="nav-tabs">
        <div class="nav-tab active" onclick="switchTab('list')">列表</div>
        <div class="nav-tab" onclick="switchTab('card')">卡片</div>
        <div class="nav-tab" onclick="switchTab('carousel')">輪播</div>
        <div class="nav-tab" onclick="switchTab('quiz')">測驗</div>
        <div class="nav-tab" onclick="switchTab('spelling')">拼字</div>
    </div>

    <div id="tab-list" class="content-section active">
        <ul class="word-list" id="wordListContainer">
            </ul>
    </div>

    <div id="tab-card" class="content-section">
        <div class="card-display" onclick="this.classList.toggle('show-meaning')">
            <div class="card-word" id="cardWord">Word</div>
            <div class="card-phonetic" id="cardPhonetic">/wɜːrd/</div>
            <div class="card-meaning" id="cardMeaning">單字</div>
            <p style="color: #999; margin-top: 30px; font-size: 0.8em;">(點擊卡片顯示/隱藏中文)</p>
            <div class="carousel-controls">
                <button class="btn btn-secondary" onclick="prevCard()">上一個</button>
                <button class="btn btn-primary" onclick="speakCurrentCard()">發音</button>
                <button class="btn btn-secondary" onclick="nextCard()">下一個</button>
            </div>
        </div>
    </div>

    <div id="tab-carousel" class="content-section">
        <div class="carousel-container">
            <div class="carousel-word" id="carouselWord">Ready</div>
            <div class="carousel-meaning" id="carouselMeaning">準備開始</div>
        </div>
        <div class="carousel-controls">
            <button class="btn btn-primary" id="btnStartCarousel" onclick="toggleCarousel()">開始輪播</button>
            <label style="display:flex; align-items:center; gap:5px;">
                <input type="checkbox" id="carouselSound" checked> 開啟聲音
            </label>
        </div>
    </div>

    <div id="tab-quiz" class="content-section">
        <p>測驗功能區 (待實作)</p>
    </div>
    
    <div id="tab-spelling" class="content-section">
        <p>拼字功能區 (待實作)</p>
    </div>

</div>

<script>
    // 模擬資料數據
    let words = [
        { word: 'Apple', phonetic: '/ˈæp.l̩/', meaning: '蘋果' },
        { word: 'Banana', phonetic: '/bəˈnæn.ə/', meaning: '香蕉' },
        { word: 'Computer', phonetic: '/kəmˈpjuː.tər/', meaning: '電腦' },
        { word: 'Elephant', phonetic: '/ˈel.ɪ.fənt/', meaning: '大象' }
    ];

    let currentCardIndex = 0;
    let carouselInterval;
    let isCarouselPlaying = false;

    // 初始化
    function init() {
        updateStats();
        renderList();
        updateCard();
    }

    function updateStats() {
        // 修正 5: 更新統計數字
        document.getElementById('cloudCount').textContent = `☁️ 雲端總數: ${words.length * 15}`; // 模擬數據
        document.getElementById('localCount').textContent = `📖 本子字數: ${words.length}`;
    }

    function switchTab(tabName) {
        document.querySelectorAll('.content-section').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
        
        document.getElementById(`tab-${tabName}`).classList.add('active');
        // 找到對應的 tab 按鈕並加 active (簡單邏輯)
        const tabs = ['list', 'card', 'carousel', 'quiz', 'spelling'];
        document.querySelectorAll('.nav-tab')[tabs.indexOf(tabName)].classList.add('active');

        // 如果離開輪播頁面，停止輪播
        if (tabName !== 'carousel' && isCarouselPlaying) {
            toggleCarousel();
        }
    }

    // --- 修正 2 & 3: 列表渲染 ---
    function renderList() {
        const list = document.getElementById('wordListContainer');
        list.innerHTML = '';
        words.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = 'word-item';
            li.innerHTML = `
                <div class="word-info">
                    <span class="word-text">${item.word}</span>
                    <span class="word-phonetic">${item.phonetic}</span>
                    <span class="word-meaning">${item.meaning}</span>
                </div>
                <div class="word-actions">
                    <button class="action-btn" title="發音" onclick="speak('${item.word}')"><i class="fas fa-volume-up"></i></button>
                    <button class="action-btn" title="Google翻譯" onclick="window.open('https://translate.google.com/?sl=en&tl=zh-TW&text=${item.word}', '_blank')"><i class="fab fa-google"></i></button>
                    <button class="action-btn" title="Yahoo字典" onclick="window.open('https://tw.dictionary.yahoo.com/dictionary?p=${item.word}', '_blank')"><i class="fab fa-yahoo"></i></button>
                    <button class="action-btn delete" title="刪除" onclick="deleteWord(${index})"><i class="fas fa-trash-alt"></i></button>
                </div>
            `;
            list.appendChild(li);
        });
    }

    function addWord() {
        const w = document.getElementById('newWord').value.trim();
        const m = document.getElementById('newMeaning').value.trim();
        if(w && m) {
            words.push({ word: w, phonetic: '/.../', meaning: m });
            document.getElementById('newWord').value = '';
            document.getElementById('newMeaning').value = '';
            init();
        } else {
            alert('請輸入單字和中文');
        }
    }

    function batchAdd() {
        alert('請輸入格式：單字,中文 (換行區隔)');
        // 這裡可以跳出一個 modal 讓使用者貼上大量文字
    }

    function deleteWord(index) {
        if(confirm('確定刪除?')) {
            words.splice(index, 1);
            init();
        }
    }

    function speak(text) {
        window.speechSynthesis.cancel(); // 停止目前的發音
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        utterance.rate = 0.8; // 稍微慢一點
        window.speechSynthesis.speak(utterance);
    }

    // --- 卡片功能 ---
    function updateCard() {
        if(words.length === 0) return;
        const item = words[currentCardIndex];
        document.getElementById('cardWord').textContent = item.word;
        document.getElementById('cardPhonetic').textContent = item.phonetic;
        document.getElementById('cardMeaning').textContent = item.meaning;
    }
    
    function nextCard() {
        currentCardIndex = (currentCardIndex + 1) % words.length;
        updateCard();
    }
    
    function prevCard() {
        currentCardIndex = (currentCardIndex - 1 + words.length) % words.length;
        updateCard();
    }

    function speakCurrentCard() {
        if(words.length > 0) speak(words[currentCardIndex].word);
    }

    // --- 修正 6: 輪播功能 (包含聲音) ---
    let carouselIndex = 0;
    
    function toggleCarousel() {
        const btn = document.getElementById('btnStartCarousel');
        if (isCarouselPlaying) {
            // 停止
            clearInterval(carouselInterval);
            isCarouselPlaying = false;
            btn.textContent = "開始輪播";
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-primary');
        } else {
            // 開始
            if(words.length === 0) { alert('沒有單字可輪播'); return; }
            isCarouselPlaying = true;
            btn.textContent = "停止輪播";
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-danger');
            
            runCarouselStep(); // 立即執行一次
            carouselInterval = setInterval(runCarouselStep, 3500); // 每 3.5 秒切換
        }
    }

    function runCarouselStep() {
        const item = words[carouselIndex];
        const wEl = document.getElementById('carouselWord');
        const mEl = document.getElementById('carouselMeaning');
        const soundEnabled = document.getElementById('carouselSound').checked;

        // 1. 顯示單字
        wEl.textContent = item.word;
        mEl.textContent = item.meaning;
        mEl.classList.remove('visible'); // 先隱藏中文

        // 2. 發音 (如果開啟)
        if(soundEnabled) {
            speak(item.word);
        }

        // 3. 延遲顯示中文 (模擬學習效果)
        setTimeout(() => {
            mEl.classList.add('visible');
        }, 1500);

        // 準備下一個
        carouselIndex = (carouselIndex + 1) % words.length;
    }

    function downloadData() {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(words));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", "vocabulary.json");
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    }

    // 啟動
    init();

</script>

</body>
</html>
