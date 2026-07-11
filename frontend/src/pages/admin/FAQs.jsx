import React, { useState, useEffect } from 'react';
import axiosClient from '../../api/axiosClient';
import { Loader2, Plus, Edit, Trash2 } from 'lucide-react';

const FAQs = () => {
  const [faqs, setFaqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const fetchFaqs = async () => {
    try {
      const res = await axiosClient.get('/faqs');
      if (res.success) {
        setFaqs(res.data.items);
      } else {
        setError(res.message);
      }
    } catch (err) {
      setError('Lỗi khi tải danh sách FAQs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFaqs();
  }, []);

  const deleteFaq = async (id) => {
    if (!window.confirm('Bạn có chắc muốn xoá FAQ này?')) return;
    try {
      const res = await axiosClient.delete(`/faqs/${id}`);
      if (res.success) {
        setFaqs(faqs.filter(f => f.id !== id));
      }
    } catch (err) {
      alert('Không thể xoá FAQ');
    }
  };

  // Mock add/edit for now to keep it simple, or we can use a prompt
  const addFaq = async () => {
    const q = prompt('Nhập câu hỏi:');
    if (!q) return;
    const a = prompt('Nhập câu trả lời:');
    if (!a) return;
    
    try {
      const res = await axiosClient.post('/faqs', {
        question: q,
        answer: a,
        category: 'Chung'
      });
      if (res.success) {
        setFaqs([...faqs, res.data]);
      }
    } catch (err) {
      alert('Lỗi tạo FAQ');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-800">Danh sách câu hỏi thường gặp (FAQ)</h2>
        <button onClick={addFaq} className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 flex items-center gap-2 text-sm font-medium">
          <Plus className="w-4 h-4" /> Thêm FAQ
        </button>
      </div>

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
                  <th className="p-4 font-medium">Câu hỏi</th>
                  <th className="p-4 font-medium">Câu trả lời</th>
                  <th className="p-4 font-medium">Danh mục</th>
                  <th className="p-4 font-medium text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {faqs.map(f => (
                  <tr key={f.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 font-medium text-gray-900 max-w-xs">{f.question}</td>
                    <td className="p-4 text-sm text-gray-600 max-w-md truncate" title={f.answer}>{f.answer}</td>
                    <td className="p-4 text-sm text-gray-500">{f.category}</td>
                    <td className="p-4 text-right space-x-2">
                      <button onClick={() => alert('Tính năng Edit đang phát triển')} className="text-blue-600 hover:bg-blue-50 p-2 rounded-lg">
                        <Edit className="w-4 h-4" />
                      </button>
                      <button onClick={() => deleteFaq(f.id)} className="text-red-600 hover:bg-red-50 p-2 rounded-lg">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
                {faqs.length === 0 && (
                  <tr><td colSpan="4" className="p-8 text-center text-gray-500">Chưa có FAQ nào.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default FAQs;
