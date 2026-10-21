// Меандр — греческий орнамент полосой. Цвет берёт из currentColor,
// поэтому полосу красим через CSS (.meander { color: … }).

import { useId } from "react";

export function Meander({ className = "" }: { className?: string }) {
  const id = `meander-${useId().replace(/:/g, "")}`;

  return (
    <svg className={`meander ${className}`} width="100%" height="14" aria-hidden="true">
      <defs>
        <pattern id={id} width="14" height="14" patternUnits="userSpaceOnUse">
          <path d="M0 13H13V1H3V9H9V5H6" fill="none" stroke="currentColor" strokeWidth="1.6" />
        </pattern>
      </defs>
      <rect width="100%" height="14" fill={`url(#${id})`} />
    </svg>
  );
}
