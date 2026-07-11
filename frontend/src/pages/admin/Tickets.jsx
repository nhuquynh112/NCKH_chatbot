import React, { useState, useEffect } from 'react';
import axiosClient from '../../api/axiosClient';
import { Loader2, MessageSquare, CheckCircle, Clock } from 'lucide-react';

const Tickets = () => {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Chat History Modal State
  const [chatHistory, setChatHistory] = useState([]);
  const [loadingChat, setLoadingChat] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState(null);

  const fetchTickets = async () => {
    try {
      const res = await axiosClient.get('/tickets');
      if (res.success) {
        setTickets(res.data.items);
      } else {
        setError(res.message);
      }
    } catch (err) {
      setError('Lỗi khi tải danh sách tickets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  const updateStatus = async (id, newStatus) => {
    try {
      const res = await axiosClient.patch(`/tickets/${id}`, { status: newStatus });
      if (res.success) {
        // Cập nhật local state
        setTickets(tickets.map(t => t.id === id ? { ...t, status: newStatus } : t));
      }
    } catch (err) {
      alert('Không thể cập nhật trạng thái');
    }
  };

  const viewChatHistory = async (sessionId) => {
    setSelectedSessionId(sessionId);
    setLoadingChat(true);
    try {
      const res = await axiosClient.get(`/chat/sessions/${sessionId}/messages`);
      if (res.success) {
        setChatHistory(res.data.items);
      }
    } catch (err) {
      alert('Lỗi tải lịch sử chat');
    } finally {
      setLoadingChat(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex justify-center p-12"><Loader2 className="w-8 h-8 animate-spin text-primary-500" /></div>
        ) : error ? (
          <div className="p-8 text-red-500 text-center">{error}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-sm text-gray-500 uppercase tracking-wider">
                  <th className="p-4 font-medium">ID</th>
                  <th className="p-4 font-medium">Khách hàng</th>
                  <th className="p-4 font-medium">Vấn đề</th>
                  <th className="p-4 font-medium">Trạng thái</th>
                  <th className="p-4 font-medium text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {tickets.map(t => (
                  <tr key={t.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm text-gray-500">#{t.id}</td>
                    <td className="p-4">
                      <div className="font-medium text-gray-900">{t.customer_name || 'Khách vãng lai'}</div>
                      <div className="text-sm text-gray-500">{t.customer_email || 'Không có email'}</div>
                    </td>
                    <td className="p-4 text-sm max-w-xs truncate text-gray-700" title={t.issue}>{t.issue}</td>
                    <td className="p-4">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                        t.status === 'pending' ? 'bg-amber-100 text-amber-800' :
                        t.status === 'resolved' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {t.status === 'pending' ? <Clock className="w-3 h-3" /> : <CheckCircle className="w-3 h-3" />}
                        {t.status}
                      </span>
                    </td>
                    <td className="p-4 text-right space-x-2">
                      <button 
                        onClick={() => viewChatHistory(t.session_id)}
                        className="text-primary-600 hover:bg-primary-50 p-2 rounded-lg transition-colors inline-flex items-center"
                        title="Xem lịch sử chat"
                      >
                        <MessageSquare className="w-4 h-4" />
                      </button>
                      {t.status === 'pending' && (
                        <button 
                          onClick={() => updateStatus(t.id, 'resolved')}
                          className="text-green-600 hover:bg-green-50 px-3 py-1.5 rounded-lg border border-green-200 text-sm font-medium transition-colors"
                        >
                          Hoàn tất
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {tickets.length === 0 && (
                  <tr><td colSpan="5" className="p-8 text-center text-gray-500">Không có ticket nào.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Chat History Modal */}
      {selectedSessionId && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
              <h3 className="font-bold text-gray-800">Lịch sử hội thoại</h3>
              <button onClick={() => setSelectedSessionId(null)} className="text-gray-500 hover:text-gray-900">Đóng</button>
            </div>
            <div className="p-4 flex-1 overflow-y-auto space-y-4 bg-gray-50">
              {loadingChat ? (
                <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-primary-500" /></div>
              ) : (
                chatHistory.map(msg => (
                  <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <span className="text-[10px] text-gray-400 mb-1">{msg.role.toUpperCase()} - {new Date(msg.created_at).toLocaleString()}</span>
                    <div className={`px-4 py-2 rounded-2xl max-w-[80%] ${msg.role === 'user' ? 'bg-primary-100 text-primary-900' : 'bg-white border text-gray-800'}`}>
                      {msg.content}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Tickets;
