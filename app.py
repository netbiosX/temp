from flask import Flask, request, render_template, send_file, redirect, url_for, flash
import yaml
import io
from sigma.parser.collection import SigmaCollection
from sigma.backends.microsoft_defender import MicrosoftDefenderBackend
from sigma.mapper.fieldmapping import FieldMapping, SigmaFieldMappingConfig

app = Flask(__name__)
app.secret_key = "your_secret_key"  # for flash messages

# Example: Default field mapping for Windows Defender (can be customized)
DEFAULT_FIELD_MAP = {
    'Image': 'FileName',
    'TargetFilename': 'FolderPath',
    'ParentImage': 'ProcessCommandLine',
    # Add more as needed for your org/environment
}

@app.route('/', methods=['GET', 'POST'])
def index():
    kql = ""
    sigma_content = ""
    mapping = DEFAULT_FIELD_MAP.copy()
    error = None

    if request.method == 'POST':
        sigma_content = request.form.get('sigma', '')
        try:
            # YAML Validation
            yaml_data = yaml.safe_load(sigma_content)
            # Simple structural validation
            if not isinstance(yaml_data, dict) or 'detection' not in yaml_data:
                error = "Not a valid Sigma rule (missing 'detection' key)."
                raise ValueError
        except Exception as e:
            error = f"Invalid YAML or Sigma structure: {e}"
            flash(error, 'danger')
            return render_template('index.html', sigma=sigma_content, kql=kql, mapping=mapping, error=error)

        # Optional: Let user tweak mapping
        for s_field in DEFAULT_FIELD_MAP:
            mapping[s_field] = request.form.get(f'map_{s_field}', DEFAULT_FIELD_MAP[s_field])

        # Build custom field mapping config
        field_mapping = FieldMapping(mapping)
        backend = MicrosoftDefenderBackend(field_mapping=field_mapping)

        try:
            rules = SigmaCollection.from_yaml(sigma_content)
            kql_parts = []
            for rule in rules:
                kql_query = backend.convert(rule)
                kql_parts.append(kql_query)
            kql = "\n\n---\n\n".join(kql_parts)
        except Exception as e:
            error = f"Sigma conversion error: {e}"
            flash(error, 'danger')
            return render_template('index.html', sigma=sigma_content, kql=kql, mapping=mapping, error=error)

        return render_template('index.html', sigma=sigma_content, kql=kql, mapping=mapping, error=error)

    return render_template('index.html', sigma=sigma_content, kql=kql, mapping=mapping, error=error)

@app.route('/download_kql', methods=['POST'])
def download_kql():
    kql = request.form.get('kql', '')
    filename = "mde_query.kql"
    return send_file(
        io.BytesIO(kql.encode('utf-8')),
        as_attachment=True,
        download_name=filename,
        mimetype='text/plain'
    )

if __name__ == '__main__':
    app.run(debug=True)