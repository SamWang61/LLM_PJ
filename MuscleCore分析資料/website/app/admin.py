from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from importlib.util import find_spec
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from .auth import admin_required
from .db import get_db
from .services.admin_catalog import AdminListError, product_list
from .services.admin_records import member_list, order_detail, order_list, revoke_customer_sessions
from .services.ai_compare import comparison
from .services.ai_payload import InsightDataError, build_insight_payload, insight_ranges
from .services.ai_workflows import FAILURE_LABELS, INTENTS, InsightRequestError, clean_question, insight_answer, operational_summary
from .services.local_ai import (LocalModelUnavailable, install_commands, refresh_vectors, sellable_products,
                                similar_products, vector_status)
from .services.dashboard import TAIPEI, dashboard_filters, load_dashboard, recommendation_monitor, DashboardFilterError

bp = Blueprint('admin', __name__, url_prefix='/admin')


def system_status():
    """Configuration-level status only; a green light never claims a model call succeeded."""
    config = current_app.config
    # Admin pages only render after admin_required has read the users collection.
    lights = [{"name": "資料庫", "state": "ok", "label": f"已連線（{config['DATA_MODE']}）"}]
    storefront = "前台已啟用" if config["AI_RECOMMENDATIONS_ENABLED"] else "前台未啟用"
    if "bge_embeddings" in current_app.extensions or config.get("EMBEDDINGS_FACTORY"):
        lights.append({"name": "BGE", "state": "ok", "label": f"已載入（{storefront}）"})
    elif find_spec("langchain_huggingface") is None:
        lights.append({"name": "BGE", "state": "warn", "label": f"未安裝，退回規則（{storefront}）"})
    else:
        lights.append({"name": "BGE", "state": "off", "label": f"尚未載入（{storefront}）"})
    if not config["AI_SUMMARY_ENABLED"]:
        lights.append({"name": "雲端 LLM", "state": "off", "label": "未啟用"})
    elif config.get("CLAUDE_FACTORY") or (config["ANTHROPIC_API_KEY"] and config["CLAUDE_MODEL"]):
        lights.append({"name": "雲端 LLM", "state": "ok", "label": "已設定"})
    else:
        lights.append({"name": "雲端 LLM", "state": "warn", "label": "未設定，退回規則"})
    return lights


@bp.context_processor
def admin_context():
    return {"system_status": system_status(), "admin_endpoints": set(current_app.view_functions),
            "read_at": datetime.now(TAIPEI).strftime("%Y-%m-%d %H:%M")}


@bp.app_template_global()
def spark_path(values, width=100, height=30):
    """SVG path for a KPI sparkline; None values break the line instead of being drawn as zero."""
    numbers = [float(v) for v in values if v is not None]
    if len(values) < 2 or not numbers:
        return ""
    low, high = min(numbers), max(numbers)
    span = (high - low) or 1
    step = width / (len(values) - 1)
    parts, pen_down = [], False
    for index, value in enumerate(values):
        if value is None:
            pen_down = False
            continue
        x = round(index * step, 2)
        y = round(height - (float(value) - low) / span * height if high != low else height / 2, 2)
        parts.append(f"{'L' if pen_down else 'M'}{x} {y}")
        pen_down = True
    return " ".join(parts)


@bp.app_template_global()
def column_chart(daily, start="", end=""):
    """Geometry for the daily revenue column chart (viewBox 720x240).

    A date-range filter is zero-filled so gaps show as empty days; without dates only days that
    have valid orders are drawn, matching the table below the chart.
    """
    rows = {row["date"]: row for row in daily}
    if start and end:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        days = [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]
    else:
        days = sorted(rows)
    if not days:
        return None
    series = [(day, rows.get(day, {"orders": 0, "revenue": Decimal("0")})) for day in days]
    peak = max((row["revenue"] for _, row in series), default=Decimal("0"))
    left, top, plot_w, plot_h = 58, 8, 650, 200
    slot = plot_w / len(series)
    bar_w = max(1.0, min(slot * 0.72, 36))
    label_every = max(1, -(-len(series) // 10))
    bars = []
    for index, (day, row) in enumerate(series):
        share = float(row["revenue"] / peak) if peak > 0 else 0.0
        h = round(share * plot_h, 2)
        bars.append({"date": day, "orders": row["orders"], "revenue": row["revenue"], "share": round(share * 100, 1),
                     "x": round(left + index * slot + (slot - bar_w) / 2, 2), "w": round(bar_w, 2),
                     "y": round(top + plot_h - h, 2), "h": h,
                     "label": day[5:] if index % label_every == 0 or index == len(series) - 1 else ""})
    total = sum((row["revenue"] for _, row in series), Decimal("0"))
    average = total / len(series)
    ticks = [{"y": round(top + plot_h - fraction * plot_h, 2), "value": peak * Decimal(str(fraction))} for fraction in (0, 0.5, 1)]
    return {"bars": bars, "ticks": ticks, "average": average, "days": len(series), "left": left, "right": left + plot_w,
            "baseline": top + plot_h, "avg_y": round(top + plot_h - (float(average / peak) * plot_h if peak > 0 else 0), 2)}


@bp.app_template_filter('pct')
def pct(value):
    return "—" if value is None else f"{value:+.1f}%"


@bp.app_template_filter('compact_ntd')
def compact_ntd(value):
    """Axis labels only; exact amounts are shown with the ntd filter."""
    value = float(value)
    return f"{value / 10000:.1f} 萬" if value >= 10000 else f"{value:,.0f}"


@bp.app_template_filter('taipei')
def taipei(value):
    """UTC datetimes from MongoDB shown in Taipei time; missing values show a dash."""
    if not isinstance(value, datetime):
        return "—"
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(TAIPEI).strftime("%Y-%m-%d %H:%M")


@bp.app_template_filter('duration')
def duration(ms):
    """Design spec 9: under one second in ms, otherwise seconds with one decimal."""
    return "—" if ms is None else (f"{ms:.0f} ms" if ms < 1000 else f"{ms / 1000:.1f} 秒")


@bp.app_template_filter('ntd')
def ntd(value):
    return "—" if value is None else f"NT$ {Decimal(str(value)):,.2f}"


@bp.errorhandler(DashboardFilterError)
def invalid_filters(error):
    return render_template('admin/filter_error.html', message=str(error)), 400


def dashboard_data():
    return load_dashboard(get_db(), current_app.config['DATA_MODE'], dashboard_filters(request.args))


@bp.get('/')
@admin_required
def dashboard():
    insights, orders = dashboard_data()
    return render_template('admin/dashboard.html', insights=insights, recent_orders=orders, summary_source='rules')


@bp.post('/summary')
@admin_required
def summary():
    insights, orders = dashboard_data()
    result = operational_summary(insights)
    insights['messages'] = result['messages']
    return render_template('admin/dashboard.html', insights=insights, recent_orders=orders, summary_source=result['source'])


@bp.get('/recommendations')
@admin_required
def recommendations():
    result = recommendation_monitor(get_db(), current_app.config['DATA_MODE'])
    return render_template('admin/recommendations.html', **result)


def insight_page(values, intent=None, answer=None, error=None, status=200):
    db, mode = get_db(), current_app.config['DATA_MODE']
    payload = None
    try:
        current, comparison = insight_ranges(db, values)
        payload = build_insight_payload(db, mode, current, comparison, intent)
    except InsightDataError as data_error:
        error, status = {"code": data_error.code, "message": str(data_error)}, 400
        current = {"start": values.get("start", ""), "end": values.get("end", ""), "demo": values.get("demo", "all")}
    return render_template('admin/ai_insight.html', payload=payload, range=current, intents=INTENTS, answer=answer,
                           error=error, failure_labels=FAILURE_LABELS,
                           free_question_enabled=free_question_enabled()), status


def free_question_enabled():
    config = current_app.config
    return (config.get('AI_FREE_QUESTION_ENABLED', False)
            and config.get('AI_SUMMARY_ENABLED', False)
            and config.get('DATA_MODE') == 'v4')


@bp.get('/ai/insight')
@admin_required
def ai_insight():
    return insight_page(request.args)


@bp.post('/ai/insight')
@admin_required
def ai_insight_ask():
    intent = request.form.get('intent', '')
    if intent not in INTENTS:
        abort(400, description="未知的提問類型。")
    if intent == 'free_question' and not free_question_enabled():
        abort(403, description="自由提問尚未啟用。")
    try:
        # Preset buttons never forward the text box; only the free-question button does.
        question = clean_question(request.form.get('question')) if intent == 'free_question' else None
        current, comparison = insight_ranges(get_db(), request.form)
        payload = build_insight_payload(get_db(), current_app.config['DATA_MODE'], current, comparison, intent)
        answer = insight_answer(payload, intent, question, session['user_id'])
    except InsightRequestError as request_error:
        return insight_page(request.form, intent, error={"code": request_error.code, "message": str(request_error)},
                            status=request_error.status)
    except InsightDataError:
        return insight_page(request.form, intent)
    return render_template('admin/ai_insight.html', payload=payload, range=current, intents=INTENTS, answer=answer,
                           error=None, failure_labels=FAILURE_LABELS,
                           free_question_enabled=free_question_enabled())


UNAVAILABLE_LABELS = {"not_installed": "本機模型套件尚未安裝", "model_missing": "模型檔案尚未下載或無法載入"}


@bp.get('/ai/recommendation')
@admin_required
def ai_recommendation():
    products = sellable_products(get_db())
    selected = request.args.get('product_id', '')
    result, unavailable, status = None, None, 200
    if selected:
        try:
            result = similar_products(products, selected)
        except KeyError:
            flash("找不到這個商品，或它目前不可推薦／沒有可售 SKU。", "danger")
            status = 404
        except LocalModelUnavailable as error:
            unavailable = error.reason
    return render_template('admin/ai_recommendation.html', products=products, selected=selected, result=result,
                           unavailable=unavailable, unavailable_labels=UNAVAILABLE_LABELS,
                           install_commands=install_commands(), vectors=vector_status()), status


@bp.post('/ai/recommendation/refresh')
@admin_required
def ai_recommendation_refresh():
    products = sellable_products(get_db())
    selected = request.form.get('product_id', '')
    if not products:
        flash("資料庫尚無可推薦商品，沒有向量需要更新。", "warning")
    else:
        try:
            outcome = refresh_vectors(products)
            seconds = outcome["latency_ms"] / 1000
            flash(f"已更新 {outcome['count']} 筆商品向量，耗時 {seconds:.1f} 秒。", "success")
        except LocalModelUnavailable as error:
            flash(f"無法更新向量：{UNAVAILABLE_LABELS[error.reason]}。", "danger")
    return redirect(url_for('admin.ai_recommendation', product_id=selected or None))


@bp.get('/ai/compare')
@admin_required
def ai_compare():
    return render_template('admin/ai_compare.html', **comparison())


LIST_PAGES = {"admin.products": "返回商品管理", "admin.orders": "返回訂單管理", "admin.members": "返回會員管理"}


@bp.errorhandler(AdminListError)
def invalid_list_filters(error):
    endpoint = request.endpoint if request.endpoint in LIST_PAGES else None
    return render_template('admin/filter_error.html', message=str(error),
                           back_url=url_for(endpoint) if endpoint else None,
                           back_label=LIST_PAGES.get(endpoint)), 400


@bp.get('/products')
@admin_required
def products():
    return render_template('admin/products.html', **product_list(get_db(), request.args))


@bp.get('/orders')
@admin_required
def orders():
    return render_template('admin/orders.html', **order_list(get_db(), request.args))


@bp.get('/orders/<order_id>')
@admin_required
def order_detail_page(order_id):
    detail = order_detail(get_db(), order_id)
    if detail is None:
        abort(404, description="找不到這筆訂單。")
    return render_template('admin/order_detail.html', order=detail)


@bp.get('/members')
@admin_required
def members():
    return render_template('admin/members.html', **member_list(get_db(), request.args))


MEMBER_FILTER_KEYS = ("q", "role", "status", "page")


@bp.post('/members/<user_id>/revoke-sessions')
@admin_required
def revoke_member_sessions(user_id):
    """Sign a customer out of all devices (CSRF is enforced for every POST by security.py)."""
    back = {key: request.form[key] for key in MEMBER_FILTER_KEYS if request.form.get(key)}
    try:
        count = revoke_customer_sessions(get_db(), user_id)
    except LookupError:
        abort(404, description="找不到這位會員。")
    except PermissionError:
        abort(403, description="只能撤銷一般會員的裝置登入，管理員帳號不可從後台操作。")
    current_app.logger.info("admin %s revoked %s device sessions of member %s", session.get("user_id"), count, user_id)
    flash(f"已撤銷 {count} 個裝置", "success")
    return redirect(url_for('admin.members', **back))
