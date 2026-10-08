import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Stories } from "./Stories";
import { miniAppApi } from "./api";
import type { Publication, PublicationTemplate } from "../../shared/publications";
import fixture from "../../shared/publication-template.fixture.json";
import { fitPublicationText } from "../../shared/publications";

vi.mock("./api", () => ({ miniAppApi: { publications: vi.fn() } }));
const template = fixture as unknown as PublicationTemplate;
const first: Publication = { id: "1", lottery_code: "pulse", status: "published", revision: 2, content: { template, fields: { kicker: "Новость", title: "Первая история", value: "42 CAS", description: "Текст", fact: "" }, cta_label: "Открыть PULSE", channel_caption: "" }, published_at: "2026-10-05T00:00:00Z", created_at: "2026-10-05T00:00:00Z", updated_at: "2026-10-05T00:00:00Z" };
beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  vi.mocked(miniAppApi.publications).mockResolvedValue([first, { ...first, id: "2", lottery_code: "shadow", content: { ...first.content, template: { ...template, lottery: "shadow", lotteryLabel: "CODE" }, fields: { ...first.content.fields, title: "Вторая история" }, cta_label: "Открыть CODE" } }]);
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
});

it("shows at most ten news items and remembers viewed stories", async () => {
  vi.mocked(miniAppApi.publications).mockResolvedValue(Array.from({ length: 15 }, (_, i) => ({ ...first, id: String(i), content: { ...first.content, fields: { ...first.content.fields, title: `Новость ${i}` } } })));
  render(<Stories initData="signed" onOpen={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: /Новость 0/ }));
  expect(screen.getByText("10 историй")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Новость 10/ })).not.toBeInTheDocument();
  expect(JSON.parse(localStorage.getItem("casper-news-seen")!)).toContain("0");
});

it("loads once, navigates manually and opens the selected game's existing route", async () => {
  const onOpen = vi.fn();render(<Stories initData="signed" onOpen={onOpen} />);
  fireEvent.click(await screen.findByRole("button", { name: /Первая история/ }));
  expect(screen.getByRole("dialog")).toHaveAttribute("open");
  fireEvent.keyDown(screen.getByRole("dialog"), { key: "ArrowRight" });
  fireEvent.click(screen.getByRole("button", { name: "Открыть CODE" }));
  expect(onOpen).toHaveBeenCalledWith("shadow");
  expect(miniAppApi.publications).toHaveBeenCalledOnce();
});

it("hides an empty feed and offers an explicit retry after failure", async () => {
  vi.mocked(miniAppApi.publications).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce([]);
  render(<Stories initData="signed" onOpen={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: /повторить/ }));
  await waitFor(() => expect(screen.queryByRole("region", { name: "Новости Casper" })).not.toBeInTheDocument());
});

it("fits maximum field lengths and explicit line breaks inside the smallest safe regions", () => {
  for (const format of Object.values(template.formats)) for (const [key, box] of Object.entries(format.zones)) {
    const limits = { kicker: 50, title: 120, value: 80, description: 240, fact: 100 };
    const result = fitPublicationText("W".repeat(limits[key as keyof typeof limits]), box, format.fonts[key as keyof typeof limits]);
    expect(result.lines.length * result.size * 1.18).toBeLessThanOrEqual(box[3]);
    expect(Math.max(...result.lines.map(line => line.length)) * result.size * 1.05).toBeLessThanOrEqual(box[2]);
  }
  expect(fitPublicationText("Один\nДва", [0, 0, 500, 200], 40).lines).toEqual(["Один", "Два"]);
});

it("moves forward and back by taps and closes after the final story", async () => {
  render(<Stories initData="signed" onOpen={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: /Первая история/ }));
  fireEvent.click(screen.getByRole("button", { name: "Предыдущая история" }));
  expect(screen.getByRole("dialog")).toHaveAccessibleName("Первая история");
  fireEvent.click(screen.getByRole("button", { name: "Следующая история" }));
  expect(screen.getByRole("dialog")).toHaveAccessibleName("Вторая история");
  fireEvent.click(screen.getByRole("button", { name: "Предыдущая история" }));
  expect(screen.getByRole("dialog")).toHaveAccessibleName("Первая история");
  fireEvent.click(screen.getByRole("button", { name: "Следующая история" }));
  fireEvent.click(screen.getByRole("button", { name: "Следующая история" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("uses the fullscreen Telegram fallback and keeps the lottery action separate", async () => {
  window.Telegram = { WebApp: { initData: "signed", ready: vi.fn(), expand: vi.fn(), isFullscreen: true } };
  const onOpen = vi.fn();
  render(<Stories initData="signed" onOpen={onOpen} />);
  fireEvent.click(await screen.findByRole("button", { name: /Первая история/ }));
  expect(screen.getByRole("dialog").style.getPropertyValue("--story-telegram-top")).toBe("56px");
  fireEvent.click(screen.getByRole("button", { name: "Открыть PULSE" }));
  expect(onOpen).toHaveBeenCalledExactlyOnceWith("pulse");
  delete window.Telegram;
});

it("handles a swipe only once and does not advance on a long press", async () => {
  window.PointerEvent = MouseEvent as typeof PointerEvent;
  render(<Stories initData="signed" onOpen={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: /Первая история/ }));
  const next = screen.getByRole("button", { name: "Следующая история" });
  fireEvent.pointerDown(next, { clientX: 260, clientY: 180 });
  fireEvent.pointerUp(next, { clientX: 140, clientY: 180 });
  fireEvent.click(next);
  expect(screen.getByRole("dialog")).toHaveAccessibleName("Вторая история");
  const previous = screen.getByRole("button", { name: "Предыдущая история" });
  const clock = vi.spyOn(Date, "now").mockReturnValue(1000);
  fireEvent.pointerDown(previous, { clientX: 30, clientY: 180 });
  clock.mockReturnValue(1400);
  fireEvent.pointerUp(previous, { clientX: 30, clientY: 180 });
  fireEvent.click(previous);
  expect(screen.getByRole("dialog")).toHaveAccessibleName("Вторая история");
  clock.mockRestore();
});

it("advances automatically, preserves remaining time when paused and pauses while held", async () => {
  render(<Stories initData="signed" onOpen={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: /Первая история/ }));
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "performance"] });
  fireEvent.keyDown(screen.getByRole("dialog"), { code: "Space" });
  fireEvent.keyDown(screen.getByRole("dialog"), { code: "Space" });
  act(() => vi.advanceTimersByTime(4000));
  const next = screen.getByRole("button", { name: "Следующая история" });
  fireEvent.pointerDown(next, { clientX: 260, clientY: 180 });
  act(() => vi.advanceTimersByTime(10000));
  expect(screen.getByRole("dialog")).toHaveAccessibleName("Первая история");
  fireEvent.pointerUp(next, { clientX: 260, clientY: 180 });
  fireEvent.keyDown(screen.getByRole("dialog"), { code: "Space" });
  act(() => vi.advanceTimersByTime(10000));
  expect(screen.getByRole("dialog")).toHaveAccessibleName("Первая история");
  fireEvent.keyDown(screen.getByRole("dialog"), { code: "Space" });
  act(() => vi.advanceTimersByTime(3050));
  expect(screen.getByRole("dialog")).toHaveAccessibleName("Вторая история");
  act(() => vi.advanceTimersByTime(7050));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  vi.useRealTimers();
});

it("closes on a downward swipe, restores the viewport and has no pause icon", async () => {
  window.PointerEvent = MouseEvent as typeof PointerEvent;
  const disableVerticalSwipes = vi.fn(), enableVerticalSwipes = vi.fn();
  window.Telegram = { WebApp: { initData: "signed", ready: vi.fn(), expand: vi.fn(), isVerticalSwipesEnabled: true, disableVerticalSwipes, enableVerticalSwipes } };
  render(<Stories initData="signed" onOpen={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: /Первая история/ }));
  expect(screen.queryByRole("button", { name: /Приостановить|Продолжить истории/ })).not.toBeInTheDocument();
  expect(document.body.style.position).toBe("fixed");
  expect(disableVerticalSwipes).toHaveBeenCalledOnce();
  const next = screen.getByRole("button", { name: "Следующая история" });
  fireEvent.pointerDown(next, { clientX: 180, clientY: 100 });
  fireEvent.pointerUp(next, { clientX: 185, clientY: 220 });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(document.body.style.position).toBe("");
  expect(enableVerticalSwipes).toHaveBeenCalledOnce();
  delete window.Telegram;
});

it("does not count time spent in a hidden app when returning to a story", async () => {
  render(<Stories initData="signed" onOpen={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: /Первая история/ }));
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "performance"] });
  fireEvent.keyDown(screen.getByRole("dialog"), { code: "Space" });
  fireEvent.keyDown(screen.getByRole("dialog"), { code: "Space" });
  act(() => vi.advanceTimersByTime(3000));
  const hidden = vi.spyOn(document, "hidden", "get").mockReturnValue(true);
  fireEvent(document, new Event("visibilitychange"));
  act(() => vi.advanceTimersByTime(20000));
  hidden.mockReturnValue(false);
  fireEvent(document, new Event("visibilitychange"));
  act(() => vi.advanceTimersByTime(3000));
  expect(screen.getByRole("dialog")).toHaveAccessibleName("Первая история");
  act(() => vi.advanceTimersByTime(1100));
  expect(screen.getByRole("dialog")).toHaveAccessibleName("Вторая история");
  hidden.mockRestore();
  vi.useRealTimers();
});
