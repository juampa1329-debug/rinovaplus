const paths: Record<string, string> = {
  menu: "M4 6h16 M4 12h16 M4 18h16",
  paperclip:
    "M21 11l-9 9a6 6 0 0 1-8.5-8.5l9-9a4 4 0 0 1 5.7 5.7l-9 9a2 2 0 0 1-2.8-2.8L15 6",
  microphone:
    "M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0z M5 10v2a7 7 0 0 0 14 0v-2 M12 19v3 M8 22h8",
  admissions: "M4 4h16v16H4z M8 8h8 M8 12h5 M8 16h3",
  overview: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  clients:
    "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M22 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75",
  inbox:
    "M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5z",
  application:
    "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M8 13h8 M8 17h5",
  review: "M9 3H5v18h14V3h-4 M9 2h6v4H9z M8 13l3 3 5-6",
  assistant:
    "M12 3v3 M5 8h14v11H5z M8 12h.01 M16 12h.01 M9 16h6 M2 11v5 M22 11v5",
  knowledge:
    "M12 5c-3-2-6-2-10-1v16c4-1 7-1 10 1 3-2 6-2 10-1V4c-4-1-7-1-10 1z M12 5v16",
  memory: "M3 12a9 9 0 1 0 3-6.7 M3 3v6h6 M12 7v5l3 2",
  campaigns: "M3 10v5h4l12 5V5L7 10H3z M7 15l2 6h4l-3-5 M22 9v7",
  agents: "M12 3v4 M5 8h14v10H5z M8 12h.01 M16 12h.01 M9 16h6 M3 21h18",
  settings: "M4 6h16 M4 12h16 M4 18h16 M8 3v6 M16 9v6 M10 15v6",
  access: "M5 10h14v11H5z M8 10V6a4 4 0 0 1 8 0v4 M12 14v3",
  retention: "M3 12h4l3-8 4 16 3-8h4",
  corporate:
    "M4 21V7h6V3h10v18H4z M8 11h.01 M8 15h.01 M14 7h2 M14 11h2 M14 15h2 M12 21v-3h4v3",
  creators:
    "M12 3l2.8 5.7L21 9.6l-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9z",
  sun: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1.5 1.5 M17.5 17.5 19 19 M5 19l1.5-1.5 M17.5 6.5 19 5",
  moon: "M21 13a9 9 0 1 1-10-10 7 7 0 0 0 10 10z",
  monitor: "M3 3h18v13H3z M8 21h8 M12 16v5",
};

export function Icon({
  name,
  className = "",
}: {
  name: string;
  className?: string;
}) {
  return (
    <svg
      className={`ui-icon ${className}`}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={paths[name] ?? paths.overview} />
    </svg>
  );
}
