import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useAuthStore } from './auth';

vi.mock('@/service/api', () => ({
    default: {
        defaults: { headers: { common: {} } },
        post: vi.fn(),
        get: vi.fn()
    }
}));

describe('useAuthStore', () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        localStorage.clear();
        sessionStorage.clear();
    });

    it('isAuthenticated é falso sem token', () => {
        const store = useAuthStore();
        store.token = null;
        expect(store.isAuthenticated).toBe(false);
    });

    it('isAuthenticated é verdadeiro com token', () => {
        const store = useAuthStore();
        store.token = 'fake-jwt';
        expect(store.isAuthenticated).toBe(true);
    });

    it('isGuardian reconhece grupos de responsável', () => {
        const store = useAuthStore();
        store.user = { groups: ['Responsaveis'] };
        expect(store.isGuardian).toBe(true);
    });
});
