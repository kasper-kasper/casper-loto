import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Publications } from "./Publications";
import { adminApi } from "./api";
import type { Publication, PublicationTemplate } from "../../shared/publications";
import fixture from "../../shared/publication-template.fixture.json";

vi.mock("./api", () => ({ adminApi: { preparePublicationSuggestions: vi.fn().mockResolvedValue({ prepared: true }), publicationTemplates: vi.fn(), publicationChannel: vi.fn().mockResolvedValue({ channel: "@casper_loto", checked: false, can_post: false, delivery_enabled: false }), publications: vi.fn(), savePublication: vi.fn(), editPublication: vi.fn(), publicationAction: vi.fn() } }));
const template = fixture as unknown as PublicationTemplate;
const row: Publication = { id: "1", lottery_code: "pulse", status: "draft", revision: 1, content: { template, fields: { kicker: "", title: "Ручная новость", description: "", value: "", fact: "" }, cta_label: "Открыть лотерею", channel_caption: "#PULSE" }, published_at: null, created_at: "2026-10-05T00:00:00Z", updated_at: "2026-10-05T00:00:00Z" };
beforeEach(() => { vi.mocked(adminApi.publicationTemplates).mockResolvedValue([template]);vi.mocked(adminApi.publications).mockResolvedValue([]);vi.mocked(adminApi.savePublication).mockResolvedValue(row);vi.mocked(adminApi.publicationAction).mockResolvedValue({ ...row, status: "published", revision: 2 }); });

it("saves a private draft before explicit publication and blocks publishing unsaved edits", async () => {
  render(<Publications />);
  await screen.findByText("Нет черновиков, ожидающих решения. Автоматические события публикуются самостоятельно.");
  fireEvent.click(screen.getByRole("button", { name: "Новая публикация" }));
  fireEvent.change(await screen.findByLabelText("Заголовок"), { target: { value: "Ручная новость" } });
  fireEvent.change(screen.getByLabelText("Подпись поста для канала"), { target: { value: "#PULSE" } });
  fireEvent.click(screen.getByRole("button", { name: "Сохранить черновик" }));
  const publish = await screen.findByRole("button", { name: "Опубликовать в Mini App" });
  expect(adminApi.publicationAction).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Заголовок"), { target: { value: "Изменённая новость" } });
  expect(publish).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: /Ручная новость.*Черновик/ }));
  fireEvent.click(screen.getByRole("button", { name: "Опубликовать в Mini App" }));
  await waitFor(() => expect(adminApi.publicationAction).toHaveBeenCalledWith("1", 1, "publish"));
  expect(await screen.findByRole("button", { name: "Создать копию" })).toBeEnabled();
  await waitFor(() => expect(screen.getByLabelText("Заголовок")).toBeDisabled());
});

it("reports a failed save and keeps the editor's text", async () => {
  vi.mocked(adminApi.savePublication).mockRejectedValue(new Error("Сохранение недоступно"));
  render(<Publications />);
  await screen.findByText("Нет черновиков, ожидающих решения. Автоматические события публикуются самостоятельно.");
  fireEvent.click(screen.getByRole("button", { name: "Новая публикация" }));
  fireEvent.change(await screen.findByLabelText("Заголовок"), { target: { value: "Мой текст" } });
  fireEvent.click(screen.getByRole("button", { name: "Сохранить черновик" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Сохранение недоступно");
  expect(screen.getByLabelText("Заголовок")).toHaveValue("Мой текст");
});

it("opens ready proposals first and removes a rejected draft from the list", async () => {
  vi.mocked(adminApi.publications).mockResolvedValue([row]);
  render(<Publications />);
  expect(await screen.findByRole("button", { name: "Опубликовать" })).toBeEnabled();
  expect(screen.queryByLabelText("Заголовок")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Удалить" }));
  await waitFor(() => expect(adminApi.publicationAction).toHaveBeenCalledWith("1", 1, "delete"));
  expect(screen.queryByRole("button", { name: "Отредактировать" })).not.toBeInTheDocument();
});

it("edits ready event copy while keeping calculated values read only", async () => {
  vi.mocked(adminApi.publications).mockResolvedValue([{ ...row, event_type: template.subcategory, content: { ...row.content, delivery: { state: "approval_required" } } }]);
  render(<Publications />);
  fireEvent.click(await screen.findByRole("button", { name: "Отредактировать" }));
  expect(screen.getByLabelText("Заголовок")).toBeEnabled();
  expect(screen.getByLabelText("Сумма / число / результат")).toHaveAttribute("readonly");
  expect(screen.getByLabelText("Событие")).toBeDisabled();
});
