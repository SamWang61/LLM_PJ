from flask import Blueprint, current_app, render_template, request
from .auth import admin_required
from .db import get_db
from .services.ai_workflows import operational_summary
from .services.dashboard import dashboard_filters, load_dashboard, recommendation_monitor, DashboardFilterError

bp = Blueprint('admin', __name__, url_prefix='/admin')


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
