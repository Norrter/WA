// Штанга с блинами, собранными под нужный вес

import { formatNumber } from "../lib/format";
import { BAR_WEIGHT, loadBar } from "../lib/plates";

export function PlateBar({ weight }: { weight: number }) {
  const load = loadBar(weight);

  if (!load) {
    return (
      <p className="platebar-note">
        Меньше веса грифа ({BAR_WEIGHT} кг) — блины не нужны
      </p>
    );
  }

  const plates = load.perSide;

  return (
    <figure className="platebar" aria-label={`Раскладка на ${formatNumber(weight)} кг`}>
      <div className="platebar-bar">
        <div className="platebar-side platebar-left">
          {[...plates].reverse().map((plate, index) => (
            <span
              key={index}
              className={`plate plate-${plate.tone}`}
              data-weight={plate.weight}
            />
          ))}
        </div>
        <span className="platebar-grip" />
        <div className="platebar-side">
          {plates.map((plate, index) => (
            <span
              key={index}
              className={`plate plate-${plate.tone}`}
              data-weight={plate.weight}
            />
          ))}
        </div>
      </div>
      <figcaption className="platebar-caption">
        {plates.length === 0
          ? "Пустой гриф 20 кг"
          : `На каждую сторону: ${plates.map((plate) => formatNumber(plate.weight)).join(" + ")} кг`}
        {load.remainder > 0 && ` · не хватает ${formatNumber(load.remainder)} кг до точного веса`}
      </figcaption>
    </figure>
  );
}
