import type { PublicationFields, PublicationTemplate, TextField } from "../../shared/publications";
import { fitPublicationText } from "../../shared/publications";

export function PublicationArtwork({ template, fields, format = "story", ctaLabel = "Открыть лотерею", onOpen }: { template: PublicationTemplate; fields: PublicationFields; format?: "story" | "post"; ctaLabel?: string; onOpen?: () => void }) {
  const spec = template.formats[format], cta = spec.cta;
  return <div className="publication-artwork" style={{ position: "relative", width: "100%", aspectRatio: `${spec.width}/${spec.height}` }}>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox={`0 0 ${spec.width} ${spec.height}`} width="100%" height="100%" role="img" aria-label={`${template.lotteryLabel}: ${fields.title}`}>
      <title>{fields.title}</title><image href={spec.background} width={spec.width} height={spec.height} />
      {(Object.entries(spec.zones) as [TextField, [number, number, number, number]][]).map(([key, box]) => { const text = fitPublicationText(fields[key], box, spec.fonts[key]);return <text key={key} x={box[0]} y={box[1] + text.size * .9} fill={key === "kicker" || key === "value" ? template.accent : template.light} fontSize={text.size} fontWeight={key === "value" ? 700 : 400} fontFamily={key === "title" && template.serif ? "Georgia, serif" : "Arial, sans-serif"}>{text.lines.map((line, index) => <tspan x={box[0]} dy={index ? text.size * 1.18 : 0} key={index}>{line}</tspan>)}</text>; })}
      {cta && <text x={cta[0] + 32} y={cta[1] + 58} fill={template.base} fontSize={30} fontFamily="Arial, sans-serif">{ctaLabel}<tspan x={cta[0] + cta[2] - 60}>↗</tspan></text>}
    </svg>
    {cta && onOpen && <button className="publication-story-cta" type="button" aria-label={ctaLabel} onClick={onOpen} style={{ position: "absolute", left: `${cta[0] / spec.width * 100}%`, top: `${cta[1] / spec.height * 100}%`, width: `${cta[2] / spec.width * 100}%`, height: `${cta[3] / spec.height * 100}%`, minHeight: 44, border: 0, background: "transparent", cursor: "pointer" }} />}
  </div>;
}

