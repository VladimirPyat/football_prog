export const auth = {
  login: () => "/api/v1/auth/login",
  me: () => "/api/v1/auth/me",
  changePassword: () => "/api/v1/auth/change-password",
  contacts: () => "/api/v1/auth/me/contacts",
  setupPreview: () => "/api/v1/auth/setup-preview",
  completeSetup: () => "/api/v1/auth/complete-setup",
  requestPasswordReset: () => "/api/v1/auth/request-password-reset",
};

export const me = {
  contests: () => "/api/v1/me/contests",
};

export const contests = {
  list: () => "/api/v1/contests",
  public: () => "/api/v1/contests/public",
  byId: (id: number) => `/api/v1/contests/${id}`,
  create: () => "/api/v1/contests",
  patch: (id: number) => `/api/v1/contests/${id}`,
  start: (id: number) => `/api/v1/contests/${id}/start`,
  pause: (id: number) => `/api/v1/contests/${id}/pause`,
  resume: (id: number) => `/api/v1/contests/${id}/resume`,
  finish: (id: number) => `/api/v1/contests/${id}/finish`,
  delete: (id: number) => `/api/v1/contests/${id}`,
  deleted: () => `/api/v1/contests/deleted`,
  restore: (id: number) => `/api/v1/contests/${id}/restore`,
};

export const contestAdmin = {
  teams: {
    list: (contestId: number) => `/api/v1/contests/${contestId}/teams`,
    create: (contestId: number) => `/api/v1/contests/${contestId}/teams`,
    patch: (contestId: number, teamId: number) => `/api/v1/contests/${contestId}/teams/${teamId}`,
    delete: (contestId: number, teamId: number) => `/api/v1/contests/${contestId}/teams/${teamId}`,
    logo: (contestId: number, teamId: number) =>
      `/api/v1/contests/${contestId}/teams/${teamId}/logo`,
  },
  participants: {
    list: (contestId: number) => `/api/v1/contests/${contestId}/participants`,
    create: (contestId: number) => `/api/v1/contests/${contestId}/participants`,
    delete: (contestId: number, userId: number) =>
      `/api/v1/contests/${contestId}/participants/${userId}`,
    tiebreak: (contestId: number, userId: number) =>
      `/api/v1/contests/${contestId}/participants/${userId}/exceptional-tiebreak`,
  },
  rounds: {
    list: (contestId: number) => `/api/v1/contests/${contestId}/rounds`,
    predictions: (contestId: number, roundId: number) =>
      `/api/v1/contests/${contestId}/rounds/${roundId}/predictions`,
    results: (contestId: number, roundId: number) =>
      `/api/v1/contests/${contestId}/rounds/${roundId}/results`,
    leaderboard: (contestId: number, roundId: number) =>
      `/api/v1/contests/${contestId}/rounds/${roundId}/leaderboard`,
    create: (contestId: number) => `/api/v1/contests/${contestId}/admin/rounds`,
    freeTour: (contestId: number) => `/api/v1/contests/${contestId}/admin/rounds/free-tour`,
    patch: (contestId: number, roundId: number) =>
      `/api/v1/contests/${contestId}/admin/rounds/${roundId}`,
    activate: (contestId: number, roundId: number) =>
      `/api/v1/contests/${contestId}/admin/rounds/${roundId}/activate`,
    close: (contestId: number, roundId: number) =>
      `/api/v1/contests/${contestId}/admin/rounds/${roundId}/close`,
    calculate: (contestId: number, roundId: number) =>
      `/api/v1/contests/${contestId}/admin/rounds/${roundId}/calculate`,
    publish: (contestId: number, roundId: number) =>
      `/api/v1/contests/${contestId}/admin/rounds/${roundId}/publish`,
  },
  matches: {
    result: (contestId: number, matchId: number) =>
      `/api/v1/contests/${contestId}/admin/matches/${matchId}/result`,
    status: (contestId: number, matchId: number) =>
      `/api/v1/contests/${contestId}/admin/matches/${matchId}/status`,
  },
  recalculate: (contestId: number) => `/api/v1/contests/${contestId}/admin/recalculate`,
};

export const adminUsers = {
  createSupervisor: () => "/api/v1/admin/users/supervisor",
};
