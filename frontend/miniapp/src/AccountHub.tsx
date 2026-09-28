import { DimensionalIcon } from "./DimensionalIcon";
import { Money } from "./components";
import { formatMoscow } from "./format";
import { MINIAPP_TEXTS as copy } from "./content";
import type { Account, Lottery, NotificationPreferences } from "./types";
import "./account-hub.css";
import accountTickets from "./assets/account/account-tickets-v1.webp";

export function AccountHub({ account, lotteries, onCatalog, onTickets, onHistory, onNotifications, onEnableTelegram, onSavePreferences }: { account: Account; lotteries: Lottery[]; onCatalog: () => void; onTickets: () => void; onHistory: () => void; onNotifications: () => void; onEnableTelegram: () => void; onSavePreferences: (preferences: NotificationPreferences) => void }) {
  const preferences = account.notification_preferences;
  const net = account.total_won - account.total_spent;
  const favoriteLottery = lotteries.find(lottery => lottery.code === account.favorite_lottery_code);
  const favoriteOffset = favoriteLottery?.secondary_storage_offset ?? 0;
  const nextActive = lotteries.filter(lottery => lottery.player_ticket_count > 0 && lottery.scheduled_at).sort((left, right) => Date.parse(left.scheduled_at!) - Date.parse(right.scheduled_at!))[0];

  return <div className="personal-hub">
    <header className="hub-heading"><div><span>ЛИЧНЫЙ КАБИНЕТ</span><h1>Моё</h1></div><button type="button" className="hub-bell" aria-label={account.unread_notification_count ? "Уведомления: есть непрочитанные" : "Уведомления"} onClick={onNotifications}><DimensionalIcon name="bell" />{account.unread_notification_count > 0 && <i />}</button></header>
    <section className="hub-wallet" aria-label="Мой баланс">
      <div className="hub-wallet-copy"><span>Доступно на балансе</span><strong><Money value={account.balance} compact /></strong><small>CAS · игровой баланс</small></div>
      <div className="hub-wallet-art" aria-hidden="true"><img src={accountTickets} alt="" width="512" height="414" decoding="async" /></div>
      <footer><span className="hub-avatar" aria-hidden="true">{Array.from(account.display_name.trim())[0] ?? "К"}</span><div><strong>{account.display_name}</strong><small>Личный счёт</small></div><span className="hub-wallet-brand">CASPER</span></footer>
    </section>
    <button type="button" className="hub-tickets" aria-label={`Активные билеты: ${account.active_ticket_count}`} onClick={onTickets}>
      <span className="hub-ticket-main"><span className="hub-ticket-object"><DimensionalIcon name="ticket" /></span><span className="hub-ticket-copy"><strong>Активные билеты</strong><small>{account.active_ticket_count ? "Участвуют в тиражах" : "Пока нет билетов в игре"}</small></span><span className="hub-ticket-count">{account.active_ticket_count}<span aria-hidden="true">↗</span></span></span>
      {nextActive && <span className="hub-next"><span><small>Ближайший тираж</small><strong>{nextActive.name}</strong></span><time dateTime={nextActive.scheduled_at!}>{formatMoscow(nextActive.scheduled_at!)} МСК</time></span>}
    </button>
    <nav className="hub-shortcuts" aria-label="Быстрые разделы"><button type="button" onClick={onHistory}><DimensionalIcon name="history" /><strong>История участия</strong><small>Билеты и результаты</small><span aria-hidden="true">↗</span></button><button type="button" onClick={onCatalog}><DimensionalIcon name="catalog" /><strong>Выбрать игру</strong><small>Каталог лотерей</small><span aria-hidden="true">↗</span></button></nav>
    <div className="hub-details-list">
      <details className="hub-details"><summary><span className="hub-detail-icon"><DimensionalIcon name="history" /></span><span><strong>Статистика и любимые числа</strong><small>Все результаты участия</small></span><span className="hub-detail-plus" aria-hidden="true">＋</span></summary><div className="hub-detail-body">
        <dl><div><dt>Всего билетов</dt><dd>{account.ticket_count}</dd></div><div><dt>Выигрышных билетов</dt><dd>{account.winning_ticket_count}</dd></div><div><dt>Потрачено</dt><dd><Money value={account.total_spent} compact /></dd></div><div><dt>Выиграно</dt><dd><Money value={account.total_won} compact /></dd></div><div><dt>Выиграно − потрачено</dt><dd><Money value={Math.abs(net)} prefix={net >= 0 ? "+" : "−"} compact /></dd></div><div><dt>Крупнейший выигрыш</dt><dd><Money value={account.best_win} compact /></dd></div><div><dt>Любимая лотерея</dt><dd>{account.favorite_lottery_name ?? "Пока нет данных"}</dd></div></dl>
        <div className="hub-favorite-numbers"><span>Чаще всего выбираете</span>{account.favorite_numbers?.length ? <div>{account.favorite_numbers.map(value => <span key={value}>{account.favorite_lottery_code === "pulse" && value > 1000 ? `Шифр ${value - 1000}` : favoriteOffset && value > favoriteOffset ? `${account.favorite_lottery_code === "pulse" ? "P" : "★"}${value - favoriteOffset}` : value}</span>)}</div> : <small>Пока мало данных</small>}</div>
      </div></details>
      <details className="hub-details"><summary><span className="hub-detail-icon"><DimensionalIcon name="settings" /></span><span><strong>Настройки уведомлений</strong><small>Telegram · {preferences.telegram_enabled ? "включены" : "выключены"}</small></span><span className="hub-detail-plus" aria-hidden="true">＋</span></summary><div className="hub-detail-body hub-notification-settings"><p>{copy.notifications.explanation}</p><button type="button" onClick={preferences.telegram_enabled ? () => onSavePreferences({ telegram_enabled: false, draw_results_enabled: true, inactivity_reminders_enabled: true }) : onEnableTelegram}>{preferences.telegram_enabled ? copy.notifications.disable : copy.notifications.enable}</button></div></details>
    </div>
  </div>;
}
