// data_for_agents.js - the agent fleet summary hook.
import { create_swr } from './swr.svelte.js';

export const fleet = create_swr('/api/main_menu/agents/fleet', 'inky_mm_fleet_v2', { fresh_window_ms: 120_000 });
