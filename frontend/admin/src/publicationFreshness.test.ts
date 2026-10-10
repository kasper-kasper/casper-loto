import { expect, it } from "vitest";
import type { Publication } from "../../shared/publications";
import { freshProposal } from "./publicationFreshness";

it("expires at 24 hours and an old event cannot regain freshness", () => {
  const now = Date.parse("2026-10-11T08:00:00Z"), day = 86400000;
  const row = { created_at: new Date(now - day + 1).toISOString(), content: {} } as Publication;
  expect(freshProposal(row, now)).toBe(true);
  expect(freshProposal(row, now + 1)).toBe(false);
  expect(freshProposal({ ...row, created_at: new Date(now).toISOString(), content: { ...row.content, event: { occurred_at: new Date(now-day).toISOString() } } }, now)).toBe(false);
});
