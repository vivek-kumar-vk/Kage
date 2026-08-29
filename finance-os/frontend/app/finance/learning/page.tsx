"use client";
import { useState } from "react";
import { Card } from "@/components/finance/Card";
import { useFinanceData } from "@/lib/api";

interface Topic {
  id: number;
  slug: string;
  title: string;
}
interface TopicDetail {
  id: number;
  title: string;
  content: string;
  related: { title: string; source: string }[];
}
interface Lesson {
  slug: string;
  title: string;
  content: string;
}

function TopicList({
  onPick,
  activeId,
}: {
  onPick: (id: number) => void;
  activeId: number;
}) {
  const { data, isLoading, error } = useFinanceData<{ topics: Topic[] }>(
    "/learning/topics"
  );
  return (
    <Card title="Topics" isLoading={isLoading} error={error}>
      {!data || data.topics.length === 0 ? (
        <p className="text-sm text-racing-silver">No content available.</p>
      ) : (
        <ul className="space-y-1 text-sm">
          {data.topics.map((t) => (
            <li key={t.id}>
              <button
                onClick={() => onPick(t.id)}
                className={`w-full text-left ${
                  t.id === activeId ? "text-racing-blue" : "hover:text-racing-blue"
                }`}
              >
                {t.title}
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function TopicReader({ topicId }: { topicId: number }) {
  const { data, isLoading, error } = useFinanceData<TopicDetail>(
    `/learning/topic/${topicId}`
  );
  return (
    <Card title={data?.title ?? "Reader"} isLoading={isLoading} error={error}>
      {!data ? (
        <p className="text-sm text-racing-silver">Pick a topic.</p>
      ) : (
        <>
          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-gray-200">
            {data.content}
          </pre>
          {data.related.length > 0 && (
            <p className="mt-3 text-xs text-racing-silver">
              Related: {data.related.map((r) => r.title).join(" · ")}
            </p>
          )}
        </>
      )}
    </Card>
  );
}

function PersonalizedStrip() {
  const { data, isLoading, error } = useFinanceData<{ lessons: Lesson[] }>(
    "/learning/personalized"
  );
  return (
    <Card title="Suggested for your situation" isLoading={isLoading} error={error}>
      {!data || data.lessons.length === 0 ? (
        <p className="text-sm text-racing-silver">Nothing to suggest yet.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {data.lessons.map((l) => (
            <li key={l.slug}>
              <p className="text-racing-yellow">{l.title}</p>
              <p className="line-clamp-3 text-racing-silver">
                {l.content.replace(/^#.*\n+/, "").slice(0, 240)}…
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function LearningPage() {
  const [topicId, setTopicId] = useState(1);
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
      <TopicList onPick={setTopicId} activeId={topicId} />
      <div className="xl:col-span-2">
        <TopicReader topicId={topicId} />
      </div>
      <div className="xl:col-span-3">
        <PersonalizedStrip />
      </div>
    </div>
  );
}
