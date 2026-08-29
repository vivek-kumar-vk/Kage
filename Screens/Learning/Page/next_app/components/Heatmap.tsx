"use client";

export default function Heatmap({ values }: { values: number[] }) {
  return (
    <div className="flex gap-1 flex-wrap">
      {values.map((value, index) => {
        const level = Math.max(0, Math.min(4, value));

        return (
          <div
            key={index}
            className={`w-3 h-3 rounded-sm bg-heat-${level}`}
            title={`value ${value}`}
          />
        );
      })}
    </div>
  );
}
