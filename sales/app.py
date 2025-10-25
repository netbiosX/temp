import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from collections import defaultdict, Counter
from io import StringIO
import csv
from flask import Flask, render_template_string, request, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from jinja2 import DictLoader

# --- Config ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sales_security.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
db = SQLAlchemy(app)

# --- Models ---
class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(120), nullable=False)
    primary_contact = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(40))
    notes = db.Column(db.Text)
    opportunities = relationship('Opportunity', back_populates='client', cascade='all, delete')

class Opportunity(db.Model):
    __tablename__ = 'opportunities'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    status = db.Column(db.String(40), default='Lead')  # Lead, Qualified, Proposal, Negotiation, Won, Lost
    engagement_type = db.Column(db.String(50), default='Mixed')  # Red | Purple | Mixed
    value = db.Column(db.Numeric(12, 2), default=0)
    probability = db.Column(db.Integer, default=10)  # 0-100
    expected_close = db.Column(db.Date)
    owner = db.Column(db.String(120), default='Unassigned')
    tags = db.Column(db.Text)  # comma or space separated tags
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # NEW: for cycle time
    closed_at = db.Column(db.DateTime)  # NEW: auto-set for Won/Lost

    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    client = relationship('Client', back_populates='opportunities')

    activities = relationship('Activity', back_populates='opportunity', cascade='all, delete')
    budget = relationship('ProjectBudget', back_populates='opportunity', uselist=False, cascade='all, delete')
    reminders = relationship('Reminder', back_populates='opportunity', cascade='all, delete')

    @property
    def tags_list(self):
        if not self.tags:
            return []
        raw = [t.strip() for part in self.tags.split(',') for t in part.split()]
        return [t for t in raw if t]

class Activity(db.Model):
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(40), default='Note')  # Email, Call, Meeting, Note
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'))
    opportunity = relationship('Opportunity', back_populates='activities')

class ProjectBudget(db.Model):
    __tablename__ = 'budgets'
    id = db.Column(db.Integer, primary_key=True)
    total_budget = db.Column(db.Numeric(12, 2), default=0)
    cost_estimate = db.Column(db.Numeric(12, 2), default=0)
    currency = db.Column(db.String(8), default='GBP')
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'))
    opportunity = relationship('Opportunity', back_populates='budget')

    @property
    def margin(self):
        try:
            return Decimal(self.total_budget or 0) - Decimal(self.cost_estimate or 0)
        except Exception:
            return Decimal(0)

class Reminder(db.Model):
    __tablename__ = 'reminders'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(200), nullable=False)
    due_at = db.Column(db.DateTime, nullable=False)
    sent = db.Column(db.Boolean, default=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'))
    opportunity = relationship('Opportunity', back_populates='reminders')

# --- Helpers ---
STAGE_ORDER = ['Lead','Qualified','Proposal','Negotiation','Won','Lost']
STAGE_COMPLETION = {
    'Lead': 10,
    'Qualified': 25,
    'Proposal': 50,
    'Negotiation': 75,
    'Won': 100,
    'Lost': 0,
}

def stage_color(stage: str) -> str:
    return {
        'Lead': 'info',
        'Qualified': 'secondary',
        'Proposal': 'primary',
        'Negotiation': 'warning',
        'Won': 'success',
        'Lost': 'danger',
    }.get(stage, 'secondary')

# --- Templates (embedded) ---
TEMPLATES = {
    'layout.html': r"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Security Sales Tracker</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
      <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
      <style>
        /* Purple theme overrides */
        :root{
          --bs-primary: #6f42c1;          /* purple */
          --bs-primary-rgb: 111,66,193;
          --bs-secondary: #9370db;        /* medium purple */
          --bs-info: #b39ddb;             /* light purple */
        }
        .navbar{ background: linear-gradient(90deg, #4c2a85, #6f42c1); }
        .navbar-brand{ font-weight:700 }
        .card-ghost { box-shadow: 0 0.5rem 1rem rgba(111,66,193,0.08); border: 1px solid rgba(111,66,193,0.1); }
        .badge.tag{ background-color: rgba(111,66,193,.15); color:#4c2a85; border:1px solid rgba(111,66,193,.25)}
        .kanban-col{ background:#faf7ff; border:1px dashed rgba(111,66,193,.25); border-radius:.75rem; padding:.5rem }
        .kanban-card{ background:#fff; border:1px solid rgba(111,66,193,.15); border-radius:.75rem; padding:.5rem; margin-bottom:.5rem }
      </style>
    </head>
    <body class="bg-light">
      <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
          <a class="navbar-brand" href="{{ url_for('dashboard') }}">🔐 Security Sales</a>
          <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav"><span class="navbar-toggler-icon"></span></button>
          <div id="nav" class="collapse navbar-collapse">
            <ul class="navbar-nav me-auto mb-2 mb-lg-0">
              <li class="nav-item"><a class="nav-link" href="{{ url_for('list_clients') }}">Clients</a></li>
              <li class="nav-item"><a class="nav-link" href="{{ url_for('list_opportunities') }}">Opportunities</a></li>
              <li class="nav-item"><a class="nav-link" href="{{ url_for('kanban') }}">Kanban</a></li>
              <li class="nav-item"><a class="nav-link" href="{{ url_for('analytics') }}">Analytics</a></li>
              <li class="nav-item"><a class="nav-link" href="{{ url_for('list_reminders') }}">Reminders</a></li>
            </ul>
            <div class="d-flex gap-2">
              <a href="{{ url_for('export_csv') }}" class="btn btn-outline-light btn-sm">Export CSV</a>
              <a href="{{ url_for('new_opportunity') }}" class="btn btn-success btn-sm">+ New Opportunity</a>
            </div>
          </div>
        </div>
      </nav>

      <main class="container my-4">
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="alert alert-info">{{ messages[0] }}</div>
          {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
      </main>

      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """,
    'dashboard.html': r"""
    {% extends 'layout.html' %}
    {% block content %}
      <div class="row g-3">
        <div class="col-md-3">
          <div class="card card-ghost"><div class="card-body">
            <div class="text-muted">Pipeline (weighted)</div>
            <div class="fs-4 fw-bold">£{{ '%.2f'|format(kpis.weighted_pipeline) }}</div>
          </div></div>
        </div>
        <div class="col-md-3">
          <div class="card card-ghost"><div class="card-body">
            <div class="text-muted">Opportunities</div>
            <div class="fs-4 fw-bold">{{ kpis.count_open }}</div>
          </div></div>
        </div>
        <div class="col-md-3">
          <div class="card card-ghost"><div class="card-body">
            <div class="text-muted">Won (last 30d)</div>
            <div class="fs-4 fw-bold">£{{ '%.2f'|format(kpis.won_last_30) }}</div>
          </div></div>
        </div>
        <div class="col-md-3">
          <div class="card card-ghost"><div class="card-body">
            <div class="text-muted">Due/Overdue reminders</div>
            <div class="fs-4 fw-bold">{{ reminders|length }}</div>
          </div></div>
        </div>
      </div>

      {% if reminders %}
      <div class="alert alert-warning mt-3">
        <strong>Heads up!</strong> You have {{ reminders|length }} reminder(s) due. 
        <a href="{{ url_for('list_reminders') }}" class="alert-link">Review now</a>.
      </div>
      {% endif %}

      <div class="row mt-4 g-3">
        <div class="col-lg-7">
          <div class="card card-ghost"><div class="card-body">
            <h6 class="mb-3">Value by Stage</h6>
            <canvas id="stageChart"></canvas>
          </div></div>
        </div>
        <div class="col-lg-5">
          <div class="card card-ghost"><div class="card-body">
            <h6 class="mb-3">Engagement Mix</h6>
            <canvas id="engChart"></canvas>
          </div></div>
        </div>
      </div>

      <script>
        const stageLabels = {{ chart.labels|tojson }};
        const stageTotals = {{ chart.totals|tojson }};
        new Chart(document.getElementById('stageChart'), { type: 'bar', data: { labels: stageLabels, datasets: [{ label: '£ value', data: stageTotals }] }, options: { responsive: true, plugins:{ legend:{display:true } } } });

        const engLabels = {{ mix.labels|tojson }};
        const engCounts = {{ mix.counts|tojson }};
        new Chart(document.getElementById('engChart'), { type: 'doughnut', data: { labels: engLabels, datasets: [{ data: engCounts }] }, options: { responsive: true } });
      </script>
    {% endblock %}
    """,
    'clients/list.html': r"""
    {% extends 'layout.html' %}
    {% block content %}
    <div class="d-flex justify-content-between align-items-center">
      <h4>Clients</h4>
      <a href="{{ url_for('new_client') }}" class="btn btn-primary btn-sm">+ New Client</a>
    </div>
    <div class="table-responsive mt-3">
      <table class="table table-striped align-middle">
        <thead><tr><th>Company</th><th>Primary Contact</th><th>Email</th><th>Phone</th><th></th></tr></thead>
        <tbody>
          {% for c in clients %}
          <tr>
            <td>{{ c.company }}</td>
            <td>{{ c.primary_contact or '-' }}</td>
            <td>{{ c.email or '-' }}</td>
            <td>{{ c.phone or '-' }}</td>
            <td class="text-end">
              <a href="{{ url_for('edit_client', cid=c.id) }}" class="btn btn-sm btn-outline-secondary">Edit</a>
              <a href="{{ url_for('delete_client', cid=c.id) }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('Delete client?')">Delete</a>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% endblock %}
    """,
    'clients/form.html': r"""
    {% extends 'layout.html' %}
    {% block content %}
    <h4>{{ 'Edit' if client else 'New' }} Client</h4>
    <form method="post" class="mt-3">
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label">Company</label>
          <input required name="company" class="form-control" value="{{ client.company if client else '' }}">
        </div>
        <div class="col-md-6">
          <label class="form-label">Primary Contact</label>
          <input name="primary_contact" class="form-control" value="{{ client.primary_contact if client else '' }}">
        </div>
        <div class="col-md-6">
          <label class="form-label">Email</label>
          <input name="email" class="form-control" value="{{ client.email if client else '' }}">
        </div>
        <div class="col-md-6">
          <label class="form-label">Phone</label>
          <input name="phone" class="form-control" value="{{ client.phone if client else '' }}">
        </div>
        <div class="col-12">
          <label class="form-label">Notes</label>
          <textarea name="notes" class="form-control" rows="3">{{ client.notes if client else '' }}</textarea>
        </div>
      </div>
      <div class="mt-3">
        <button class="btn btn-primary">Save</button>
        <a href="{{ url_for('list_clients') }}" class="btn btn-secondary">Cancel</a>
      </div>
    </form>
    {% endblock %}
    """,
    'opps/list.html': r"""
    {% extends 'layout.html' %}
    {% block content %}
    <div class="d-flex justify-content-between align-items-center">
      <h4>Opportunities</h4>
      <a href="{{ url_for('new_opportunity') }}" class="btn btn-primary btn-sm">+ New Opportunity</a>
    </div>

    <form class="row g-2 mt-2" method="get">
      <div class="col-md-3">
        <label class="form-label">Stage</label>
        <select name="stage" class="form-select">
          <option value="">All</option>
          {% for s in stages %}
            <option value="{{ s }}" {% if request.args.get('stage')==s %}selected{% endif %}>{{ s }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-3">
        <label class="form-label">Engagement</label>
        <select name="eng" class="form-select">
          <option value="">All</option>
          {% for t in ['Red','Purple','Mixed'] %}
            <option value="{{ t }}" {% if request.args.get('eng')==t %}selected{% endif %}>{{ t }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-3">
        <label class="form-label">Owner</label>
        <input name="owner" class="form-control" value="{{ request.args.get('owner','') }}" placeholder="e.g., Alice">
      </div>
      <div class="col-md-3 d-flex align-items-end gap-2">
        <button class="btn btn-outline-primary">Filter</button>
        <a href="{{ url_for('list_opportunities') }}" class="btn btn-outline-secondary">Reset</a>
      </div>
    </form>

    <div class="table-responsive mt-3">
      <table class="table table-striped align-middle">
        <thead>
          <tr><th>Title</th><th>Client</th><th>Stage</th><th>Owner</th><th>Engagement</th><th>Value</th><th>Probability</th><th>Expected Close</th><th>Tags</th><th></th></tr>
        </thead>
        <tbody>
          {% for o in opportunities %}
          <tr>
            <td>{{ o.title }}</td>
            <td>{{ o.client.company if o.client else '-' }}</td>
            <td><span class="badge bg-{{ stage_color(o.status) }}">{{ o.status }}</span></td>
            <td>{{ o.owner or '—' }}</td>
            <td>{{ o.engagement_type }}</td>
            <td>£{{ '%.2f'|format(o.value or 0) }}</td>
            <td>{{ o.probability }}%</td>
            <td>{{ o.expected_close or '-' }}</td>
            <td>{% for t in o.tags_list %}<span class="badge tag me-1">{{ t }}</span>{% endfor %}</td>
            <td class="text-end"><a href="{{ url_for('view_opportunity', oid=o.id) }}" class="btn btn-sm btn-outline-secondary">Open</a></td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% endblock %}
    """,
    'opps/form.html': r"""
    {% extends 'layout.html' %}
    {% block content %}
    <h4>{{ 'Edit' if opp else 'New' }} Opportunity</h4>
    <form method="post" class="mt-3">
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label">Title</label>
          <input required name="title" class="form-control" value="{{ opp.title if opp else '' }}">
        </div>
        <div class="col-md-3">
          <label class="form-label">Client</label>
          <select name="client_id" class="form-select">
            <option value="">--</option>
            {% for c in clients %}
              <option value="{{ c.id }}" {% if opp and opp.client_id==c.id %}selected{% endif %}>{{ c.company }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-3">
          <label class="form-label">Engagement Type</label>
          <select name="engagement_type" class="form-select">
            {% for t in ['Red','Purple','Mixed'] %}
              <option value="{{ t }}" {% if opp and opp.engagement_type==t %}selected{% endif %}>{{ t }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-3">
          <label class="form-label">Stage</label>
          <select name="status" class="form-select">
            {% for s in stages %}
              <option value="{{ s }}" {% if opp and opp.status==s %}selected{% endif %}>{{ s }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-3">
          <label class="form-label">Owner</label>
          <input name="owner" class="form-control" value="{{ opp.owner if opp else '' }}" placeholder="e.g., Alice">
        </div>
        <div class="col-md-3">
          <label class="form-label">Value (£)</label>
          <input name="value" type="number" step="0.01" class="form-control" value="{{ opp.value if opp and opp.value is not none else '' }}">
        </div>
        <div class="col-md-3">
          <label class="form-label">Probability (%)</label>
          <input name="probability" type="number" min="0" max="100" class="form-control" value="{{ opp.probability if opp else 10 }}">
        </div>
        <div class="col-md-3">
          <label class="form-label">Expected Close</label>
          <input name="expected_close" type="date" class="form-control" value="{{ opp.expected_close }}">
        </div>
        <div class="col-md-6">
          <label class="form-label">Tags (comma or space separated)</label>
          <input name="tags" class="form-control" value="{{ opp.tags if opp else '' }}" placeholder="e.g., purple-team red-team MDR pentest">
        </div>
      </div>
      <div class="mt-3">
        <button class="btn btn-primary">Save</button>
        <a href="{{ url_for('list_opportunities') }}" class="btn btn-secondary">Cancel</a>
      </div>
    </form>
    {% endblock %}
    """,
    'opps/view.html': r"""
    {% extends 'layout.html' %}
    {% block content %}
    <div class="d-flex justify-content-between align-items-center">
      <h4>{{ opp.title }}</h4>
      <div>
        <a href="{{ url_for('edit_opportunity', oid=opp.id) }}" class="btn btn-sm btn-outline-secondary">Edit</a>
        <a href="{{ url_for('delete_opportunity', oid=opp.id) }}" onclick="return confirm('Delete?')" class="btn btn-sm btn-outline-danger">Delete</a>
      </div>
    </div>

    <div class="row g-3 mt-1">
      <div class="col-md-8">
        <div class="card card-ghost">
          <div class="card-body">
            <div class="d-flex justify-content-between">
              <div>
                <div class="mb-1">Client: <strong>{{ opp.client.company if opp.client else '-' }}</strong></div>
                <div class="mb-1">Stage: <span class="badge bg-{{ stage_color(opp.status) }}">{{ opp.status }}</span></div>
                <div class="mb-1">Engagement: {{ opp.engagement_type }}</div>
                <div class="mb-1">Owner: {{ opp.owner or '—' }}</div>
                <div class="mb-1">Tags: {% for t in opp.tags_list %}<span class="badge tag me-1">{{ t }}</span>{% else %}—{% endfor %}</div>
                <div class="mb-1 text-muted small">Created: {{ opp.created_at.strftime('%Y-%m-%d') if opp.created_at else '—' }}{% if opp.closed_at %} • Closed: {{ opp.closed_at.strftime('%Y-%m-%d') }}{% endif %}</div>
              </div>
              <div style="min-width:220px">
                <div class="text-muted small">Progress</div>
                <div class="progress">
                  <div class="progress-bar bg-{{ stage_color(opp.status) }}" style="width: {{ completion(opp.status) }}%">{{ completion(opp.status) }}%</div>
                </div>
              </div>
            </div>

            <hr/>
            <h6>Activities</h6>
            <form method="post" action="{{ url_for('add_activity', oid=opp.id) }}" class="row g-2 mb-3">
              <div class="col-md-3">
                <select name="kind" class="form-select">
                  {% for k in ['Email','Call','Meeting','Note'] %}
                  <option value="{{ k }}">{{ k }}</option>
                  {% endfor %}
                </select>
              </div>
              <div class="col-md-7">
                <input name="notes" class="form-control" placeholder="Notes...">
              </div>
              <div class="col-md-2">
                <button class="btn btn-primary w-100">Add</button>
              </div>
            </form>

            <ul class="list-group">
              {% for a in opp.activities|sort(attribute='occurred_at', reverse=True) %}
              <li class="list-group-item d-flex justify-content-between align-items-center">
                <span><strong>{{ a.kind }}</strong> — {{ a.notes or '' }}</span>
                <span class="text-muted small">{{ a.occurred_at.strftime('%Y-%m-%d %H:%M') }}</span>
              </li>
              {% else %}
              <li class="list-group-item">No activities yet.</li>
              {% endfor %}
            </ul>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card card-ghost mb-3">
          <div class="card-body">
            <h6 class="mb-3">Budget</h6>
            <form method="post" action="{{ url_for('save_budget', oid=opp.id) }}" class="row g-2">
              <div class="col-12">
                <label class="form-label">Total Budget ({{ opp.budget.currency if opp.budget else 'GBP' }})</label>
                <input name="total_budget" type="number" step="0.01" class="form-control" value="{{ opp.budget.total_budget if opp.budget else '' }}">
              </div>
              <div class="col-12">
                <label class="form-label">Cost Estimate</label>
                <input name="cost_estimate" type="number" step="0.01" class="form-control" value="{{ opp.budget.cost_estimate if opp.budget else '' }}">
              </div>
              <div class="col-6">
                <label class="form-label">Currency</label>
                <input name="currency" class="form-control" value="{{ opp.budget.currency if opp.budget else 'GBP' }}">
              </div>
              <div class="col-6 d-flex align-items-end justify-content-end">
                <button class="btn btn-outline-primary">Save</button>
              </div>
            </form>
            {% if opp.budget %}
            <div class="mt-2 small text-muted">Margin: <strong>{{ opp.budget.margin }}</strong></div>
            {% endif %}
          </div>
        </div>

        <div class="card card-ghost">
          <div class="card-body">
            <h6 class="mb-3">Reminders</h6>
            <form method="post" action="{{ url_for('add_reminder', oid=opp.id) }}" class="row g-2">
              <div class="col-8">
                <input name="message" class="form-control" placeholder="E.g., Send follow-up email" required>
              </div>
              <div class="col-4">
                <input name="due_at" type="datetime-local" class="form-control" required>
              </div>
              <div class="col-12 d-flex justify-content-end">
                <button class="btn btn-outline-primary">Add Reminder</button>
              </div>
            </form>
            <ul class="list-group mt-2">
              {% for r in opp.reminders|sort(attribute='due_at') %}
              <li class="list-group-item d-flex justify-content-between align-items-center">
                <span>{{ r.message }}<br><span class="small text-muted">Due: {{ r.due_at.strftime('%Y-%m-%d %H:%M') }}</span></span>
                <span>
                  {% if not r.sent and r.due_at <= now %}<span class="badge bg-warning text-dark me-2">Due</span>{% endif %}
                  {% if r.sent %}<span class="badge bg-success me-2">Sent</span>{% endif %}
                  <a class="btn btn-sm btn-outline-success" href="{{ url_for('mark_reminder_sent', rid=r.id) }}">Mark sent</a>
                </span>
              </li>
              {% else %}
              <li class="list-group-item">No reminders yet.</li>
              {% endfor %}
            </ul>
          </div>
        </div>
      </div>
    </div>
    {% endblock %}
    """,
    'kanban.html': r"""
    {% extends 'layout.html' %}
    {% block content %}
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h4>Kanban</h4>
      <div>
        <a href="{{ url_for('new_opportunity') }}" class="btn btn-primary btn-sm">+ New Opportunity</a>
      </div>
    </div>

    <form class="row g-2 mb-3" method="get">
      <div class="col-md-3">
        <label class="form-label">Engagement</label>
        <select name="eng" class="form-select">
          <option value="">All</option>
          {% for t in ['Red','Purple','Mixed'] %}
          <option value="{{ t }}" {% if request.args.get('eng')==t %}selected{% endif %}>{{ t }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-3">
        <label class="form-label">Owner</label>
        <input name="owner" class="form-control" value="{{ request.args.get('owner','') }}" placeholder="e.g., Alice">
      </div>
      <div class="col-md-3">
        <label class="form-label">Tag contains</label>
        <input name="tag" class="form-control" value="{{ request.args.get('tag','') }}" placeholder="e.g., pentest">
      </div>
      <div class="col-md-3 d-flex align-items-end gap-2">
        <button class="btn btn-outline-primary">Filter</button>
        <a href="{{ url_for('kanban') }}" class="btn btn-outline-secondary">Reset</a>
      </div>
    </form>

    <div class="row g-3">
      {% for stage in stages %}
      <div class="col-md-4 col-lg-2">
        <div class="kanban-col">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="fw-semibold">{{ stage }}</span>
            <span class="badge bg-{{ stage_color(stage) }}">{{ board[stage]|length }}</span>
          </div>
          {% for o in board[stage] %}
          <div class="kanban-card">
            <div class="small text-muted">{{ o.client.company if o.client else '—' }}</div>
            <div class="fw-semibold">{{ o.title }}</div>
            <div class="d-flex justify-content-between align-items-center small mt-1">
              <span>£{{ '%.0f'|format(o.value or 0) }}</span>
              <span>{{ o.owner or '—' }}</span>
            </div>
            <div class="mt-1">{% for t in o.tags_list %}<span class="badge tag me-1">{{ t }}</span>{% endfor %}</div>
            <div class="mt-2 d-flex gap-2">
              <a class="btn btn-sm btn-outline-secondary flex-fill" href="{{ url_for('view_opportunity', oid=o.id) }}">Open</a>
              <form method="post" action="{{ url_for('quick_move', oid=o.id) }}">
                <input type="hidden" name="next" value="{{ stage }}">
                <select name="to" class="form-select form-select-sm" onchange="this.form.submit()">
                  <option value="">Move…</option>
                  {% for s in stages %}
                    {% if s!=stage %}<option value="{{ s }}">{{ s }}</option>{% endif %}
                  {% endfor %}
                </select>
              </form>
            </div>
          </div>
          {% else %}
          <div class="text-muted small">No items</div>
          {% endfor %}
        </div>
      </div>
      {% endfor %}
    </div>
    {% endblock %}
    """,
    'analytics.html': r"""
    {% extends 'layout.html' %}
    {% block content %}
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h4>Analytics</h4>
    </div>

    <div class="row g-3">
      <div class="col-lg-6">
        <div class="card card-ghost"><div class="card-body">
          <h6 class="mb-3">Win Rate (last 6 months)</h6>
          <canvas id="winRate"></canvas>
        </div></div>
      </div>
      <div class="col-lg-6">
        <div class="card card-ghost"><div class="card-body">
          <h6 class="mb-3">Average Cycle Time in Days (by stage at close)</h6>
          <canvas id="cycleTime"></canvas>
        </div></div>
      </div>
      <div class="col-lg-6">
        <div class="card card-ghost"><div class="card-body">
          <h6 class="mb-3">Forecast — Weighted Pipeline by Month (next 6 months)</h6>
          <canvas id="forecast"></canvas>
        </div></div>
      </div>
      <div class="col-lg-6">
        <div class="card card-ghost"><div class="card-body">
          <h6 class="mb-3">Owner Leaderboard (Won value, last 90 days)</h6>
          <canvas id="owners"></canvas>
        </div></div>
      </div>
    </div>

    <script>
      new Chart(document.getElementById('winRate'), { type:'line', data:{ labels: {{ charts['win']['labels']|tojson }}, datasets:[{ label:'Win %', data: {{ charts['win']['values']|tojson }} }] }, options:{ scales:{ y:{ min:0, max:100 } } } });
      new Chart(document.getElementById('cycleTime'), { type:'bar', data:{ labels: {{ charts['cycle']['labels']|tojson }}, datasets:[{ label:'Days', data: {{ charts['cycle']['values']|tojson }} }] } });
      new Chart(document.getElementById('forecast'), { type:'bar', data:{ labels: {{ charts['forecast']['labels']|tojson }}, datasets:[{ label:'Weighted £', data: {{ charts['forecast']['values']|tojson }} }] } });
      new Chart(document.getElementById('owners'), { type:'bar', data:{ labels: {{ charts['owners']['labels']|tojson }}, datasets:[{ label:'Won £', data: {{ charts['owners']['values']|tojson }} }] }, options:{ indexAxis:'y' } });
    </script>
    {% endblock %}
    """,
    'reminders/list.html': r"""
    {% extends 'layout.html' %}
    {% block content %}
    <h4>Reminders</h4>
    <div class="table-responsive mt-3">
      <table class="table align-middle">
        <thead><tr><th>Opportunity</th><th>Message</th><th>Due</th><th>Status</th><th></th></tr></thead>
        <tbody>
          {% for r in reminders %}
          <tr class="{% if not r.sent and r.due_at <= now %}table-warning{% endif %}">
            <td>{{ r.opportunity.title if r.opportunity else '-' }}</td>
            <td>{{ r.message }}</td>
            <td>{{ r.due_at.strftime('%Y-%m-%d %H:%M') }}</td>
            <td>{% if r.sent %}<span class="badge bg-success">Sent</span>{% else %}<span class="badge bg-secondary">Pending</span>{% endif %}</td>
            <td class="text-end">
              {% if not r.sent %}<a href="{{ url_for('mark_reminder_sent', rid=r.id) }}" class="btn btn-sm btn-outline-success">Mark sent</a>{% endif %}
              <a href="{{ url_for('delete_reminder', rid=r.id) }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('Delete reminder?')">Delete</a>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% endblock %}
    """,
}

app.jinja_loader = DictLoader(TEMPLATES)

# --- Routes ---
@app.route('/')
def dashboard():
    now = datetime.utcnow()
    # KPIs
    open_opps = Opportunity.query.filter(Opportunity.status.in_(['Lead','Qualified','Proposal','Negotiation'])).all()
    weighted_pipeline = sum(float(o.value or 0) * (float(o.probability or 0)/100.0) for o in open_opps)
    won_last_30 = sum(float(o.value or 0) for o in Opportunity.query.filter_by(status='Won').all() if (o.closed_at and (datetime.utcnow() - o.closed_at).days <= 30))
    due_reminders = Reminder.query.filter(Reminder.sent==False, Reminder.due_at <= now).all()

    # Chart data: total value by stage
    totals_by_stage = defaultdict(float)
    mix_counts = Counter()
    for o in Opportunity.query.all():
        totals_by_stage[o.status] += float(o.value or 0)
        mix_counts[o.engagement_type or 'Mixed'] += 1
    labels = STAGE_ORDER
    totals = [round(totals_by_stage[s], 2) for s in labels]

    return render_template_string(
        TEMPLATES['dashboard.html'],
        kpis={
            'weighted_pipeline': weighted_pipeline,
            'count_open': len(open_opps),
            'won_last_30': won_last_30,
        },
        opportunities=open_opps,
        reminders=due_reminders,
        stage_color=stage_color,
        completion=lambda s: STAGE_COMPLETION.get(s, 0),
        chart={'labels': labels, 'totals': totals},
        mix={'labels': list(mix_counts.keys()), 'counts': list(mix_counts.values())}
    )

# Clients
@app.route('/clients')
def list_clients():
    clients = Client.query.order_by(Client.company).all()
    return render_template_string(TEMPLATES['clients/list.html'], clients=clients)

@app.route('/clients/new', methods=['GET','POST'])
def new_client():
    if request.method == 'POST':
        c = Client(
            company=request.form['company'],
            primary_contact=request.form.get('primary_contact') or None,
            email=request.form.get('email') or None,
            phone=request.form.get('phone') or None,
            notes=request.form.get('notes') or None,
        )
        db.session.add(c)
        db.session.commit()
        flash('Client created')
        return redirect(url_for('list_clients'))
    return render_template_string(TEMPLATES['clients/form.html'], client=None)

@app.route('/clients/<int:cid>/edit', methods=['GET','POST'])
def edit_client(cid):
    c = Client.query.get_or_404(cid)
    if request.method == 'POST':
        c.company = request.form['company']
        c.primary_contact = request.form.get('primary_contact') or None
        c.email = request.form.get('email') or None
        c.phone = request.form.get('phone') or None
        c.notes = request.form.get('notes') or None
        db.session.commit()
        flash('Client updated')
        return redirect(url_for('list_clients'))
    return render_template_string(TEMPLATES['clients/form.html'], client=c)

@app.route('/clients/<int:cid>/delete')
def delete_client(cid):
    c = Client.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    flash('Client deleted')
    return redirect(url_for('list_clients'))

# Opportunities
@app.route('/opportunities')
def list_opportunities():
    q = Opportunity.query
    stage = request.args.get('stage') or None
    eng = request.args.get('eng') or None
    owner = (request.args.get('owner') or '').strip()
    if stage:
        q = q.filter_by(status=stage)
    if eng:
        q = q.filter_by(engagement_type=eng)
    if owner:
        q = q.filter(Opportunity.owner.ilike(f"%{owner}%"))
    opps = q.order_by(Opportunity.expected_close.is_(None), Opportunity.expected_close).all()
    return render_template_string(TEMPLATES['opps/list.html'], opportunities=opps, stage_color=stage_color, stages=STAGE_ORDER)

@app.route('/opportunities/new', methods=['GET','POST'])
def new_opportunity():
    clients = Client.query.order_by(Client.company).all()
    if request.method == 'POST':
        expected_close = request.form.get('expected_close') or None
        expected_close = datetime.strptime(expected_close, '%Y-%m-%d').date() if expected_close else None
        o = Opportunity(
            title=request.form['title'],
            client_id=request.form.get('client_id') or None,
            engagement_type=request.form.get('engagement_type') or 'Mixed',
            status=request.form.get('status') or 'Lead',
            owner=request.form.get('owner') or 'Unassigned',
            tags=(request.form.get('tags') or '').strip() or None,
            value=Decimal(request.form.get('value') or '0'),
            probability=int(request.form.get('probability') or 10),
            expected_close=expected_close,
        )
        db.session.add(o)
        db.session.commit()
        flash('Opportunity created')
        return redirect(url_for('view_opportunity', oid=o.id))
    return render_template_string(TEMPLATES['opps/form.html'], opp=None, clients=clients, stages=STAGE_ORDER)

@app.route('/opportunities/<int:oid>')
def view_opportunity(oid):
    o = Opportunity.query.get_or_404(oid)
    return render_template_string(
        TEMPLATES['opps/view.html'],
        opp=o,
        now=datetime.utcnow(),
        stage_color=stage_color,
        completion=lambda s: STAGE_COMPLETION.get(s,0),
    )

@app.route('/opportunities/<int:oid>/edit', methods=['GET','POST'])
def edit_opportunity(oid):
    o = Opportunity.query.get_or_404(oid)
    prev_status = o.status
    clients = Client.query.order_by(Client.company).all()
    if request.method == 'POST':
        o.title = request.form['title']
        o.client_id = request.form.get('client_id') or None
        o.engagement_type = request.form.get('engagement_type') or 'Mixed'
        o.status = request.form.get('status') or 'Lead'
        o.owner = request.form.get('owner') or 'Unassigned'
        o.tags = (request.form.get('tags') or '').strip() or None
        o.value = Decimal(request.form.get('value') or '0')
        o.probability = int(request.form.get('probability') or 10)
        expected_close = request.form.get('expected_close') or None
        o.expected_close = datetime.strptime(expected_close, '%Y-%m-%d').date() if expected_close else None
        # auto timestamp close
        if o.status in ('Won','Lost') and not o.closed_at:
            o.closed_at = datetime.utcnow()
        if prev_status in ('Won','Lost') and o.status not in ('Won','Lost'):
            o.closed_at = None
        db.session.commit()
        flash('Opportunity updated')
        return redirect(url_for('view_opportunity', oid=o.id))
    return render_template_string(TEMPLATES['opps/form.html'], opp=o, clients=clients, stages=STAGE_ORDER)

@app.route('/opportunities/<int:oid>/delete')
def delete_opportunity(oid):
    o = Opportunity.query.get_or_404(oid)
    db.session.delete(o)
    db.session.commit()
    flash('Opportunity deleted')
    return redirect(url_for('list_opportunities'))

# Quick move from Kanban
@app.route('/opportunities/<int:oid>/move', methods=['POST'])
def quick_move(oid):
    o = Opportunity.query.get_or_404(oid)
    to = request.form.get('to')
    if to and to in STAGE_ORDER:
        o.status = to
        if o.status in ('Won','Lost') and not o.closed_at:
            o.closed_at = datetime.utcnow()
        db.session.commit()
        flash(f'Moved to {to}')
    return redirect(url_for('kanban'))

# Activities
@app.route('/opportunities/<int:oid>/activities/add', methods=['POST'])
def add_activity(oid):
    o = Opportunity.query.get_or_404(oid)
    a = Activity(kind=request.form.get('kind','Note'), notes=request.form.get('notes') or None, opportunity=o)
    db.session.add(a)
    db.session.commit()
    flash('Activity added')
    return redirect(url_for('view_opportunity', oid=oid))

# Budget
@app.route('/opportunities/<int:oid>/budget/save', methods=['POST'])
def save_budget(oid):
    o = Opportunity.query.get_or_404(oid)
    if not o.budget:
        o.budget = ProjectBudget()
    o.budget.total_budget = Decimal(request.form.get('total_budget') or '0')
    o.budget.cost_estimate = Decimal(request.form.get('cost_estimate') or '0')
    o.budget.currency = request.form.get('currency') or o.budget.currency
    db.session.commit()
    flash('Budget saved')
    return redirect(url_for('view_opportunity', oid=oid))

# Reminders
@app.route('/opportunities/<int:oid>/reminders/add', methods=['POST'])
def add_reminder(oid):
    o = Opportunity.query.get_or_404(oid)
    due_str = request.form['due_at']
    # HTML datetime-local => '%Y-%m-%dT%H:%M'
    due_at = datetime.strptime(due_str, '%Y-%m-%dT%H:%M')
    r = Reminder(message=request.form['message'], due_at=due_at, opportunity=o)
    db.session.add(r)
    db.session.commit()
    flash('Reminder added')
    return redirect(url_for('view_opportunity', oid=oid))

@app.route('/reminders')
def list_reminders():
    reminders = Reminder.query.order_by(Reminder.due_at).all()
    return render_template_string(TEMPLATES['reminders/list.html'], reminders=reminders, now=datetime.utcnow())

@app.route('/reminders/<int:rid>/sent')
def mark_reminder_sent(rid):
    r = Reminder.query.get_or_404(rid)
    r.sent = True
    db.session.commit()
    flash('Marked as sent')
    return redirect(request.referrer or url_for('list_reminders'))

@app.route('/reminders/<int:rid>/delete')
def delete_reminder(rid):
    r = Reminder.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    flash('Reminder deleted')
    return redirect(url_for('list_reminders'))

# Kanban
@app.route('/kanban')
def kanban():
    q = Opportunity.query
    eng = request.args.get('eng') or None
    owner = (request.args.get('owner') or '').strip()
    tag = (request.args.get('tag') or '').strip().lower()
    if eng:
        q = q.filter_by(engagement_type=eng)
    if owner:
        q = q.filter(Opportunity.owner.ilike(f"%{owner}%"))
    if tag:
        q = q.filter(Opportunity.tags.ilike(f"%{tag}%"))
    opps = q.all()

    board = {s: [] for s in STAGE_ORDER}
    for o in opps:
        board.get(o.status, board['Lead']).append(o)

    return render_template_string(TEMPLATES['kanban.html'], stages=STAGE_ORDER, board=board, stage_color=stage_color)

# Analytics
@app.route('/analytics')
def analytics():
    # Win rate last 6 months (won / (won+lost)) by closed_at month
    def month_key(dt):
        return dt.strftime('%Y-%m')

    now = datetime.utcnow()
    months = []
    for i in range(5, -1, -1):
        m = (now.replace(day=1) - timedelta(days=30*i))
        months.append(m.strftime('%Y-%m'))

    won_counts = {m:0 for m in months}
    lost_counts = {m:0 for m in months}
    for o in Opportunity.query.filter(Opportunity.closed_at.isnot(None)).all():
        m = month_key(o.closed_at)
        if m in won_counts or m in lost_counts:
            if o.status == 'Won':
                won_counts[m] += 1
            elif o.status == 'Lost':
                lost_counts[m] += 1
    win_rate = []
    for m in months:
        w = won_counts[m]; l = lost_counts[m]
        win_rate.append(round((w/(w+l)*100) if (w+l)>0 else 0, 1))

    # Cycle time (days) average for closed deals by closing stage ('Won' and 'Lost')
    cycle_days = defaultdict(list)
    for o in Opportunity.query.filter(Opportunity.closed_at.isnot(None)).all():
        start = o.created_at or o.closed_at
        days = max(0, (o.closed_at - start).days)
        cycle_days[o.status].append(days)
    cycle_labels = ['Won','Lost']
    cycle_values = [round(sum(cycle_days[s])/len(cycle_days[s]),1) if cycle_days[s] else 0 for s in cycle_labels]

    # Forecast next 6 months: sum(value*prob) grouped by expected_close month
    def add_months(d, n):
        y = d.year + (d.month - 1 + n)//12
        m = (d.month - 1 + n)%12 + 1
        return date(y, m, 1)
    start = date.today().replace(day=1)
    f_months = [add_months(start, i) for i in range(0, 6)]
    f_labels = [m.strftime('%Y-%m') for m in f_months]
    f_values = [0.0 for _ in f_months]
    index = {lab:i for i,lab in enumerate(f_labels)}
    for o in Opportunity.query.filter(Opportunity.expected_close.isnot(None)).all():
        m = o.expected_close.strftime('%Y-%m')
        if m in index:
            f_values[index[m]] += float(o.value or 0) * (float(o.probability or 0)/100.0)
    f_values = [round(v,2) for v in f_values]

    # Owner leaderboard (won value last 90 days)
    owners = defaultdict(float)
    cutoff = datetime.utcnow() - timedelta(days=90)
    for o in Opportunity.query.filter_by(status='Won').all():
        if o.closed_at and o.closed_at >= cutoff:
            owners[o.owner or 'Unassigned'] += float(o.value or 0)
    owner_labels = list(owners.keys())
    owner_values = [round(owners[k],2) for k in owner_labels]

    charts = {
        'win': {'labels': months, 'values': win_rate},
        'cycle': {'labels': cycle_labels, 'values': cycle_values},
        'forecast': {'labels': f_labels, 'values': f_values},
        'owners': {'labels': owner_labels, 'values': owner_values},
    }

    return render_template_string(TEMPLATES['analytics.html'], charts=charts)

# Export CSV
@app.route('/export.csv')
@app.route('/export')
def export_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID','Title','Client','Status','Owner','Engagement','Value','Probability','Expected Close','Created At','Closed At','Tags'])
    for o in Opportunity.query.all():
        writer.writerow([
            o.id,
            o.title,
            (o.client.company if o.client else ''),
            o.status,
            o.owner or '',
            o.engagement_type or '',
            float(o.value or 0),
            int(o.probability or 0),
            o.expected_close.isoformat() if o.expected_close else '',
            o.created_at.isoformat() if o.created_at else '',
            o.closed_at.isoformat() if o.closed_at else '',
            ' '.join(o.tags_list)
        ])
    csv_data = output.getvalue()
    output.close()
    return Response(csv_data, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=opportunities.csv'})

# --- CLI / bootstrap ---
@app.cli.command('init-db')
def init_db_cmd():
    """Initialize the database tables."""
    db.create_all()
    print('Database initialized.')

# --- App start ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)), debug=True)
