import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { miniAppApi } from "./api";
import { AuroraView } from "./AuroraView";
import { VaultView } from "./VaultView";
import { KasperLiveView } from "./KasperLiveView";
vi.mock("./api", () => ({ ApiError: class extends Error {}, miniAppApi: {
  auroraHistory: vi.fn(), auroraPurchase: vi.fn(), vaultHistory: vi.fn(), vaultPurchase: vi.fn(), kasperLiveHistory: vi.fn(), kasperLivePurchase: vi.fn(),
} }));
vi.mock("./telegram", () => ({ errorHaptic: vi.fn(), selectionHaptic: vi.fn(), successHaptic: vi.fn() }));
const games = [
  { name: "LIVE", View: KasperLiveView, history: miniAppApi.kasperLiveHistory, purchase: miniAppApi.kasperLivePurchase, price: 2000 },
  { name: "Aurora", View: AuroraView, history: miniAppApi.auroraHistory, purchase: miniAppApi.auroraPurchase, price: 3000 },
  { name: "Vault", View: VaultView, history: miniAppApi.vaultHistory, purchase: miniAppApi.vaultPurchase, price: 30000 },
];
const batch=(price:number,quantity:number,number:number)=>({operation_id:`op-${number}`,tickets:Array.from({length:quantity},(_,i)=>({id:`${number+i}`,public_number:number+i,symbols:[1,2,3],prize_amount:0})),total_cost:price*quantity,total_prize:0,balance_after:90000,already_processed:false});
beforeEach(()=>{vi.clearAllMocks();vi.spyOn(HTMLCanvasElement.prototype,"getContext").mockReturnValue(null);for(const game of games)vi.mocked(game.history).mockResolvedValue([]);});
it.each([1, 3])("Vault requires the new full price for %i tickets", async quantity => {
  const price = quantity * 30000;
  const props = { initData: "signed", onClose: vi.fn(), onSettled: vi.fn() };
  const { rerender } = render(<VaultView {...props} balance={price - 1} />);
  if (quantity === 3) fireEvent.click(screen.getByRole("button", { name: /3 билета.*Откры/ }));
  const button = screen.getByRole("button", { name: quantity === 3 ? /Купить 3 билета/ : /Купить билет/ });
  expect(button).toHaveTextContent(quantity === 3 ? /90\s*000/ : /30\s*000/);
  expect(button).toBeDisabled();
  fireEvent.click(button);
  expect(miniAppApi.vaultPurchase).not.toHaveBeenCalled();
  expect(screen.queryByText("Стоимость билета")).not.toBeInTheDocument();
  rerender(<VaultView {...props} balance={price} />);
  expect(button).toBeEnabled();
});
for(const {name,View,purchase,price} of games){
  for(const quantity of [1,3]) it(`${name} buys another ${quantity} directly and disables duplicate clicks`,async()=>{
    const api=vi.mocked(purchase);api.mockResolvedValueOnce(batch(price,quantity,100));
    let resolve!:(value:ReturnType<typeof batch>)=>void;
    api.mockImplementationOnce(()=>new Promise(done=>{resolve=done;}));
    render(<View initData="signed" balance={100000} onClose={vi.fn()} onSettled={vi.fn()} />);
    if(quantity===3)fireEvent.click(screen.getByRole("button",{name:/3 билета.*Откры/}));
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:quantity===3?/Купить 3 билета/:/Купить билет/}));});
    fireEvent.click(screen.getByRole("button",{name:quantity===3?/Открыть все/:/^Открыть билет[\s✧✦]*$/}));
    fireEvent.click(screen.getByRole("button",{name:/Купить ещё/}));
    const loading=screen.getByRole("button",{name:/Готовим билеты|Печатаем/});expect(loading).toBeDisabled();fireEvent.click(loading);
    expect(api).toHaveBeenCalledTimes(2);expect(api.mock.calls[1][1]).toBe(quantity);expect(api.mock.calls[1][2]).not.toBe(api.mock.calls[0][2]);
    expect(screen.queryByRole("group",{name:"Количество билетов"})).not.toBeInTheDocument();
    await act(async()=>{resolve(batch(price,quantity,200));});
    expect(screen.getByRole("article",{name:"Билет № 200"})).toHaveClass("sealed");
  });
  it(`${name} keeps the previous result, retries unknown repeat with same key and respects updated balance`,async()=>{
    const api=vi.mocked(purchase);api.mockResolvedValueOnce(batch(price,1,100)).mockRejectedValueOnce(new Error("timeout")).mockResolvedValueOnce(batch(price,1,200));
    const props={initData:"signed",onClose:vi.fn(),onSettled:vi.fn()};const {rerender}=render(<View {...props} balance={100000} />);
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:/Купить билет/}));});fireEvent.click(screen.getByRole("button",{name:/^Открыть билет[\s✧✦]*$/}));
    rerender(<View {...props} balance={price-1} />);expect(screen.getByRole("button",{name:/Купить ещё/})).toBeDisabled();
    rerender(<View {...props} balance={100000} />);
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:/Купить ещё/}));});
    expect(screen.getByRole("alert")).toHaveTextContent("Повторите запрос");expect(screen.getByRole("article",{name:"Билет № 100"})).toHaveClass("revealed");
    const key=api.mock.calls[1][2];await act(async()=>{fireEvent.click(screen.getByRole("button",{name:/Повторить запрос/}));});
    expect(api).toHaveBeenLastCalledWith("signed",1,key);expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByRole("article",{name:"Билет № 200"})).toHaveClass("sealed");
  });
}
