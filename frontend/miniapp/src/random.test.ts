import { randomCombination } from "./random";

describe("randomCombination", () => {
  it("creates a sorted valid Weekly combination without duplicates", () => {
    const values = randomCombination(20, 5);

    expect(values).toHaveLength(5);
    expect(new Set(values)).toHaveLength(5);
    expect(values).toEqual([...values].sort((left, right) => left - right));
    expect(values.every((value) => value >= 1 && value <= 20)).toBe(true);
  });
});
