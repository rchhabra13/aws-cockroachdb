"use client";

import { useState } from "react";
import type { MemoryHit } from "@/lib/api";
import styles from "./MemoryInspector.module.css";

// Everything the character was given, split the same way the prompt splits it. This pane
// is the point of the demo: it makes an access control decision visible, rather than
// asking the viewer to trust that one happened.
export default function MemoryInspector({
  hits,
  prompt,
  role,
}: {
  hits: MemoryHit[];
  prompt: string;
  role?: string;
}) {
  const [showPrompt, setShowPrompt] = useState(false);
  const shared = hits.filter((h) => h.source_type === "shared_event");
  const priv = hits.filter((h) => h.source_type !== "shared_event");

  return (
    <div className={styles.pane}>
      <h2 className={styles.title}>Memory inspector</h2>

      {hits.length === 0 && (
        <p className={styles.empty}>
          Nothing retrieved. The character answers with no memory of this topic.
        </p>
      )}

      {shared.length > 0 && (
        <section>
          <h3 className={styles.sharedHeading}>
            Branch announcements{role ? ` to ${role}s` : ""}
          </h3>
          {shared.map((h) => (
            <Row key={h.source_id} hit={h} variant="shared" />
          ))}
        </section>
      )}

      {priv.length > 0 && (
        <section>
          <h3 className={styles.privateHeading}>Their own memories</h3>
          {priv.map((h) => (
            <Row key={h.source_id} hit={h} variant="private" />
          ))}
        </section>
      )}

      {prompt && (
        <div className={styles.promptBlock}>
          <button className={styles.toggle} onClick={() => setShowPrompt(!showPrompt)}>
            {showPrompt ? "Hide" : "Show"} the prompt this produced
          </button>
          {showPrompt && <pre className={styles.prompt}>{prompt}</pre>}
        </div>
      )}
    </div>
  );
}

function Row({ hit, variant }: { hit: MemoryHit; variant: "shared" | "private" }) {
  const pct = Math.max(0, Math.min(1, hit.similarity)) * 100;
  return (
    <div className={`${styles.row} ${styles[variant]}`}>
      <div className={styles.rowHead}>
        <span className={styles.badge}>{variant === "shared" ? "SHARED" : "PRIVATE"}</span>
        <span className={styles.score}>{hit.similarity.toFixed(3)}</span>
      </div>
      <div className={styles.bar}>
        <div className={styles.barFill} style={{ width: `${pct}%` }} />
      </div>
      <p className={styles.content}>{hit.content}</p>
    </div>
  );
}
