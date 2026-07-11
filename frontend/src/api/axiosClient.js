import axios from 'axios';

const axiosClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor cho Request
axiosClient.interceptors.request.use(
  (config) => {
    // Nếu có auth token, gắn vào đây
    const token = localStorage.getItem('admin_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor cho Response
axiosClient.interceptors.response.use(
  (response) => {
    if (response && response.data) {
      // Backend của chúng ta trả về { success, message, data }
      return response.data;
    }
    return response;
  },
  (error) => {
    // Xử lý lỗi tập trung
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('admin_token');
      // Chuyển hướng về trang đăng nhập nếu bị lỗi auth (ngoại trừ đang ở trang login)
      if (window.location.pathname !== '/admin/login') {
        window.location.href = '/admin/login';
      }
    }
    console.error('API Error:', error.response || error.message);
    return Promise.reject(error);
  }
);

export default axiosClient;
