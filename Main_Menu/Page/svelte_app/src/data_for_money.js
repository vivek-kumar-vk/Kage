// data_for_money.js - the money card's hook: assets, liabilities, surplus.
import { create_swr } from './swr.svelte.js';

export const money = create_swr('/api/main_menu/home_brief', 'inky_mm_home_brief_v2', { fresh_window_ms: 120_000 });
