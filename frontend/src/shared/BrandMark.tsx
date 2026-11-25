import rinovaMark from "../assets/rinovaplus.svg?no-inline";

export function BrandMark({ width = 48 }: { width?: number }) {
  return (
    <img
      src={rinovaMark}
      alt=""
      width={width}
      height={(width * 339) / 395}
      style={{ height: "auto" }}
    />
  );
}
