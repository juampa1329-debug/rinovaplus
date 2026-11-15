import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { KeyboardEvent, RefObject } from "react";
import { Icon } from "../shared/Icon";
import { Button } from "../shared/ui";

const categories = [
  { group: 0, label: "Caras y emociones", icon: "😀" },
  { group: 1, label: "Personas y gestos", icon: "👋" },
  { group: 3, label: "Animales y naturaleza", icon: "🐻" },
  { group: 4, label: "Comida y bebida", icon: "🍕" },
  { group: 5, label: "Viajes y lugares", icon: "🚗" },
  { group: 6, label: "Actividades", icon: "⚽" },
  { group: 7, label: "Objetos", icon: "💡" },
  { group: 8, label: "Símbolos", icon: "❤️" },
  { group: 9, label: "Banderas", icon: "🏁" },
];
const tones = [
  { value: "0", label: "Tono predeterminado" },
  { value: "1", label: "🏻 Tono claro" },
  { value: "2", label: "🏼 Tono claro medio" },
  { value: "3", label: "🏽 Tono medio" },
  { value: "4", label: "🏾 Tono oscuro medio" },
  { value: "5", label: "🏿 Tono oscuro" },
  { value: "all", label: "Todos los tonos y combinaciones" },
];
type Emoji = {
  hexcode: string;
  unicode: string;
  label: string;
  group?: number;
  order?: number;
  tags?: string[];
  skins?: Emoji[];
};
const pageSize = 96;
const normalize = (value: string) =>
  value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase("es");
function hasSkinTone(variant: Emoji, tone: string) {
  const modifiers = variant.hexcode.match(/1F3F[B-F]/g);
  return !!modifiers?.every(
    (modifier) => Number.parseInt(modifier, 16) - 0x1f3fa === Number(tone),
  );
}
function moveWithinGrid(event: KeyboardEvent<HTMLDivElement>) {
  if (
    ![
      "ArrowLeft",
      "ArrowRight",
      "ArrowUp",
      "ArrowDown",
      "Home",
      "End",
    ].includes(event.key)
  )
    return;
  const buttons = Array.from(event.currentTarget.querySelectorAll("button"));
  const index = buttons.indexOf(event.target as HTMLButtonElement);
  if (index < 0) return;
  const columns = getComputedStyle(
    event.currentTarget,
  ).gridTemplateColumns.split(" ").length;
  const positions: Record<string, number> = {
    ArrowLeft: index - 1,
    ArrowRight: index + 1,
    ArrowUp: index - columns,
    ArrowDown: index + columns,
    Home: 0,
    End: buttons.length - 1,
  };
  event.preventDefault();
  buttons[
    Math.min(buttons.length - 1, Math.max(0, positions[event.key]))
  ]?.focus();
}

export function EmojiPicker({
  value,
  setValue,
  input,
}: {
  value: string;
  setValue: (value: string) => void;
  input: RefObject<HTMLTextAreaElement | null>;
}) {
  const [open, setOpen] = useState(false);
  const [group, setGroup] = useState(0);
  const [tone, setTone] = useState("0");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(pageSize);
  const [catalog, setCatalog] = useState<Emoji[]>([]);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const trigger = useRef<HTMLButtonElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const id = useId();

  useEffect(() => {
    if (!open || catalog.length) return;
    let active = true;
    void import("emojibase-data/es/compact.json")
      .then(({ default: emojis }) => {
        if (active)
          setCatalog(
            (emojis as Emoji[])
              .filter((item) => item.group != null && item.group !== 2)
              .sort((left, right) => (left.order ?? 0) - (right.order ?? 0)),
          );
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, [open, attempt, catalog.length]);
  useEffect(() => {
    if (open) search.current?.focus();
  }, [open]);
  const results = useMemo(() => {
    const words = normalize(query.trim()).split(/\s+/).filter(Boolean);
    return catalog.flatMap((emoji) => {
      const searchText = normalize(
        [
          emoji.label,
          emoji.unicode,
          ...(emoji.tags ?? []),
          ...(emoji.skins?.flatMap((skin) => [skin.label, skin.unicode]) ?? []),
        ].join(" "),
      );
      if (
        words.length
          ? !words.every((word) => searchText.includes(word))
          : emoji.group !== group
      )
        return [];
      if (tone === "all") return [emoji, ...(emoji.skins ?? [])];
      const variant = emoji.skins?.find((skin) => hasSkinTone(skin, tone));
      return [variant ?? emoji];
    });
  }, [catalog, group, query, tone]);

  function insert(emoji: string) {
    const start = input.current?.selectionStart ?? value.length;
    const end = input.current?.selectionEnd ?? start;
    if (value.length - (end - start) + emoji.length > 4000) return;
    setValue(value.slice(0, start) + emoji + value.slice(end));
    setOpen(false);
    requestAnimationFrame(() => {
      input.current?.focus();
      input.current?.setSelectionRange(
        start + emoji.length,
        start + emoji.length,
      );
    });
  }
  return (
    <div
      className="inbox-emoji-tool"
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          setOpen(false);
          trigger.current?.focus();
        }
      }}
      onBlur={(event) => {
        if (
          event.relatedTarget instanceof Node &&
          !event.currentTarget.contains(event.relatedTarget)
        )
          setOpen(false);
      }}
    >
      <button
        type="button"
        className="inbox-tool-button"
        ref={trigger}
        aria-label="Elegir emoji"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        title="Elegir emoji"
        onClick={() => setOpen(!open)}
      >
        <Icon name="smile" />
      </button>
      {open && (
        <div
          id={id}
          className="inbox-composer-popover inbox-emoji-picker"
          role="group"
          aria-label="Emojis"
        >
          <input
            type="search"
            ref={search}
            aria-label="Buscar emojis"
            placeholder="Buscar emojis"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setLimit(pageSize);
            }}
          />
          <div
            className="inbox-emoji-categories"
            role="group"
            aria-label="Categorías de emojis"
          >
            {categories.map(({ label, icon, group: id }) => (
              <Button
                key={label}
                variant="quiet"
                aria-label={label}
                title={label}
                aria-pressed={!query.trim() && group === id}
                onClick={() => {
                  setGroup(id);
                  setQuery("");
                  setLimit(pageSize);
                }}
              >
                {icon}
              </Button>
            ))}
          </div>
          <select
            className="inbox-emoji-tones"
            aria-label="Tonos de piel de emojis"
            value={tone}
            onChange={(event) => {
              setTone(event.target.value);
              setLimit(pageSize);
            }}
          >
            {tones.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          {error ? (
            <Button
              variant="quiet"
              onClick={() => {
                setError(false);
                setAttempt((n) => n + 1);
              }}
            >
              Reintentar catálogo
            </Button>
          ) : !catalog.length ? (
            <small role="status">Cargando emojis…</small>
          ) : !results.length ? (
            <small role="status">Sin emojis para esta búsqueda.</small>
          ) : (
            <div className="inbox-emoji-results">
              <div className="inbox-emoji-grid" onKeyDown={moveWithinGrid}>
                {results.slice(0, limit).map((emoji) => (
                  <Button
                    key={emoji.hexcode}
                    variant="quiet"
                    aria-label={emoji.label}
                    title={emoji.label}
                    onClick={() => insert(emoji.unicode)}
                  >
                    {emoji.unicode}
                  </Button>
                ))}
              </div>
              {limit < results.length && (
                <Button
                  variant="quiet"
                  onClick={() => setLimit((count) => count + pageSize)}
                >
                  Mostrar más emojis
                </Button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
