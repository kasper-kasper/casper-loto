# Библиотека текстов B

90 редактируемых вариантов в `telegram-posts.v1.txt`. Все 10 фонов доступны для каждого согласованного события B; макеты Story/Post используют центральную область.

Переменные:

- `account_feature_description`
- `account_feature_name`
- `as_of_moscow`
- `changes_summary`
- `day_moscow`
- `feature_description`
- `feature_name`
- `game_name`
- `integration_description`
- `integration_name`
- `interface_changes`
- `interface_name`
- `jackpots_count`
- `jackpots_list`
- `leader_tickets`
- `milestone_draws`
- `milestone_players`
- `milestone_tickets`
- `milestone_winning_tickets`
- `new_record_cas`
- `period_draws`
- `period_moscow`
- `period_players`
- `period_tickets`
- `period_winning_tickets`
- `platform_details`
- `platform_name`
- `popular_games_label`
- `previous_record_cas`
- `public_topic_hashtag`
- `release_summary`
- `section_description`
- `section_name`
- `topic_hashtag`
- `total_jackpot_cas`
- `update_name`
- `version_name`
- `winning_tickets_today`

Счётчики и суммы берутся из payload события; даты форматируются по МСК. `jackpots_list` содержит игру, сумму, время и номер тиража каждого срыва. `popular_games_label` перечисляет всех лидеров при равенстве. Поля B4 заполняет редактор. Хэштеги темы выбираются по категории; общие теги скрываются spoiler entity. Перед отправкой обязательна проверка отсутствия незаполненных переменных и длины Telegram caption.

При подключении автоматизации нельзя превращать B3/B4 в automatic. Интервал автоматических публикаций — 30 минут, ручные вне интервала. В этом выпуске автоматическая отправка не включается.

Стабильные теги: общий `#CasperLoto`; B1 `#CasperДостижения`, B2 `#CasperРекорды`, B3.1–B3.4 `#CasperСтатистика`, B3.5 `#CasperДжекпоты`, B4 `#CasperОбновления`. Общедоступный тег темы под спойлером: соответственно `#достижения`, `#рекорд`, `#статистика`, `#джекпот`, `#обновления`; рядом общий `#лотерея`.
