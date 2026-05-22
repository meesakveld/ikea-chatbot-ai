// —— Modules ——
import axios from 'axios';

const API = axios.create({
    baseURL: process.env.EXPO_PUBLIC_API_URL,
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.EXPO_PUBLIC_API_KEY}`,
    },
});

export default API;
