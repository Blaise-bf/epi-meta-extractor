export type StoredUser = {
  id: string;
  email: string;
};

const TOKEN_KEY = "epi_access_token";
const USER_KEY = "epi_user";

export const loadAuthFromStorage = () => {
  if (typeof window === "undefined") {
    return { token: null as string | null, user: null as StoredUser | null };
  }

  const token = window.localStorage.getItem(TOKEN_KEY);
  const userRaw = window.localStorage.getItem(USER_KEY);
  let user: StoredUser | null = null;

  if (userRaw) {
    try {
      user = JSON.parse(userRaw) as StoredUser;
    } catch {
      user = null;
    }
  }

  return { token, user };
};

export const saveAuthToStorage = (token: string, user: StoredUser) => {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
};

export const clearAuthStorage = () => {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
};
