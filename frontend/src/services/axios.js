import axios from 'axios';
import { getAuthToken, removeAuthToken } from './authApi';

const API_URL =  'http://localhost:8000/';

const axiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, 
  timeout: 30000,
});

// 📤 REQUEST INTERCEPTOR
axiosInstance.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    
    if (token) {
      config.headers.Authorization = `Token ${token}`; 
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

axiosInstance.interceptors.response.use(
  (response) => response,
 (error) => {
    if (error.response?.status === 401) {
      removeAuthToken();
      console.warn("Session expired. User needs to log in again.");
    }
    return Promise.reject(error);
  }
);

export default axiosInstance;