"""LLM Advisor service - grounded summary and recommendations."""
import json
from datetime import date

from flask import current_app

from app.services.analytics import (
    compute_runway,
    get_alerts,
    get_burn_rate,
    get_category_breakdown,
    get_current_balance,
    get_monthly_totals,
)
from app.services.forecast import run_forecast


def _gather_metrics(user_id: int) -> dict:
    """Collect all computed metrics for the advisor prompt."""
    today = date.today()
    totals = get_monthly_totals(user_id, today.year, today.month)
    categories = get_category_breakdown(user_id, today.year, today.month)
    burn = get_burn_rate(user_id, 30)
    balance = get_current_balance(user_id)
    runway = compute_runway(user_id, balance, burn)
    alerts = get_alerts(user_id)
    try:
        forecast = run_forecast(user_id, horizon_days=30)
    except Exception:
        forecast = {"predicted_net": 0, "predicted_balance": balance, "metrics": {}}

    return {
        "month": f"{today.year}-{today.month:02d}",
        "monthly_income": totals["income"],
        "monthly_expense": totals["expense"],
        "monthly_net": totals["net"],
        "current_balance": balance,
        "burn_rate_per_day": burn,
        "runway_days": runway,
        "predicted_net_30d": forecast.get("predicted_net", 0),
        "predicted_balance": forecast.get("predicted_balance", balance),
        "category_breakdown": categories[:10],
        "alerts": [{"kind": a.kind, "severity": a.severity, "message": a.message} for a in alerts[:5]],
    }


def _build_fallback_narrative(metrics: dict) -> tuple[str, list[str]]:
    """Template-based narrative when LLM is unavailable."""
    summary_parts = []
    if metrics["runway_days"] is not None:
        if metrics["runway_days"] < 7:
            summary_parts.append(
                f"Critical: Runway is only {metrics['runway_days']:.0f} days. "
                "Immediate action is needed to avoid cash shortfall."
            )
        elif metrics["runway_days"] < 30:
            summary_parts.append(
                f"Warning: Runway is {metrics['runway_days']:.0f} days. "
                "Consider reducing expenses or accelerating collections."
            )
        else:
            summary_parts.append(
                f"Runway is approximately {metrics['runway_days']:.0f} days at current burn rate."
            )
    summary_parts.append(
        f"This month: income {metrics['monthly_income']:.2f}, expenses {metrics['monthly_expense']:.2f}, "
        f"net {metrics['monthly_net']:.2f}. Current balance: {metrics['current_balance']:.2f}."
    )
    if metrics["predicted_net_30d"]:
        summary_parts.append(
            f"30-day forecast: predicted net {metrics['predicted_net_30d']:.2f}, "
            f"end balance {metrics['predicted_balance']:.2f}."
        )

    actions = []
    if metrics["runway_days"] is not None and metrics["runway_days"] < 30:
        actions.append("Review and cut non-essential expenses.")
        actions.append("Follow up on outstanding receivables.")
    if metrics["monthly_net"] < 0:
        actions.append("Address the monthly deficit—increase revenue or reduce costs.")
    if metrics["alerts"]:
        for a in metrics["alerts"]:
            if a["severity"] in ("warning", "critical"):
                actions.append(f"Address alert: {a['message']}")
    if not actions:
        actions.append("Continue monitoring cashflow. Run forecasts regularly.")

    return "\n".join(summary_parts), actions


def generate_summary(user_id: int) -> tuple[str, list[str]]:
    """
    Generate executive summary and recommended actions.
    Uses LLM if API key is set; otherwise falls back to template narrative.
    """
    metrics = _gather_metrics(user_id)
    api_key = current_app.config.get("OPENAI_API_KEY", "").strip()

    if not api_key:
        return _build_fallback_narrative(metrics)

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=current_app.config.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
        model = current_app.config.get("OPENAI_MODEL", "gpt-4o-mini")

        prompt = f"""You are a cashflow advisor for a small business. Based ONLY on the following computed metrics (do not invent numbers), write:
1. A brief Executive Summary (2-3 sentences) describing the cashflow situation.
2. A list of 3-5 Recommended Actions, each as a short actionable item.

Metrics (use these exact numbers):
{json.dumps(metrics, indent=2)}

Respond in JSON format:
{{"summary": "your executive summary here", "actions": ["action 1", "action 2", ...]}}
"""

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message.content.strip()
        # Extract JSON (handle markdown code blocks)
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
        return data.get("summary", ""), data.get("actions", [])
    except Exception as e:
        current_app.logger.warning(f"LLM advisor failed: {e}")
        return _build_fallback_narrative(metrics)
