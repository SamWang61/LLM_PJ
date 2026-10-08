from datetime import datetime
from decimal import Decimal
from importlib.util import find_spec
from flask import Blueprint, abort, current_app, render_template, request, session
from .auth import admin_required
from .db import get_db
from .services.ai_payload import InsightDataError, build_insight_payload, insight_ranges
from .services.ai_workflows import FAILURE_LABELS, INTENTS, InsightRequestError, clean_question, insight_answer, operational_summary
from .services.dashboard import TAIPEI, dashboard_filters, load_dashboard, recommendation_monitor, DashboardFilterError

bp = Blueprint('admin', __name__, url_prefix='/admin')


def system_status():
    """Configuration-level status only; a green light never claims a model call succeeded."""
    config = current_app.config
    # Admin pages only render after admin_required has read the users collection.
    lights = [{"name": "資料庫", "state": "ok", "label": f"已連線（{config['DATA_MODE']}）"}]
    if not config["AI_RECOMMENDATIONS_ENABLED"]:
        lights.append({"name": "BGE", "state": "off", "label": "未啟用"})
    elif "bge_embeddings" in current_app.extensions or config.get("EMBEDDINGS_FACTORY"):
        lights.append({"name": "BGE", "state": "ok", "label": "已載入"})
    elif find_spec("langchain_huggingface") is None:
        lights.append({"name": "BGE", "state": "warn", "label": "未安裝，退回規則"})
    else:
        lights.append({"name": "BGE", "state": "warn", "label": "尚未載入"})
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
                           error=error, failure_labels=FAILURE_LABELS), status


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
                           error=None, failure_labels=FAILURE_LABELS)
