import type { Publication } from "../../shared/publications";

export function freshProposal(row: Publication, now: number): boolean {
  const created = Date.parse(row.created_at);
  const occurred = row.content.event?.occurred_at ? Date.parse(row.content.event.occurred_at) : created;
  return now < Math.min(created, occurred) + 24 * 60 * 60 * 1000;
}
