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
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
