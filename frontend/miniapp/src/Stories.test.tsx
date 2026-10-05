import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  vi.mocked(miniAppApi.publications).mockResolvedValue([first, { ...first, id: "2", lottery_code: "shadow", content: { ...first.content, template: { ...template, lottery: "shadow", lotteryLabel: "CODE" }, fields: { ...first.content.fields, title: "Вторая история" }, cta_label: "Открыть CODE" } }]);
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
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
