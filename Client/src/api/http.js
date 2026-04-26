import axios from "axios";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || "http://localhost:5000/v1",
});

api.interceptors.request.use((config) => {
  const token = (localStorage.getItem("token") || "").replace(/"/g, "");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
