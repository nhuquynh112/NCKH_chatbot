import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Products from './pages/Products';
import ProductDetail from './pages/ProductDetail';
import AdminLayout from './pages/admin/AdminLayout';
import Tickets from './pages/admin/Tickets';
import FAQs from './pages/admin/FAQs';
import Login from './pages/admin/Login';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/products" replace />} />
          <Route path="products" element={<Products />} />
          <Route path="products/:id" element={<ProductDetail />} />
        </Route>
        
        {/* Admin Routes */}
        <Route path="/admin/login" element={<Login />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="/admin/tickets" replace />} />
          <Route path="tickets" element={<Tickets />} />
          <Route path="faqs" element={<FAQs />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
