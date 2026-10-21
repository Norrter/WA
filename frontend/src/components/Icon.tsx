// Небольшой набор иконок (линии 1.75px, сетка 24×24)

const PATHS = {
  today: "M4 5h16v15H4zM4 10h16M9 3v4M15 3v4M8 14h3v3H8z",
  calendar: "M4 5h16v15H4zM4 10h16M9 3v4M15 3v4",
  programs: "M5 4h14v16H5zM9 8h6M9 12h6M9 16h4",
  exercises: "M2 12h3M19 12h3M5 8v8M19 8v8M8 6v12M16 6v12M8 12h8",
  progress: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  profile: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c1.5-4 4.5-6 8-6s6.5 2 8 6",
  plus: "M12 5v14M5 12h14",
  minus: "M5 12h14",
  check: "M5 12.5l4.5 4.5L19 7.5",
  close: "M6 6l12 12M18 6L6 18",
  up: "M12 19V5M6 11l6-6 6 6",
  down: "M12 5v14M6 13l6 6 6-6",
  left: "M15 5l-7 7 7 7",
  right: "M9 5l7 7-7 7",
  edit: "M4 20h4L19 9l-4-4L4 16zM13 7l4 4",
  trash: "M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4",
  timer: "M12 21a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM12 9v4l2.5 2.5M9 2h6",
  logout: "M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10",
  menu: "M4 7h16M4 12h16M4 17h10",
  coach: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20c1-3.5 3.5-5.5 6.5-5.5s5.5 2 6.5 5.5M16 4.6a3.5 3.5 0 0 1 0 6.3M18 14.8c2 .8 3.1 2.6 3.6 5.2",
  admin: "M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6zM9 12l2 2 4-4",
  dumbbell: "M6.5 7v10M17.5 7v10M3.5 9.5v5M20.5 9.5v5M6.5 12h11",
  month: "M4 6.5h16V20H4zM4 10.5h16M8.5 3.5v4M15.5 3.5v4",
  list: "M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01",
  chart: "M4 4v16h16M8 15l3.5-4 3 2.5L19 8",
  dots: "M5 12h.01M12 12h.01M19 12h.01",
  play: "M7 4.5v15l13-7.5z",
  repeat: "M4 12a8 8 0 0 1 13.7-5.6L20 8.5M20 4v4.5h-4.5M20 12a8 8 0 0 1-13.7 5.6L4 15.5M4 20v-4.5h4.5",
  send: "M5 12h14M13 6l6 6-6 6",
  chevronDown: "M6 9l6 6 6-6",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({
  name,
  size = 20,
  strokeWidth = 1.75,
}: {
  name: IconName;
  size?: number;
  strokeWidth?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={name === "dots" ? 3 : strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={PATHS[name]} fill={name === "play" ? "currentColor" : "none"} />
    </svg>
  );
}
