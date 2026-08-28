// data_for_calendar.js - today's calendar events hook.
import { create_swr } from './swr.svelte.js';

export const calendar = create_swr('/api/main_menu/calendar/events', 'inky_mm_calendar_v2', { fresh_window_ms: 300_000 });
