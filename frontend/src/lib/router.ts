// Простой роутер на адресах вида #/workouts/12

import { useEffect, useState } from "react";

export type Route =
  | { name: "today" }
  | { name: "schedule" }
  | { name: "workout"; id: number }
  | { name: "programs" }
  | { name: "program"; id: number }
  | { name: "exercises" }
  | { name: "exercise"; id: number }
  | { name: "progress" }
  | { name: "profile" }
  | { name: "coach" }
  | { name: "coachUser"; id: number }
  | { name: "admin"; table: string | null }
  | { name: "notFound" };

export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const [section, rawId] = parts;
  const id = Number(rawId);

  if (parts.length === 0) return { name: "today" };

  if (parts.length === 1) {
    switch (section) {
      case "schedule":
        return { name: "schedule" };
      case "programs":
        return { name: "programs" };
      case "exercises":
        return { name: "exercises" };
      case "progress":
        return { name: "progress" };
      case "profile":
        return { name: "profile" };
      case "coach":
        return { name: "coach" };
      case "admin":
        return { name: "admin", table: null };
    }
  }

  if (parts.length === 2 && Number.isInteger(id) && id > 0) {
    switch (section) {
      case "workouts":
        return { name: "workout", id };
      case "programs":
        return { name: "program", id };
      case "exercises":
        return { name: "exercise", id };
    }
  }

  // #/admin/users
  if (parts.length === 2 && section === "admin" && /^[a-z_]+$/.test(parts[1])) {
    return { name: "admin", table: parts[1] };
  }

  // #/coach/clients/5
  if (parts.length === 3 && section === "coach" && parts[1] === "clients") {
    const userId = Number(parts[2]);
    if (Number.isInteger(userId) && userId > 0) return { name: "coachUser", id: userId };
  }

  return { name: "notFound" };
}

export function navigate(path: string): void {
  window.location.hash = path;
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));

  useEffect(() => {
    const onChange = () => {
      setRoute(parseRoute(window.location.hash));
      window.scrollTo(0, 0);
    };

    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  return route;
}
