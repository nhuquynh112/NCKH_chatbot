import React, { useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Ticket, HelpCircle, ArrowLeft, LogOut } from 'lucide-react';

const AdminLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();

  // Kiểm tra token
  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (!token) {
      navigate('/admin/login');
    }
  }, [navigate, location.pathname]);

  const menuItems = [
    { path: '/admin/tickets', label: 'Quản lý Tickets', icon: Ticket },
    { path: '/admin/faqs', label: 'Quản lý FAQs', icon: HelpCircle },
  ];

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    navigate('/admin/login');
  };

  return (
    <div className="min-h-screen bg-gray-100 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="p-6">
          <h2 className="text-2xl font-bold text-white">Admin Panel</h2>
        </div>
        <nav className="flex-1 px-4 space-y-2">
          {menuItems.map((item) => {
            const isActive = location.pathname.includes(item.path);
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive ? 'bg-primary-600 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-gray-800 space-y-2">
          <button onClick={handleLogout} className="w-full flex items-center gap-2 text-red-400 hover:text-red-300 hover:bg-gray-800 px-4 py-2 rounded-lg transition-colors">
            <LogOut className="w-4 h-4" /> Đăng xuất
          </button>
          <Link to="/" className="flex items-center gap-2 text-gray-400 hover:text-white hover:bg-gray-800 px-4 py-2 rounded-lg transition-colors">
            <ArrowLeft className="w-4 h-4" /> Về trang khách
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <header className="bg-white shadow-sm h-16 flex items-center px-8">
          <h1 className="text-xl font-semibold text-gray-800">
            {menuItems.find(m => location.pathname.includes(m.path))?.label || 'Dashboard'}
          </h1>
        </header>
        <div className="flex-1 overflow-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default AdminLayout;
