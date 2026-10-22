import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AchievementBadge } from "./AchievementBadge";
import type { Achievement } from "./achievementTypes";

const item: Achievement = { code: "ten_tickets", title: "Затянуло", rarity: "common", secret: false, status: "earned", icon: "tickets" };

describe("approved achievement badges", () => {
  it("keeps the six-digit epic threshold compact", () => {
    const { container } = render(<AchievementBadge item={{ ...item, code: "epic_hundred_thousand_tickets", rarity: "epic" }} />);
    expect(container.querySelector(".achievement-badge-mark")).toHaveTextContent("100000");
    expect(container.querySelector(".achievement-badge-mark")).toHaveClass("badge-mark-long");
  });
  it("updates artwork for an existing award without changing its saved icon metadata", () => {
    const { container } = render(<AchievementBadge item={item} />);
    expect(container.querySelector('[data-glyph="magnet"]')).not.toBeNull();
    expect(container.querySelector(".achievement-badge-mark")).toHaveTextContent("10");
    expect(item.icon).toBe("tickets");
  });

  it("hides all artwork, threshold marks and special shapes for an unearned secret", () => {
    const { container } = render(<AchievementBadge item={{ ...item, status: "locked", secret: true }} />);
    expect(container.querySelector('[data-glyph="lock"]')).not.toBeNull();
    expect(container.querySelector('[data-glyph="magnet"]')).toBeNull();
    expect(container.querySelector(".achievement-badge-mark")).toBeNull();
    expect(container.querySelector(".badge-distinct")).toBeNull();
  });

  it("uses the earned secret's real rarity and supports future catalogue icons", () => {
    const { container } = render(<AchievementBadge item={{ ...item, code: "future-legend", secret: true, rarity: "legendary", icon: "castle" }} />);
    expect(container.querySelector(".achievement-badge")).toHaveClass("rarity-legendary", "is-earned");
    expect(container.querySelector(".rarity-secret")).toBeNull();
    expect(container.querySelector('[data-glyph="castle"]')).not.toBeNull();
  });
});
