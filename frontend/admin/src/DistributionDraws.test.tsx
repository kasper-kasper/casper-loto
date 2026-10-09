import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { DistributionDraws } from "./DistributionDraws";
import { adminApi } from "./api";
import type { DistributionDraw } from "./api";
import type { Lottery } from "./types";

vi.mock("./api", () => ({ adminApi: { lotteries: vi.fn(), distributionDraws: vi.fn(), assignDistribution: vi.fn() } }));
const lottery = { id:"grand",code:"weekly",name:"Casper Grand",is_active:true } as Lottery;
const draw: DistributionDraw = {id:"draw",lottery_id:"grand",lottery_name:"Casper Grand",number:9,scheduled_at:"2099-10-10T17:00:00Z",sales_close_at:"2099-10-10T16:55:00Z",jackpot:5000000,ticket_count:145,is_distribution:false,status:"SCHEDULED",announcement_state:null,post:"Полностью распределим весь джекпот. #CasperLotto"};
beforeEach(()=>{vi.clearAllMocks();vi.mocked(adminApi.lotteries).mockResolvedValue([lottery,{...lottery,id:"dual",code:"dual",name:"Casper Dual"},{...lottery,id:"vault",code:"vault",name:"Vault"}]);vi.mocked(adminApi.distributionDraws).mockResolvedValue([draw]);vi.mocked(adminApi.assignDistribution).mockResolvedValue({...draw,is_distribution:true,announcement_state:"sent"});});

test("Dual and instant games are absent; purchased tickets remain and confirmation precedes post",async()=>{
  render(<DistributionDraws/>);
  await screen.findByText("Casper Grand · тираж №9");
  const options=within(screen.getByLabelText("Лотерея распределительного тиража")).getAllByRole("option");
  expect(options.map(o=>o.textContent)).toEqual(["Casper Grand"]);
  expect(screen.getByText("145")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button",{name:"Назначить распределительный тираж"}));
  expect(adminApi.assignDistribution).not.toHaveBeenCalled();
  expect(screen.getByText(draw.post)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button",{name:"Подтвердить и опубликовать пост"}));
  await screen.findByText("Пост опубликован");
  expect(adminApi.assignDistribution).toHaveBeenCalledExactlyOnceWith(draw);
});

test("closed sales cannot be designated",async()=>{
  vi.mocked(adminApi.distributionDraws).mockResolvedValue([{...draw,sales_close_at:"2020-01-01T00:00:00Z"}]);
  render(<DistributionDraws/>);
  await screen.findByText("Продажи закрыты — назначить распределение уже нельзя.");
  expect(screen.queryByRole("button",{name:"Назначить распределительный тираж"})).not.toBeInTheDocument();
});

test("date change clears old confirmation and loads Moscow day",async()=>{
  render(<DistributionDraws/>);
  await screen.findByText("Casper Grand · тираж №9");
  fireEvent.click(screen.getByRole("button",{name:"Назначить распределительный тираж"}));
  fireEvent.change(screen.getByLabelText("Дата распределительного тиража"),{target:{value:"2099-10-17"}});
  await waitFor(()=>expect(adminApi.distributionDraws).toHaveBeenLastCalledWith("grand","2099-10-17"));
  expect(screen.queryByRole("button",{name:"Подтвердить и опубликовать пост"})).not.toBeInTheDocument();
});
