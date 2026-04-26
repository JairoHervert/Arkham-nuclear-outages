import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL;

export const apiClient = axios.create({
  baseURL,
  headers: {
    "X-Internal-API-Key": import.meta.env.VITE_NUCLEAR_OUTAGES_READ_API_KEY,
  },
});

export const adminApiClient = axios.create({
  baseURL,
  headers: {
    "X-Internal-API-Key":
      import.meta.env.VITE_NUCLEAR_OUTAGES_ADMIN_API_KEY ||
      import.meta.env.VITE_NUCLEAR_OUTAGES_READ_API_KEY,
  },
});