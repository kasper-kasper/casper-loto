import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Collection } from "./Collection";
import { miniAppApi } from "./api";
import type { CollectionState } from "./collectionTypes";
import { AchievementRewards } from "./AchievementRewards";
import { AchievementBadge } from "./AchievementBadge";

vi.mock("./api",()=>({miniAppApi:{collection:vi.fn(),chooseCollection:vi.fn()}}));
afterEach(()=>vi.clearAllMocks());
const data:CollectionState={active_badge:null,active_theme:null,items:[
  {code:"badge:flash",kind:"badge",title:"FLASH",game:"flash",description:"Удар молнии",unlocked:true,unlocked_at:"2026-10-20T10:00:00Z"},
  {code:"badge:casper-master",kind:"badge",title:"Каспер, подвинься",game:"casper-master",description:"Все десять",unlocked:false,unlocked_at:null},
  {code:"theme:gold",kind:"theme",title:"Золотая",game:"",description:"Первое легендарное",unlocked:true,unlocked_at:"2026-10-20T10:00:00Z"},
  {code:"theme:beyond",kind:"theme",title:"За гранью",game:"",description:"Все десять",unlocked:false,unlocked_at:null},
]};

it("selects an owned badge, preserves it when choosing a theme and clears the theme",async()=>{
  vi.mocked(miniAppApi.collection).mockResolvedValue(data);
  vi.mocked(miniAppApi.chooseCollection).mockImplementation(async(_init,badge,theme)=>({active_badge:badge,active_theme:theme}));
  render(<Collection initData="fixture" onBack={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button",{name:"Выбрать: FLASH"}));
  await waitFor(()=>expect(miniAppApi.chooseCollection).toHaveBeenCalledWith("fixture","badge:flash",null));
  expect(await screen.findByRole("button",{name:"Выбрано: FLASH"})).toBeDisabled();
  expect(screen.getByRole("button",{name:"Выбрать: Каспер, подвинься"})).toBeDisabled();
  fireEvent.click(screen.getByRole("button",{name:"Темы профиля"}));
  fireEvent.click(screen.getByRole("button",{name:"Выбрать: Золотая"}));
  await waitFor(()=>expect(miniAppApi.chooseCollection).toHaveBeenLastCalledWith("fixture","badge:flash","theme:gold"));
  await screen.findByRole("button",{name:"Выбрано: Золотая"});
  fireEvent.click(screen.getByRole("button",{name:"Стандартная тема"}));
  await waitFor(()=>expect(miniAppApi.chooseCollection).toHaveBeenLastCalledWith("fixture","badge:flash",null));
});

it("previews a locked theme without unlocking it or saving a selection",async()=>{
  vi.mocked(miniAppApi.collection).mockResolvedValue(data);
  const {container}=render(<Collection initData="fixture" onBack={vi.fn()}/>);
  await screen.findByRole("button",{name:"Выбрать: FLASH"});
  fireEvent.click(screen.getByRole("button",{name:"Темы профиля"}));
  fireEvent.click(screen.getAllByRole("button",{name:"Посмотреть оформление"})[1]);
  expect(screen.getByText("Предпросмотр")).toBeInTheDocument();
  expect(container.querySelector(".collection-preview.profile-theme-beyond")).not.toBeNull();
  expect(screen.getByRole("button",{name:"Выбрать: За гранью"})).toBeDisabled();
  expect(miniAppApi.chooseCollection).not.toHaveBeenCalled();
});

it("shows a final large reward and approved Casper artwork without a legendary case",()=>{
  const item={code:"legendary_casper_move_over",rarity:"legendary" as const,status:"locked" as const,secret:false,rewards:[{type:"cas",amount:1_000_000_000},{type:"ticket_pack",amount:300,lottery:"pulse"},{type:"case",amount:200,planned:true},{type:"cosmetic",item:"badge:casper-master"},{type:"cosmetic",item:"theme:beyond"}]};
  const {container}=render(<><AchievementBadge item={item}/><AchievementRewards item={item}/></>);
  expect(screen.getByText("300 билетов «PULSE»")).toBeInTheDocument();
  expect(screen.queryByText(/кейс/i)).not.toBeInTheDocument();
  expect(screen.getByText("Тема «За гранью»")).toBeInTheDocument();
  expect(container.querySelector(".emblem-master img")).toHaveAttribute("src","/brand/logo-symbol-128-v1.png");
});

it("opens the full-color master badge preview without granting or choosing it",async()=>{
  Object.defineProperty(HTMLDialogElement.prototype,"showModal",{value:function(this:HTMLDialogElement){this.setAttribute("open","");},configurable:true});
  Object.defineProperty(HTMLDialogElement.prototype,"close",{value:function(this:HTMLDialogElement){this.removeAttribute("open");},configurable:true});
  vi.mocked(miniAppApi.collection).mockResolvedValue(data);
  render(<Collection initData="fixture" onBack={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button",{name:"Посмотреть значок: Каспер, подвинься"}));
  const dialog=screen.getByRole("dialog",{name:"Предпросмотр: Каспер, подвинься"});
  expect(dialog.querySelector(".emblem-master.emblem-locked")).toBeNull();
  expect(miniAppApi.chooseCollection).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button",{name:"Закрыть предпросмотр значка"}));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
