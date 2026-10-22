import { tr } from "./i18n";
import { DimensionalIcon } from "./DimensionalIcon";
import { Money } from "./components";
import { formatMoscow } from "./format";
import { MINIAPP_TEXTS as copy } from "./content";
import type { Account, Lottery, NotificationPreferences } from "./types";
import "./account-hub.css";
import { AchievementSummary } from "./Achievements";
import { AchievementIcon } from "./AchievementIcon";
import { useProfileCosmetics } from "./useProfileCosmetics";
import { LegendaryBadge } from "./LegendaryBadge";
import { LanguageSelector } from "./LanguageSelector";

export function AccountHub({ account, lotteries, initData = "", onAchievements = () => {}, onCollection = () => {}, onCatalog, onTickets, onHistory, onNotifications, onEnableTelegram, onSavePreferences }: { account: Account; lotteries: Lottery[]; initData?: string; onAchievements?: () => void; onCollection?: () => void; onCatalog: () => void; onTickets: () => void; onHistory: () => void; onNotifications: () => void; onEnableTelegram: () => void; onSavePreferences: (preferences: NotificationPreferences) => void }) {
  const {data:cosmetics}=useProfileCosmetics(initData);
  const preferences = account.notification_preferences;
  const net = account.total_won - account.total_spent;
  const favoriteLottery = lotteries.find(lottery => lottery.code === account.favorite_lottery_code);
  const favoriteOffset = favoriteLottery?.secondary_storage_offset ?? 0;
  const nextActive = lotteries.filter(lottery => lottery.player_ticket_count > 0 && lottery.scheduled_at).sort((left, right) => Date.parse(left.scheduled_at!) - Date.parse(right.scheduled_at!))[0];

  return <div className={`personal-hub profile-theme-${cosmetics?.active_theme?.split(":")[1]??"standard"}`}>
    <header className="hub-heading"><h1>{tr("Личный кабинет")}</h1><button type="button" className="hub-bell" aria-label={account.unread_notification_count ? tr("Уведомления: есть непрочитанные") : tr("Уведомления")} onClick={onNotifications}><DimensionalIcon name="bell" />{account.unread_notification_count > 0 && <i />}</button></header>
    <section className="hub-wallet hub-wallet-compact" aria-label={tr("Мой баланс")}>
      <div className="hub-wallet-copy"><span>{tr("Доступно на балансе")}</span><strong><Money value={account.balance} compact /></strong><small>{tr("CAS · игровой баланс")}</small></div>
      <span className="hub-wallet-small-icon" aria-hidden="true"><AchievementIcon name="wallet" /></span>
    </section>
    <AchievementSummary initData={initData} onOpen={onAchievements} />
    <div className="hub-identity"><span className="hub-avatar" aria-hidden="true">{Array.from(account.display_name.trim())[0] ?? tr("К")}</span><strong>{account.display_name}</strong>{cosmetics?.active_badge&&<span aria-label={tr("Активный значок")}><LegendaryBadge game={cosmetics.active_badge.slice(6)} compact/></span>}<small>{tr("Личный счёт")}</small></div>
    <button type="button" className="hub-collection" onClick={onCollection}><LegendaryBadge game="casper-master" compact/><span><strong>{tr("Коллекция")}</strong><small>{tr("Значки и темы профиля")}</small></span><span aria-hidden="true">↗</span></button>
    <button type="button" className="hub-tickets" aria-label={tr("Активные билеты: {0}", account.active_ticket_count)} onClick={onTickets}>
      <span className="hub-ticket-main"><span className="hub-ticket-object"><DimensionalIcon name="ticket" /></span><span className="hub-ticket-copy"><strong>{tr("Активные билеты")}</strong><small>{account.active_ticket_count ? tr("Участвуют в тиражах") : tr("Пока нет билетов в игре")}</small></span><span className="hub-ticket-count">{account.active_ticket_count}<span aria-hidden="true">↗</span></span></span>
      {nextActive && <span className="hub-next"><span><small>{tr("Ближайший тираж")}</small><strong>{tr(nextActive.name)}</strong></span><time dateTime={nextActive.scheduled_at!}>{tr(formatMoscow(nextActive.scheduled_at!))}  {tr("МСК")}</time></span>}
    </button>
    <nav className="hub-shortcuts" aria-label={tr("Быстрые разделы")}><button type="button" onClick={onHistory}><DimensionalIcon name="history" /><strong>{tr("История участия")}</strong><small>{tr("Билеты и результаты")}</small><span aria-hidden="true">↗</span></button><button type="button" onClick={onCatalog}><DimensionalIcon name="catalog" /><strong>{tr("Выбрать игру")}</strong><small>{tr("Каталог лотерей")}</small><span aria-hidden="true">↗</span></button></nav>
    <div className="hub-details-list">
      <LanguageSelector />
      <details className="hub-details"><summary><span className="hub-detail-icon"><DimensionalIcon name="history" /></span><span><strong>{tr("Статистика и любимые числа")}</strong><small>{tr("Все результаты участия")}</small></span><span className="hub-detail-plus" aria-hidden="true">＋</span></summary><div className="hub-detail-body">
        <dl><div><dt>{tr("Всего билетов")}</dt><dd>{account.ticket_count}</dd></div><div><dt>{tr("Выигрышных билетов")}</dt><dd>{account.winning_ticket_count}</dd></div><div><dt>{tr("Потрачено")}</dt><dd><Money value={account.total_spent} compact /></dd></div><div><dt>{tr("Выиграно")}</dt><dd><Money value={account.total_won} compact /></dd></div><div><dt>{tr("Выиграно − потрачено")}</dt><dd><Money value={Math.abs(net)} prefix={net >= 0 ? "+" : "−"} compact /></dd></div><div><dt>{tr("Крупнейший выигрыш")}</dt><dd><Money value={account.best_win} compact /></dd></div><div><dt>{tr("Любимая лотерея")}</dt><dd>{tr(account.favorite_lottery_name ?? tr("Пока нет данных"))}</dd></div></dl>
        <div className="hub-favorite-numbers"><span>{tr("Чаще всего выбираете")}</span>{account.favorite_numbers?.length ? <div>{account.favorite_numbers.map(value => <span key={value}>{tr(account.favorite_lottery_code === "pulse" && value > 1000 ? tr("Шифр {0}", value - 1000) : favoriteOffset && value > favoriteOffset ? `${account.favorite_lottery_code === "pulse" ? "P" : "★"}${value - favoriteOffset}` : value)}</span>)}</div> : <small>{tr("Пока мало данных")}</small>}</div>
      </div></details>
      <details className="hub-details"><summary><span className="hub-detail-icon"><DimensionalIcon name="settings" /></span><span><strong>{tr("Настройки уведомлений")}</strong><small>Telegram · {preferences.telegram_enabled ? tr("включены") : tr("выключены")}</small></span><span className="hub-detail-plus" aria-hidden="true">＋</span></summary><div className="hub-detail-body hub-notification-settings"><p>{tr(copy.notifications.explanation)}</p><button type="button" onClick={preferences.telegram_enabled ? () => onSavePreferences({ telegram_enabled: false, draw_results_enabled: true, inactivity_reminders_enabled: true }) : onEnableTelegram}>{tr(preferences.telegram_enabled ? copy.notifications.disable : copy.notifications.enable)}</button></div></details>
    </div>
  </div>;
}
