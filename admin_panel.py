"""Web-based admin panel for managing the forwarder configuration."""
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import os
import signal
from src.config_manager import ConfigManager


app = Flask(__name__)
config_manager = ConfigManager()


# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Forwarder Admin Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .content { padding: 30px; }
        .section {
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 2px solid #f0f0f0;
        }
        .section:last-child { border-bottom: none; }
        .section h2 {
            color: #667eea;
            font-size: 22px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
        }
        .section h2:before {
            content: '';
            width: 4px;
            height: 24px;
            background: #667eea;
            margin-right: 10px;
            border-radius: 2px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #333;
        }
        input[type="text"], input[type="number"], select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .btn-danger {
            background: #ef4444;
            color: white;
        }
        .btn-danger:hover {
            background: #dc2626;
        }
        .btn-success {
            background: #10b981;
            color: white;
        }
        .btn-success:hover {
            background: #059669;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #667eea;
        }
        tr:hover { background: #f8f9fa; }
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .checkbox-group input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        .alert {
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        .alert-success {
            background: #d1fae5;
            color: #065f46;
            border-left: 4px solid #10b981;
        }
        .alert-info {
            background: #dbeafe;
            color: #1e40af;
            border-left: 4px solid #3b82f6;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border: 2px solid #e0e0e0;
        }
        .card h3 {
            color: #667eea;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Telegram Forwarder Admin Panel</h1>
            <p>Manage your multi-channel forwarding system</p>
        </div>
        
        <div class="content">
            {% if message %}
            <div class="alert alert-success">{{ message }}</div>
            {% endif %}
            
            <!-- Channel Pairs Section -->
            <div class="section">
                <h2>📡 Channel Pairs</h2>
                <form method="POST" action="/add_channel_pair">
                    <div class="grid">
                        <div class="form-group">
                            <label>Source Channel ID</label>
                            <input type="text" name="source" placeholder="-1001234567890" required>
                        </div>
                        <div class="form-group">
                            <label>Target Channel ID</label>
                            <input type="text" name="target" placeholder="-1009876543210" required>
                        </div>
                        <div class="form-group">
                            <label>Backfill Count</label>
                            <input type="number" name="backfill_count" value="10" min="0" max="100">
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">Add Channel Pair</button>
                </form>
                
                {% if channel_pairs %}
                <table>
                    <thead>
                        <tr>
                            <th>Source</th>
                            <th>Target</th>
                            <th>Backfill</th>
                            <th>Enabled</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for i, pair in channel_pairs %}
                        <tr>
                            <td>{{ pair.source }}</td>
                            <td>{{ pair.target }}</td>
                            <td>{{ pair.backfill_count }}</td>
                            <td>{{ '✅' if pair.enabled else '❌' }}</td>
                            <td>
                                <form method="POST" action="/toggle_channel_pair/{{ i }}" style="display:inline;">
                                    <button type="submit" class="btn btn-success">Toggle</button>
                                </form>
                                <form method="POST" action="/remove_channel_pair/{{ i }}" style="display:inline;">
                                    <button type="submit" class="btn btn-danger" onclick="return confirm('Are you sure?')">Remove</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="alert alert-info">No channel pairs configured yet.</div>
                {% endif %}
            </div>
            
            <!-- Replacement Rules Section -->
            <div class="section">
                <h2>🔄 Text Replacement Rules</h2>
                <form method="POST" action="/add_replacement_rule">
                    <div class="grid">
                        <div class="form-group">
                            <label>Find Text</label>
                            <input type="text" name="find" placeholder="Elite" required>
                        </div>
                        <div class="form-group">
                            <label>Replace With</label>
                            <input type="text" name="replace" placeholder="Excellent" required>
                        </div>
                        <div class="form-group">
                            <label class="checkbox-group">
                                <input type="checkbox" name="case_sensitive" value="1">
                                <span>Case Sensitive</span>
                            </label>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">Add Rule</button>
                </form>
                
                {% if replacement_rules %}
                <table>
                    <thead>
                        <tr>
                            <th>Find</th>
                            <th>Replace</th>
                            <th>Case Sensitive</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for i, rule in replacement_rules %}
                        <tr>
                            <td>{{ rule.find }}</td>
                            <td>{{ rule.replace }}</td>
                            <td>{{ '✅' if rule.case_sensitive else '❌' }}</td>
                            <td>
                                <form method="POST" action="/remove_replacement_rule/{{ i }}" style="display:inline;">
                                    <button type="submit" class="btn btn-danger" onclick="return confirm('Are you sure?')">Remove</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="alert alert-info">No replacement rules configured.</div>
                {% endif %}
            </div>
            
            <!-- Filters Section -->
            <div class="section">
                <h2>🔍 Message Filters</h2>
                <form method="POST" action="/update_filters">
                    <div class="form-group">
                        <label class="checkbox-group">
                            <input type="checkbox" name="enabled" value="1" {{ 'checked' if filters.enabled else '' }}>
                            <span>Enable Filtering</span>
                        </label>
                    </div>
                    <div class="form-group">
                        <label>Filter Mode</label>
                        <select name="mode">
                            <option value="whitelist" {{ 'selected' if filters.mode == 'whitelist' else '' }}>Whitelist (forward only if contains keywords)</option>
                            <option value="blacklist" {{ 'selected' if filters.mode == 'blacklist' else '' }}>Blacklist (forward only if doesn't contain keywords)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Keywords (one per line)</label>
                        <textarea name="keywords" rows="5" style="width:100%; padding:12px; border:2px solid #e0e0e0; border-radius:6px;">{{ filters.keywords|join('\n') }}</textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Update Filters</button>
                </form>
            </div>
            
            <!-- API Credentials Section -->
            <div class="section">
                <h2>🔑 API Credentials</h2>
                <div class="alert alert-info">
                    <strong>Current Configuration:</strong><br>
                    API ID: {{ api_creds.api_id }}<br>
                    Session: {{ api_creds.session_name }}<br>
                    <em>To change credentials, edit config.json directly</em>
                </div>
            </div>
            
            <!-- Settings Section -->
            <div class="section">
                <h2>⚙️ Advanced Settings</h2>
                <form method="POST" action="/update_settings">
                    <div class="grid">
                        <div class="form-group">
                            <label>Retry Attempts</label>
                            <input type="number" name="retry_attempts" value="{{ settings.retry_attempts }}" min="1" max="10">
                        </div>
                        <div class="form-group">
                            <label>Retry Delay (seconds)</label>
                            <input type="number" name="retry_delay" value="{{ settings.retry_delay }}" min="1" max="60">
                        </div>
                        <div class="form-group">
                            <label>Log Level</label>
                            <select name="log_level">
                                <option value="DEBUG" {{ 'selected' if settings.log_level == 'DEBUG' else '' }}>DEBUG</option>
                                <option value="INFO" {{ 'selected' if settings.log_level == 'INFO' else '' }}>INFO</option>
                                <option value="WARNING" {{ 'selected' if settings.log_level == 'WARNING' else '' }}>WARNING</option>
                                <option value="ERROR" {{ 'selected' if settings.log_level == 'ERROR' else '' }}>ERROR</option>
                            </select>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">Update Settings</button>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
"""


@app.route('/')
def index():
    """Main admin panel page."""
    config_manager.load()  # Reload config
    
    return render_template_string(
        HTML_TEMPLATE,
        channel_pairs=enumerate(config_manager.get_all_channel_pairs()),
        replacement_rules=enumerate(config_manager.get_replacement_rules()),
        filters=config_manager.get_filters(),
        api_creds=config_manager.get_api_credentials(),
        settings=config_manager.get_settings(),
        message=request.args.get('message')
    )


@app.route('/add_channel_pair', methods=['POST'])
def add_channel_pair():
    """Add a new channel pair."""
    try:
        source = int(request.form['source'])
        target = int(request.form['target'])
        backfill_count = int(request.form.get('backfill_count', 10))
        
        config_manager.add_channel_pair(source, target, backfill_count)
        return redirect(url_for('index', message='Channel pair added successfully'))
    except Exception as e:
        return redirect(url_for('index', message=f'Error: {str(e)}'))


@app.route('/remove_channel_pair/<int:index>', methods=['POST'])
def remove_channel_pair(index):
    """Remove a channel pair."""
    config_manager.remove_channel_pair(index)
    return redirect(url_for('index', message='Channel pair removed'))


@app.route('/toggle_channel_pair/<int:index>', methods=['POST'])
def toggle_channel_pair(index):
    """Toggle a channel pair's enabled status."""
    pairs = config_manager.get_all_channel_pairs()
    if 0 <= index < len(pairs):
        current_status = pairs[index].get('enabled', True)
        config_manager.update_channel_pair(index, enabled=not current_status)
    return redirect(url_for('index', message='Channel pair toggled'))


@app.route('/add_replacement_rule', methods=['POST'])
def add_replacement_rule():
    """Add a new replacement rule."""
    find = request.form['find']
    replace = request.form['replace']
    case_sensitive = bool(request.form.get('case_sensitive'))
    
    config_manager.add_replacement_rule(find, replace, case_sensitive)
    return redirect(url_for('index', message='Replacement rule added'))


@app.route('/remove_replacement_rule/<int:index>', methods=['POST'])
def remove_replacement_rule(index):
    """Remove a replacement rule."""
    config_manager.remove_replacement_rule(index)
    return redirect(url_for('index', message='Replacement rule removed'))


@app.route('/update_filters', methods=['POST'])
def update_filters():
    """Update filter settings."""
    enabled = bool(request.form.get('enabled'))
    mode = request.form['mode']
    keywords_text = request.form.get('keywords', '')
    keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
    
    config_manager.update_filters(enabled=enabled, mode=mode, keywords=keywords)
    return redirect(url_for('index', message='Filters updated'))


@app.route('/update_settings', methods=['POST'])
def update_settings():
    """Update general settings."""
    retry_attempts = int(request.form['retry_attempts'])
    retry_delay = int(request.form['retry_delay'])
    log_level = request.form['log_level']
    
    config_manager.update_settings(
        retry_attempts=retry_attempts,
        retry_delay=retry_delay,
        log_level=log_level
    )
    return redirect(url_for('index', message='Settings updated'))


def run_admin_panel(host='127.0.0.1', port=5000):
    """Run the admin panel server."""
    print(f"\n{'='*60}")
    print(f"🚀 Telegram Forwarder Admin Panel")
    print(f"{'='*60}")
    print(f"\n📡 Server running at: http://{host}:{port}")
    print(f"🔧 Press Ctrl+C to stop\n")
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    run_admin_panel()

