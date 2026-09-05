import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import App from "./App";
vi.mock("./api",()=>({ApiError:class extends Error{},webApi:{session:vi.fn().mockRejectedValue(new Error("guest"))}}));
test("shows simple browser login and registration",async()=>{render(<App/>);expect(await screen.findByText("С возвращением")).toBeInTheDocument();expect(screen.getByText("Первый раз? Зарегистрироваться")).toBeInTheDocument()});
