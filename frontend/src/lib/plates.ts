// Раскладка блинов на штангу: какие блины повесить на каждую сторону

export const BAR_WEIGHT = 20;

export interface Plate {
  weight: number;
  // имя CSS-класса с цветом блина
  tone: string;
}

const PLATES: Plate[] = [
  { weight: 25, tone: "red" },
  { weight: 20, tone: "blue" },
  { weight: 15, tone: "yellow" },
  { weight: 10, tone: "green" },
  { weight: 5, tone: "white" },
  { weight: 2.5, tone: "black" },
  { weight: 1.25, tone: "steel" },
];

export interface PlateLoad {
  perSide: Plate[];
  // вес, который не удалось набрать имеющимися блинами
  remainder: number;
}

export function loadBar(total: number): PlateLoad | null {
  if (!Number.isFinite(total) || total < BAR_WEIGHT) {
    return null;
  }

  let side = (total - BAR_WEIGHT) / 2;
  const perSide: Plate[] = [];

  for (const plate of PLATES) {
    while (side + 1e-9 >= plate.weight) {
      perSide.push(plate);
      side -= plate.weight;
    }
  }

  return { perSide, remainder: Math.round(side * 2 * 100) / 100 };
}
