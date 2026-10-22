import { useEffect, useRef, useState } from "react";
import { ApiError, webApi } from "./api";
import { displayedNumber, FAST_ORDER, fastName, fastPresentation, randomFastTicket, timeLeft } from "./fast-model";
import type { LiveFeed, Lottery } from "./types";
import flashArt from "./assets/fast/flash.jpg";
import codeArt from "./assets/fast/code.jpg";
import pulseArt from "./assets/fast/pulse.jpg";

const art: Record<string, string> = { flash: flashArt, shadow: codeArt, pulse: pulseArt };
const tagline: Record<string, string> = { flash: "Пять чисел. Один джекпот.", shadow: "Пять цифр. Ваш секрет.", pulse: "Два поля. Секретный шифр." };
const cas = (n: number) => `${n.toLocaleString("ru-RU")} CAS`;
type Pending = { key: string; numbers: number[]; draw: number | null; price: number | null };

function readPending(key: string): Pending | null {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(key) ?? "null");
    if (value && typeof value === "object" && "key" in value && "numbers" in value
      && typeof value.key === "string" && Array.isArray(value.numbers)) return value as Pending;
  } catch { /* A corrupt local retry record must not prevent loading the page. */ }
  return null;
}

export function FastBroadcast({ feed, lottery, now, failed = false }: {
  feed: LiveFeed | null; lottery: Lottery; now: number; failed?: boolean;
}) {
  const stale = !feed || now - Date.parse(feed.server_time) > 15000;
  const state = fastPresentation(stale ? null : feed, now);
  const draw = state.draw;
  const active = ["prelive", "starting", "revealing", "result"].includes(state.phase);
  const slotCount = draw?.winning_numbers?.length || draw?.reveal_at.length
    || lottery.primary_numbers_to_pick + lottery.secondary_numbers_to_pick;
  const result = state.phase === "result";
  const status = failed || stale ? "Связь с эфиром" : result ? "Результат"
    : state.phase === "revealing" ? "Прямой эфир" : state.phase === "starting" ? "Ждём результат сервера"
      : state.phase === "prelive" ? "Сейчас начнётся" : "Следующий эфир";
  const recent = feed?.recent_completed.find(d => Date.parse(d.live_ends_at) <= now && d.winning_numbers?.length);
  return <section className={`fast-broadcast phase-${state.phase}`} aria-label={`Эфир ${fastName(lottery.code)}`}>
    <header><span className={active ? "broadcast-status active" : "broadcast-status"}><i/>{status}</span>
      <span>{draw ? `№${draw.draw_number}` : "—"}</span></header>
    <div className={`broadcast-slots ${lottery.code === "shadow" ? "cipher-slots" : ""}`} aria-label="Числа тиража">
      {Array.from({ length: slotCount }, (_, index) => <span key={`${draw?.draw_number}-${index}-${state.numbers[index] ?? "empty"}`}
        className={`${state.numbers[index] !== undefined ? "is-revealed" : ""} ${lottery.code === "pulse" && index >= (draw?.primary_numbers_to_pick || lottery.primary_numbers_to_pick) ? "is-secondary" : ""}`}>
        <small>{lottery.code === "pulse" && state.numbers[index] > 1000 ? "ШИФР" : lottery.code === "pulse" && index >= (draw?.primary_numbers_to_pick || lottery.primary_numbers_to_pick) ? "PULSE" : `0${index + 1}`}</small>
        <b>{draw && state.numbers[index] !== undefined ? displayedNumber(draw, state.numbers[index], index) : "—"}</b>
      </span>)}
    </div>
    <div className="broadcast-track" aria-hidden="true"><i className={active ? "scanning" : ""}/></div>
    <div className="broadcast-caption" aria-live="polite">
      {failed || stale ? <span>{failed ? "Не удалось обновить эфир. Повторяем подключение…" : "Синхронизируем эфир…"}</span>
        : result ? <><strong>{draw!.player_ticket_count === 0 ? "Вы не участвовали" : draw!.player_total_prize > 0 ? `+ ${cas(draw!.player_total_prize)}` : "Без выигрыша"}</strong><span>Итог тиража №{draw!.draw_number}</span></>
          : active ? <><strong>{state.phase === "prelive" ? `Начало через ${timeLeft(draw!.scheduled_at, now)}` : state.phase === "starting" ? "Сигнал готовится" : `${state.numbers.length} из ${slotCount} чисел`}</strong><span>Ваших билетов в эфире: {draw!.player_ticket_count}</span></>
            : <><strong>{draw ? timeLeft(draw.scheduled_at, now) : "Расписание готовится"}</strong><span>Числа появятся здесь автоматически</span></>}
    </div>
    {recent && <div className="broadcast-previous"><span>ПРОШЛЫЙ · №{recent.draw_number}</span><b>{recent.winning_numbers!.map((n, i) => displayedNumber(recent, n, i)).join(" · ")}</b></div>}
  </section>;
}

function FastStation({ lottery, feed, failed, now, balance, userId, onBought, onTickets }: {
  lottery: Lottery; feed: LiveFeed | null; failed: boolean; now: number; balance: number; userId: string;
  onBought: (message: string) => void; onTickets: () => void;
}) {
  const storageKey = `casper:fast-pending:${userId}:${lottery.code}`;
  const [pending, setPending] = useState<Pending | null>(() => readPending(storageKey));
  const [choosing, setChoosing] = useState(false);
  const [main, setMain] = useState<number[]>([]);
  const [special, setSpecial] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const inFlight = useRef(false);
  const code = lottery.ruleset_code.startsWith("code_");
  const stalePending = pending && (pending.draw !== lottery.draw_number || pending.price !== lottery.ticket_price);
  const open = lottery.purchase_available && lottery.sales_close_at !== null && Date.parse(lottery.sales_close_at) > now;
  const affordable = lottery.ticket_price !== null && balance >= lottery.ticket_price;
  const valid = main.length === lottery.primary_numbers_to_pick && special.length === lottery.secondary_numbers_to_pick;
  const remember = (value: Pending | null) => {
    if (value) sessionStorage.setItem(storageKey, JSON.stringify(value)); else sessionStorage.removeItem(storageKey);
    setPending(value);
  };
  const buy = async (manual: boolean) => {
    if (inFlight.current || !open || stalePending || (!pending && (!affordable || (manual && !valid)))) return;
    inFlight.current = true; setBusy(true); setError(""); setMessage("");
    let submitted = false;
    try {
      const current = (await webApi.dashboard()).lotteries.find(l => l.code === lottery.code);
      if (!current?.purchase_available || current.draw_number !== lottery.draw_number || current.ticket_price !== lottery.ticket_price
        || !current.sales_close_at || Date.parse(current.sales_close_at) <= now) {
        throw new Error("Тираж или цена обновились. Дождитесь обновления экрана перед покупкой.");
      }
      const attempt = pending ?? { key: crypto.randomUUID(), draw: lottery.draw_number, price: lottery.ticket_price,
        numbers: manual ? [...main, ...special.map(n => n + lottery.secondary_storage_offset)] : randomFastTicket(current) };
      remember(attempt); // Persist before sending, so retries and reloads cannot create duplicate tickets.
      submitted = true;
      const result = await webApi.purchase(lottery.code, [attempt.numbers], attempt.key, 1);
      remember(null); setMain([]); setSpecial([]); setChoosing(false);
      setMessage(`Билет куплен · ${cas(result.total_cost)}. Тираж №${attempt.draw}`);
      onBought(`${fastName(lottery.code)}: билет куплен. Списано ${cas(result.total_cost)}.`);
    } catch (reason) {
      const definitive = reason instanceof ApiError && reason.status < 500 && ![408, 429].includes(reason.status);
      if (submitted && definitive) remember(null);
      setError(submitted && !definitive ? "Ответ не получен. Повторите тот же запрос — повторного списания не будет."
        : reason instanceof Error ? reason.message : "Не удалось купить билет.");
    } finally { inFlight.current = false; setBusy(false) }
  };
  const select = (value: number, secondary = false) => {
    const list = secondary ? special : main; const set = secondary ? setSpecial : setMain;
    const limit = secondary ? lottery.secondary_numbers_to_pick : lottery.primary_numbers_to_pick;
    if (code) { if (list.length < limit) set([...list, value]); return }
    set(list.includes(value) ? list.filter(n => n !== value) : list.length < limit ? [...list, value].sort((a, b) => a - b) : list);
  };
  const freshFeed = feed && now - Date.parse(feed.server_time) <= 15000 ? feed : null;
  const phase = fastPresentation(freshFeed, now).phase;
  const broadcasting = ["prelive", "starting", "revealing", "result"].includes(phase);
  return <article id={`fast-${lottery.code}`} className={`fast-station station-${lottery.code} ${broadcasting ? "is-broadcasting" : ""} ${choosing ? "is-choosing" : ""}`} aria-labelledby={`title-${lottery.code}`}>
    <div className="station-identity"><span>0{FAST_ORDER.indexOf(lottery.code) + 1} / CASPER FAST</span><span>{lottery.draw_number ? `ТИРАЖ №${lottery.draw_number}` : "СКОРО"}</span></div>
    <div className="station-scene"><img src={art[lottery.code]} alt="" fetchPriority="high"/><div className="station-sheen"/>
      <div className="station-title"><h2 id={`title-${lottery.code}`}>{fastName(lottery.code)}</h2><p>{tagline[lottery.code]}</p></div>
      {lottery.code === "pulse" && <svg className="station-heartbeat" viewBox="0 0 400 80" aria-hidden="true"><path d="M0 40H92L111 28L125 42L147 5L170 73L191 30L209 40H400" pathLength="100"/></svg>}
      {lottery.code === "shadow" && <div className="station-cipher" aria-hidden="true">{Array.from({ length: lottery.primary_numbers_to_pick }, (_, index) => <i key={index}/>)}</div>}
      <div className="scene-atmosphere" aria-hidden="true"><i/><i/><i/></div>
      <div className="station-format">{code ? `${lottery.primary_numbers_to_pick} ЦИФР · ПОРЯДОК ВАЖЕН` : `${lottery.primary_numbers_to_pick} из ${lottery.primary_max_number}${lottery.secondary_numbers_to_pick ? ` + ${lottery.secondary_numbers_to_pick} из ${lottery.secondary_max_number}` : ""}${lottery.code === "pulse" ? " · ШИФР 001–199" : ""}`}</div>
      {choosing && <fieldset className="fast-selector" disabled={busy || !!pending} hidden={broadcasting}><legend>{code ? "Введите код · повторы разрешены" : "Ваши числа"}</legend>
        {code && <div className="chosen-code">{Array.from({ length: lottery.primary_numbers_to_pick }, (_, i) => <b key={i}>{main[i] ?? "—"}</b>)}<button aria-label="Удалить последнюю цифру" onClick={() => setMain(main.slice(0, -1))}>⌫</button></div>}
        <div className="fast-number-field">{Array.from({ length: code ? 10 : lottery.primary_max_number }, (_, i) => i + (code ? 0 : 1)).map(n => <button type="button" key={n} aria-label={`${code ? "Цифра" : "Число"} ${n}`} aria-pressed={!code && main.includes(n)} onClick={() => select(n)}>{n}</button>)}</div>
        {lottery.secondary_numbers_to_pick > 0 && <><p>PULSE · {special.length}/{lottery.secondary_numbers_to_pick}</p><div className="fast-number-field special">{Array.from({ length: lottery.secondary_max_number }, (_, i) => i + 1).map(n => <button type="button" key={n} aria-label={`Pulse-число ${n}`} aria-pressed={special.includes(n)} onClick={() => select(n, true)}>{n}</button>)}</div></>}
        {!code && <p>Выбрано {main.length}/{lottery.primary_numbers_to_pick}{special.length ? ` + ${special.length}/${lottery.secondary_numbers_to_pick}` : ""}</p>}
      </fieldset>}
      <div className="scene-transmission" hidden={choosing && !broadcasting}><FastBroadcast feed={feed} lottery={lottery} now={now} failed={failed}/></div>
    </div>
    <div className="station-controls"><div className="station-stakes"><div><span>ДЖЕКПОТ</span><strong>{lottery.jackpot.toLocaleString("ru-RU")} <small>CAS</small></strong></div><div><span>{open ? "ДО ЗАКРЫТИЯ" : "ПРОДАЖИ"}</span><b>{open ? timeLeft(lottery.sales_close_at, now) : "ЗАКРЫТЫ"}</b></div></div>
      <button className="station-buy" disabled={busy || !open || !!stalePending || (!pending && (!affordable || (choosing && !valid)))} onClick={() => void buy(choosing)}>
        <span>{busy ? "Покупаем…" : pending ? "Повторить запрос" : choosing ? "Купить выбранный билет" : "Купить случайный билет"}</span><b>{cas(lottery.ticket_price ?? 0)} <i>↗</i></b>
      </button>
      <button className="station-choose" disabled={busy || !!pending || !open} aria-expanded={choosing} onClick={() => { setChoosing(!choosing); setError("") }}>{choosing ? "← Вернуться к случайному билету" : "Выбрать числа самостоятельно"}<span>{choosing ? "" : "+"}</span></button>
      <div className="station-purchase-note"><span>{!open ? "Ждём следующего раунда" : !affordable ? "Недостаточно CAS" : "1 нажатие — 1 билет"}</span><button onClick={onTickets}>Мои билеты · {lottery.player_ticket_count} ↗</button></div>
      {message && <p className="station-receipt" role="status">{message}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {pending && (!open || stalePending) && <div className="fast-retry-warning" role="alert"><p>У предыдущей покупки нет подтверждения. Сначала проверьте билеты и баланс, чтобы не купить лишний билет.</p><button onClick={onTickets}>Проверить билеты ↗</button><button onClick={() => { remember(null); setError("") }}>Я проверил — разрешить новую покупку</button></div>}
    </div>
  </article>;
}

export function FastExperience({ lotteries, now, balance, userId, onBought, onTickets }: {
  lotteries: Lottery[]; now: number; balance: number; userId: string;
  onBought: (message: string) => void; onTickets: () => void;
}) {
  const [feeds, setFeeds] = useState<Record<string, LiveFeed>>({});
  const [failures, setFailures] = useState<Record<string, boolean>>({});
  const [paused, setPaused] = useState(false);
  useEffect(() => {
    let cancelled = false; let polling = false;
    const poll = async () => {
      if (polling || document.hidden) return;
      polling = true;
      await Promise.all(FAST_ORDER.map(async code => {
        try {
          const feed = await webApi.live("fast", code);
          if (!cancelled) {
            setFeeds(current => !current[code] || Date.parse(current[code].server_time) <= Date.parse(feed.server_time) ? { ...current, [code]: feed } : current);
            setFailures(current => ({ ...current, [code]: false }));
          }
        } catch { if (!cancelled) setFailures(current => ({ ...current, [code]: true })) }
      }));
      polling = false;
    };
    const visible = () => { if (!document.hidden) void poll() };
    void poll(); const timer = window.setInterval(() => void poll(), 3000);
    document.addEventListener("visibilitychange", visible);
    return () => { cancelled = true; window.clearInterval(timer); document.removeEventListener("visibilitychange", visible) };
  }, []);
  const ordered = FAST_ORDER.flatMap(code => lotteries.filter(l => l.code === code));
  return <section className={`fast-room ${paused ? "motion-paused" : ""}`}>
    <header className="fast-room-heading"><div><span className="eyebrow">ТРИ ИГРЫ · ОДИН ЭКРАН</span><h1>В своём <em>ритме.</em><span>FAST</span></h1></div><div><p>Выберите игру. Купите билет.<br/>Следите за эфиром прямо здесь.</p><button aria-pressed={paused} onClick={() => setPaused(!paused)}>{paused ? "Включить анимацию" : "Остановить анимацию"}</button></div></header>
    <nav className="fast-jump" aria-label="Быстрый переход к игре">{ordered.map(l => <a href={`#fast-${l.code}`} key={l.code}><i className={`dot-${l.code}`}/>{fastName(l.code)}<span>{timeLeft(l.scheduled_at, now)}</span></a>)}</nav>
    <div className="fast-stations">{ordered.map(lottery => <FastStation key={`${userId}:${lottery.code}`} lottery={lottery} feed={feeds[lottery.code] ?? null} failed={failures[lottery.code] ?? false} now={now} balance={balance} userId={userId} onBought={onBought} onTickets={onTickets}/>)}</div>
    {!ordered.length && <p className="fast-empty">Загружаем расписание Fast…</p>}
    <div className="fast-room-foot"><span>СЛУЧАЙНЫЙ ВЫБОР И СВОИ ЧИСЛА — ОДНИ ПРАВИЛА ИГРЫ.</span><span>ЭФИР СИНХРОНИЗИРОВАН С СЕРВЕРОМ · ВРЕМЯ МСК</span></div>
  </section>;
}
