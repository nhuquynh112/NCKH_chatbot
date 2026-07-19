import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../contexts/ChatContext';
import { Bot, User, Send, Loader2, Plus, MessageSquare, Trash2, Edit2, Check, X } from 'lucide-react';
import axiosClient from '../api/axiosClient';

const QnAPage = () => {
  const { 
    visitorId, sessionId, sessions, messages, isTyping, setIsTyping,
    changeSession, createNewSession, addTempMessage, refreshSessions
  } = useChat();

  const [inputValue, setInputValue] = useState('');
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const userText = inputValue.trim();
    setInputValue('');

    // Nếu chưa có session, tạo session mới trước khi gửi tin nhắn
    let currentSession = sessionId;
    if (!currentSession) {
      try {
        const res = await axiosClient.post('/chat/sessions', { visitor_id: visitorId });
        if (res.success) {
          currentSession = res.data.id;
          changeSession(currentSession); // Sẽ tự fetch lại sau
        } else {
          return; // Lỗi tạo session
        }
      } catch (err) {
        console.error("Failed to start session:", err);
        return;
      }
    }

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
        session_id: currentSession,
        content: userText
      });

      if (res.success) {
        addTempMessage(res.data.message);
        
        // Cập nhật title tự động nếu là tin nhắn đầu tiên (title đang là "New Chat")
        const currentSessionObj = sessions.find(s => s.id === currentSession);
        if (currentSessionObj && currentSessionObj.title === "New Chat") {
           try {
             await axiosClient.post(`/chat/sessions/${currentSession}/generate-title`, { message: userText });
           } catch (err) {
             console.error("Failed to generate title", err);
           }
        }
        refreshSessions(); // Luôn refresh để đưa lên đầu hoặc cập nhật title mới
      }
    } catch (err) {
      console.error("Failed to send message", err);
    } finally {
      setIsTyping(false);
    }
  };

  const handleDeleteSession = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("Bạn có chắc muốn xóa cuộc hội thoại này?")) return;
    try {
      await axiosClient.delete(`/chat/sessions/${id}`);
      refreshSessions();
      if (sessionId === id) createNewSession();
    } catch (err) {
      console.error("Error deleting session", err);
    }
  };

  const startEditTitle = (e, session) => {
    e.stopPropagation();
    setEditingSessionId(session.id);
    setEditTitle(session.title);
  };

  const handleUpdateTitle = async (id, newTitle) => {
    try {
      await axiosClient.patch(`/chat/sessions/${id}`, { title: newTitle });
      refreshSessions();
    } catch (err) {
      console.error("Error updating title", err);
    } finally {
      setEditingSessionId(null);
    }
  };

  return (
    <div className="flex h-[calc(100vh-64px)] max-h-[800px] bg-white border border-gray-200 rounded-xl overflow-hidden mx-4 my-6 shadow-sm">
      
      {/* Sidebar - Lịch sử */}
      <div className="w-1/4 min-w-[250px] bg-gray-50 border-r border-gray-200 flex flex-col">
        <div className="p-4">
          <button 
            onClick={createNewSession}
            className="w-full flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-700 text-white font-medium py-2.5 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" /> Đoạn chat mới
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1">
          <div className="text-xs font-semibold text-gray-500 px-3 py-2 uppercase tracking-wider">Lịch sử trò chuyện</div>
          {sessions.length === 0 ? (
            <p className="text-sm text-gray-400 px-3 italic">Chưa có lịch sử</p>
          ) : (
            sessions.map((s) => (
              <div 
                key={s.id} 
                onClick={() => changeSession(s.id)}
                className={`group relative flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors
                  ${sessionId === s.id ? 'bg-primary-50 text-primary-900' : 'hover:bg-gray-100 text-gray-700'}
                `}
              >
                {editingSessionId === s.id ? (
                  <div className="flex w-full items-center gap-1" onClick={e => e.stopPropagation()}>
                    <input 
                      autoFocus
                      className="flex-1 px-2 py-1 text-sm border rounded"
                      value={editTitle}
                      onChange={e => setEditTitle(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleUpdateTitle(s.id, editTitle)}
                    />
                    <button onClick={() => handleUpdateTitle(s.id, editTitle)} className="text-green-600 hover:bg-green-100 p-1 rounded"><Check className="w-3.5 h-3.5"/></button>
                    <button onClick={() => setEditingSessionId(null)} className="text-red-500 hover:bg-red-100 p-1 rounded"><X className="w-3.5 h-3.5"/></button>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2 overflow-hidden">
                      <MessageSquare className={`w-4 h-4 shrink-0 ${sessionId === s.id ? 'text-primary-600' : 'text-gray-400'}`} />
                      <span className="text-sm font-medium truncate">{s.title || 'New Chat'}</span>
                    </div>
                    
                    {/* Hành động (Sửa/Xóa) chỉ hiện khi hover */}
                    <div className="hidden group-hover:flex items-center gap-1 shrink-0 bg-gradient-to-l from-gray-100 pl-2">
                      <button onClick={(e) => startEditTitle(e, s)} className="p-1 text-gray-400 hover:text-blue-500 transition-colors"><Edit2 className="w-3.5 h-3.5"/></button>
                      <button onClick={(e) => handleDeleteSession(e, s.id)} className="p-1 text-gray-400 hover:text-red-500 transition-colors"><Trash2 className="w-3.5 h-3.5"/></button>
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white">
        {/* Header */}
        <div className="h-16 border-b border-gray-100 flex items-center px-6">
          <h2 className="text-lg font-bold text-gray-800">
            {sessionId ? (sessions.find(s => s.id === sessionId)?.title || 'Đang trò chuyện...') : 'Bắt đầu một cuộc trò chuyện mới'}
          </h2>
        </div>

        {/* Messages Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-400">
              <Bot className="w-16 h-16 mb-4 text-gray-200" />
              <h3 className="text-xl font-medium text-gray-600">Trợ lý ảo TechCare xin chào!</h3>
              <p className="mt-2 text-sm text-center max-w-md">Bạn có thể hỏi tôi về các sản phẩm, chính sách bảo hành, hoặc bất cứ thắc mắc nào về dịch vụ của chúng tôi.</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-primary-100 text-primary-700' : 'bg-green-100 text-green-700'}`}>
                  {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                </div>
                <div className={`max-w-[75%] rounded-2xl p-4 shadow-sm ${msg.role === 'user' ? 'bg-primary-600 text-white rounded-tr-sm' : 'bg-gray-50 border border-gray-100 text-gray-800 rounded-tl-sm'}`}>
                  <p className="text-sm whitespace-pre-line leading-relaxed">{msg.content}</p>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs font-semibold text-gray-500 mb-1">Nguồn tham khảo:</p>
                      <ul className="text-xs text-gray-400 list-disc pl-4 space-y-0.5">
                        {msg.sources.map((src, idx) => (
                          <li key={idx}>{src.source}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {isTyping && (
             <div className="flex gap-4">
                <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                  <Bot className="w-5 h-5 text-green-700" />
                </div>
                <div className="bg-gray-50 border border-gray-100 rounded-2xl rounded-tl-sm px-5 py-4 flex items-center gap-1.5">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
             </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-white border-t border-gray-100">
          <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto relative flex items-center shadow-sm border border-gray-300 rounded-xl overflow-hidden focus-within:ring-2 focus-within:ring-primary-500 focus-within:border-primary-500 transition-all">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Nhập câu hỏi của bạn vào đây..."
              className="w-full bg-transparent border-none py-3.5 pl-5 pr-14 text-sm focus:outline-none focus:ring-0"
              disabled={isTyping}
            />
            <button 
              type="submit" 
              disabled={!inputValue.trim() || isTyping}
              className="absolute right-2 w-10 h-10 flex items-center justify-center bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:hover:bg-primary-600 transition-colors"
            >
              <Send className="w-5 h-5 ml-0.5" />
            </button>
          </form>
          <div className="text-center mt-2">
            <span className="text-[11px] text-gray-400">Trợ lý AI có thể cung cấp thông tin không chính xác. Hãy kiểm tra lại các thông tin quan trọng.</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QnAPage;
