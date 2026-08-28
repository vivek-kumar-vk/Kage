// data_for_screens.js - the screens navigator's hook.
import { create_swr } from './swr.svelte.js';

export const navigation = create_swr(
  '/api/main_menu/navigation',
  'inky_main_menu_svelte_navigation_cache_v2',
  { fresh_window_ms: 120_000 },
);
