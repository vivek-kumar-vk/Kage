export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-md bg-carbon-light/60 motion-reduce:animate-none ${className}`}
      aria-hidden="true"
    />
  );
}

export default Skeleton;
