import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import App from "./App";
vi.mock("./api",()=>({ApiError:class extends Error{},webApi:{session:vi.fn().mockRejectedValue(new Error("guest"))}}));
test("offers Telegram and password access without email",async()=>{
 render(<App/>);
 expect(await screen.findByText("С возвращением.")).toBeInTheDocument();
 expect(screen.getByLabelText("Код из Telegram")).toBeInTheDocument();
 fireEvent.click(screen.getByText("Логин и пароль"));
 fireEvent.click(screen.getByText("Первый раз? Зарегистрироваться"));
 expect(screen.getByLabelText("Пароль")).toHaveAttribute("autocomplete","new-password");
 expect(screen.getByText(/Уже играете в Telegram/)).toBeInTheDocument();
 expect(screen.queryByRole("textbox",{name:/почт/i})).not.toBeInTheDocument();
});
