import { tr } from "./i18n";
import type { PublicationFields, PublicationTemplate, TextField } from "../../shared/publications";
import { fitPublicationText } from "../../shared/publications";

export function PublicationArtwork({ template, fields, format = "story", ctaLabel = tr("Открыть лотерею"), onOpen }: { template: PublicationTemplate; fields: PublicationFields; format?: "story" | "post"; ctaLabel?: string; onOpen?: () => void }) {
  const spec = template.formats[format], cta = spec.cta, centered = template.textAlign === "center";
  return <div className="publication-artwork" style={{ position: "relative", width: "100%", aspectRatio: `${spec.width}/${spec.height}` }}>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox={`0 0 ${spec.width} ${spec.height}`} width="100%" height="100%" role="img" aria-label={tr(`${tr(template.lotteryLabel)}: ${fields.title}`)}>
      <title>{fields.title}</title><image href={spec.background} width={spec.width} height={spec.height} />
      {(Object.entries(spec.zones) as [TextField, [number, number, number, number]][]).map(([key, box]) => { const text = fitPublicationText(fields[key], box, spec.fonts[key]);const x = box[0] + (centered ? box[2] / 2 : 0);return <text key={key} textAnchor={centered ? "middle" : "start"} x={x} y={box[1] + (centered ? Math.max(0, (box[3] - text.lines.length * text.size * 1.18) / 2) : 0) + text.size * .9} fill={key === "kicker" || key === "value" ? template.accent : template.light} fontSize={text.size} fontWeight={key === "value" ? 700 : 400} fontFamily={key === "title" && template.serif ? "Georgia, serif" : "Arial, sans-serif"}>{text.lines.map((line, index) => <tspan x={x} dy={index ? text.size * 1.18 : 0} key={index}>{line}</tspan>)}</text>; })}
      {cta && <text textAnchor={centered ? "middle" : "start"} x={cta[0] + (centered ? cta[2] / 2 : 32)} y={cta[1] + 58} fill={template.base} fontSize={30} fontFamily="Arial, sans-serif">{tr(ctaLabel)}{!centered && <tspan x={cta[0] + cta[2] - 60}>↗</tspan>}</text>}
    </svg>
    {cta && onOpen && <button className="publication-story-cta" type="button" aria-label={tr(ctaLabel)} onClick={onOpen} style={{ position: "absolute", left: `${cta[0] / spec.width * 100}%`, top: `${cta[1] / spec.height * 100}%`, width: `${cta[2] / spec.width * 100}%`, height: `${cta[3] / spec.height * 100}%`, minHeight: 44, border: 0, background: "transparent", cursor: "pointer" }} />}
  </div>;
}

