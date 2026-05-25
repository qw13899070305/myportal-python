import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
    const token = ref(localStorage.getItem('token') || '')
    const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

    function setAuth(t, u) {
        token.value = t
        user.value = u
        localStorage.setItem('token', t)
        localStorage.setItem('user', JSON.stringify(u))
    }

    function logout() {
        token.value = ''
        user.value = null
        localStorage.clear()
    }

    async function fetchUser() {
        const res = await fetch("/api/v1/auth/me", {
            headers: { Authorization: `Bearer ${token.value}` }
        });
        if (res.ok) {
            const u = await res.json();
            user.value = u;
            localStorage.setItem("user", JSON.stringify(u));
        } else {
            throw new Error("会话已过期");
        }
    }

    function isAdmin() {
        return user.value?.roles?.includes('admin') || user.value?.roles?.includes('super_admin')
    }

    return { token, user, setAuth, logout, isAdmin, fetchUser }
})
