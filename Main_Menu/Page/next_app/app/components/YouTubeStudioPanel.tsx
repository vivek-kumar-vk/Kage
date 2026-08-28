"use client";

/** Left column, bottom module - "YOUTUBE STUDIO" from the reference: a
    big subscriber count, lifetime views, a longforms-this-month line, a
    dot grid, and a round camera button. Static content, an exact copy
    of the reference image. */

// 5 rows x 12 dots. `filled` indices are amber; `ringed` gets an outline.
const ROWS = 5;
const COLS = 12;
const FILLED = new Set([1, 4, 7, 13, 15, 26, 27, 30, 38, 40]);
const RINGED = new Set([37]);

export function YouTubeStudioPanel() {
  return (
    <section aria-label="YouTube Studio" className="rubric-panel p-4">
      <header className="mb-3">
        <p className="rubric-label flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" className="text-dim">
            <rect x="3" y="6" width="18" height="12" rx="3" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <path d="M10 9.5 15 12l-5 2.5z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
          </svg>
          YouTube Studio
        </p>
      </header>

      <p className="num text-[30px] font-semibold leading-none text-white">170,000</p>
      <p className="rubric-sub mt-1 text-[9px]">
        Subscribers <span className="text-dim">&middot; 8.5M lifetime views</span>
      </p>

      <p className="rubric-sub mt-3 text-[9px]">5 Longforms This Month</p>

      <div className="mt-2 flex flex-col gap-[5px]">
        {Array.from({ length: ROWS }).map((_, r) => (
          <div key={r} className="flex gap-[5px]">
            {Array.from({ length: COLS }).map((_, c) => {
              const idx = r * COLS + c;
              const filled = FILLED.has(idx);
              const ringed = RINGED.has(idx);
              return (
                <span
                  key={c}
                  className="h-[7px] w-[7px] rounded-full"
                  style={{
                    background: filled ? "#ff7a00" : ringed ? "transparent" : "#333333",
                    border: ringed ? "1.5px solid #ff7a00" : "none",
                  }}
                />
              );
            })}
          </div>
        ))}
      </div>

      <button
        type="button"
        aria-label="open camera"
        className="mt-4 flex h-9 w-9 items-center justify-center rounded-full border border-[#ff7a00] text-[#ff7a00] transition-colors hover:bg-[#ff7a00] hover:text-black"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
          <rect x="3" y="6" width="13" height="12" rx="2" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <path d="m16 10 5-3v10l-5-3z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
        </svg>
      </button>
    </section>
  );
}
