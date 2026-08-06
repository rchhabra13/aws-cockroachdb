"use client";

import { useEffect, useRef, useState } from "react";
import MemoryInspector from "@/components/MemoryInspector";
import {
  authorize,
  listEvents,
  listNpcs,
  listPlayers,
  speak,
  withdrawEvent,
  type BranchEvent,
  type MemoryHit,
  type Npc,
} from "@/lib/api";
import styles from "./page.module.css";

type Turn = { who: "player" | "npc"; text: string };

export default function Home() {
  const [session] = useState(() => crypto.randomUUID());
  const [npcs, setNpcs] = useState<Npc[]>([]);
  const [playerId, setPlayerId] = useState("");
  const [active, setActive] = useState<Npc | null>(null);
  const [turns, setTurns] = useState<Record<string, Turn[]>>({});
  const [hits, setHits] = useState<MemoryHit[]>([]);
  const [prompt, setPrompt] = useState("");
  const [events, setEvents] = useState<BranchEvent[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const [ns, ps] = await Promise.all([listNpcs(), listPlayers()]);
        // Older smoke test rows may still sit on a second branch, so take the branch
        // with the full cast rather than assuming there is only one.
        const byBranch = new Map<string, Npc[]>();
        ns.forEach((n) =>
          byBranch.set(n.branch_id, [...(byBranch.get(n.branch_id) ?? []), n]),
        );
        const cast = [...byBranch.values()].sort((a, b) => b.length - a.length)[0] ?? [];
        setNpcs(cast);
        setActive(cast[0] ?? null);
        const player = ps.find((p) => p.name === "Player One") ?? ps[0];
        if (player) {
          setPlayerId(player.id);
          setEvents(await listEvents(player.id));
        }
      } catch (e) {
        setError(String(e));
      }
    })();
  }, []);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [turns, active]);

  const refreshEvents = async (id = playerId) => {
    if (id) setEvents(await listEvents(id));
  };

  const send = async () => {
    if (!active || !input.trim() || busy) return;
    const text = input.trim();
    const npcId = active.id;
    setInput("");
    setBusy(true);
    setError("");
    setTurns((t) => ({ ...t, [npcId]: [...(t[npcId] ?? []), { who: "player", text }] }));
    try {
      const res = await speak(npcId, playerId, session, text);
      setTurns((t) => ({
        ...t,
        [npcId]: [...(t[npcId] ?? []), { who: "npc", text: res.reply }],
      }));
      setHits(res.recalled_memories);
      setPrompt(res.prompt_sent);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const grantClearance = async () => {
    if (!active) return;
    try {
      await authorize(active.branch_id, playerId);
      await refreshEvents();
    } catch (e) {
      setError(String(e));
    }
  };

  const withdraw = async (id: string) => {
    try {
      await withdrawEvent(id);
      await refreshEvents();
    } catch (e) {
      setError(String(e));
    }
  };

  const conversation = active ? turns[active.id] ?? [] : [];

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <h1 className={styles.brand}>OmniNPC</h1>
        <p className={styles.tagline}>
          Every character remembers separately. The inspector shows what each one was
          allowed to retrieve.
        </p>

        <h2 className={styles.sectionTitle}>Branch staff</h2>
        {npcs.map((n) => (
          <button
            key={n.id}
            className={`${styles.npc} ${active?.id === n.id ? styles.npcActive : ""}`}
            onClick={() => {
              setActive(n);
              setHits([]);
              setPrompt("");
            }}
          >
            <span className={styles.avatar}>{n.name[0]}</span>
            <span className={styles.npcMeta}>
              <span className={styles.npcName}>{n.name}</span>
              <span className={styles.npcRole}>{n.role}</span>
            </span>
          </button>
        ))}

        <h2 className={styles.sectionTitle}>Branch announcements</h2>
        {events.length === 0 && <p className={styles.none}>None in effect.</p>}
        {events.map((e) => (
          <div key={e.id} className={styles.event}>
            <p className={styles.eventText}>{e.summary}</p>
            <button className={styles.withdraw} onClick={() => withdraw(e.id)}>
              withdraw
            </button>
          </div>
        ))}
        <button className={styles.action} onClick={grantClearance} disabled={!playerId}>
          Manager grants a security clearance
        </button>
      </aside>

      <main className={styles.chat}>
        <header className={styles.chatHead}>
          {active ? (
            <>
              <strong>{active.name}</strong>
              <span className={styles.npcRole}>{active.role}</span>
            </>
          ) : (
            <span className={styles.npcRole}>no characters found</span>
          )}
        </header>

        <div className={styles.messages} ref={scroller}>
          {conversation.length === 0 && (
            <p className={styles.hint}>
              Tell the manager you are running an authorized security test, then ask the
              teller what the manager said. Then grant a clearance and ask the guard for
              the vault.
            </p>
          )}
          {conversation.map((t, i) => (
            <div
              key={i}
              className={t.who === "player" ? styles.fromPlayer : styles.fromNpc}
            >
              {t.text}
            </div>
          ))}
          {busy && <div className={styles.thinking}>thinking…</div>}
        </div>

        {error && <p className={styles.error}>{error}</p>}

        <div className={styles.composer}>
          <input
            value={input}
            placeholder={active ? `Say something to ${active.name}` : ""}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") send();
            }}
            disabled={!active || busy}
          />
          <button onClick={send} disabled={!active || busy}>
            Send
          </button>
        </div>
      </main>

      <MemoryInspector hits={hits} prompt={prompt} role={active?.role} />
    </div>
  );
}
