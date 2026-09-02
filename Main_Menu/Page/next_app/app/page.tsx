import { TopBar } from "./components/TopBar";
import { CalendarPanel } from "./components/CalendarPanel";
import { YouTubeStudioPanel } from "./components/YouTubeStudioPanel";
import { CenterCore } from "./components/CenterCore";
import { EmailPanel } from "./components/EmailPanel";
import { SkillsDeckPanel } from "./components/SkillsDeckPanel";
import { RoutinesPanel } from "./components/RoutinesPanel";

/** The Main Menu home screen - an exact-copy rebuild of the "RUBRIC
    Agentic OS" reference (this type of desing..png): a strict 3-column
    dashboard with a rotating agent ring around a real Three.js particle
    core in the centre. Every panel is its own self-contained component
    with its own content (AGENTS.md rule 4) - this shell only places
    them on the grid.

    Owner layout (2026-09-02): the navigation lives in the TopBar - name
    left, screens centre, live date/clock right - so the left column is
    panels only, pushed all the way up. */
export default function Home() {
  return (
    <>
      <TopBar />
      <div className="home-grid mx-auto grid w-full max-w-[1512px] flex-1 gap-6 p-6">
        <div className="flex min-w-0 flex-col gap-5">
          <CalendarPanel />
          <YouTubeStudioPanel />
        </div>

        <CenterCore />

        <div className="flex min-w-0 flex-col gap-5">
          <EmailPanel />
          <SkillsDeckPanel />
          <RoutinesPanel />
        </div>
      </div>
    </>
  );
}
