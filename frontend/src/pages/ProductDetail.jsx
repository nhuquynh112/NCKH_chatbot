import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Loader, ArrowLeft, MessageSquareText, ShieldCheck, Tag } from 'lucide-react';
import axiosClient from '../api/axiosClient';

const ProductDetail = () => {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        const res = await axiosClient.get(`/products/${id}`);
        if (res.success) {
          setProduct(res.data);
        } else {
          setError(res.message);
        }
      } catch (err) {
        setError('Không thể tải thông tin sản phẩm');
      } finally {
        setLoading(false);
      }
    };
    fetchProduct();
  }, [id]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="text-center py-12 space-y-4">
        <div className="text-red-500">{error || 'Sản phẩm không tồn tại'}</div>
        <Link to="/products" className="text-primary-600 hover:underline flex items-center justify-center gap-2">
          <ArrowLeft className="w-4 h-4" /> Quay lại danh sách
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-500">
      <Link to="/products" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">
        <ArrowLeft className="w-4 h-4 mr-1" /> Quay lại
      </Link>

      <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-0">
          {/* Cột trái: Ảnh */}
          <div className="bg-gray-50 p-8 flex items-center justify-center border-b md:border-b-0 md:border-r border-gray-100">
            {product.image_url ? (
              <img src={product.image_url} alt={product.name} className="max-w-full h-auto object-contain drop-shadow-xl rounded-xl" />
            ) : (
              <div className="text-gray-400">Chưa có hình ảnh</div>
            )}
          </div>
          
          {/* Cột phải: Thông tin */}
          <div className="p-8 lg:p-12 flex flex-col justify-center">
            <div className="flex items-center gap-2 mb-4">
              <span className="px-3 py-1 bg-primary-50 text-primary-700 text-xs font-bold rounded-full uppercase tracking-wider">
                {product.category}
              </span>
              {product.brand && (
                <span className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-bold rounded-full flex items-center gap-1">
                  <Tag className="w-3 h-3" /> {product.brand}
                </span>
              )}
            </div>
            
            <h1 className="text-3xl lg:text-4xl font-extrabold text-gray-900 mb-4 leading-tight">
              {product.name}
            </h1>
            
            <div className="text-3xl font-extrabold text-primary-600 mb-6">
              {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(product.price)}
            </div>

            <p className="text-gray-600 mb-8 leading-relaxed whitespace-pre-line">
              {product.description}
            </p>

            <div className="flex items-center gap-3 text-sm text-gray-600 mb-8 p-4 bg-gray-50 rounded-xl border border-gray-100">
              <ShieldCheck className="w-5 h-5 text-green-500" />
              <span>Bảo hành chính hãng: <strong className="text-gray-900">{product.warranty_months} tháng</strong></span>
            </div>

            {/* Nút Chat AI (Sẽ kích hoạt Widget ở Giai đoạn 3) */}
            <button className="w-full sm:w-auto px-8 py-4 bg-gray-900 hover:bg-gray-800 text-white font-bold rounded-xl shadow-lg hover:shadow-xl transition-all flex items-center justify-center gap-2 transform hover:-translate-y-0.5">
              <MessageSquareText className="w-5 h-5" />
              Hỏi AI về sản phẩm này
            </button>
          </div>
        </div>
      </div>

      {/* Thông số kỹ thuật */}
      {product.specifications && Object.keys(product.specifications).length > 0 && (
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-8 lg:p-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Thông số kỹ thuật</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
            {Object.entries(product.specifications).map(([key, value]) => (
              <div key={key} className="flex justify-between py-3 border-b border-gray-100 last:border-0">
                <span className="text-gray-500 font-medium">{key}</span>
                <span className="text-gray-900 font-semibold text-right">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductDetail;
