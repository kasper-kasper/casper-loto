export type TextField = "kicker" | "title" | "description" | "value" | "fact";
export type PublicationFields = Record<TextField, string>;
export type Rectangle = [number, number, number, number];
export interface PublicationFormat { width: number; height: number; background: string; zones: Record<TextField, Rectangle>; fonts: Record<TextField, number>; cta: Rectangle | null }
export interface PublicationTemplate { id: string; lottery: string; lotteryLabel: string; subcategory: string; subcategoryLabel: string; compositionLabel: string; accent: string; base: string; light: string; serif: boolean; formats: Record<"story" | "post", PublicationFormat> }
export interface PublicationInput { template_id: string; fields: PublicationFields; cta_label: string; channel_caption: string }
export interface Publication { id: string; lottery_code: string; status: "draft" | "published" | "archived"; revision: number; content: { template: PublicationTemplate; fields: PublicationFields; cta_label: string; channel_caption: string }; created_at: string; updated_at: string; published_at: string | null }

// Deterministic layout in source pixels, shared by preview, Story and exports.
export function fitPublicationText(text: string, box: Rectangle, preferred: number): { lines: string[]; size: number } {
  if (!text.trim()) return { lines: [], size: preferred };
  const wrap = (size: number) => {
    const max = Math.max(1, Math.floor(box[2] / (size * 1.05))), lines: string[] = [];
    for (const paragraph of text.split(/\r?\n/)) {
      let line = "";
      for (const word of paragraph.split(/\s+/).filter(Boolean)) {
        const parts = word.match(new RegExp(`.{1,${max}}`, "gu")) ?? [];
        for (const part of parts) { if (line && line.length + 1 + part.length > max) { lines.push(line); line = ""; } line += (line ? " " : "") + part; }
      }
      lines.push(line);
    }
    return lines;
  };
  let size = preferred, lines = wrap(size);
  while (lines.length * size * 1.18 > box[3] && size > 1) { size -= 1; lines = wrap(size); }
  return { lines, size };
}
