// Lấy các phần tử từ DOM
const chatForm = document.querySelector('form');
const chatInput = document.querySelector('input[type="text"]');
const chatArea = document.querySelector('.flex-1.p-6');
const submitBtn = document.querySelector('button[type="button"]');

// Lưu trữ session_id để duy trì ngữ cảnh trò chuyện
let currentSessionId = null;

// Hàm cuộn xuống cuối màn hình chat
function scrollToBottom() {
    chatArea.scrollTop = chatArea.scrollHeight;
}

// Hàm hiển thị tin nhắn lên giao diện
function appendMessage(role, text) {
    const msgDiv = document.createElement('div');
    
    if (role === 'user') {
        msgDiv.className = "flex gap-3 max-w-[85%] self-end flex-row-reverse";
        msgDiv.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 text-lg">👤</div>
            <div class="bg-blue-600 text-white px-4 py-3 rounded-2xl rounded-tr-sm shadow-sm whitespace-pre-wrap">${text}</div>
        `;
    } else {
        msgDiv.className = "flex gap-3 max-w-[85%]";
        // Sử dụng marked.parse() để chuyển đổi Markdown thành HTML
        const htmlContent = marked.parse(text);
        msgDiv.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 text-lg">🤖</div>
            <div class="bg-white border border-slate-200 text-slate-700 px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm markdown-content break-words">${htmlContent}</div>
        `;
    }
    
    chatArea.appendChild(msgDiv);
    scrollToBottom();
}

// Hàm tạo hiệu ứng "Đang gõ..."
function addLoadingIndicator() {
    const loadingDiv = document.createElement('div');
    loadingDiv.id = "loading-indicator";
    loadingDiv.className = "flex gap-3 max-w-[85%]";
    loadingDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">🤖</div>
        <div class="bg-white border border-slate-200 text-slate-500 px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-1">
            <span class="animate-bounce">●</span>
            <span class="animate-bounce" style="animation-delay: 0.2s">●</span>
            <span class="animate-bounce" style="animation-delay: 0.4s">●</span>
        </div>
    `;
    chatArea.appendChild(loadingDiv);
    scrollToBottom();
    return loadingDiv;
}

// Hàm xử lý gửi tin nhắn
async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    // 1. Lấy chế độ tìm kiếm được chọn (local hoặc global)
    const selectedMode = document.querySelector('input[name="search_mode"]:checked').value;

    // 2. Hiển thị tin nhắn user
    appendMessage('user', text);
    chatInput.value = '';
    
    // 3. Khóa input và hiện loading
    chatInput.disabled = true;
    submitBtn.disabled = true;
    const loadingNode = addLoadingIndicator();

    try {
        // 4. Gửi Request lên FastAPI Server
        const response = await fetch('http://localhost:8000/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: text,
                mode: selectedMode,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error("Lỗi kết nối tới Server");

        const data = await response.json();
        
        // Cập nhật session_id cho các câu hỏi tiếp theo
        currentSessionId = data.session_id;

        // 5. Xóa loading và hiển thị câu trả lời
        loadingNode.remove();
        appendMessage('bot', data.answer);

    } catch (error) {
        loadingNode.remove();
        appendMessage('bot', `❌ Lỗi: Không thể kết nối tới Server. Hãy đảm bảo bạn đã chạy 'uvicorn api:app --reload'.\nChi tiết: ${error.message}`);
    } finally {
        // Mở khóa input
        chatInput.disabled = false;
        submitBtn.disabled = false;
        chatInput.focus();
    }
}

// Gắn sự kiện click nút gửi và nhấn Enter
submitBtn.addEventListener('click', sendMessage);
chatForm.addEventListener('submit', (e) => {
    e.preventDefault(); // Ngăn form tải lại trang
    sendMessage();
});

chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        sendMessage();
    }
});