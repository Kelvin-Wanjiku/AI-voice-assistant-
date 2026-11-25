import AppStatus from "../components/AppStatus";
import { useMilo } from "../data/MiloDataContext";
import type { MemoryCategory } from "../types";

const CATEGORY_ORDER: MemoryCategory[] = ["Interests", "Food", "Routines", "Family and friends", "Health", "Goals"];

export default function AboutMeScreen() {
  const { memories, forgetMemory, lastForgotten, undoForget } = useMilo();

  // Only show categories that have something in them.
  const groups = CATEGORY_ORDER.map((category) => ({
    category,
    items: memories.filter((m) => m.category === category),
  })).filter((g) => g.items.length > 0);

  return (
    <>
      <h1 className="screen__title" tabIndex={-1}>About me</h1>
      <p className="screen__lead">
        These are the things Milo remembers about you. You can remove anything you don't want Milo to keep.
      </p>

      {lastForgotten && (
        <div className="undo" role="status">
          <p>Forgotten: “{lastForgotten.text}”</p>
          <button className="button button--quiet" onClick={undoForget}>Undo</button>
        </div>
      )}

      {groups.length === 0 ? (
        <p className="panel">Milo doesn't remember anything about you yet.</p>
      ) : (
        groups.map(({ category, items }) => (
          <section key={category} className="memory-group" aria-labelledby={`cat-${category}`}>
            <h2 id={`cat-${category}`} className="memory-group__title">{category}</h2>
            <ul className="memory-list">
              {items.map((m) => (
                <li key={m.id} className="memory">
                  <p>{m.text}</p>
                  <button className="button button--quiet" onClick={() => forgetMemory(m.id)} aria-label={`Forget: ${m.text}`}>
                    Forget
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))
      )}

      <AppStatus />
    </>
  );
}
