# Frontend TechCare

React/Vite, Tailwind CSS, Axios, React Router và Lucide. Xem [README chính](../README.md) để cài backend/model.

Chạy trong thư mục này:

```powershell
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
npm.cmd run lint
npm.cmd run build
```

API mặc định: `http://localhost:8000/api`; đổi bằng `VITE_API_BASE_URL` trước khi chạy Vite. Khi đổi cổng, cập nhật CORS backend.

Demo B0/B1/B2/P chỉ có trong development với `VITE_BENCHMARK_DEMO=true`; xem [hướng dẫn](../docs/LOCAL_BENCHMARK_DEMO.md). Production build không bật route demo.