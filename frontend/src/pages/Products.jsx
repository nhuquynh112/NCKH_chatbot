import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ImageOff, Search, Loader } from 'lucide-react';
import axiosClient from '../api/axiosClient';

const ProductImage = ({ product }) => {
  const [failed, setFailed] = useState(false);
  const showImage = product.image_url && !failed;

  return (
    <div className="h-56 bg-gray-50 flex items-center justify-center overflow-hidden">
      {showImage ? (
        <img
          src={product.image_url}
          alt={product.name}
          loading="lazy"
          onError={() => setFailed(true)}
          className="h-full w-full object-contain p-5"
        />
      ) : (
        <div className="flex flex-col items-center justify-center gap-2 text-gray-400">
          <ImageOff className="h-8 w-8" />
          <span className="text-sm font-medium">Dang cap nhat anh</span>
        </div>
      )}
    </div>
  );
};

const Products = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  
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

  // Debounce logic: Tự động cập nhật debouncedSearch sau 400ms khi ngừng gõ
  useEffect(() => {
    const handler = setTimeout(() => {
      if (search !== debouncedSearch) {
        setDebouncedSearch(search);
        setPage(1); // Quay về trang 1 khi tìm kiếm mới
      }
    }, 400);
    return () => clearTimeout(handler);
  }, [search, debouncedSearch]);

  // Fetch dữ liệu mỗi khi page hoặc từ khóa tìm kiếm (đã debounce) thay đổi
  useEffect(() => {
    fetchProducts(page, debouncedSearch);
  }, [page, debouncedSearch]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (search !== debouncedSearch) {
      setDebouncedSearch(search);
      setPage(1);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <h1 className="text-3xl font-bold text-gray-900">Khám phá Sản phẩm</h1>
        
        {/* Search Bar */}
        <form onSubmit={handleSearch} className="relative w-full md:w-96 flex items-center">
          <input 
            type="text" 
            placeholder="Tìm kiếm sản phẩm..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-4 pr-12 py-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-primary-500 shadow-sm transition-shadow"
          />
          <button 
            type="submit" 
            className="absolute right-2 p-1.5 bg-primary-50 text-primary-600 hover:bg-primary-100 rounded-full transition-colors"
            title="Tìm kiếm"
          >
            <Search className="w-4 h-4" />
          </button>
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
                <ProductImage product={p} />
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
