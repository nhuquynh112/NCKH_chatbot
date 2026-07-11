import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, Loader } from 'lucide-react';
import axiosClient from '../api/axiosClient';

const Products = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  
  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchProducts = async (currentPage, searchQuery) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axiosClient.get('/products', {
        params: {
          page: currentPage,
          page_size: 8,
          search: searchQuery || undefined,
          is_active: true
        }
      });
      if (res.success) {
        setProducts(res.data.items);
        setTotalPages(res.data.total_pages || 1);
      } else {
        setError(res.message);
      }
    } catch (err) {
      setError('Lỗi khi tải danh sách sản phẩm');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts(page, search);
  }, [page]); // Chỉ tự động fetch khi đổi trang

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    fetchProducts(1, search);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <h1 className="text-3xl font-bold text-gray-900">Khám phá Sản phẩm</h1>
        
        {/* Search Bar */}
        <form onSubmit={handleSearch} className="relative w-full md:w-96">
          <input 
            type="text" 
            placeholder="Tìm kiếm sản phẩm..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-primary-500 shadow-sm transition-shadow"
          />
          <Search className="absolute left-3 top-2.5 text-gray-400 w-5 h-5" />
          <button type="submit" className="hidden">Tìm</button>
        </form>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Loader className="w-8 h-8 text-primary-500 animate-spin" />
        </div>
      ) : error ? (
        <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
      ) : products.length === 0 ? (
        <div className="text-center text-gray-500 py-12">Không tìm thấy sản phẩm nào.</div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {products.map((p) => (
              <Link to={`/products/${p.id}`} key={p.id} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1 group">
                <div className="aspect-w-1 aspect-h-1 bg-gray-100 relative">
                  {p.image_url ? (
                    <img src={p.image_url} alt={p.name} className="object-cover w-full h-48" />
                  ) : (
                    <div className="w-full h-48 flex items-center justify-center text-gray-400 bg-gray-50">
                      No Image
                    </div>
                  )}
                </div>
                <div className="p-5">
                  <div className="text-xs font-semibold text-primary-600 mb-1 uppercase tracking-wider">{p.category}</div>
                  <h3 className="text-lg font-bold text-gray-900 line-clamp-2 mb-2 group-hover:text-primary-600 transition-colors">{p.name}</h3>
                  <div className="text-xl font-extrabold text-gray-900">
                    {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(p.price)}
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-2 mt-8">
              <button 
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
                className="px-4 py-2 rounded-lg border border-gray-300 disabled:opacity-50 hover:bg-gray-50 transition-colors"
              >
                Trước
              </button>
              <span className="text-gray-600 font-medium">Trang {page} / {totalPages}</span>
              <button 
                disabled={page === totalPages}
                onClick={() => setPage(p => p + 1)}
                className="px-4 py-2 rounded-lg border border-gray-300 disabled:opacity-50 hover:bg-gray-50 transition-colors"
              >
                Sau
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Products;
