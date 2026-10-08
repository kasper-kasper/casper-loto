import { HalloweenBrand } from "../../../miniapp/src/HalloweenBrand";
import scene from "../../../miniapp/src/assets/lotteries/halloween-pumpkins-v1.webp";
import "../../../miniapp/src/halloween.css";
import type { LiveDraw } from "../types";
import "./halloween-web.css";

export default function HalloweenLiveHost({ draw, now }: { draw: LiveDraw; now: number; [key: string]: unknown }) {
  const count = draw.reveal_at.filter(value => Date.parse(value) <= now).length;
  const active = now >= Date.parse(draw.live_starts_at) && now <= Date.parse(draw.live_ends_at);
  return <article className="halloween-web-live"><img src={scene} alt="" /><div><span>{active ? "ПРЯМОЙ ЭФИР" : `ТИРАЖ №${draw.draw_number}`}</span><h2 aria-label={draw.lottery_name}><HalloweenBrand /></h2><p>3 из {draw.primary_max_number ?? 16}</p><div className="reveal-row">{Array.from({ length: draw.reveal_at.length }, (_, index) => <span key={index}>{index < count ? draw.winning_numbers?.[index] ?? "?" : "?"}</span>)}</div><p>Ваших билетов: {draw.player_ticket_count}</p>{draw.player_total_prize > 0 && <strong>Выигрыш {draw.player_total_prize.toLocaleString("ru-RU")} CAS</strong>}</div></article>;
}
