/** Fixed full-viewport backdrop: three slow-drifting blurred colour
    blobs over the void, plus a faint film grain. All motion is CSS
    (globals.css) and freezes under prefers-reduced-motion. Purely
    decorative — aria-hidden, pointer-events none via its classes. */
export function AuroraBackground() {
  return (
    <>
      <div className="aurora" aria-hidden="true">
        <span className="aurora-blob a" />
        <span className="aurora-blob b" />
        <span className="aurora-blob c" />
      </div>
      <div className="grain" aria-hidden="true" />
    </>
  );
}
