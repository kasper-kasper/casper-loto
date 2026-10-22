import { tr } from "./i18n";
export function GiftTicketBadge() {
  return <span className="gift-ticket-badge"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="8" width="18" height="4" rx="1" /><path d="M5 12v9h14v-9M12 8v13m0-13H8a3 3 0 1 1 3-3Zm0 0h4a3 3 0 1 0-3-3Z" /></svg>{tr("Подарочный")}</span>;
}
