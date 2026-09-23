import { useState, type FormEvent } from "react";
import { webApi } from "./api";
import type { Lottery, WebSession } from "./types";
import symbol from "../../miniapp/public/brand/kasper-symbol.svg";
import grand from "../../miniapp/src/assets/lotteries/kasper-grand-scene.webp";
import khan from "../../miniapp/src/assets/lotteries/khan-scene.webp";
import grob from "../../miniapp/src/assets/lotteries/grob-scene.webp";
import pll from "../../miniapp/src/assets/lotteries/pll-scene.webp";
import pss from "../../miniapp/src/assets/lotteries/pss-nature-scene.webp";
import september from "../../miniapp/src/assets/lotteries/september-embankment.jpg";

const scenes: Record<string, string> = { weekly: grand, khan, grob, pll, pss, september };
const money = (n: number) => n.toLocaleString("ru-RU");
export function Brand() { return <span className="identity"><img src={symbol} alt=""/><span>CASPER<small>LOTO · PRIVATE CLUB</small></span></span>; }

export function Login({ onDone }: { onDone: (session: WebSession) => void }) {
  const [mode, setMode] = useState<"telegram" | "login" | "register">("telegram");
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError(""); const data = new FormData(event.currentTarget);
    try {
      const result = mode === "telegram"
        ? await webApi.telegram(String(data.get("code")).replaceAll(" ", ""))
        : await (mode === "login" ? webApi.login : webApi.register)(String(data.get("username")), String(data.get("password")));
      onDone(result);
    }
    catch (e) { setError(e instanceof Error ? e.message : "Не удалось войти.") } finally { setBusy(false) }
  };
  return <main className="entrance"><div className="entrance-scene" style={{ backgroundImage: `url(${grand})` }}><Brand/><div className="entrance-copy"><span className="eyebrow">ВАШ МОМЕНТ. ВАША ИГРА.</span><h1>Удача любит<br/><em>присутствие.</em></h1><p>Знакомые игры. Новое измерение.<br/>Добро пожаловать в мир Casper Loto.</p></div><div className="entrance-footer"><span>01 — CASPER UNIVERSE</span><span>Только виртуальные CAS</span></div></div><section className="entrance-form"><span className="chapter">ВХОД В КЛУБ / 01</span><h2>{mode === "register" ? "Начало истории." : "С возвращением."}</h2><p className="muted">Ваши билеты, ваш баланс, ваш Casper.</p><div className="login-switch"><button type="button" aria-pressed={mode === "telegram"} onClick={() => { setMode("telegram"); setError("") }}>Через Telegram</button><button type="button" aria-pressed={mode !== "telegram"} onClick={() => { setMode("login"); setError("") }}>Логин и пароль</button></div><form onSubmit={event => void submit(event)}>{mode === "telegram" ? <><p className="login-instruction">Отправьте <b>/web</b> вашему боту Casper Loto и введите полученный код. Откроется тот же профиль, что и в Mini App.</p><label>Код из Telegram<input name="code" autoComplete="one-time-code" spellCheck={false} minLength={16} maxLength={32} required placeholder="16 символов"/></label></> : <><label>Логин<input name="username" autoComplete="username" minLength={3} maxLength={128} required/></label><label>Пароль<input name="password" type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} minLength={8} maxLength={256} required/></label>{mode === "register" && <p className="login-instruction">Уже играете в Telegram? Сначала войдите через Telegram, затем добавьте пароль в кабинете — так сохранится ваш баланс.</p>}</>}{error && <p role="alert" className="error">{error}</p>}<button className="primary" disabled={busy}>{busy ? "Проверяем…" : mode === "register" ? "Создать аккаунт →" : "Войти в Casper →"}</button></form>{mode !== "telegram" && <button className="text-button" onClick={() => { setMode(mode === "register" ? "login" : "register"); setError("") }}>{mode === "register" ? "Уже есть аккаунт? Войти" : "Первый раз? Зарегистрироваться"}</button>}<p className="entrance-note">Без электронной почты. У каждого игрока свой уникальный ID. CAS — игровые единицы без денежной стоимости.</p></section></main>;
}

export function AddPassword() {
  const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = new FormData(event.currentTarget); setBusy(true); try { await webApi.addPassword(String(data.get("username")), String(data.get("password"))); setMessage("Логин добавлен. Оба способа входа открывают этот же профиль.") } catch (e) { setMessage(e instanceof Error ? e.message : "Не удалось сохранить") } finally { setBusy(false) } };
  return <section className="credential-section"><div><span className="eyebrow">ОДИН ПРОФИЛЬ · ДВА СПОСОБА ВХОДА</span><h2>Добавить пароль</h2><p className="muted">После входа через Telegram вы можете создать логин для этого же аккаунта.</p></div><form onSubmit={e => void submit(e)}><label>Логин<input name="username" autoComplete="username" minLength={3} maxLength={128} required/></label><label>Новый пароль<input name="password" type="password" autoComplete="new-password" minLength={8} maxLength={256} required/></label><button className="secondary" disabled={busy}>Сохранить способ входа</button>{message && <p role="status">{message}</p>}</form></section>;
}

export function LotteryGallery({ lotteries, now, onOpen }: { lotteries: Lottery[]; now: number; onOpen: (l: Lottery) => void }) {
  const featured = lotteries.find(l => l.code === "weekly") ?? lotteries[0];
  return <><section className="editorial-intro"><span className="eyebrow">CASPER COLLECTION / ВЫБЕРИТЕ СВОЮ ИГРУ</span><h1>У каждого момента<br/>есть <em>свои числа.</em></h1><span className="editorial-index">01—{String(lotteries.length).padStart(2,"0")}</span></section>{featured && <section className="feature-scene" style={{ backgroundImage: `url(${scenes[featured.code] ?? grand})` }}><div className="scene-shade"/><div className="feature-copy"><span className="eyebrow">ГЛАВНАЯ СЦЕНА · ТИРАЖ №{featured.draw_number ?? "—"}</span><h2>{featured.name}</h2><span className="jackpot-caption">ДЖЕКПОТ</span><strong>{money(featured.jackpot)} <small>CAS</small></strong><button className="primary" onClick={() => onOpen(featured)} disabled={!featured.purchase_available}>{featured.purchase_available ? "Выбрать свои числа ↗" : "Продажи закрыты"}</button></div><span className="scene-number">{featured.primary_numbers_to_pick}<i>/{featured.primary_max_number}</i></span></section>}<div className="collection-heading"><span>ДРУГИЕ МИРЫ CASPER</span><span>РАСПИСАНИЕ · МОСКВА</span></div><section className="worlds">{lotteries.filter(l => l !== featured).map((l, i) => <article className={`world world-${l.code}`} key={l.code} style={{ backgroundImage: scenes[l.code] ? `url(${scenes[l.code]})` : undefined }}><div className="world-shade"/><span className="world-index">/{String(i + 2).padStart(2,"0")}</span><div className="world-copy"><span className="eyebrow">{l.scheduled_at ? new Intl.DateTimeFormat("ru-RU", {hour:"2-digit",minute:"2-digit",timeZone:"Europe/Moscow"}).format(new Date(l.scheduled_at)) + " МСК" : "СКОРО"}</span><h2>{l.name}</h2><p>{l.code === "bingo" ? "Своя история в каждом билете." : `${l.primary_numbers_to_pick} из ${l.primary_max_number}${l.secondary_numbers_to_pick ? ` + ${l.secondary_numbers_to_pick} из ${l.secondary_max_number}` : ""}`}</p><strong>{money(l.jackpot)} <small>CAS</small></strong><button className="world-action" onClick={() => onOpen(l)} disabled={!l.purchase_available && l.code !== "grob"}>{l.purchase_available ? "Войти в игру" : l.code === "grob" ? "Войти в крипту" : "Продажи закрыты"}<span>↗</span></button></div><span className="world-foot">{l.player_ticket_count > 0 ? `У ВАС ${l.player_ticket_count} БИЛЕТОВ` : l.scheduled_at && new Date(l.scheduled_at).getTime() > now ? "СЛЕДУЮЩИЙ ТИРАЖ" : "CASPER LOTO"}</span></article>)}</section></>;
}
