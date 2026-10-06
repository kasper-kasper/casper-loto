import { useEffect, useRef, useState } from "react";
import { adminApi } from "./api";
import type { Publication, PublicationFields, PublicationTemplate, TextField } from "../../shared/publications";
import { PublicationArtwork } from "./PublicationArtwork";
import "./publications.css";

const emptyFields: PublicationFields = { kicker: "", title: "", description: "", value: "", fact: "" };
const labels: Record<TextField, string> = { kicker: "Рубрика", title: "Заголовок", description: "Краткое пояснение", value: "Сумма / число / результат", fact: "Дополнительный факт" };
const limits: Record<TextField, number> = { kicker: 50, title: 120, description: 240, value: 80, fact: 100 };
const statusLabels = { draft: "Черновик", published: "В Mini App", archived: "Снято с показа" };

export function Publications() {
  const [templates, setTemplates] = useState<PublicationTemplate[]>([]), [rows, setRows] = useState<Publication[]>([]);
  const [game, setGame] = useState("pulse"), [event, setEvent] = useState("A1.1"), [templateId, setTemplateId] = useState("");
  const [fields, setFields] = useState<PublicationFields>(emptyFields), [cta, setCta] = useState("Открыть лотерею"), [caption, setCaption] = useState("");
  const [selected, setSelected] = useState<Publication | null>(null), [draftId, setDraftId] = useState(() => crypto.randomUUID());
  const [dirty, setDirty] = useState(false), [busy, setBusy] = useState(false), [loading, setLoading] = useState(true), [error, setError] = useState(""), [notice, setNotice] = useState(""), [more, setMore] = useState(false);
  const preview = useRef<HTMLDivElement>(null);
  const [channel, setChannel] = useState<{ channel: string | null; delivery_enabled: boolean; checked: boolean; can_post: boolean; bot_username?: string; error?: string } | null>(null);
  useEffect(() => { let active = true;void adminApi.publicationChannel().then(value => { if (active) setChannel(value); }).catch(() => undefined);return () => { active = false; }; }, []);
  useEffect(() => { let active = true;Promise.all([adminApi.publicationTemplates(), adminApi.publications()]).then(([library, publications]) => { if (!active) return;setTemplates(library);setTemplateId(library[0]?.id ?? "");setGame(library[0]?.lottery ?? "pulse");setRows(publications);setMore(publications.length === 30); }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : "Не удалось загрузить публикации."); }).finally(() => { if (active) setLoading(false); });return () => { active = false; }; }, []);
  const template = selected && selected.status !== "draft" ? selected.content.template : templates.find(item => item.id === templateId);
  const editable = !selected || (selected.status === "draft" && !selected.event_type);
  const games = [...new Map(templates.map(item => [item.lottery, item.lotteryLabel])).entries()];
  const available = templates.filter(item => item.lottery === game);
  const events = [...new Map(available.map(item => [item.subcategory, item.subcategoryLabel])).entries()];
  const choices = available.filter(item => item.subcategory === event);
  function changeSelection(nextGame: string, nextEvent?: string) { const gameTemplates = templates.filter(item => item.lottery === nextGame);const actualEvent = nextEvent ?? gameTemplates[0]?.subcategory ?? "";setGame(nextGame);setCta(nextGame === "casper-loto" ? "Открыть Casper Loto" : "Открыть лотерею");setEvent(actualEvent);setTemplateId(gameTemplates.find(item => item.subcategory === actualEvent)?.id ?? "");setDirty(true); }
  function open(row: Publication) { setSelected(row);setFields(row.content.fields);setCta(row.content.cta_label);setCaption(row.content.channel_caption);setGame(row.lottery_code);setEvent(row.content.template.subcategory);setTemplateId(row.content.template.id);setDirty(false);setNotice("");setError(""); }
  function fresh(copy = false) { setSelected(null);setDraftId(crypto.randomUUID());setDirty(true);setNotice("");if (!copy) { setFields(emptyFields);setCaption("");setCta("Открыть лотерею");changeSelection(templates[0]?.lottery ?? "pulse"); } }
  function apply(row: Publication) { setRows(current => [row, ...current.filter(item => item.id !== row.id)]);open(row); }
  async function perform(operation: () => Promise<void>) { setBusy(true);setError("");setNotice("");try { await operation(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось сохранить публикацию."); } finally { setBusy(false); } }
  async function save() { if (!template) return;await perform(async () => { const payload = { template_id: template.id, fields, cta_label: cta, channel_caption: caption };const row = selected ? await adminApi.editPublication(selected.id, selected.revision, payload) : await adminApi.savePublication(draftId, payload);apply(row);setNotice("Черновик сохранён. Он ещё не виден игрокам."); }); }
  async function transition(action: "publish" | "archive") { if (!selected) return;await perform(async () => { const row = await adminApi.publicationAction(selected.id, selected.revision, action);apply(row);setNotice(action === "publish" ? "Story опубликована в Mini App." : "Публикация снята с показа."); }); }
  async function downloadPost() { const svg = preview.current?.querySelector('[data-post-preview] svg');if (!svg || !template) return;await perform(async () => {
    const clone = svg.cloneNode(true) as SVGSVGElement;const background = clone.querySelector('image');if (!background) return;
    const response = await fetch(template.formats.post.background);if (!response.ok) throw new Error("Не удалось загрузить фон.");
    const blob = await response.blob();const data = await new Promise<string>((resolve, reject) => { const reader = new FileReader();reader.onload = () => resolve(String(reader.result));reader.onerror = reject;reader.readAsDataURL(blob); });background.setAttribute('href', data);clone.setAttribute('width', '1200');clone.setAttribute('height', '900');
    const source = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: 'image/svg+xml' }));try { const img = new Image();img.src = source;await img.decode();const canvas = document.createElement('canvas');canvas.width = 1200;canvas.height = 900;canvas.getContext('2d')!.drawImage(img, 0, 0);const output = await new Promise<Blob>((resolve, reject) => canvas.toBlob(result => result ? resolve(result) : reject(new Error('Не удалось экспортировать пост.')), 'image/png'));const url = URL.createObjectURL(output);const a = document.createElement('a');a.href = url;a.download = `${selected?.id ?? draftId}-post.png`;a.click();window.setTimeout(() => URL.revokeObjectURL(url), 1000); } finally { URL.revokeObjectURL(source); }
  }); }
  return <section className="publication-editor"><header><div><h2>Stories и посты</h2><p>События A и B поступают в общую очередь. Рассчитанные черновики принимаются отдельно.</p></div><button type="button" onClick={() => fresh()} disabled={busy}>Новая публикация</button></header>
    <div className="publication-channel"><p>Канал: {channel?.channel ?? "проверка подключения"}. {channel?.delivery_enabled ? "Автопубликация включена." : "Автопубликация выключена."}</p><button type="button" disabled={busy} onClick={() => void perform(async () => setChannel(await adminApi.publicationChannel(true)))}>Проверить права бота</button>{channel?.checked && <p role="status">{channel.error ?? (channel.can_post ? `Бот @${channel.bot_username} может публиковать.` : "Боту нужно право публикации сообщений в канале.")}</p>}</div>
    {error && <p role="alert" className="error">{error}</p>}{notice && <p role="status">{notice}</p>}{loading ? <p>Загружаем библиотеку…</p> : <>
    <div className="publication-editor-grid"><form onSubmit={event => { event.preventDefault();void save(); }}><fieldset disabled={busy || !editable}>
      <label>Лотерея<select value={game} onChange={e => changeSelection(e.target.value)}>{games.map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></label>
      <label>Событие<select value={event} onChange={e => changeSelection(game, e.target.value)}>{events.map(([code, name]) => <option key={code} value={code}>{code} · {name}</option>)}</select></label>
      <label>Композиция<select value={templateId} onChange={e => { setTemplateId(e.target.value);setDirty(true); }}>{choices.map(item => <option key={item.id} value={item.id}>{item.compositionLabel}</option>)}</select></label>
      {(Object.keys(labels) as TextField[]).map(key => <label key={key}>{labels[key]}<textarea rows={key === "description" ? 3 : 2} required={key === "title"} maxLength={limits[key]} value={fields[key]} onChange={e => { setFields(current => ({ ...current, [key]: e.target.value }));setDirty(true); }} /></label>)}
      <label>Кнопка Stories<input value={cta} required maxLength={40} onChange={e => { setCta(e.target.value);setDirty(true); }} /></label>
      <label>Подпись поста для канала<textarea rows={4} maxLength={1000} value={caption} onChange={e => { setCaption(e.target.value);setDirty(true); }} /></label>
      <small>Подпись сохраняется отдельно от изображения. Рассчитанные факты защищены от ручного изменения.</small>
      <button type="submit" disabled={!template || !fields.title.trim() || !cta.trim()}>Сохранить черновик</button>
    </fieldset></form>
    <div className="publication-previews" ref={preview}>{template && <><div><h3>Stories · 9:16</h3><PublicationArtwork template={template} fields={fields} ctaLabel={cta} /><p>Переход: {template.lotteryLabel}</p></div><div data-post-preview><h3>Пост · 4:3</h3><PublicationArtwork template={template} fields={fields} format="post" /><button type="button" disabled={busy || !fields.title.trim()} onClick={() => void downloadPost()}>Скачать пост PNG</button></div></>}</div></div>
    <div className="publication-actions">{selected && <><b>{statusLabels[selected.status]}</b>{selected.status === "draft" && <button type="button" disabled={busy || dirty} onClick={() => void transition("publish")}>{selected.event_type ? "Принять и отправить в канал" : "Опубликовать в Mini App"}</button>}{selected.status !== "archived" && <button type="button" disabled={busy} onClick={() => void transition("archive")}>Снять с показа</button>}<button type="button" disabled={busy} onClick={() => fresh(true)}>Создать копию</button></>}{dirty && selected?.status === "draft" && <small>Сохраните изменения перед публикацией.</small>}</div>
    <section className="publication-history"><h3>Публикации</h3>{rows.length ? rows.map(row => <button type="button" className={selected?.id === row.id ? "selected" : ""} key={row.id} disabled={busy} onClick={() => open(row)}><span>{row.content.template.lotteryLabel}</span><strong>{row.content.fields.title}</strong><small>{statusLabels[row.status]}</small></button>) : <p>Создайте первую публикацию. Черновики видны только вам.</p>}{more && <button type="button" disabled={busy} onClick={() => void perform(async () => { const page = await adminApi.publications(rows.at(-1)?.id);setRows(current => [...current, ...page.filter(row => !current.some(item => item.id === row.id))]);setMore(page.length === 30); })}>Показать ещё</button>}</section>
    </>}
  </section>;
}

