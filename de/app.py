import os
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from jinja2 import DictLoader

# --- Config ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scheduler.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
db = SQLAlchemy(app)

# --- Models ---
class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    client = db.Column(db.String(120))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    engagement_type = db.Column(db.String(50))  # Red | Purple | Mixed
    status = db.Column(db.String(50), default='Planned')  # Planned, Active, On Hold, Completed
    notes = db.Column(db.Text)

    assignments = relationship('Assignment', back_populates='project', cascade='all, delete-orphan')

class Resource(db.Model):
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120))  # e.g., Red Team Operator, Purple Team Lead, Threat Intel
    skills = db.Column(db.String(250))  # comma-separated tags
    clearance = db.Column(db.String(50))  # e.g., None, SC, DV
    availability_pct = db.Column(db.Integer, default=100)  # 0-100
    color_team = db.Column(db.String(20))  # Red | Purple | Blue | Mixed

    assignments = relationship('Assignment', back_populates='resource', cascade='all, delete-orphan')

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False)
    allocation_pct = db.Column(db.Integer, default=50)  # percentage allocation to this project
    role_on_project = db.Column(db.String(120))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    project = relationship('Project', back_populates='assignments')
    resource = relationship('Resource', back_populates='assignments')

# --- Utilities ---
def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except ValueError:
        return None

# --- Templates (Bootstrap 5) ---
BASE = """
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>Project Scheduler – Red/Purple</title>
    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
    <style>
      body { background: #0b1020; color: #eef; }
      .navbar, .card { background: #111833; border: 1px solid #263052; }
      .form-control, .form-select { background: #0f162d; color: #eef; border-color:#263052; }
      a, .nav-link { color: #a9c1ff; }
      .badge-red { background: #d7263d; }
      .badge-purple { background: #8a2be2; }
      .chip { border:1px solid #394569; border-radius: 999px; padding: 2px 10px; margin-right: 6px; }
      .table { color:#dbe2ff; }
      .table thead th { color:#9ab; }
    </style>
  </head>
  <body>
    <nav class=\"navbar navbar-expand-lg navbar-dark mb-4\">
      <div class=\"container-fluid\">
        <a class=\"navbar-brand\" href=\"{{ url_for('index') }}\">⚔️ Project Scheduler</a>
        <div>
          <a class=\"btn btn-outline-light btn-sm me-2\" href=\"{{ url_for('projects') }}\">Projects</a>
          <a class=\"btn btn-outline-light btn-sm me-2\" href=\"{{ url_for('resources_index') }}\">Resources</a>
          <a class=\"btn btn-outline-light btn-sm me-2\" href=\"{{ url_for('skills_matrix') }}\">Skills Matrix</a>
          <a class=\"btn btn-outline-light btn-sm me-2\" href=\"{{ url_for('heatmap_view') }}\">Heatmap</a>
          <a class=\"btn btn-light btn-sm\" href=\"{{ url_for('calendar_view') }}\">Calendar</a>
        </div>
      </div>
    </nav>
    <div class=\"container\">
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <div class=\"alert alert-info\">{{ messages[0] }}</div>
        {% endif %}
      {% endwith %}
      {% block content %}{% endblock %}
    </div>
    <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js\"></script>
  </body>
</html>
"""

INDEX = """
{% extends 'base.html' %}
{% block content %}
<div class=\"row g-4\">
  <div class=\"col-md-6\">
    <div class=\"card p-3 shadow-sm\">
      <h5>Quick Add – Project</h5>
      <form method=\"post\" action=\"{{ url_for('create_project') }}\">
        <div class=\"row g-2\">
          <div class=\"col-md-6\"><input required name=\"name\" class=\"form-control\" placeholder=\"Project name\"></div>
          <div class=\"col-md-6\"><input name=\"client\" class=\"form-control\" placeholder=\"Client\"></div>
          <div class=\"col-md-4\"><input type=\"date\" name=\"start_date\" class=\"form-control\"></div>
          <div class=\"col-md-4\"><input type=\"date\" name=\"end_date\" class=\"form-control\"></div>
          <div class=\"col-md-4\">
            <select name=\"engagement_type\" class=\"form-select\">
              <option value=\"Red\">Red</option>
              <option value=\"Purple\">Purple</option>
              <option value=\"Mixed\">Mixed</option>
            </select>
          </div>
          <div class=\"col-12\"><textarea name=\"notes\" class=\"form-control\" placeholder=\"Notes\"></textarea></div>
          <div class=\"col-12\"><button class=\"btn btn-primary\">Create Project</button></div>
        </div>
      </form>
    </div>
  </div>
  <div class=\"col-md-6\">
    <div class=\"card p-3 shadow-sm\">
      <h5>Quick Add – Resource</h5>
      <form method=\"post\" action=\"{{ url_for('create_resource') }}\">
        <div class=\"row g-2\">
          <div class=\"col-md-6\"><input required name=\"name\" class=\"form-control\" placeholder=\"Name\"></div>
          <div class=\"col-md-6\"><input name=\"role\" class=\"form-control\" placeholder=\"Role (e.g., Red Op, Purple Lead)\"></div>
          <div class=\"col-md-6\"><input name=\"skills\" class=\"form-control\" placeholder=\"Skills (comma-separated)\"></div>
          <div class=\"col-md-3\"><input name=\"clearance\" class=\"form-control\" placeholder=\"Clearance\"></div>
          <div class=\"col-md-3\"><input type=\"number\" name=\"availability_pct\" class=\"form-control\" min=\"0\" max=\"100\" value=\"100\" placeholder=\"Availability %\"></div>
          <div class=\"col-md-6\">
            <select name=\"color_team\" class=\"form-select\">
              <option value=\"Red\">Red</option>
              <option value=\"Purple\">Purple</option>
              <option value=\"Blue\">Blue</option>
              <option value=\"Mixed\">Mixed</option>
            </select>
          </div>
          <div class=\"col-12\"><button class=\"btn btn-success\">Create Resource</button></div>
        </div>
      </form>
    </div>
  </div>
</div>

<div class=\"row mt-4\">
  <div class=\"col-md-12\">
    <div class=\"card p-3 shadow-sm\">
      <div class=\"d-flex justify-content-between align-items-center\">
        <h5 class=\"mb-0\">Upcoming & Active Projects</h5>
        <a class=\"btn btn-outline-light btn-sm\" href=\"{{ url_for('projects') }}\">View all</a>
      </div>
      <table class=\"table table-sm table-striped mt-2\">
        <thead><tr><th>Name</th><th>Client</th><th>Type</th><th>Status</th><th>Start</th><th>End</th><th>Res.</th><th></th></tr></thead>
        <tbody>
          {% for p in recent_projects %}
          <tr>
            <td>{{ p.name }}</td>
            <td>{{ p.client or '-' }}</td>
            <td>
              {% if p.engagement_type == 'Red' %}<span class=\"badge badge-red\">Red</span>
              {% elif p.engagement_type == 'Purple' %}<span class=\"badge badge-purple\">Purple</span>
              {% else %}<span class=\"badge bg-secondary\">Mixed</span>{% endif %}
            </td>
            <td>{{ p.status }}</td>
            <td>{{ p.start_date or '-' }}</td>
            <td>{{ p.end_date or '-' }}</td>
            <td>{{ p.assignments|length }}</td>
            <td><a class=\"btn btn-sm btn-light\" href=\"{{ url_for('project_detail', project_id=p.id) }}\">Open</a></td>
          </tr>
          {% else %}
          <tr><td colspan=\"8\" class=\"text-center\">No projects yet.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>
{% endblock %}
"""

PROJECTS = """
{% extends 'base.html' %}
{% block content %}
<div class=\"d-flex justify-content-between align-items-center mb-2\">
  <h4>Projects</h4>
  <a class=\"btn btn-primary\" href=\"{{ url_for('new_project') }}\">New Project</a>
</div>
<div class=\"card p-3\">
  <form class=\"row g-2\" method=\"get\">
    <div class=\"col-md-4\"><input name=\"q\" value=\"{{ request.args.get('q','') }}\" class=\"form-control\" placeholder=\"Search by name or client\"></div>
    <div class=\"col-md-3\">
      <select name=\"type\" class=\"form-select\">
        <option value=\"\">Any Type</option>
        {% for t in ['Red','Purple','Mixed'] %}
          <option value=\"{{t}}\" {% if request.args.get('type')==t %}selected{% endif %}>{{t}}</option>
        {% endfor %}
      </select>
    </div>
    <div class=\"col-md-3\">
      <select name=\"status\" class=\"form-select\">
        <option value=\"\">Any Status</option>
        {% for s in ['Planned','Active','On Hold','Completed'] %}
          <option value=\"{{s}}\" {% if request.args.get('status')==s %}selected{% endif %}>{{s}}</option>
        {% endfor %}
      </select>
    </div>
    <div class=\"col-md-2\"><button class=\"btn btn-light w-100\">Filter</button></div>
  </form>
</div>

<div class=\"card p-3 mt-3\">
  <table class=\"table table-striped table-hover\">
    <thead><tr><th>Name</th><th>Client</th><th>Type</th><th>Status</th><th>Start</th><th>End</th><th>Assignments</th><th></th></tr></thead>
    <tbody>
      {% for p in projects %}
      <tr>
        <td>{{ p.name }}</td>
        <td>{{ p.client or '-' }}</td>
        <td>{{ p.engagement_type }}</td>
        <td>{{ p.status }}</td>
        <td>{{ p.start_date or '-' }}</td>
        <td>{{ p.end_date or '-' }}</td>
        <td>{{ p.assignments|length }}</td>
        <td>
          <a class=\"btn btn-sm btn-light\" href=\"{{ url_for('project_detail', project_id=p.id) }}\">Open</a>
          <a class=\"btn btn-sm btn-outline-danger\" href=\"{{ url_for('delete_project', project_id=p.id) }}\" onclick=\"return confirm('Delete this project?')\">Delete</a>
        </td>
      </tr>
      {% else %}
      <tr><td colspan=\"8\" class=\"text-center\">No projects found.</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
"""

PROJECT_DETAIL = """
{% extends 'base.html' %}
{% block content %}
<div class=\"d-flex justify-content-between align-items-center mb-2\">
  <h4>{{ project.name }}</h4>
  <div>
    <a class=\"btn btn-outline-light btn-sm\" href=\"{{ url_for('projects') }}\">Back</a>
  </div>
</div>

<div class=\"row g-3\">
  <div class=\"col-md-6\">
    <div class=\"card p-3\">
      <h6>Project Info</h6>
      <form method=\"post\" action=\"{{ url_for('update_project', project_id=project.id) }}\">
        <div class=\"row g-2\">
          <div class=\"col-md-6\"><input name=\"name\" class=\"form-control\" value=\"{{ project.name }}\" required></div>
          <div class=\"col-md-6\"><input name=\"client\" class=\"form-control\" value=\"{{ project.client or '' }}\" placeholder=\"Client\"></div>
          <div class=\"col-md-4\"><input type=\"date\" name=\"start_date\" class=\"form-control\" value=\"{{ project.start_date }}\"></div>
          <div class=\"col-md-4\"><input type=\"date\" name=\"end_date\" class=\"form-control\" value=\"{{ project.end_date }}\"></div>
          <div class=\"col-md-4\">
            <select name=\"engagement_type\" class=\"form-select\">
              {% for t in ['Red','Purple','Mixed'] %}
                <option value=\"{{t}}\" {% if project.engagement_type==t %}selected{% endif %}>{{t}}</option>
              {% endfor %}
            </select>
          </div>
          <div class=\"col-md-4\">
            <select name=\"status\" class=\"form-select\">
              {% for s in ['Planned','Active','On Hold','Completed'] %}
                <option value=\"{{s}}\" {% if project.status==s %}selected{% endif %}>{{s}}</option>
              {% endfor %}
            </select>
          </div>
          <div class=\"col-12\"><textarea name=\"notes\" class=\"form-control\" rows=\"3\" placeholder=\"Notes\">{{ project.notes or '' }}</textarea></div>
          <div class=\"col-12\"><button class=\"btn btn-primary\">Save</button></div>
        </div>
      </form>
    </div>
  </div>

  <div class=\"col-md-6\">
    <div class=\"card p-3\">
      <h6>Assign Resources</h6>
      <form method=\"post\" action=\"{{ url_for('assign_resource', project_id=project.id) }}\">
        <div class=\"row g-2\">
          <div class=\"col-md-5\">
            <select name=\"resource_id\" class=\"form-select\" required>
              <option value=\"\">Select resource</option>
              {% for r in resources %}
                <option value=\"{{ r.id }}\">{{ r.name }} — {{ r.color_team }} / {{ r.role }}</option>
              {% endfor %}
            </select>
          </div>
          <div class=\"col-md-3\"><input type=\"number\" name=\"allocation_pct\" class=\"form-control\" min=\"1\" max=\"100\" value=\"50\"></div>
          <div class=\"col-md-4\"><input name=\"role_on_project\" class=\"form-control\" placeholder=\"Role (e.g., Operator)\"></div>
          <div class=\"col-md-6\"><input type=\"date\" name=\"start_date\" class=\"form-control\"></div>
          <div class=\"col-md-6\"><input type=\"date\" name=\"end_date\" class=\"form-control\"></div>
          <div class=\"col-12\"><button class=\"btn btn-success\">Add to Project</button></div>
        </div>
      </form>

      <table class=\"table table-sm table-striped mt-3\">
        <thead><tr><th>Resource</th><th>Alloc %</th><th>Role</th><th>Start</th><th>End</th><th></th></tr></thead>
        <tbody>
        {% for a in project.assignments %}
          <tr>
            <td>{{ a.resource.name }}</td>
            <td>{{ a.allocation_pct }}</td>
            <td>{{ a.role_on_project or '-' }}</td>
            <td>{{ a.start_date or '-' }}</td>
            <td>{{ a.end_date or '-' }}</td>
            <td><a class=\"btn btn-sm btn-outline-danger\" href=\"{{ url_for('delete_assignment', assignment_id=a.id) }}\">Remove</a></td>
          </tr>
        {% else %}
          <tr><td colspan=\"6\" class=\"text-center\">No assignments yet.</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>
{% endblock %}
"""

RESOURCES = """
{% extends 'base.html' %}
{% block content %}
<div class=\"d-flex justify-content-between align-items-center mb-2\">
  <h4>Resources</h4>
  <div>
    <a class=\"btn btn-outline-light me-2\" href=\"{{ url_for('skills_matrix') }}\">Skills Matrix</a>
    <a class=\"btn btn-success\" href=\"{{ url_for('new_resource') }}\">New Resource</a>
  </div>
</div>
<div class=\"card p-3\">
  <form class=\"row g-2\" method=\"get\">
    <div class=\"col-md-4\"><input name=\"q\" value=\"{{ request.args.get('q','') }}\" class=\"form-control\" placeholder=\"Search by name, role, or skill\"></div>
    <div class=\"col-md-3\">
      <select name=\"team\" class=\"form-select\">
        <option value=\"\">Any Team</option>
        {% for t in ['Red','Purple','Blue','Mixed'] %}
          <option value=\"{{t}}\" {% if request.args.get('team')==t %}selected{% endif %}>{{t}}</option>
        {% endfor %}
      </select>
    </div>
    <div class=\"col-md-3\"><input name=\"skill\" value=\"{{ request.args.get('skill','') }}\" class=\"form-control\" placeholder=\"Skill tag (e.g., ADCS)\"></div>
    <div class=\"col-md-2\"><button class=\"btn btn-light w-100\">Filter</button></div>
  </form>
</div>

<div class=\"card p-3 mt-3\">
  <table class=\"table table-striped table-hover\">
    <thead><tr><th>Name</th><th>Team</th><th>Role</th><th>Skills</th><th>Clearance</th><th>Avail %</th><th>Assigned</th><th></th></tr></thead>
    <tbody>
      {% for r in resources %}
      <tr>
        <td>{{ r.name }}</td>
        <td>{{ r.color_team }}</td>
        <td>{{ r.role or '-' }}</td>
        <td>
          {% for s in (r.skills or '').split(',') if s.strip() %}
            <span class=\"chip\">{{ s.strip() }}</span>
          {% endfor %}
        </td>
        <td>{{ r.clearance or '-' }}</td>
        <td>{{ r.availability_pct }}</td>
        <td>{{ r.assignments|length }}</td>
        <td>
          <a class=\"btn btn-sm btn-light\" href=\"{{ url_for('resource_detail', resource_id=r.id) }}\">Open</a>
          <a class=\"btn btn-sm btn-outline-danger\" href=\"{{ url_for('delete_resource', resource_id=r.id) }}\" onclick=\"return confirm('Delete this resource?')\">Delete</a>
        </td>
      </tr>
      {% else %}
      <tr><td colspan=\"8\" class=\"text-center\">No resources found.</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
"""

RESOURCE_DETAIL = """
{% extends 'base.html' %}
{% block content %}
<div class=\"d-flex justify-content-between align-items-center mb-2\">
  <h4>{{ resource.name }}</h4>
  <div>
    <a class=\"btn btn-outline-light btn-sm\" href=\"{{ url_for('resources_index') }}\">Back</a>
  </div>
</div>
<div class=\"card p-3\">
  <form method=\"post\" action=\"{{ url_for('update_resource', resource_id=resource.id) }}\">
    <div class=\"row g-2\">
      <div class=\"col-md-6\"><input name=\"name\" class=\"form-control\" value=\"{{ resource.name }}\" required></div>
      <div class=\"col-md-6\"><input name=\"role\" class=\"form-control\" value=\"{{ resource.role or '' }}\" placeholder=\"Role\"></div>
      <div class=\"col-md-6\"><input name=\"skills\" class=\"form-control\" value=\"{{ resource.skills or '' }}\" placeholder=\"Skills (comma-separated)\"></div>
      <div class=\"col-md-3\"><input name=\"clearance\" class=\"form-control\" value=\"{{ resource.clearance or '' }}\" placeholder=\"Clearance\"></div>
      <div class=\"col-md-3\"><input type=\"number\" name=\"availability_pct\" class=\"form-control\" min=\"0\" max=\"100\" value=\"{{ resource.availability_pct }}\"></div>
      <div class=\"col-md-6\">
        <select name=\"color_team\" class=\"form-select\">
          {% for t in ['Red','Purple','Blue','Mixed'] %}
            <option value=\"{{t}}\" {% if resource.color_team==t %}selected{% endif %}>{{t}}</option>
          {% endfor %}
        </select>
      </div>
      <div class=\"col-12\"><button class=\"btn btn-primary\">Save</button></div>
    </div>
  </form>
</div>
{% endblock %}
"""

ASSIGNMENTS = """
{% extends 'base.html' %}
{% block content %}
<div class=\"d-flex justify-content-between align-items-center mb-2\">
  <h4>Assignments</h4>
</div>
<div class=\"card p-3\">
  <table class=\"table table-striped table-hover\">
    <thead><tr><th>Project</th><th>Resource</th><th>Role</th><th>Alloc %</th><th>Start</th><th>End</th><th></th></tr></thead>
    <tbody>
      {% for a in assignments %}
      <tr>
        <td><a href=\"{{ url_for('project_detail', project_id=a.project.id) }}\">{{ a.project.name }}</a></td>
        <td><a href=\"{{ url_for('resource_detail', resource_id=a.resource.id) }}\">{{ a.resource.name }}</a></td>
        <td>{{ a.role_on_project or '-' }}</td>
        <td>{{ a.allocation_pct }}</td>
        <td>{{ a.start_date or '-' }}</td>
        <td>{{ a.end_date or '-' }}</td>
        <td><a class=\"btn btn-sm btn-outline-danger\" href=\"{{ url_for('delete_assignment', assignment_id=a.id) }}\">Remove</a></td>
      </tr>
      {% else %}
      <tr><td colspan=\"7\" class=\"text-center\">No assignments yet.</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
"""

# --- Red/Purple Team Skills Catalog ---
SKILL_CATALOG = [
    # Red Team Core
    'Initial Access', 'Phishing', 'Social Engineering','C2', 'Evasion',
    'Active Directory', 'Malware Development',
    # Purple Team / Collaboration
    'Detection Engineering', 'Threat Simulation',
    'Purple TTPs', 'Report Writing'
]

SKILLS_MATRIX = """
{% extends 'base.html' %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-2">
  <h4>Red & Purple Team Skills Matrix</h4>
  <a class="btn btn-outline-light btn-sm" href="{{ url_for('resources_index') }}">Back to Resources</a>
</div>
<div class="card p-3">
  {% if catalog and resources %}
  <div class="table-responsive">
    <table class="table table-striped table-hover align-middle text-center">
      <thead>
        <tr>
          <th class="text-start">Resource</th>
          <th>Completion</th>
          {% for s in catalog %}
            <th>{{ s }}</th>
          {% endfor %}
          <th>Update</th>
        </tr>
      </thead>
      <tbody>
        {% for r in resources %}
        {% set rskills = (r.skills or '').lower().split(',') %}
        {% set rskills_clean = rskills | map('trim') | list %}
        {% set pct = percents[r.id] %}
        <tr>
          <td class="text-start" style="min-width:220px">
            <div class="fw-semibold">{{ r.name }}</div>
            <div class="text-muted small">{{ r.role or '—' }} • {{ r.color_team }}</div>
          </td>
          <td style="min-width:140px">
            <div class="progress" style="height:8px;background:#243252">
              <div class="progress-bar {% if pct>=100 %}bg-success{% elif pct>=60 %}bg-info{% else %}bg-warning{% endif %}" style="width: {{ pct }}%"></div>
            </div>
            <small class="text-muted">{{ pct }}%</small>
          </td>
          <form method="post" action="{{ url_for('update_skills', resource_id=r.id) }}">
            {% for s in catalog %}
              {% set has = s|lower in rskills_clean %}
              <td>
                {% if has %}
                  <span class="text-success">✅</span>
                {% else %}
                  <span class="text-danger" title="Missing">✗</span>
                {% endif %}
                <div class="form-check mt-1 d-flex justify-content-center">
                  <input class="form-check-input" type="checkbox" name="skills" value="{{ s }}" {% if has %}checked{% endif %}>
                </div>
              </td>
            {% endfor %}
            <td><button class="btn btn-sm btn-success mt-1">Save</button></td>
          </form>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% else %}
    <p>No skills catalog or resources found.</p>
  {% endif %}
</div>
{% endblock %}
"""


CALENDAR = """
{% extends 'base.html' %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-2">
  <h4>Project Calendar</h4>
  <form class="d-flex align-items-center" method="get" action="{{ url_for('calendar_view') }}">
    <label class="me-2 small text-muted">Month</label>
    <input class="form-control form-control-sm me-2" type="month" name="month" value="{{ active_month or '' }}" />
    <button class="btn btn-sm btn-light me-2">Go</button>
    {% if active_month %}
      <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('calendar_view') }}">Clear</a>
    {% endif %}
  </form>
</div>
<div class="card p-3">
  {% if projects %}
  <div class="d-flex justify-content-between align-items-center mb-2">
    <small class="text-muted">Range: {{ start_date }} → {{ end_date }}</small>
    <div class="small">
      <span class="me-3"><span style="display:inline-block;width:14px;height:8px;background:#ff476f;border-radius:2px;vertical-align:middle"></span> Red</span>
      <span class="me-3"><span style="display:inline-block;width:14px;height:8px;background:#b388ff;border-radius:2px;vertical-align:middle"></span> Purple</span>
      <span class="me-3"><span style="display:inline-block;width:14px;height:8px;background:#4dd2ff;border-radius:2px;vertical-align:middle"></span> Mixed</span>
      <span class="me-3"><span style="display:inline-block;width:14px;height:8px;background:#00e5a8;border-radius:2px;vertical-align:middle;border:1px solid #003b2e"></span> Alloc: Blue</span>
      <span class="me-3"><span style="display:inline-block;width:14px;height:8px;background:#ff9fb0;border-radius:2px;vertical-align:middle;border:1px solid #5b0012"></span> Alloc: Red</span>
      <span class="me-3"><span style="display:inline-block;width:14px;height:8px;background:#d7c2ff;border-radius:2px;vertical-align:middle;border:1px solid #2b1a4a"></span> Alloc: Purple</span>
      <span class="me-3"><span style="display:inline-block;width:14px;height:8px;background:#9ad7ff;border-radius:2px;vertical-align:middle;border:1px solid #002a3a"></span> Alloc: Mixed</span>
    </div>
  </div>
  <div class="border rounded p-3" style="background:#0f162d">
    <svg width="100%" height="{{ 60 + projects|length * 48 }}" viewBox="0 0 {{ width }} {{ 60 + projects|length * 48 }}" preserveAspectRatio="none">
      <!-- Axis -->
      <line x1="60" y1="20" x2="{{ width-20 }}" y2="20" stroke="#445" stroke-width="1" />
      {% for tick in ticks %}
        <line x1="{{ tick.x }}" y1="20" x2="{{ tick.x }}" y2="{{ 50 + projects|length * 48 }}" stroke="#233" stroke-width="1" />
        <text x="{{ tick.x+2 }}" y="18" font-size="10" fill="#9ab">{{ tick.label }}</text>
      {% endfor %}

      {% for p in projects %}
        {% set row = loop.index0 %}
        {% set y = 50 + row * 48 %}
        <!-- Label -->
        <text x="8" y="{{ y+12 }}" font-size="12" fill="#dbe2ff">{{ p.name }}</text>
        <!-- Main bar -->
        <g>
          <title>{{ p.name }} ({{ p.start_str }} → {{ p.end_str }}) — {{ p.engagement_type }}</title>
          <rect x="{{ p.x1 }}" y="{{ y }}" width="{{ [p.x2 - p.x1, 2]|max }}" height="16" rx="6" fill="{{ p.color }}" opacity="0.95" stroke="#0b0f1f" stroke-width="1" />
        </g>
        <!-- Allocation segments (colored by resource team) -->
        {% for s in p.segs %}
          <g>
            <title>{{ s.title }}</title>
            <rect x="{{ s.x1 }}" y="{{ y+3 }}" width="{{ [s.x2 - s.x1, 1]|max }}" height="10" rx="3" fill="{{ s.color }}" stroke="{{ s.stroke }}" stroke-width="1" opacity="0.95" />
            <text x="{{ s.x1+2 }}" y="{{ y+11 }}" font-size="9" fill="#000">{{ s.short }}</text>
          </g>
        {% endfor %}
      {% endfor %}
    </svg>
  </div>
  {% else %}
    <p class="mb-0">No dated projects yet. Add start/end dates to see them here.</p>
  {% endif %}
</div>
{% endblock %}
"""

# --- Routes ---
@app.route('/')
def index():
    recent_projects = Project.query.order_by(Project.start_date.desc().nullslast()).limit(5).all()
    return render_template_string(INDEX, recent_projects=recent_projects)

@app.route('/projects')
def projects():
    q = request.args.get('q', '').strip().lower()
    typ = request.args.get('type', '')
    status = request.args.get('status', '')

    query = Project.query
    if q:
        query = query.filter(db.or_(Project.name.ilike(f'%{q}%'), Project.client.ilike(f'%{q}%')))
    if typ:
        query = query.filter_by(engagement_type=typ)
    if status:
        query = query.filter_by(status=status)
    projs = query.order_by(Project.start_date.asc().nullsfirst()).all()
    return render_template_string(PROJECTS, projects=projs)

@app.route('/projects/new')
def new_project():
    return render_template_string(NEW_PROJECT)

NEW_PROJECT = """
{% extends 'base.html' %}
{% block content %}
<h4>New Project</h4>
<div class=\"card p-3\">
  <form method=\"post\" action=\"{{ url_for('create_project') }}\">
    <div class=\"row g-2\">
      <div class=\"col-md-6\"><label class=\"form-label\">Name</label><input required name=\"name\" class=\"form-control\" placeholder=\"Project name\"></div>
      <div class=\"col-md-6\"><label class=\"form-label\">Client</label><input name=\"client\" class=\"form-control\" placeholder=\"Client\"></div>
      <div class=\"col-md-3\"><label class=\"form-label\">Start</label><input type=\"date\" name=\"start_date\" class=\"form-control\"></div>
      <div class=\"col-md-3\"><label class=\"form-label\">End</label><input type=\"date\" name=\"end_date\" class=\"form-control\"></div>
      <div class=\"col-md-3\"><label class=\"form-label\">Engagement Type</label>
        <select name=\"engagement_type\" class=\"form-select\">
          <option value=\"Red\">Red</option>
          <option value=\"Purple\">Purple</option>
          <option value=\"Mixed\">Mixed</option>
        </select>
      </div>
      <div class=\"col-md-3\"><label class=\"form-label\">Status</label>
        <select name=\"status\" class=\"form-select\">
          {% for s in ['Planned','Active','On Hold','Completed'] %}
            <option value=\"{{s}}\">{{s}}</option>
          {% endfor %}
        </select>
      </div>
      <div class=\"col-12\"><label class=\"form-label\">Notes</label><textarea name=\"notes\" class=\"form-control\" rows=\"3\"></textarea></div>
      <div class=\"col-12\"><button class=\"btn btn-primary\">Create</button></div>
    </div>
  </form>
</div>
{% endblock %}
"""

@app.route('/projects', methods=['POST'])
def create_project():
    p = Project(
        name=request.form.get('name'),
        client=request.form.get('client'),
        start_date=parse_date(request.form.get('start_date')),
        end_date=parse_date(request.form.get('end_date')),
        engagement_type=request.form.get('engagement_type') or 'Mixed',
        status=request.form.get('status') or 'Planned',
        notes=request.form.get('notes'),
    )
    db.session.add(p)
    db.session.commit()
    flash('Project created.')
    return redirect(url_for('project_detail', project_id=p.id))

@app.route('/projects/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    resources = Resource.query.order_by(Resource.name).all()
    return render_template_string(PROJECT_DETAIL, project=project, resources=resources)

@app.route('/projects/<int:project_id>', methods=['POST'])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    project.name = request.form.get('name')
    project.client = request.form.get('client')
    project.start_date = parse_date(request.form.get('start_date'))
    project.end_date = parse_date(request.form.get('end_date'))
    project.engagement_type = request.form.get('engagement_type')
    project.status = request.form.get('status')
    project.notes = request.form.get('notes')
    db.session.commit()
    flash('Project updated.')
    return redirect(url_for('project_detail', project_id=project.id))

@app.route('/projects/<int:project_id>/assign', methods=['POST'])
def assign_resource(project_id):
    project = Project.query.get_or_404(project_id)
    resource_id = request.form.get('resource_id')
    if not resource_id:
        flash('Choose a resource.')
        return redirect(url_for('project_detail', project_id=project.id))

    a = Assignment(
        project_id=project.id,
        resource_id=int(resource_id),
        allocation_pct=int(request.form.get('allocation_pct') or 50),
        role_on_project=request.form.get('role_on_project'),
        start_date=parse_date(request.form.get('start_date')),
        end_date=parse_date(request.form.get('end_date')),
    )
    db.session.add(a)
    db.session.commit()
    flash('Resource assigned.')
    return redirect(url_for('project_detail', project_id=project.id))

@app.route('/projects/<int:project_id>/delete')
def delete_project(project_id):
    p = Project.query.get_or_404(project_id)
    db.session.delete(p)
    db.session.commit()
    flash('Project deleted.')
    return redirect(url_for('projects'))

# ---- Resources ----
@app.route('/resources', endpoint='resources_index')
def resources_index():
    q = request.args.get('q', '').strip().lower()
    team = request.args.get('team', '')
    skill = request.args.get('skill', '').strip().lower()

    query = Resource.query
    if q:
        query = query.filter(db.or_(Resource.name.ilike(f'%{q}%'), Resource.role.ilike(f'%{q}%'), Resource.skills.ilike(f'%{q}%')))
    if team:
        query = query.filter_by(color_team=team)
    if skill:
        query = query.filter(Resource.skills.ilike(f'%{skill}%'))

    res = query.order_by(Resource.name.asc()).all()
    return render_template_string(RESOURCES, resources=res)

@app.route('/resources/new')
def new_resource():
    return render_template_string(NEW_RESOURCE)

NEW_RESOURCE = """
{% extends 'base.html' %}
{% block content %}
<h4>New Resource</h4>
<div class=\"card p-3\">
  <form method=\"post\" action=\"{{ url_for('create_resource') }}\">
    <div class=\"row g-2\">
      <div class=\"col-md-6\"><label class=\"form-label\">Name</label><input required name=\"name\" class=\"form-control\" placeholder=\"Name\"></div>
      <div class=\"col-md-6\"><label class=\"form-label\">Role</label><input name=\"role\" class=\"form-control\" placeholder=\"Role (e.g., Red Op, Purple Lead)\"></div>
      <div class=\"col-md-6\"><label class=\"form-label\">Skills</label><input name=\"skills\" class=\"form-control\" placeholder=\"Skills (comma-separated)\"></div>
      <div class=\"col-md-3\"><label class=\"form-label\">Clearance</label><input name=\"clearance\" class=\"form-control\" placeholder=\"Clearance\"></div>
      <div class=\"col-md-3\"><label class=\"form-label\">Availability %</label><input type=\"number\" name=\"availability_pct\" class=\"form-control\" min=\"0\" max=\"100\" value=\"100\"></div>
      <div class=\"col-md-6\"><label class=\"form-label\">Team</label>
        <select name=\"color_team\" class=\"form-select\">
          <option value=\"Red\">Red</option>
          <option value=\"Purple\">Purple</option>
          <option value=\"Blue\">Blue</option>
          <option value=\"Mixed\">Mixed</option>
        </select>
      </div>
      <div class=\"col-12\"><button class=\"btn btn-success\">Create</button></div>
    </div>
  </form>
</div>
{% endblock %}
"""

@app.route('/resources', methods=['POST'])
def create_resource():
    r = Resource(
        name=request.form.get('name'),
        role=request.form.get('role'),
        skills=request.form.get('skills'),
        clearance=request.form.get('clearance'),
        availability_pct=int(request.form.get('availability_pct') or 100),
        color_team=request.form.get('color_team') or 'Mixed',
    )
    db.session.add(r)
    db.session.commit()
    flash('Resource created.')
    return redirect(url_for('resource_detail', resource_id=r.id))

@app.route('/resources/<int:resource_id>')
def resource_detail(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    return render_template_string(RESOURCE_DETAIL, resource=resource)

@app.route('/resources/<int:resource_id>/delete')
def delete_resource(resource_id):
    r = Resource.query.get_or_404(resource_id)
    db.session.delete(r)
    db.session.commit()
    flash('Resource deleted.')
    return redirect(url_for('resources_index'))

@app.route('/resources/<int:resource_id>', methods=['POST'])
def update_resource(resource_id):
    r = Resource.query.get_or_404(resource_id)
    r.name = request.form.get('name')
    r.role = request.form.get('role')
    r.skills = request.form.get('skills')
    r.clearance = request.form.get('clearance')
    r.availability_pct = int(request.form.get('availability_pct') or 100)
    r.color_team = request.form.get('color_team')
    db.session.commit()
    flash('Resource updated.')
    return redirect(url_for('resource_detail', resource_id=r.id))

# ---- Assignments ----
@app.route('/assignments')
def assignments():
    all_a = Assignment.query.order_by(Assignment.start_date.asc().nullsfirst()).all()
    return render_template_string(ASSIGNMENTS, assignments=all_a)

@app.route('/assignments/<int:assignment_id>/delete')
def delete_assignment(assignment_id):
    a = Assignment.query.get_or_404(assignment_id)
    db.session.delete(a)
    db.session.commit()
    flash('Assignment removed.')
    return redirect(url_for('assignments'))

# --- New Views ---

HEATMAP = """
{% extends 'base.html' %}
{% block content %}
<h4>Resource Utilization Heatmap</h4>
<div class="card p-3">
  {% if heatmap %}
  <div class="table-responsive">
    <table class="table table-striped table-hover text-center align-middle">
      <thead>
        <tr>
          <th>Resource</th>
          {% for m in months %}
            <th>{{ m }}</th>
          {% endfor %}
        </tr>
      </thead>
      <tbody>
        {% for r in heatmap %}
        <tr>
          <td class="text-start">{{ r.name }}</td>
          {% for val in r['values'] %}
            {% set color = 'rgba(0,255,0,' ~ (val/100) ~ ')' if val<=100 else 'rgba(255,0,0,0.8)' %}
            <td style="background:{{ color }};color:#000;">{{ val }}%</td>
          {% endfor %}
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% else %}
    <p class="mb-0">No utilization data yet.</p>
  {% endif %}
</div>
{% endblock %}
"""

@app.route('/heatmap')
def heatmap_view():
    resources = Resource.query.order_by(Resource.name.asc()).all()
    # gather months from assignments
    assigns = Assignment.query.filter(Assignment.start_date.isnot(None), Assignment.end_date.isnot(None)).all()
    if not assigns:
        return render_template_string(HEATMAP, heatmap=[], months=[])

    # find overall range
    min_d = min(a.start_date for a in assigns)
    max_d = max(a.end_date for a in assigns)
    months = []
    cur = min_d.replace(day=1)
    while cur <= max_d:
        months.append(cur.strftime('%b %Y'))
        if cur.month == 12:
            cur = cur.replace(year=cur.year+1, month=1)
        else:
            cur = cur.replace(month=cur.month+1)

    # build map resource->month->sum allocation
    from collections import defaultdict
    heatmap_data = []
    for r in resources:
        vals = []
        for m in months:
            total = 0
            for a in r.assignments:
                if not (a.start_date and a.end_date):
                    continue
                m_start = datetime.strptime(m, '%b %Y').date().replace(day=1)
                if m_start.month == 12:
                    m_end = m_start.replace(year=m_start.year+1, month=1, day=1)
                else:
                    m_end = m_start.replace(month=m_start.month+1, day=1)
                # overlap?
                if a.end_date < m_start or a.start_date >= m_end:
                    continue
                total += a.allocation_pct or 0
            vals.append(min(total, 150))  # cap at 150%
        heatmap_data.append({'name': r.name, 'values': vals})

    return render_template_string(HEATMAP, heatmap=heatmap_data, months=months)
@app.route('/resources/matrix')
def skills_matrix():
    resources = Resource.query.order_by(Resource.name.asc()).all()

    # Merge catalog with discovered custom skills (keep catalog first)
    discovered = []
    seen_lower = {s.lower() for s in SKILL_CATALOG}
    for r in resources:
        if r.skills:
            for s in [x.strip() for x in r.skills.split(',') if x.strip()]:
                if s.lower() not in seen_lower:
                    discovered.append(s)
                    seen_lower.add(s.lower())

    catalog = SKILL_CATALOG + sorted(discovered, key=lambda x: x.lower())

    # Compute completion % per resource based on catalog coverage
    percents = {}
    denom = max(len(catalog), 1)
    for r in resources:
        rskills_clean = [x.strip().lower() for x in (r.skills or '').split(',') if x.strip()]
        have = sum(1 for s in catalog if s.lower() in rskills_clean)
        percents[r.id] = int(round(100 * have / denom))

    return render_template_string(SKILLS_MATRIX, resources=resources, catalog=catalog, percents=percents)


@app.route('/calendar')
def calendar_view():
    # Optional month filter (YYYY-MM)
    month_q = request.args.get('month', '').strip()
    month_start = None
    month_end = None
    if month_q:
        try:
            month_start = datetime.strptime(month_q + '-01', '%Y-%m-%d').date()
            # next month
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year+1, month=1, day=1)
            else:
                month_end = month_start.replace(month=month_start.month+1, day=1)
        except ValueError:
            month_start = None
            month_end = None

    # Base list
    all_projects = Project.query.filter(Project.start_date.isnot(None), Project.end_date.isnot(None)).all()

    # If month filter, keep only projects that overlap window
    if month_start and month_end:
        projects = [p for p in all_projects if not (p.end_date < month_start or p.start_date >= month_end)]
        # Display window is month
        disp_start = month_start
        disp_end = (month_end - (month_end - month_start))  # placeholder to keep variable defined
        disp_end = month_end - (month_end - month_start)  # no-op line for clarity
        disp_end = month_end - (month_end - month_end.replace(day=1))  # keep mypy calm (ignored)
        disp_start = month_start
        disp_end = month_end
    else:
        projects = all_projects
        # Display window is min..max of projects
        if projects:
            disp_start = min(p.start_date for p in projects)
            disp_end = max(p.end_date for p in projects)
        else:
            disp_start = None
            disp_end = None

    if not projects:
        return render_template_string(CALENDAR, projects=[], start_date=None, end_date=None, width=1000, ticks=[], active_month=month_q)

    # Scale
    start = disp_start
    end = disp_end
    days = max((end - start).days, 1)
    width = 1100
    left_pad, right_pad = 60, 20
    scale = (width - left_pad - right_pad) / days

    def px_for(date):
        return left_pad + (date - start).days * scale

    # Project color map
    project_color = {'Red': '#ff476f', 'Purple': '#b388ff', 'Mixed': '#4dd2ff'}

    # Allocation color map (by resource team)
    seg_fill = {
        'Red':   {'fill': '#ff9fb0', 'stroke': '#5b0012'},
        'Purple':{'fill': '#d7c2ff', 'stroke': '#2b1a4a'},
        'Blue':  {'fill': '#00e5a8', 'stroke': '#003b2e'},
        'Mixed': {'fill': '#9ad7ff', 'stroke': '#002a3a'},
        None:    {'fill': '#ffffff', 'stroke': '#222'}
    }

    # Helper to clamp a date to [start, end)
    def clamp(d):
        if d < start: return start
        if d > end: return end
        return d

    pitems = []
    for p in projects:
        # Bar bounds (clamped to display window)
        bx1 = px_for(clamp(p.start_date))
        bx2 = px_for(clamp(p.end_date))
        segs = []
        for a in p.assignments:
            if not (a.start_date and a.end_date):
                continue
            # skip if assignment does not overlap window
            if a.end_date <= start or a.start_date >= end:
                continue
            s_date = clamp(a.start_date)
            e_date = clamp(a.end_date)
            sx1 = px_for(s_date)
            sx2 = px_for(e_date)
            who = (a.resource.name if a.resource else 'Resource')
            short = (who.split(' ')[0] or 'Res')
            if a.allocation_pct:
                short = f"{short} {a.allocation_pct}%"
            team = (a.resource.color_team if a.resource else None)
            styles = seg_fill.get(team, seg_fill[None])
            segs.append({
                'x1': sx1,
                'x2': sx2,
                'short': short,
                'title': f"{who} — {a.role_on_project or 'Role'} — {s_date} → {e_date}",
                'color': styles['fill'],
                'stroke': styles['stroke'],
            })

        pitems.append({
            'name': p.name,
            'client': p.client,
            'engagement_type': p.engagement_type,
            'x1': bx1,
            'x2': bx2,
            'start_str': max(p.start_date, start).strftime('%Y-%m-%d'),
            'end_str': min(p.end_date, end).strftime('%Y-%m-%d'),
            'color': project_color.get(p.engagement_type or 'Mixed', '#4dd2ff'),
            'segs': segs,
        })

    # Monthly ticks (within display window)
    ticks = []
    cur = start.replace(day=1)
    while cur <= end:
        ticks.append({'x': px_for(cur), 'label': cur.strftime('%b %Y')})
        if cur.month == 12:
            cur = cur.replace(year=cur.year+1, month=1)
        else:
            cur = cur.replace(month=cur.month+1)

    return render_template_string(CALENDAR, projects=pitems, start_date=start, end_date=end, width=width, ticks=ticks, active_month=month_q)

@app.route('/resources/<int:resource_id>/skills/update', methods=['POST'])
def update_skills(resource_id):
    r = Resource.query.get_or_404(resource_id)
    selected = request.form.getlist('skills')
    cleaned = sorted({s.strip() for s in selected if s.strip()}, key=lambda x: x.lower())
    r.skills = ', '.join(cleaned)
    db.session.commit()
    flash(f"Updated Red/Purple skills for {r.name}.")
    return redirect(url_for('skills_matrix'))

# --- App Factory Helpers ---
@app.context_processor
def inject_base():
    return {'BASE': BASE}

# Register base template in jinja loader
app.jinja_loader = DictLoader({
    'base.html': BASE,
})

def init_db():
    db.create_all()

# For local run
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
