import { describe, expect, it } from "vitest";

import { formatCompactAmount, formatDrawLabel } from "./format";

describe("formatCompactAmount", () => {
  it("keeps ordinary amounts exact and shortens million amounts", () => {
    expect(formatCompactAmount(999_999)).toBe("999 999");
    expect(formatCompactAmount(1_000_000)).toBe("1 млн");
    expect(formatCompactAmount(1_200_000)).toBe("1,2 млн");
    expect(formatCompactAmount(1_250_000_000)).toBe("1,3 млрд");
  });
});

it("calls Dual draws rounds in the Mini App", () => {
  expect(formatDrawLabel("dual", 501)).toBe("Раунд #0501");
});
