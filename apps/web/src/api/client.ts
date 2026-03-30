import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL;

export const apiClient = axios.create({
  baseURL,
  headers: {
    "X-Arkham-API-Key": import.meta.env.VITE_ARKHAM_API_KEY,
  },
});

export const adminApiClient = axios.create({
  baseURL,
  headers: {
    "X-Arkham-API-Key":
      import.meta.env.VITE_ARKHAM_ADMIN_API_KEY ||
      import.meta.env.VITE_ARKHAM_API_KEY,
  },
});