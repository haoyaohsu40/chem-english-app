<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>單字學習本 - 完整功能版</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <style>
        /* 卡片翻轉特效 */
        .perspective { perspective: 1000px; }
        .rotate-y-180 { transform: rotateY(180deg); }
        .transform-style-preserve-3d { transform-style: preserve-3d; }
        .backface-hidden { backface-visibility: hidden; }
    </style>
</head>
<body class="bg-gray-100 text-gray-800 font-sans" x-data="vocabApp()">

    <div class="bg-blue-600 text-white p-4 shadow-md sticky top-0 z-10">
        <div class="max-w-2xl mx-auto">
            <div class="flex justify-between items-center mb-4">
                <h1 class="text-2xl font-bold" x-text="currentNotebookName"></h1>
                <div class="flex gap-2">
                    <button @click="renameNotebook()" class="text-xs bg-blue-500 hover:bg-blue-400 px-2 py-1 rounded">更名筆記本</button>
                    <select x-model="currentNotebookId" class="text-black text-sm rounded px-2 py-1">
                        <option value="1">工作專用 (ABS)</option>
                        <option value="2">多益單字</option>
                    </select>
                </div>
            </div>

            <div class="flex flex-col gap-3">
                <input x-model="searchQuery" type="text" placeholder="🔍 搜尋單字..." class="w-full px-3 py-2 rounded text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-300">
                
                <div class="flex justify-between items-center text-sm">
                    <div class="flex gap-2 bg-blue-700 p-1 rounded">
                        <button @click="viewMode = 'list'" :class="{'bg-white text-blue-800 shadow': viewMode === 'list'}" class="px-3 py-1 rounded transition">列表</button>
                        <button @click="startFlashcard()" :class="{'bg-white text-blue-800 shadow': viewMode === 'card'}" class="px-3 py-1 rounded transition">卡片學習</button>
                    </div>
                    
                    <label class="flex items-center gap-2 cursor-pointer select-none" x-show="viewMode === 'list'">
                        <input type="checkbox" x-model="hideChinese" class="form-checkbox h-4 w-4 text-blue-600">
                        <span>遮蔽中文</span>
                    </label>
                </div>
            </div>
        </div>
    </div>

    <div class="max-w-2xl mx-auto p-4 pb-24">

        <div x-show="viewMode === 'list'">
            <template x-for="word in filteredWords" :key="word.id">
                <div class="bg-white rounded-lg shadow p-4 mb-3 flex justify-between items-center transition hover:shadow-md" :class="{'opacity-50': word.mastered}">
                    
                    <div class="flex-1">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-xl font-bold text-blue-900" x-text="word.text"></span>
                            <button @click="speak(word.text)" class="text-gray-400 hover:text-blue-500">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" /></svg>
                            </button>
                        </div>
                        <div class="text-gray-600" :class="{'blur-sm select-none': hideChinese, 'cursor-pointer': hideChinese}" @click="hideChinese = false" x-text="word.def"></div>
                    </div>

                    <div class="flex items-center gap-3">
                        <button @click="toggleMastered(word.id)" class="text-gray-300 hover:text-green-500" :class="{'text-green-500': word.mastered}" title="標記為已熟記">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        </button>
                        <button @click="editWord(word)" class="text-gray-300 hover:text-blue-500">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" /></svg>
                        </button>
                        <button @click="deleteWord(word.id)" class="text-gray-300 hover:text-red-500">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M9 2a1 1 0 00-.993.883L8 2.976 7.976 3H5a1 1 0 000 2h14a1 1 0 000-2h-2.976L16 2.976a1 1 0 00-.993-.883H9zM5.929 5h8.142l-.707 10.607a2 2 0 01-1.996 1.893H8.632a2 2 0 01-1.996-1.893L5.929 5z" clip-rule="evenodd" /></svg>
                        </button>
                    </div>
                </div>
            </template>
            
            <div x-show="filteredWords.length === 0" class="text-center text-gray-500 mt-10">
                沒有找到單字，快按右下角新增吧！
            </div>
        </div>

        <div x-show="viewMode === 'card'" class="h-[60vh] flex flex-col items-center justify-center">
            
            <template x-if="flashcardQueue.length > 0">
                <div class="w-full h-full relative perspective group cursor-pointer" @click="isFlipped = !isFlipped">
                    <div class="w-full h-full relative transform-style-preserve-3d transition-transform duration-500 shadow-xl rounded-xl" :class="{'rotate-y-180': isFlipped}">
                        
                        <div class="absolute inset-0 backface-hidden bg-white rounded-xl flex flex-col items-center justify-center p-8 border-2 border-blue-100">
                            <span class="text-sm text-gray-400 mb-4">點擊翻牌</span>
                            <h2 class="text-4xl font-bold text-blue-800 text-center" x-text="currentCard.text"></h2>
                            <button @click.stop="speak(currentCard.text)" class="mt-6 p-2 rounded-full bg-blue-50 text-blue-500 hover:bg-blue-100">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" /></svg>
                            </button>
                        </div>

                        <div class="absolute inset-0 backface-hidden rotate-y-180 bg-blue-50 rounded-xl flex flex-col items-center justify-center p-8 border-2 border-blue-200">
                            <span class="text-sm text-gray-400 mb-4">中文解釋</span>
                            <p class="text-2xl font-medium text-gray-800 text-center" x-text="currentCard.def"></p>
                        </div>
                    </div>
                </div>
            </template>

            <div class="flex items-center gap-6 mt-8" x-show="flashcardQueue.length > 0">
                <button @click="prevCard()" class="px-4 py-2 bg-gray-200 rounded-full hover:bg-gray-300">上一張</button>
                <button @click="shuffleCards()" class="px-4 py-2 bg-yellow-100 text-yellow-700 rounded-full hover:bg-yellow-200 flex items-center gap-1">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                    洗牌
                </button>
                <button @click="nextCard()" class="px-4 py-2 bg-blue-600 text-white rounded-full hover:bg-blue-700 shadow-lg">下一張</button>
            </div>

            <div x-show="flashcardQueue.length === 0" class="text-center text-gray-500">
                目前沒有卡片可以複習。<br>請切換回列表新增單字。
            </div>
        </div>

    </div>

    <button @click="openAddModal()" class="fixed bottom-6 right-6 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition transform hover:scale-110 z-20">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
    </button>

    <div x-show="isModalOpen" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" style="display: none;">
        <div class="bg-white rounded-lg shadow-xl w-full max-w-sm p-6">
            <h3 class="text-xl font-bold mb-4" x-text="isEditing ? '編輯單字' : '新增單字'"></h3>
            
            <div class="mb-3">
                <label class="block text-sm font-medium text-gray-700 mb-1">英文單字</label>
                <input x-model="modalForm.text" type="text" class="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none">
            </div>
            
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">中文解釋</label>
                <textarea x-model="modalForm.def" rows="3" class="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"></textarea>
            </div>

            <div class="mb-4" x-show="isEditing">
                 <label class="block text-sm font-medium text-gray-700 mb-1">移動到筆記本</label>
                 <select x-model="modalForm.notebookId" class="w-full border rounded px-3 py-2">
                    <option value="1">工作專用 (ABS)</option>
                    <option value="2">多益單字</option>
                 </select>
            </div>

            <div class="flex justify-end gap-2">
                <button @click="isModalOpen = false" class="px-4 py-2 text-gray-500 hover:bg-gray-100 rounded">取消</button>
                <button @click="saveWord()" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">儲存</button>
            </div>
        </div>
    </div>

    <script>
        function vocabApp() {
            return {
                // 資料狀態
                words: [
                    { id: 1, notebookId: '1', text: 'Resin', def: '樹脂 (n.)', mastered: false },
                    { id: 2, notebookId: '1', text: 'Injection Molding', def: '射出成型 (n.)', mastered: false },
                    { id: 3, notebookId: '1', text: 'Viscosity', def: '黏度 (n.)', mastered: false },
                    { id: 4, notebookId: '2', text: 'Agenda', def: '議程 (n.)', mastered: false },
                    { id: 5, notebookId: '2', text: 'Proposal', def: '提案 (n.)', mastered: false }
                ],
                currentNotebookId: '1',
                currentNotebookName: '工作專用 (ABS)',
                searchQuery: '',
                viewMode: 'list', // 'list' or 'card'
                hideChinese: false,
                
                // Modal 狀態
                isModalOpen: false,
                isEditing: false,
                modalForm: { id: null, text: '', def: '', notebookId: '1' },

                // 卡片模式狀態
                flashcardQueue: [],
                currentCardIndex: 0,
                isFlipped: false,

                // 初始化
                init() {
                    this.$watch('currentNotebookId', (val) => {
                        this.currentNotebookName = val === '1' ? '工作專用 (ABS)' : '多益單字';
                        this.viewMode = 'list'; // 切換筆記本時回到列表
                    });
                },

                // 取得目前顯示的單字 (含搜尋與筆記本過濾)
                get filteredWords() {
                    return this.words.filter(w => {
                        const matchNotebook = w.notebookId === this.currentNotebookId;
                        const matchSearch = w.text.toLowerCase().includes(this.searchQuery.toLowerCase()) || 
                                          w.def.includes(this.searchQuery);
                        return matchNotebook && matchSearch;
                    });
                },

                // 取得當前卡片
                get currentCard() {
                    return this.flashcardQueue[this.currentCardIndex] || { text: '', def: '' };
                },

                // 功能：發音 (Text-to-Speech)
                speak(text) {
                    const utterance = new SpeechSynthesisUtterance(text);
                    utterance.lang = 'en-US';
                    speechSynthesis.speak(utterance);
                },

                // 功能：切換熟記狀態
                toggleMastered(id) {
                    const word = this.words.find(w => w.id === id);
                    if (word) word.mastered = !word.mastered;
                },

                // 功能：刪除單字
                deleteWord(id) {
                    if(confirm('確定要刪除這個單字嗎？')) {
                        this.words = this.words.filter(w => w.id !== id);
                    }
                },

                // 功能：開啟新增/編輯視窗
                openAddModal() {
                    this.isEditing = false;
                    this.modalForm = { id: Date.now(), text: '', def: '', notebookId: this.currentNotebookId };
                    this.isModalOpen = true;
                },
                editWord(word) {
                    this.isEditing = true;
                    // 複製物件避免直接修改
                    this.modalForm = JSON.parse(JSON.stringify(word));
                    this.isModalOpen = true;
                },
                saveWord() {
                    if (!this.modalForm.text || !this.modalForm.def) return;

                    if (this.isEditing) {
                        // 更新舊單字
                        const index = this.words.findIndex(w => w.id === this.modalForm.id);
                        if (index !== -1) this.words[index] = { ...this.modalForm };
                    } else {
                        // 新增新單字
                        this.words.push({ ...this.modalForm, mastered: false });
                    }
                    this.isModalOpen = false;
                    
                    // 如果在卡片模式下編輯，刷新隊列
                    if(this.viewMode === 'card') this.startFlashcard();
                },

                // 功能：更名筆記本
                renameNotebook() {
                    const newName = prompt('請輸入新的筆記本名稱：', this.currentNotebookName);
                    if (newName) this.currentNotebookName = newName;
                },

                // 卡片模式邏輯
                startFlashcard() {
                    this.viewMode = 'card';
                    // 載入當前過濾後的單字進入卡片隊列
                    this.flashcardQueue = JSON.parse(JSON.stringify(this.filteredWords));
                    this.currentCardIndex = 0;
                    this.isFlipped = false;
                },
                nextCard() {
                    this.isFlipped = false;
                    setTimeout(() => {
                        if (this.currentCardIndex < this.flashcardQueue.length - 1) {
                            this.currentCardIndex++;
                        } else {
                            this.currentCardIndex = 0; // 循環
                        }
                    }, 150);
                },
                prevCard() {
                    this.isFlipped = false;
                    setTimeout(() => {
                        if (this.currentCardIndex > 0) {
                            this.currentCardIndex--;
                        } else {
                            this.currentCardIndex = this.flashcardQueue.length - 1;
                        }
                    }, 150);
                },
                shuffleCards() {
                    // Fisher-Yates Shuffle
                    for (let i = this.flashcardQueue.length - 1; i > 0; i--) {
                        const j = Math.floor(Math.random() * (i + 1));
                        [this.flashcardQueue[i], this.flashcardQueue[j]] = [this.flashcardQueue[j], this.flashcardQueue[i]];
                    }
                    this.currentCardIndex = 0;
                    this.isFlipped = false;
                }
            }
        }
    </script>
</body>
</html>
