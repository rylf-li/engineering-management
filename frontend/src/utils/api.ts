import axios from 'axios';

const TOKEN_KEY = 'jcgs_mgmt_token';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// 自动携带 JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (err) => Promise.reject(err)
);

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    // Token 过期 → 清除 token 并跳转登录页
    if (err.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      delete api.defaults.headers.common['Authorization'];
      // 避免循环重定向
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      return Promise.reject(new Error('登录已过期，请重新登录'));
    }
    const detail = err.response?.data?.detail;
    let msg = err.message || '请求失败';
    if (Array.isArray(detail)) {
      msg = detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
    } else if (typeof detail === 'string') {
      msg = detail;
    } else if (detail) {
      msg = JSON.stringify(detail);
    }
    return Promise.reject(new Error(msg));
  }
);

export default api;