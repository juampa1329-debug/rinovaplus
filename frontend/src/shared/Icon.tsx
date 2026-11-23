const paths: Record<string, string> = {
  chart: "M3 3v18h18 M7 16v-5 M12 16V7 M17 16v-8",
  panelCollapse: "M3 4h18v16H3z M9 4v16 m7-11-3 3 3 3",
  panelExpand: "M3 4h18v16H3z M9 4v16 m4-11 3 3-3 3",
  academic: "m2 9 10-5 10 5-10 5-10-5 M6 11v6c4 3 8 3 12 0v-6 M22 9v7",
  channels: "M9 5a3 3 0 1 1-6 0 3 3 0 0 1 6 0 M21 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0 M9 19a3 3 0 1 1-6 0 3 3 0 0 1 6 0 M9 6l6 4 M9 18l6-4",
  comments: "M4 3h16v13H9l-5 5V3 M8 7h8 M8 11h5",
  broadcasts: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M5 5a10 10 0 0 0 0 14 M19 5a10 10 0 0 1 0 14 M8 8a6 6 0 0 0 0 8 M16 8a6 6 0 0 1 0 8",
  ads: "M3 10v5h4l12 5V5L7 10H3 M7 15l2 6h3 M22 9v7",
  intelligence: "M12 4c-3-4-8-1-7 3-4 1-4 7-1 8-1 4 4 7 8 4 4 3 9 0 8-4 3-1 3-7-1-8 1-4-4-7-7-3 M12 4v15 M8 8l4 3 4-3 M7 15l5-2 5 2",
  user: "M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 21v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2",
  logout: "M9 4H3v16h6 M9 12h12 m-5-5 5 5-5 5",
  menu: "M4 6h16 M4 12h16 M4 18h16",
  close: "m6 6 12 12 M18 6 6 18",
  bell: "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9m-8 12a2 2 0 0 0 4 0",
  channelWhatsapp:
    "M20.4 11.6a8.4 8.4 0 0 1-12.8 7.2L4 20l1.2-3.6a8.4 8.4 0 1 1 15.2-4.8Z M9.7 8l1.2 2.3-1 1c.6 1.2 1.6 2.2 2.8 2.8l1-1 2.3 1.2c-.1 1.7-1.4 2.1-2.8 1.7-2.3-.7-4.5-2.9-5.2-5.2C7.6 9.4 8 8.1 9.7 8Z",
  channelInstagram:
    "M8 3h8a5 5 0 0 1 5 5v8a5 5 0 0 1-5 5H8a5 5 0 0 1-5-5V8a5 5 0 0 1 5-5Z M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Zm1.5-5.5h.01",
  channelFacebook:
    "M14 21v-8h3l.5-3H14V8.4c0-1 .5-1.4 1.5-1.4H18V4h-3c-3 0-4.5 1.7-4.5 4.4V10H8v3h2.5v8Z",
  channelMessenger:
    "M21 11.5a9 8.5 0 0 1-12.3 7.9L5 21v-3.6A8.2 8.2 0 0 1 3 11.5a9 8.5 0 0 1 18 0Z M7 14l4-5 3 3 3-2-4 5-3-3-3 2Z",
  channelTiktok:
    "M13 4h3c.3 2.5 1.7 4 4 4.4v3a7.7 7.7 0 0 1-4-1.6v5.7a5.5 5.5 0 1 1-6-5.5v3a2.5 2.5 0 1 0 3 2.5V4Z",
  paperclip:
    "M21 11l-9 9a6 6 0 0 1-8.5-8.5l9-9a4 4 0 0 1 5.7 5.7l-9 9a2 2 0 0 1-2.8-2.8L15 6",
  microphone:
    "M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0z M5 10v2a7 7 0 0 0 14 0v-2 M12 19v3 M8 22h8",
  image: "M3 3h18v18H3z M7 7h.01 M3 17l6-6 4 4 3-3 5 5",
  video: "M3 5h18v14H3z m7 4 6 3-6 3V9z",
  sticker: "M4 3h16v11l-7 7H4V3z M13 21v-7h7 M8 8h.01 M15 8h.01 M8 11c1 2 4 2 5 0",
  smile:
    "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z M8 14a4.5 4.5 0 0 0 8 0 M9 9h.01 M15 9h.01",
  send: "M22 2 7 17 M22 2l-5 20-5-10L2 7z",
  check: "m5 12 4 4L19 6",
  doubleCheck: "m3 12 4 4L17 6 M11 16 21 6",
  warning: "M12 3 2 20h20L12 3z M12 9v4 M12 16h.01",
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
