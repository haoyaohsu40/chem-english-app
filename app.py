import streamlit as st
import streamlit.components.v1 as components

# 設定頁面配置
st.set_page_config(page_title="CHIMEI ABS 單字學習系統", layout="wide")

# 這裡將前端的 HTML/JS/CSS 完整包裝成一個字串
html_code = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>單字學習</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        /* 隱藏滾動條但保持功能 */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #f1f1f1; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
        
        /* 卡片翻轉效果 */
        .perspective-1000 { perspective: 1000px; }
        .transform-style-3d { transform-style: preserve-3d; }
        .backface-hidden { backface-visibility: hidden; }
        .rotate-y-180 { transform: rotateY(180deg); }
    </style>
</head>
<body class="bg-gray-50 text-gray-800 h-screen flex flex-col" x-data="appData()">

    <div class="bg-white shadow-sm border-b px-4 py-3 sticky top-0 z-20">
        <div class="max-w-md mx-auto flex justify-between items-center">
            <div class="flex items-center gap-2">
                <i class="fa-solid fa-book text-red-500"></i>
                <h1 class="font-bold text-lg text-gray-800 cursor-pointer border-b border-transparent hover:border-gray-300" 
                    @click="renameNotebook()" x-text="notebookName"></h1>
            </div>
            <div class="text-xs text-gray-400">ABS Process Dept.</div>
        </div>
    </div>

    <div class="flex-1 overflow-y-auto p-4 pb-32 max-w-md mx-auto w-full">
        
        <button @click="openModal()" class="w-full bg-red-500 hover:bg-red-600 text-white font-bold py-3 px-4 rounded-lg shadow transition mb-6 flex items-center justify-center gap-2">
            <i class="fa-solid fa-plus"></i> 加入單字庫
        </button>

        <div class="bg-white rounded-lg shadow-sm border border-gray-200 mb-4 overflow-hidden">
            <div class="border-b border-gray-100">
                <button @click="showSettings = !showSettings" class="w-full flex justify-between items-center p-3 bg-gray-50 text-sm font-medium text-gray-700">
                    <span class="flex items-center gap-2"><i class="fa-solid fa-volume-high"></i> 發音設定</span>
                    <i class="fa-solid" :class="showSettings ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
                </button>
                
                <div x-show="showSettings" class="p-4 space-y-4">
                    <div>
                        <label class="block text-xs text-gray-500 mb-1">口音 (Accent)</label>
                        <select x-model="settings.accent" class="w-full border rounded p-2 text-sm bg-white">
                            <option value="en-US">美式 (US)</option>
                            <option value="en-GB">英式 (UK)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs text-gray-500 mb-1">語速 (Speed)</label>
                        <div class="flex gap-4">
                            <label class="flex items-center gap-2 text-sm cursor-pointer">
                                <input type="radio" name="speed" :value="1.0" x-model.number="settings.speed" class="text-red-500 focus:ring-red-500">
                                正常 (Normal)
                            </label>
                            <label class="flex items-center gap-2 text-sm cursor-pointer">
                                <input type="radio" name="speed" :value="0.7" x-model.number="settings.speed" class="text-red-500 focus:ring-red-500">
                                慢速 (Slow)
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            <div>
                <button @click="showPlayback = !showPlayback" class="w-full flex justify-between items-center p-3 bg-gray-50 text-sm font-medium text-gray-700">
                    <span class="flex items-center gap-2"><i class="fa-solid fa-headphones"></i> 播放順序</span>
                    <i class="fa-solid" :class="showPlayback ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
                </button>

                <div x-show="showPlayback" class="p-4 bg-blue-50">
                    <div class="flex gap-2 mb-3">
                        <button @click="addToSequence('en')" class="flex-1 bg-white border border-gray-300 rounded py-2 text-sm hover:bg-gray-50 shadow-sm">
                            <i class="fa-solid fa-plus text-xs"></i> 英文
                        </button>
                        <button @click="addToSequence('zh')" class="flex-1 bg-white border border-gray-300 rounded py-2 text-sm hover:bg-gray-50 shadow-sm">
                            <i class="fa-solid fa-plus text-xs"></i> 中文
                        </button>
                        <button @click="settings.sequence = []" class="px-3 bg-white border border-gray-300 rounded text-red-500 hover:text-red-700 shadow-sm">
                            <i class="fa-solid fa-xmark"></i> 清空
                        </button>
                    </div>
                    
                    <div class="bg-blue-100 rounded p-2 text-center text-sm font-medium text-blue-800 min-h-[40px] flex items-center justify-center gap-2 flex-wrap">
                        <span class="text-gray-500 text-xs" x-show="settings.sequence.length === 0">順序：(請點擊上方按鈕加入)</span>
                        <template x-for="(item, index) in settings.sequence" :key="index">
                            <span class="bg-white px-2 py-1 rounded shadow-sm text-xs flex items-center">
                                <span x-text="item === 'en' ? '英文' : '中文'"></span>
                                <i class="fa-solid fa-arrow-right text-gray-300 ml-2" x-show="index !== settings.sequence.length - 1"></i>
                            </span>
                        </template>
                    </div>
                </div>
            </div>
        </div>

        <div class="flex border-b mb-4">
            <button @click="mode = 'list'" :class="{'border-b-2 border-red-500 text-red-500': mode === 'list'}" class="flex-1 py-2 text-center font-medium text-gray-500 transition">列表</button>
            <button @click="mode = 'card'; startCardMode()" :class="{'border-b-2 border-red-500 text-red-500': mode === 'card'}" class="flex-1 py-2 text-center font-medium text-gray-500 transition">卡片學習</button>
        </div>

        <div x-show="mode === 'list'" class="space-y-3">
            <div class="relative">
                <i class="fa-solid fa-search absolute left-3 top-3 text-gray-400"></i>
                <input type="text" x-model="search" placeholder="搜尋單字..." class="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-red-200">
            </div>

            <template x-for="word in filteredWords" :key="word.id">
                <div class="bg-white p-4 rounded-lg shadow-sm border-l-4 border-red-400 flex justify-between items-start group">
                    <div class="flex-1">
                        <div class="flex items-center gap-2">
                            <h3 class="font-bold text-lg text-gray-800" x-text="word.en"></h3>
                            <button @click="speakWord(word)" class="text-gray-400 hover:text-red-500">
                                <i class="fa-solid fa-volume-high"></i>
                            </button>
                        </div>
                        <p class="text-gray-600 mt-1 text-sm" x-text="word.zh"></p>
                    </div>
                    <div class="flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button @click="editWord(word)" class="text-gray-400 hover:text-blue-500"><i class="fa-solid fa-pen"></i></button>
                        <button @click="deleteWord(word.id)" class="text-gray-400 hover:text-red-500"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </div>
            </template>
             <div x-show="filteredWords.length === 0" class="text-center text-gray-400 mt-8">
                找不到單字，請新增
            </div>
        </div>

        <div x-show="mode === 'card'" class="h-[60vh] flex flex-col items-center justify-center">
            <template x-if="cardQueue.length > 0">
                <div class="w-full h-full perspective-1000 cursor-pointer group" @click="isFlipped = !isFlipped">
                    <div class="relative w-full h-full transition-all duration-500 transform-style-3d shadow-xl rounded-xl" :class="isFlipped ? 'rotate-y-180' : ''">
                        <div class="absolute inset-0 backface-hidden bg-white rounded-xl flex flex-col items-center justify-center border-2 border-red-50">
                            <span class="text-gray-400 text-xs mb-4">English</span>
                            <h2 class="text-4xl font-bold text-gray-800 text-center px-4" x-text="currentCard.en"></h2>
                            <button @click.stop="speakText(currentCard.en)" class="mt-6 w-12 h-12 rounded-full bg-red-50 text-red-500 flex items-center justify-center hover:bg-red-100">
                                <i class="fa-solid fa-volume-high text-xl"></i>
                            </button>
                        </div>
                        <div class="absolute inset-0 backface-hidden rotate-y-180 bg-red-50 rounded-xl flex flex-col items-center justify-center border-2 border-red-100">
                            <span class="text-gray-500 text-xs mb-4">Chinese</span>
                            <h2 class="text-3xl font-bold text-gray-800 text-center px-4" x-text="currentCard.zh"></h2>
                        </div>
                    </div>
                </div>
            </template>

            <div class="flex items-center gap-6 mt-6" x-show="cardQueue.length > 0">
                <button @click="prevCard()" class="w-10 h-10 rounded-full bg-white shadow flex items-center justify-center hover:bg-gray-100"><i class="fa-solid fa-arrow-left"></i></button>
                <button @click="playCurrentSequence()" class="bg-red-500 text-white px-6 py-2 rounded-full shadow hover:bg-red-600 flex items-center gap-2">
                    <i class="fa-solid fa-play"></i> 播放順序
                </button>
                <button @click="nextCard()" class="w-10 h-10 rounded-full bg-white shadow flex items-center justify-center hover:bg-gray-100"><i class="fa-solid fa-arrow-right"></i></button>
            </div>
             <div x-show="cardQueue.length === 0" class="text-center text-gray-400">
                無卡片，請先在列表新增
            </div>
        </div>

    </div>

    <div x-show="showModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" style="display: none;">
        <div class="bg-white rounded-xl w-full max-w-sm p-6 shadow-2xl">
            <h3 class="text-lg font-bold mb-4" x-text="isEdit ? '編輯單字' : '新增單字'"></h3>
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700">英文單字</label>
                    <input type="text" x-model="form.en" class="w-full border rounded p-2 focus:ring-2 focus:ring-red-500 focus:outline-none">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700">中文解釋</label>
                    <input type="text" x-model="form.zh" class="w-full border rounded p-2 focus:ring-2 focus:ring-red-500 focus:outline-none">
                </div>
            </div>
            <div class="mt-6 flex justify-end gap-2">
                <button @click="showModal = false" class="px-4 py-2 text-gray-500 hover:bg-gray-100 rounded">取消</button>
                <button @click="saveWord()" class="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600">儲存</button>
            </div>
        </div>
    </div>

    <script>
        function appData() {
            return {
                notebookName: '15002ABS 單字本',
                mode: 'list', // 'list' or 'card'
                search: '',
                showSettings: true,
                showPlayback: true,
                showModal: false,
                isEdit: false,
                isFlipped: false,
                
                // 預設資料
                words: [
                    { id: 1, en: 'Extruder', zh: '擠出機' },
                    { id: 2, en: 'Pelletizer', zh: '造粒機' },
                    { id: 3, en: 'Maintenance', zh: '維修保養' },
                    { id: 4, en: 'Safety First', zh: '安全第一' }
                ],
                
                // 表單資料
                form: { id: null, en: '', zh: '' },

                // 設定資料 (符合截圖需求)
                settings: {
                    accent: 'en-US', // en-US or en-GB
                    speed: 1.0,      // 1.0 or 0.7
                    sequence: ['en', 'zh', 'en'] // 預設: 英文 -> 中文 -> 英文
                },

                // 卡片模式佇列
                cardQueue: [],
                cardIndex: 0,

                get filteredWords() {
                    if (this.search === '') return this.words;
                    const lowSearch = this.search.toLowerCase();
                    return this.words.filter(w => w.en.toLowerCase().includes(lowSearch) || w.zh.includes(lowSearch));
                },

                get currentCard() {
                    return this.cardQueue[this.cardIndex] || { en: '', zh: '' };
                },

                // 更名功能
                renameNotebook() {
                    const newName = prompt('請輸入新的單字本名稱：', this.notebookName);
                    if (newName) this.notebookName = newName;
                },

                // 播放順序設定功能
                addToSequence(type) {
                    this.settings.sequence.push(type);
                },

                // 語音合成核心
                speakText(text, lang = 'en') {
                    // 停止當前發音
                    window.speechSynthesis.cancel();
                    
                    const u = new SpeechSynthesisUtterance(text);
                    u.rate = this.settings.speed;
                    
                    if (lang === 'zh') {
                        u.lang = 'zh-TW';
                    } else {
                        u.lang = this.settings.accent; 
                    }
                    
                    window.speechSynthesis.speak(u);
                    return new Promise(resolve => {
                        u.onend = resolve;
                    });
                },

                // 依序播放 (重點功能)
                async playCurrentSequence() {
                    const word = this.currentCard;
                    for (const type of this.settings.sequence) {
                        if (type === 'en') {
                            await this.speakText(word.en, 'en');
                        } else if (type === 'zh') {
                            await this.speakText(word.zh, 'zh');
                        }
                        // 簡單的間隔
                        await new Promise(r => setTimeout(r, 500));
                    }
                },
                
                // 列表模式單點播放 (只唸英文)
                speakWord(word) {
                    this.speakText(word.en, 'en');
                },

                // CRUD
                openModal() {
                    this.isEdit = false;
                    this.form = { id: Date.now(), en: '', zh: '' };
                    this.showModal = true;
                },
                editWord(word) {
                    this.isEdit = true;
                    this.form = { ...word };
                    this.showModal = true;
                },
                saveWord() {
                    if (!this.form.en || !this.form.zh) return;
                    if (this.isEdit) {
                        const idx = this.words.findIndex(w => w.id === this.form.id);
                        if (idx !== -1) this.words[idx] = { ...this.form };
                    } else {
                        this.words.push({ ...this.form });
                    }
                    this.showModal = false;
                    if(this.mode === 'card') this.startCardMode();
                },
                deleteWord(id) {
                    if(confirm('確定刪除?')) {
                        this.words = this.words.filter(w => w.id !== id);
                    }
                },

                // 卡片邏輯
                startCardMode() {
                    this.cardQueue = JSON.parse(JSON.stringify(this.filteredWords));
                    this.cardIndex = 0;
                    this.isFlipped = false;
                },
                nextCard() {
                    this.isFlipped = false;
                    setTimeout(() => {
                        if (this.cardIndex < this.cardQueue.length - 1) this.cardIndex++;
                        else this.cardIndex = 0;
                    }, 200);
                },
                prevCard() {
                    this.isFlipped = false;
                    setTimeout(() => {
                        if (this.cardIndex > 0) this.cardIndex--;
                        else this.cardIndex = this.cardQueue.length - 1;
                    }, 200);
                }
            }
        }
    </script>
</body>
</html>
"""

# 使用 Streamlit 元件顯示 HTML
# height 設定高一點以確保手機版也容易滑動
components.html(html_code, height=900, scrolling=True)
