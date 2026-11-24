import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import ChatWidget from '../components/ChatWidget';

const MainLayout = () => {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/" className="text-xl font-bold text-primary-600">TechCare Electronics</Link>
            <nav className="hidden md:flex gap-4 text-gray-600 font-medium">
              <Link to="/products" className="hover:text-primary-600 transition-colors">Sản phẩm</Link>
              <Link to="/faqs" className="hover:text-primary-600 transition-colors">Hỏi đáp</Link>
            </nav>
          </div>
          <div>
            <Link to="/admin" className="text-sm font-medium text-gray-500 hover:text-gray-900">Admin</Link>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      <footer className="bg-white border-t py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 text-center text-gray-500 text-sm">
          &copy; 2026 NCKH Chatbot Project. All rights reserved.
        </div>
      </footer>
      
      <ChatWidget />
    </div>
  );
};

export default MainLayout;
