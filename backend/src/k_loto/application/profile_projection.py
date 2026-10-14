"""Verify/rebuild display statistics without modifying business history or money."""

# ruff: noqa: E501 -- SQL verification is one consistent statement.

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class ProfileProjectionCheck:
    profiles: int
    lotteries: int


class ProfileProjectionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def rebuild(self) -> None:
        """Run in a dedicated READ COMMITTED transaction; source writes wait."""
        await self.session.execute(text("SELECT rebuild_player_profiles()"))

    async def verify(self) -> ProfileProjectionCheck:
        """One statement snapshot prevents false mismatches during purchases."""
        row = (
            await self.session.execute(
                text("""
                    WITH activity AS (
                        SELECT user_id,count(*) AS tickets,
                            count(*) FILTER (WHERE status='PURCHASED') AS active,
                            count(*) FILTER (WHERE prize_amount>0) AS winning,
                            coalesce(sum(purchase_price) FILTER (WHERE status<>'REFUNDED'),0) AS spent,
                            sum(prize_amount) AS won,max(prize_amount) AS best
                        FROM tickets GROUP BY user_id
                        UNION ALL
                        SELECT user_id,count(*),0,count(*) FILTER (WHERE prize_amount>0),
                            sum(purchase_price),sum(prize_amount),max(prize_amount)
                        FROM instant_tickets GROUP BY user_id
                    ), totals AS (
                        SELECT user_id,sum(tickets) AS tickets,sum(active) AS active,
                            sum(winning) AS winning,sum(spent) AS spent,sum(won) AS won,max(best) AS best
                        FROM activity GROUP BY user_id
                    ), unread AS (
                        SELECT user_id,count(*) AS unread FROM user_notifications
                        WHERE read_at IS NULL AND type<>'DRAW_RESULT' GROUP BY user_id
                    ), lottery_counts AS (
                        SELECT user_id,lottery_id,count(*) AS tickets FROM tickets
                        WHERE status<>'REFUNDED' GROUP BY user_id,lottery_id
                    )
                    SELECT (
                        SELECT count(*) FROM users u
                        LEFT JOIN player_profile_stats p ON p.user_id=u.id
                        LEFT JOIN totals t ON t.user_id=u.id LEFT JOIN unread n ON n.user_id=u.id
                        WHERE p.user_id IS NULL OR
                            ROW(p.ticket_count,p.active_ticket_count,p.winning_ticket_count,
                                p.total_spent,p.total_won,p.best_win,p.unread_notification_count)
                            IS DISTINCT FROM
                            ROW(coalesce(t.tickets,0),coalesce(t.active,0),coalesce(t.winning,0),
                                coalesce(t.spent,0),coalesce(t.won,0),coalesce(t.best,0),coalesce(n.unread,0))
                    ) AS profiles, (
                        SELECT count(*) FROM lottery_counts t FULL JOIN player_lottery_stats p
                        ON p.user_id=t.user_id AND p.lottery_id=t.lottery_id
                        WHERE coalesce(p.ticket_count,0)<>coalesce(t.tickets,0)
                    ) AS lotteries
                """)
            )
        ).one()
        return ProfileProjectionCheck(int(row.profiles), int(row.lotteries))
