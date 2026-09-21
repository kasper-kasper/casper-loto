import type { Account, BingoInventory, Dashboard, LiveFeed, TicketPage, WebSession } from "./types";
let csrf="";
export class ApiError extends Error { constructor(message:string, public status:number){super(message);} }
async function request<T>(path:string, init?:RequestInit):Promise<T>{const headers=new Headers(init?.headers);headers.set("Content-Type","application/json");if(csrf&&init?.method&&init.method!=="GET")headers.set("X-Web-CSRF",csrf);const response=await fetch(`/api/v1/web${path}`,{...init,credentials:"include",cache:"no-store",headers});if(!response.ok){const body=await response.json().catch(()=>({})) as {detail?:string};throw new ApiError(body.detail??"Запрос не выполнен.",response.status);}if(response.status===204)return undefined as T;return response.json() as Promise<T>}
const remember=(value:WebSession)=>{csrf=value.csrf_token;return value};
export const webApi={
 telegram:(code:string)=>request<WebSession>("/auth/telegram",{method:"POST",body:JSON.stringify({code})}).then(remember),
 addPassword:(username:string,password:string)=>request<void>("/auth/password",{method:"POST",body:JSON.stringify({username,password})}),
 login:(username:string,password:string)=>request<WebSession>("/auth/login",{method:"POST",body:JSON.stringify({username,password})}).then(remember),
 register:(username:string,password:string)=>request<WebSession>("/auth/register",{method:"POST",body:JSON.stringify({username,password})}).then(remember),
 session:()=>request<WebSession>("/auth/session").then(remember), logout:()=>request<void>("/auth/logout",{method:"POST"}).finally(()=>{csrf=""}),
 dashboard:()=>request<Dashboard>("/dashboard"), account:()=>request<Account>("/account"),
 tickets:(state:"active"|"history",offset=0)=>request<TicketPage>(`/tickets?state=${state}&offset=${offset}&limit=100`),
 live:(scope:"standard"|"fast")=>request<LiveFeed>(`/live?scope=${scope}`),
 purchase:(code:string,combinations:number[][],key:string,drawCount:1|5=1)=>request<{ticket_ids:string[];total_cost:number;balance_after:number}>(`/lotteries/${encodeURIComponent(code)}/purchases`,{method:"POST",body:JSON.stringify({combinations,idempotency_key:key,draw_count:drawCount})}),
 bingoInventory:(offset=0)=>request<BingoInventory>(`/bingo/inventory?offset=${offset}`),
 bingoPurchase:(drawId:string,ticketIds:string[],key:string)=>request<{ticket_ids:string[];total_cost:number;balance_after:number}>("/bingo/purchases",{method:"POST",body:JSON.stringify({draw_id:drawId,ticket_ids:ticketIds,idempotency_key:key})}),
};
