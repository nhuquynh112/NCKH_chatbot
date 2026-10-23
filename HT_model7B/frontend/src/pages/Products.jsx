import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Search, Loader, LayoutGrid, Smartphone, Laptop, Tablet, PcCase, Monitor,
  Headphones, Mic, Watch, Shield, BatteryCharging, Keyboard, Mouse, PlugZap,
} from 'lucide-react';
import axiosClient from '../api/axiosClient';

const CATEGORIES = [
  { value: '', label: 'Tất cả sản phẩm', icon: LayoutGrid },
  { value: 'Điện thoại', label: 'Điện thoại', icon: Smartphone },
  { value: 'Laptop', label: 'Laptop', icon: Laptop },
  { value: 'Máy tính bảng', label: 'Máy tính bảng', icon: Tablet },
  { value: 'PC', label: 'PC', icon: PcCase },
  { value: 'Màn hình', label: 'Màn hình', icon: Monitor },
  { value: 'Tai nghe', label: 'Tai nghe', icon: Headphones },
  { value: 'Microphone', label: 'Microphone', icon: Mic },
  { value: 'Đồng hồ thông minh', label: 'Đồng hồ', icon: Watch },
  { value: 'Dán màn hình', label: 'Dán màn hình', icon: Shield },
  { value: 'Trạm sạc', label: 'Trạm sạc', icon: PlugZap },
  { value: 'Sạc dự phòng', label: 'Sạc dự phòng', icon: BatteryCharging },
  { value: 'Bàn phím', label: 'Bàn phím', icon: Keyboard },
  { value: 'Chuột', label: 'Chuột', icon: Mouse },
];

const Products = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [submittedSearch, setSubmittedSearch] = useState('');
  const [category, setCategory] = useState('');
  
  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    let active = true;
    const fetchProducts = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await axiosClient.get('/products', {
          params: {
            page,
            page_size: 8,
            search: submittedSearch || undefined,
            category: category || undefined,
            is_active: true,
          },
        });
        if (!active) return;
        if (res.success) {
          setProducts(res.data.items);
          setTotalPages(res.data.total_pages || 1);
          setTotal(res.data.total);
        } else {
          setError(res.message);
        }
      } catch (err) {
        if (!active) return;
        console.error(err);
        setError('Lỗi khi tải danh sách sản phẩm');
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchProducts();
    return () => { active = false; };
  }, [page, submittedSearch, category]);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    setSubmittedSearch(search.trim());
  };

  const handleCategory = (value) => {
    setCategory(value);
    setPage(1);
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
            aria-label="Tìm kiếm sản phẩm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-primary-500 shadow-sm transition-shadow"
          />
          <Search className="absolute left-3 top-2.5 text-gray-400 w-5 h-5" />
          <button type="submit" className="hidden">Tìm</button>
        </form>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="min-w-0 rounded-2xl border border-gray-100 bg-white p-3 shadow-sm lg:sticky lg:top-24">
          <h2 className="px-3 pt-2 pb-4 text-sm font-bold uppercase tracking-wide text-gray-900">Danh mục</h2>
          <nav aria-label="Danh mục sản phẩm" className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
            {CATEGORIES.map(({ value, label, icon: Icon }) => (
              <button
                key={value || 'all'}
                type="button"
                aria-pressed={category === value}
                onClick={() => handleCategory(value)}
                className={`flex shrink-0 items-center gap-3 whitespace-nowrap rounded-xl px-3 py-3 text-left text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 lg:w-full ${category === value ? 'bg-primary-600 text-white shadow-sm' : 'text-gray-600 hover:bg-primary-50 hover:text-primary-600'}`}
              >
                <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                {label}
              </button>
            ))}
          </nav>
        </aside>

        <section aria-label="Danh sách sản phẩm" className="min-w-0">
          <div className="mb-5 flex items-center justify-between gap-3">
            <h2 className="text-xl font-bold text-gray-900">{category || 'Tất cả sản phẩm'}</h2>
            {!loading && !error && <span className="text-sm text-gray-500">{total} sản phẩm</span>}
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
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-5">
            {products.map((p) => (
              <Link to={`/products/${p.id}`} key={p.id} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1 group">
                <div className="aspect-w-1 aspect-h-1 bg-gray-100 relative">
                  {p.image_url ? (
                    <img src={p.image_url} alt={p.name} className="object-contain bg-white w-full h-48 p-3" loading="lazy" />
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
        </section>
      </div>
    </div>
  );
};

export default Products;
