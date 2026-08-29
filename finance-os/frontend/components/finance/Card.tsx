import type { ReactNode } from "react";
import { Skeleton } from "./Skeleton";

interface CardProps {
  title?: string;
  isLoading?: boolean;
  error?: Error | null;
  children?: ReactNode;
  className?: string;
}

export function Card({ title, isLoading, error, children, className = "" }: CardProps) {
  return (
    <section className={`card ${className}`}>
      {title ? <h3 className="card-title">{title}</h3> : null}
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-8 w-1/2" />
        </div>
      ) : error ? (
        <p className="value-negative text-sm">Failed to load: {error.message}</p>
      ) : (
        children
      )}
    </section>
  );
}

export default Card;
