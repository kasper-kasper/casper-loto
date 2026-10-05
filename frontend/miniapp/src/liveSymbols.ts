// Presentation of the existing server symbol IDs. Never used to calculate prizes.
export const liveSymbolDefinitions = [
  { id: 1, name: "Подкова", material: "bronze" },
  { id: 2, name: "Клевер", material: "bronze", prize: 1_000 },
  { id: 3, name: "Серебряная монета", material: "silver", prize: 2_000 },
  { id: 4, name: "Золотая звезда", material: "gold", prize: 5_000 },
  { id: 5, name: "Рубин", material: "ruby", prize: 20_000 },
  { id: 6, name: "Бриллиант", material: "diamond", prize: 100_000 },
  { id: 7, name: "Золотой жетон Casper", material: "signature", prize: 1_000_000 },
  { id: 8, name: "Семёрка", material: "gold" },
] as const;
