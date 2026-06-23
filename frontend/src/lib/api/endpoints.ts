export const auth = {
  login: () => "/api/v1/auth/login",
  me: () => "/api/v1/auth/me",
  changePassword: () => "/api/v1/auth/change-password",
  contacts: () => "/api/v1/auth/me/contacts",
};

export const me = {
  contests: () => "/api/v1/me/contests",
};

export const contests = {
  list: () => "/api/v1/contests",
  public: () => "/api/v1/contests/public",
  byId: (id: number) => `/api/v1/contests/${id}`,
};
