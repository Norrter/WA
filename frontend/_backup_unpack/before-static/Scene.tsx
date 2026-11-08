// Кинематографичный фон сайта.
//
// За интерфейсом всегда стоит «сцена» — статуя или колонны. Каждый экран
// выбирает свою сцену через useScene(), а на длинных страницах секции
// <SceneSection> переключают сцену при прокрутке. Смена идёт плавным
// наплывом, сам кадр медленно приближается и чуть сдвигается при прокрутке.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";

export type SceneName = "olympus" | "throne" | "struggle" | "colonnade" | "pillars";

interface SceneConfig {
  src: string;
  // side — вертикальный кадр справа на всю высоту экрана;
  // cover — кадр на весь экран
  fit: "side" | "cover";
  // ширина / высота кадра: по ней слой ровно совпадает с картинкой
  ratio: number;
  position: string;
  mobilePosition: string;
}

const SCENES: Record<SceneName, SceneConfig> = {
  // Зевс в золотой короне, стоя
  olympus: {
    src: "/scenes/olympus.jpg",
    fit: "side",
    ratio: 736 / 1104,
    position: "right center",
    mobilePosition: "62% 8%",
  },
  // Зевс на троне
  throne: {
    src: "/scenes/throne.jpg",
    fit: "side",
    ratio: 896 / 1344,
    position: "right center",
    mobilePosition: "58% 10%",
  },
  // Геракл в схватке, золотой нимб
  struggle: {
    src: "/scenes/struggle.jpg",
    fit: "side",
    ratio: 750 / 910,
    position: "right center",
    mobilePosition: "62% 12%",
  },
  // Ряд колонн в зале
  colonnade: {
    src: "/scenes/colonnade.jpg",
    fit: "cover",
    ratio: 640 / 359,
    position: "center 45%",
    mobilePosition: "center 40%",
  },
  // Колонны крупным планом
  pillars: {
    src: "/scenes/pillars.jpg",
    fit: "side",
    ratio: 736 / 1104,
    position: "right center",
    mobilePosition: "70% 0%",
  },
};

interface Layer {
  name: SceneName;
  id: number;
}

const SceneContext = createContext<(name: SceneName) => void>(() => {});

const FADE_MS = 1600;

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function SceneProvider({ children }: { children: ReactNode }) {
  // Первая сцена появляется из темноты, следующие — наплывом поверх
  const [layers, setLayers] = useState<Layer[]>([]);
  const nextId = useRef(1);

  const show = useCallback((name: SceneName) => {
    setLayers((current) => {
      if (current[current.length - 1]?.name === name) return current;
      // Старая сцена остаётся под новой, пока та проявляется
      return [...current.slice(-1), { name, id: nextId.current++ }];
    });
  }, []);

  // Когда новая сцена проявилась, старую убираем
  useEffect(() => {
    if (layers.length < 2) return;
    const timer = setTimeout(() => setLayers((current) => current.slice(-1)), FADE_MS);
    return () => clearTimeout(timer);
  }, [layers]);

  // Заранее загружаем все кадры, чтобы смена была без мигания
  useEffect(() => {
    for (const scene of Object.values(SCENES)) {
      const image = new Image();
      image.src = scene.src;
    }
  }, []);

  return (
    <SceneContext.Provider value={show}>
      <SceneBackdrop layers={layers} />
      {children}
    </SceneContext.Provider>
  );
}

function SceneBackdrop({ layers }: { layers: Layer[] }) {
  const root = useRef<HTMLDivElement>(null);

  // Лёгкий параллакс: кадр движется медленнее страницы
  useEffect(() => {
    if (prefersReducedMotion()) return;

    let frame = 0;

    const update = () => {
      frame = 0;
      const shift = Math.min(window.scrollY * 0.08, 80);
      root.current?.style.setProperty("--scene-shift", `${-shift}px`);
    };

    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div className="scene" ref={root} aria-hidden="true">
      {layers.map((layer) => {
        const config = SCENES[layer.name];

        return (
          <div key={layer.id} className="scene-layer">
            <div
              className="scene-image"
              data-fit={config.fit}
              data-scene={layer.name}
              style={
                {
                  "--scene-src": `url(${config.src})`,
                  "--scene-ratio": config.ratio,
                  "--scene-pos": config.position,
                  "--scene-pos-mobile": config.mobilePosition,
                } as CSSProperties
              }
            />
          </div>
        );
      })}
      <div className="scene-shade" />
    </div>
  );
}

// Выбрать сцену для экрана
export function useScene(name: SceneName): void {
  const show = useContext(SceneContext);

  useEffect(() => {
    show(name);
  }, [name, show]);
}

// Секция, которая включает свою сцену, когда доходит до середины экрана
export function SceneSection({
  scene,
  className,
  children,
  labelledBy,
}: {
  scene: SceneName;
  className?: string;
  children: ReactNode;
  labelledBy?: string;
}) {
  const ref = useRef<HTMLElement>(null);
  const show = useContext(SceneContext);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) show(scene);
      },
      { rootMargin: "-45% 0px -45% 0px" },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [scene, show]);

  return (
    <section ref={ref} className={className} aria-labelledby={labelledBy}>
      {children}
    </section>
  );
}
