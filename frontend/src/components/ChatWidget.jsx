import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Loader2, User, AlertCircle, Bot } from 'lucide-react';
import axiosClient from '../api/axiosClient';
import { useChat } from '../contexts/ChatContext';

const ChatWidget = () => {
  const { 
    visitorId, sessionId, messages, isTyping, setIsTyping, 
    changeSession, addTempMessage, refreshSessions
  } = useChat();
  
  const [isOpen, setIsOpen] = useState(false);
  
  // States cho Pre-chat Form
  const [customerName, setCustomerName] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [isStartingSession, setIsStartingSession] = useState(false);
  const [error, setError] = useState(null);

  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen, isTyping]);

  const startSession = async (e) => {
    e.preventDefault();
    setIsStartingSession(true);
    setError(null);
    try {
      const res = await axiosClient.post('/chat/sessions', {
        visitor_id: visitorId,
        customer_name: customerName || undefined,
        customer_email: customerEmail || undefined,
      });
      if (res.success) {
        changeSession(res.data.id);
        refreshSessions();
        addTempMessage({
          id: 'welcome',
          role: 'assistant',
          content: 'Xin chào! Tôi là trợ lý ảo AI. Tôi có thể giúp gì cho bạn hôm nay?',
          created_at: new Date().toISOString()
        });
      }
    } catch (err) {
      setError('Không thể bắt đầu phiên chat. Vui lòng thử lại.');
    } finally {
      setIsStartingSession(false);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || !sessionId) return;

    const userText = inputValue.trim();
    setInputValue('');
    setError(null);

    const tempUserMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: userText,
      created_at: new Date().toISOString()
    };
    addTempMessage(tempUserMsg);
    setIsTyping(true);

    try {
      const res = await axiosClient.post('/chat/messages', {
        session_id: sessionId,
        content: userText
      });

      if (res.success) {
        addTempMessage(res.data.message);
        
        // Sinh tiêu đề nếu là tin nhắn đầu (tiêu đề vẫn đang là "New Chat")
        const currentSessionObj = sessions.find(s => s.id === sessionId);
        if (currentSessionObj && currentSessionObj.title === "New Chat") {
           axiosClient.post(`/chat/sessions/${sessionId}/generate-title`, { message: userText })
             .then(() => refreshSessions())
             .catch(err => console.error("Failed to generate title", err));
        } else {
           refreshSessions();
        }

        if (res.data.ticket_created) {
          addTempMessage({
            id: Date.now().toString() + '-sys',
            role: 'system',
            content: '⚠️ Chú ý: Hệ thống đã tự động ghi nhận câu hỏi của bạn và chuyển cho nhân viên hỗ trợ thực. Chúng tôi sẽ phản hồi sớm nhất.',
            created_at: new Date().toISOString()
          });
        }
      }
    } catch (err) {
      setError('Lỗi kết nối. Không thể gửi tin nhắn.');
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
      {/* Chat Window */}
      {isOpen && (
        <div className="bg-white w-[350px] sm:w-[400px] h-[500px] max-h-[80vh] rounded-2xl shadow-2xl border border-gray-100 flex flex-col overflow-hidden mb-4 animate-in slide-in-from-bottom-5 duration-300">
          
          {/* Header */}
          <div className="bg-primary-600 text-white p-4 flex justify-between items-center shadow-md z-10">
            <div className="flex items-center gap-2">
              <Bot className="w-6 h-6" />
              <div>
                <h3 className="font-bold">Trợ lý AI</h3>
                <p className="text-xs text-primary-100">Luôn sẵn sàng hỗ trợ</p>
              </div>
            </div>
            <button onClick={() => setIsOpen(false)} className="text-white hover:bg-primary-700 p-1 rounded-full transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 bg-gray-50 overflow-y-auto p-4 flex flex-col gap-4">
            {!sessionId ? (
              <form onSubmit={startSession} className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 space-y-4">
                <h4 className="font-bold text-gray-800 text-center mb-2">Bắt đầu trò chuyện</h4>
                <p className="text-sm text-gray-500 text-center mb-4">Vui lòng để lại thông tin để chúng tôi hỗ trợ tốt hơn (Không bắt buộc)</p>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Họ tên</label>
                  <input type="text" value={customerName} onChange={e => setCustomerName(e.target.value)} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:outline-none text-sm" placeholder="Nguyễn Văn A" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Email / Số điện thoại</label>
                  <input type="text" value={customerEmail} onChange={e => setCustomerEmail(e.target.value)} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:outline-none text-sm" placeholder="email@example.com" />
                </div>
                {error && <div className="text-red-500 text-xs text-center">{error}</div>}
                <button type="submit" disabled={isStartingSession} className="w-full bg-primary-600 text-white font-medium py-2 rounded-lg hover:bg-primary-700 flex justify-center items-center gap-2">
                  {isStartingSession ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Bắt đầu chat'}
                </button>
              </form>
            ) : (
              <>
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : msg.role === 'system' ? 'justify-center' : 'justify-start'}`}>
                    {msg.role === 'system' ? (
                      <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs px-3 py-2 rounded-lg my-2 max-w-[90%] text-center shadow-sm">
                        {msg.content}
                      </div>
                    ) : (
                      <div className={`max-w-[80%] rounded-2xl px-4 py-2 shadow-sm ${msg.role === 'user' ? 'bg-primary-600 text-white rounded-tr-sm' : 'bg-white border border-gray-100 text-gray-800 rounded-tl-sm'}`}>
                        <p className="text-sm whitespace-pre-line">{msg.content}</p>
                        <div className={`text-[10px] mt-1 ${msg.role === 'user' ? 'text-primary-200 text-right' : 'text-gray-400'}`}>
                          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                
                {isTyping && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm flex items-center gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Footer Input */}
          {sessionId && (
            <div className="bg-white p-3 border-t border-gray-100 flex flex-col gap-2">
              <a href="/faqs" className="text-[11px] text-center text-primary-600 hover:underline">
                Mở rộng cửa sổ Hỏi Đáp & Xem lịch sử
              </a>
              {error && <div className="text-red-500 text-xs px-2 flex items-center gap-1"><AlertCircle className="w-3 h-3"/> {error}</div>}
              <form onSubmit={sendMessage} className="relative flex items-center">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Nhập tin nhắn..."
                  className="w-full bg-gray-50 border-none rounded-full py-2.5 pl-4 pr-12 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
                  disabled={isTyping}
                />
                <button 
                  type="submit" 
                  disabled={!inputValue.trim() || isTyping}
                  className="absolute right-1 w-8 h-8 flex items-center justify-center bg-primary-600 text-white rounded-full hover:bg-primary-700 disabled:opacity-50 disabled:hover:bg-primary-600 transition-colors"
                >
                  <Send className="w-4 h-4 ml-0.5" />
                </button>
              </form>
            </div>
          )}
        </div>
      )}

      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-14 h-14 bg-primary-600 hover:bg-primary-700 text-white rounded-full shadow-xl hover:shadow-2xl flex items-center justify-center transition-transform hover:scale-105 active:scale-95"
      >
        {isOpen ? <X className="w-6 h-6" /> : <MessageSquare className="w-6 h-6" />}
      </button>
    </div>
  );
};

export default ChatWidget;
