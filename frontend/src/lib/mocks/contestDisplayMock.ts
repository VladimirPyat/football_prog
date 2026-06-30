/**
 * Display mock data for public leaderboard/results tabs (BUG-2.2.2).
 * Matches layout in docs/screens/user_leaderboard.jpg and user_result.jpg.
 * Replace with API hooks in Stage 2.4.
 */

export interface MockLeaderboardRow {
  rank: number;
  user_name: string;
  predictions_count: number;
  count_exact_high: number;
  count_exact: number;
  count_diff: number;
  count_outcome: number;
  bonus1: number;
  bonus2: number;
  bonus3: number;
  total_without_bonus3: number;
  total_with_bonus3: number;
}

export interface MockResultsMatch {
  id: number;
  team1: string;
  team2: string;
  score1: number;
  score2: number;
}

export interface MockResultsRow {
  user_name: string;
  match_points: (number | null)[];
  bonus1: number | null;
  bonus2: number | null;
  bonus3: number | null;
  total_without_bonus: number;
  total: number;
}

/** Leaderboard mock — Тур 9 reference (user_leaderboard.jpg). */
export const MOCK_LEADERBOARD_ROWS: MockLeaderboardRow[] = [
  {
    rank: 1,
    user_name: "Сидоров С.С.",
    predictions_count: 14,
    count_exact_high: 2,
    count_exact: 3,
    count_diff: 6,
    count_outcome: 3,
    bonus1: 5,
    bonus2: 5,
    bonus3: 10,
    total_without_bonus3: 64,
    total_with_bonus3: 84,
  },
  {
    rank: 2,
    user_name: "Попов А.А.",
    predictions_count: 19,
    count_exact_high: 1,
    count_exact: 2,
    count_diff: 5,
    count_outcome: 11,
    bonus1: 1,
    bonus2: 4,
    bonus3: 6,
    total_without_bonus3: 70,
    total_with_bonus3: 81,
  },
  {
    rank: 3,
    user_name: "Смирнов С.С.",
    predictions_count: 17,
    count_exact_high: 0,
    count_exact: 2,
    count_diff: 4,
    count_outcome: 11,
    bonus1: 4,
    bonus2: 5,
    bonus3: 8,
    total_without_bonus3: 59,
    total_with_bonus3: 76,
  },
  {
    rank: 4,
    user_name: "Лебедев Л.Л.",
    predictions_count: 16,
    count_exact_high: 1,
    count_exact: 1,
    count_diff: 5,
    count_outcome: 9,
    bonus1: 3,
    bonus2: 4,
    bonus3: 7,
    total_without_bonus3: 52,
    total_with_bonus3: 66,
  },
  {
    rank: 5,
    user_name: "Петров П.П.",
    predictions_count: 15,
    count_exact_high: 0,
    count_exact: 2,
    count_diff: 3,
    count_outcome: 10,
    bonus1: 2,
    bonus2: 3,
    bonus3: 5,
    total_without_bonus3: 48,
    total_with_bonus3: 58,
  },
  {
    rank: 6,
    user_name: "Иванов И.И.",
    predictions_count: 12,
    count_exact_high: 0,
    count_exact: 1,
    count_diff: 2,
    count_outcome: 9,
    bonus1: 1,
    bonus2: 2,
    bonus3: 4,
    total_without_bonus3: 36,
    total_with_bonus3: 43,
  },
  {
    rank: 7,
    user_name: "Волков В.В.",
    predictions_count: 11,
    count_exact_high: 0,
    count_exact: 0,
    count_diff: 2,
    count_outcome: 7,
    bonus1: 0,
    bonus2: 2,
    bonus3: 3,
    total_without_bonus3: 28,
    total_with_bonus3: 33,
  },
  {
    rank: 8,
    user_name: "Кузнецов К.К.",
    predictions_count: 10,
    count_exact_high: 0,
    count_exact: 0,
    count_diff: 1,
    count_outcome: 6,
    bonus1: 0,
    bonus2: 1,
    bonus3: 2,
    total_without_bonus3: 20,
    total_with_bonus3: 23,
  },
];

/** Results mock — Тур 4 reference (user_result.jpg). */
export const MOCK_RESULTS_MATCHES: MockResultsMatch[] = [
  { id: 1, team1: "Ахмат", team2: "Оренбург", score1: 1, score2: 0 },
  { id: 2, team1: "Ростов", team2: "Рубин", score1: 2, score2: 1 },
  { id: 3, team1: "Спартак", team2: "Динамо", score1: 0, score2: 0 },
  { id: 4, team1: "Зенит", team2: "Акрон", score1: 3, score2: 2 },
  { id: 5, team1: "ДинамоМХ", team2: "ПариНН", score1: 1, score2: 2 },
  { id: 6, team1: "Сочи", team2: "Локомотив", score1: 0, score2: 1 },
  { id: 7, team1: "Балтика", team2: "КС", score1: 2, score2: 2 },
  { id: 8, team1: "Краснодар", team2: "ЦСКА", score1: 1, score2: 1 },
];

export const MOCK_RESULTS_ROWS: MockResultsRow[] = [
  {
    user_name: "Иванов",
    match_points: [4, 0, 0, 0, 0, 0, 0, 0],
    bonus1: null,
    bonus2: null,
    bonus3: null,
    total_without_bonus: 16,
    total: 16,
  },
  {
    user_name: "Петров",
    match_points: [4, 8, 4, 12, 0, 0, 4, 8],
    bonus1: null,
    bonus2: 8,
    bonus3: null,
    total_without_bonus: 32,
    total: 40,
  },
  {
    user_name: "Сидоров",
    match_points: [4, 4, 4, 4, 4, 4, 4, 4],
    bonus1: null,
    bonus2: null,
    bonus3: null,
    total_without_bonus: 32,
    total: 32,
  },
  {
    user_name: "Кузнецов",
    match_points: [0, 0, 0, 0, 0, 0, 4, 4],
    bonus1: null,
    bonus2: null,
    bonus3: null,
    total_without_bonus: 8,
    total: 8,
  },
  {
    user_name: "Смирнов",
    match_points: [4, 4, 4, 4, 4, 4, 4, 4],
    bonus1: null,
    bonus2: null,
    bonus3: null,
    total_without_bonus: 32,
    total: 32,
  },
  {
    user_name: "Попов",
    match_points: [0, 4, 0, 0, 4, 0, 4, 0],
    bonus1: null,
    bonus2: null,
    bonus3: null,
    total_without_bonus: 12,
    total: 12,
  },
];
