"""Media, entertainment, and gaming domain pack."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from great_generator.domains._industry import c, fk, generate_industry_pandas, table
from great_generator.schemas.models import DomainSchema

CHOICES = {
    "user_segment": ["free", "standard", "premium", "family", "creator"],
    "content_type": ["movie", "series", "music", "podcast", "sports", "game"],
    "genre": ["action", "drama", "comedy", "documentary", "sports", "rpg", "casual"],
    "subscription_status": ["active", "trial", "past_due", "cancelled"],
    "view_event_type": ["play", "pause", "complete", "like", "share"],
    "campaign_channel": ["display", "video", "connected_tv", "social", "in_game"],
    "impression_status": ["served", "clicked", "skipped", "blocked"],
    "session_type": ["ranked", "casual", "co_op", "tutorial"],
}


def schema() -> DomainSchema:
    tables = {
        "users": table(
            "users",
            "user_id",
            (
                c("user_id", "int64"),
                c("user_code", "string"),
                c("first_name", "string"),
                c("last_name", "string"),
                c("user_name", "string"),
                c("email", "string"),
                c("user_segment", "string"),
                c("region", "string"),
                c("signup_date", "date"),
                c("user_status", "string"),
            ),
        ),
        "content_titles": table(
            "content_titles",
            "content_id",
            (
                c("content_id", "int64"),
                c("content_name", "string"),
                c("content_type", "string"),
                c("genre", "string"),
                c("release_year", "int64"),
                c("premium_content", "bool"),
            ),
        ),
        "subscriptions": table(
            "subscriptions",
            "subscription_id",
            (
                c("subscription_id", "int64"),
                c("user_id", "int64"),
                c("plan_name", "string"),
                c("start_date", "date"),
                c("subscription_status", "string"),
                c("monthly_fee", "float64"),
            ),
            (fk("user_id", "users", "user_id"),),
            "Streaming and gaming subscriptions.",
        ),
        "viewing_events": table(
            "viewing_events",
            "viewing_event_id",
            (
                c("viewing_event_id", "int64"),
                c("user_id", "int64"),
                c("content_id", "int64"),
                c("event_ts", "datetime64[ns]"),
                c("event_date", "date"),
                c("view_event_type", "string"),
                c("watch_minutes", "float64"),
                c("completion_percent", "float64"),
            ),
            (fk("user_id", "users", "user_id"), fk("content_id", "content_titles", "content_id")),
            "Streaming viewing and engagement telemetry.",
        ),
        "ad_campaigns": table(
            "ad_campaigns",
            "campaign_id",
            (
                c("campaign_id", "int64"),
                c("campaign_name", "string"),
                c("campaign_channel", "string"),
                c("start_date", "date"),
                c("campaign_budget", "float64"),
                c("campaign_status", "string"),
            ),
        ),
        "ad_impressions": table(
            "ad_impressions",
            "impression_id",
            (
                c("impression_id", "int64"),
                c("campaign_id", "int64"),
                c("user_id", "int64"),
                c("content_id", "int64"),
                c("impression_ts", "datetime64[ns]"),
                c("impression_status", "string"),
                c("revenue_amount", "float64"),
            ),
            (
                fk("campaign_id", "ad_campaigns", "campaign_id"),
                fk("user_id", "users", "user_id"),
                fk("content_id", "content_titles", "content_id"),
            ),
            "Ad delivery and monetization events.",
        ),
        "game_sessions": table(
            "game_sessions",
            "game_session_id",
            (
                c("game_session_id", "int64"),
                c("user_id", "int64"),
                c("content_id", "int64"),
                c("session_ts", "datetime64[ns]"),
                c("session_type", "string"),
                c("duration_minutes", "int64"),
                c("score_value", "float64"),
            ),
            (fk("user_id", "users", "user_id"), fk("content_id", "content_titles", "content_id")),
            "Game session telemetry for gaming datasets.",
        ),
    }
    return DomainSchema(
        name="media",
        tables=tables,
        description="Media, entertainment, and gaming domain for subscriptions, content, viewing, ads, and game sessions.",
        behaviors=(
            "Premium content and user segments drive engagement",
            "Ad impressions connect campaigns to content and users",
            "Game sessions support gaming analytics demos",
            "Streaming events are time-based and high-volume",
        ),
    )


def generate_pandas(
    row_counts: Mapping[str, int], seed: int | None = None
) -> dict[str, pd.DataFrame]:
    return generate_industry_pandas(schema(), row_counts, seed=seed, choices=CHOICES)
