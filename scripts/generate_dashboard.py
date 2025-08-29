#!/usr/bin/env python3
"""
Generate HTML dashboard from monitoring data
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict


def load_historical_data():
    """Load historical monitoring data"""
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    historical_file = os.path.join(cache_dir, 'monitoring_history.json')
    
    if not os.path.exists(historical_file):
        return []
    
    try:
        with open(historical_file, 'r') as f:
            data = json.load(f)
            print(f"📊 Loaded {len(data)} historical entries from cache")
            return data
    except Exception as e:
        print(f"Error loading historical data: {e}")
        return []


def load_current_status():
    """Load current status data from cache"""
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    status_file = os.path.join(cache_dir, 'current_status.json')
    
    if not os.path.exists(status_file):
        return None
    
    try:
        with open(status_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading current status: {e}")
        return None


def generate_dashboard_data(historical_data):
    """Process historical data for dashboard visualization"""
    if not historical_data:
        return {}
    
    # Process data by website
    websites = {}
    timeline_data = []
    uptime_stats = defaultdict(lambda: {'total': 0, 'successful': 0})
    response_time_data = defaultdict(list)

    # Sort by timestamp to ensure chronological order
    historical_data.sort(key=lambda x: x['timestamp'])
    
    for entry in historical_data:
        timestamp = entry['timestamp']
        
        # Overall timeline data
        timeline_data.append({
            'timestamp': timestamp,
            'total_sites': entry['summary']['total_sites'],
            'successful_sites': entry['summary']['successful_sites'],
            'failed_sites': entry['summary']['failed_sites'],
            'average_response_time': entry['summary']['average_response_time']
        })
        
        # Per-website data
        for result in entry['results']:
            site_name = result['name']
            
            if site_name not in websites:
                websites[site_name] = {
                    'name': site_name,
                    'url': result['url'],
                    'checks': [],
                    'uptime_percentage': 0,
                    'current_status': 'unknown',
                    'last_response_time': None
                }
            
            # Add check data
            check_data = {
                'timestamp': timestamp,
                'success': result['success'],
                'response_time': result.get('response_time'),
                'status_code': result.get('status_code'),
                'error': result.get('error')
            }

            websites[site_name]['checks'].append(check_data)

            # Update current status (last entry will be the current status)
            websites[site_name]['current_status'] = 'up' if result['success'] else 'down'
            websites[site_name]['last_response_time'] = result.get('response_time')
            
            # Uptime statistics
            uptime_stats[site_name]['total'] += 1
            if result['success']:
                uptime_stats[site_name]['successful'] += 1
            
            # Response time data
            if result['success'] and result.get('response_time'):
                response_time_data[site_name].append({
                    'timestamp': timestamp,
                    'response_time': result['response_time']
                })
    
    # Calculate uptime percentages
    for site_name, stats in uptime_stats.items():
        if stats['total'] > 0:
            uptime_percentage = (stats['successful'] / stats['total']) * 100
            websites[site_name]['uptime_percentage'] = round(uptime_percentage, 2)
    
    return {
        'websites': websites,
        'timeline': timeline_data,
        'uptime_stats': dict(uptime_stats),
        'response_times': dict(response_time_data),
        'last_updated': datetime.now().isoformat()
    }


def generate_html_dashboard(dashboard_data, current_status=None):
    """Generate HTML dashboard with Chart.js visualizations"""

    html_template_start = """
<!DOCTYPE html>
<html lang="en">
    """

    html_template_head = """
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🐤 Canary Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }
        .alert {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
            font-weight: bold;
        }
        .alert-success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-danger { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #007bff;
        }
        .stat-card.success { border-left-color: #28a745; }
        .stat-card.warning { border-left-color: #ffc107; }
        .stat-card.danger { border-left-color: #dc3545; }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-label {
            color: #666;
            font-size: 0.9em;
        }
        .chart-container {
            margin: 30px 0;
            height: 400px;
        }
        .website-list {
            margin-top: 30px;
        }
        .website-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            margin: 10px 0;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 4px solid #28a745;
        }
        .website-item.down {
            border-left-color: #dc3545;
        }
        .website-info {
            flex-grow: 1;
        }
        .website-metrics {
            display: flex;
            gap: 15px;
            align-items: center;
        }
        .uptime-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .uptime-excellent { background: #d4edda; color: #155724; }
        .uptime-good { background: #fff3cd; color: #856404; }
        .uptime-poor { background: #f8d7da; color: #721c24; }
        .response-time {
            font-size: 0.9em;
            color: #666;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 0.9em;
        }
        .filter-controls {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
        }
        
        .filter-controls h3 {
            margin: 0 0 15px 0;
            color: #333;
        }
        
        .filter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .filter-section {
            background: white;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #e9ecef;
        }
        
        .filter-section h4 {
            margin: 0 0 10px 0;
            color: #495057;
            font-size: 0.9em;
            text-transform: uppercase;
            font-weight: 600;
        }
        
        .filter-section label {
            display: block;
            margin-bottom: 8px;
            font-size: 0.9em;
            color: #666;
        }
        
        .filter-input {
            width: 100%;
            padding: 6px 10px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 0.9em;
            margin-top: 3px;
        }
        
        .filter-input:focus {
            outline: none;
            border-color: #007bff;
            box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
        }
        
        .filter-button {
            padding: 6px 12px;
            border: 1px solid #6c757d;
            background: white;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8em;
            margin-top: 8px;
            margin-right: 5px;
        }
        
        .filter-button:hover {
            background: #e9ecef;
        }
        
        .filter-button.primary {
            background: #007bff;
            color: white;
            border-color: #007bff;
        }
        
        .filter-button.primary:hover {
            background: #0056b3;
        }
        
        .filter-actions {
            text-align: center;
            padding-top: 15px;
            border-top: 1px solid #dee2e6;
        }
    </style>
</head>
    """
    
    html_template_body = """
<body>
    <div class="container">
        <div class="header">
            <h1>🐤 Canary Dashboard</h1>
            <p>Last updated: {last_updated}</p>
            {alert_section}
        </div>
        
        <div class="stats-grid">
            <div class="stat-card success">
                <div class="stat-number">{total_websites}</div>
                <div class="stat-label">Total Websites</div>
            </div>
            <div class="stat-card {overall_status_class}">
                <div class="stat-number">{overall_uptime}%</div>
                <div class="stat-label">Overall Uptime</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{avg_response_time}ms</div>
                <div class="stat-label">Avg Response Time</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_checks}</div>
                <div class="stat-label">Total Checks</div>
            </div>
        </div>

        <div class="filter-controls">
            <h3>📊 Chart Filters</h3>
            
            <form onsubmit="applyFilters()" action="javascript:void(0);">
            <div class="filter-grid">
                <div class="filter-section">
                    <h4>Time Range</h4>
                    <label>
                        Start Date:
                        <input type="datetime-local" id="startDate" class="filter-input">
                    </label>
                    <label>
                        End Date:
                        <input type="datetime-local" id="endDate" class="filter-input">
                    </label>
                    <button onclick="resetTimeRange()" class="filter-button" type="button">Reset</button>
                </div>
                
                <div class="filter-section">
                    <h4>Response Time Range (seconds)</h4>
                    <label>
                        Min Response Time:
                        <input type="number" id="minResponseTime" step="0.1" min="0" class="filter-input" placeholder="0.0">
                    </label>
                    <label>
                        Max Response Time:
                        <input type="number" id="maxResponseTime" step="0.1" min="0" class="filter-input" placeholder="Auto">
                    </label>
                    <button onclick="resetResponseTimeRange()" class="filter-button" type="button">Reset</button>
                </div>
                
                <div class="filter-section">
                    <h4>Failed Site Count Range</h4>
                    <label>
                        Min Y Value:
                        <input type="number" id="minFailedSiteCount" min="0" class="filter-input" placeholder="0">
                    </label>
                    <label>
                        Max Y Value:
                        <input type="number" id="maxFailedSiteCount" min="0" class="filter-input" placeholder="Auto">
                    </label>
                    <button onclick="resetSiteCountRange()" class="filter-button" type="button">Reset</button>
                </div>
            </div>
            
            <div class="filter-actions">
                <button onclick="applyFilters()" class="filter-button primary" type="submit">Apply Filters</button>
                <button onclick="resetAllFilters()" class="filter-button" type="button">Reset All</button>
            </div>
            </form>
        </div>
        
        <div class="chart-container">
            <canvas id="uptimeChart"></canvas>
        </div>
        
        <div class="chart-container">
            <canvas id="responseTimeChart"></canvas>
        </div>
        
        <div class="website-list">
            <h2>Website Status</h2>
            {website_list_html}
        </div>
        
        <div class="footer">
            Generated by <a href="https://github.com/3d12/canary">Canary</a><br>
            Total historical entries: {total_entries}
        </div>
    </div>
    
    <script>
        const dashboardData = {dashboard_data_json};

        // Helper function to interpret timestamp as UTC
        function timestampToUTC(timestamp) {{
            const date = new Date(timestamp);
            const dateUTC = Date.UTC(date.getFullYear(), date.getMonth(), date.getDate(), date.getHours(), date.getMinutes(), date.getSeconds())
            return new Date(dateUTC);
        }}
        
        // Helper function to convert timestamp to milliseconds
        function timestampToMs(timestamp) {{
            const date = new Date(timestamp);
            return new Date(date).getTime();
        }}
        
        // Helper function to format milliseconds back to readable time
        function formatTime(ms) {{
            const date = new Date(ms);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {{hour: '2-digit', minute:'2-digit'}});
        }}

        // Global variables for chart instances
        let uptimeChart, responseTimeChart;
        
        // Initialize filter controls with current data range
        function initializeFilters() {{
            if (!dashboardData.timeline || dashboardData.timeline.length === 0) return;
            
            const timestamps = dashboardData.timeline.map(d => new Date(d.timestamp));
            //const minDate = timestampToUTC(new Date(Math.min(...timestamps)));
            const maxDate = timestampToUTC(new Date(Math.max(...timestamps)));
            let minDate = new Date(maxDate);
            minDate.setHours(maxDate.getHours()-24);
            
            // Set default date range
            document.getElementById('startDate').value = formatDateForInput(minDate);
            document.getElementById('endDate').value = formatDateForInput(maxDate);
            
            // Set default response time range
            const allResponseTimes = [];
            Object.values(dashboardData.response_times).forEach(siteData => {{
                siteData.forEach(d => allResponseTimes.push(d.response_time));
            }});
            
            if (allResponseTimes.length > 0) {{
                document.getElementById('maxResponseTime').placeholder = Math.max(...allResponseTimes).toFixed(2);
            }}

            // Set default failed site count range
            const allFailedSiteCounts = dashboardData.timeline.map(d => d.failed_sites);
            document.getElementById('maxFailedSiteCount').placeholder = Math.max(...allFailedSiteCounts);
        }}
        
        function formatDateForInput(date) {{
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            return `${{year}}-${{month}}-${{day}}T${{hours}}:${{minutes}}`;
        }}
        
        function getFilteredData() {{
            console.log("getFilteredData() called");
            const startDate = document.getElementById('startDate').value ? new Date(document.getElementById('startDate').value) : null;
            const endDate = document.getElementById('endDate').value ? new Date(document.getElementById('endDate').value) : null;
            const minResponseTime = parseFloat(document.getElementById('minResponseTime').value);
            const maxResponseTime = parseFloat(document.getElementById('maxResponseTime').value);
            const minFailedSiteCount = parseInt(document.getElementById('minFailedSiteCount').value);
            const maxFailedSiteCount = parseInt(document.getElementById('maxFailedSiteCount').value);

            // Filter timeline data
            const filteredTimeline = dashboardData.timeline.filter(d => {{
                const timestamp = new Date(d.timestamp);
                const timeInRange = (!startDate || timestampToUTC(timestamp) >= startDate) && (!endDate || timestampToUTC(timestamp) <= endDate);
                const failedSitesInRange = (!minFailedSiteCount || d.failed_sites >= minFailedSiteCount) && (!maxFailedSiteCount || d.failed_sites <= maxFailedSiteCount);
                return timeInRange && failedSitesInRange;
            }});
            
            // Filter response time data
            const filteredResponseTimes = {{}};
            Object.keys(dashboardData.response_times).forEach(siteName => {{
                filteredResponseTimes[siteName] = dashboardData.response_times[siteName].filter(d => {{
                    const timestamp = new Date(d.timestamp);
                    const timeInRange = (!startDate || timestampToUTC(timestamp) >= startDate) && (!endDate || timestampToUTC(timestamp) <= endDate);
                    const responseTimeInRange = (!minResponseTime || d.response_time >= minResponseTime) && (!maxResponseTime || d.response_time <= maxResponseTime);
                    return timeInRange && responseTimeInRange;
                }});
            }});

            return {{
                timeline: filteredTimeline,
                response_times: filteredResponseTimes
            }};
        }}
        
        function resetTimeRange() {{
            console.log("resetTimeRange() called");
            const timestamps = dashboardData.timeline.map(d => new Date(d.timestamp));
            const minDate = timestampToUTC(new Date(Math.min(...timestamps)));
            const maxDate = timestampToUTC(new Date(Math.max(...timestamps)));
            document.getElementById('startDate').value = formatDateForInput(minDate);
            document.getElementById('endDate').value = formatDateForInput(maxDate);
        }}
        
        function resetResponseTimeRange() {{
            document.getElementById('minResponseTime').value = '';
            document.getElementById('maxResponseTime').value = '';
        }}
        
        function resetSiteCountRange() {{
            document.getElementById('minFailedSiteCount').value = '';
            document.getElementById('maxFailedSiteCount').value = '';
        }}
        
        function resetAllFilters() {{
            console.log("resetAllFilters() called");
            resetTimeRange();
            resetResponseTimeRange();
            resetSiteCountRange();
            applyFilters();
        }}
        
        function applyFilters() {{
            console.log("applyFilters() called");
            const filteredData = getFilteredData();
            updateCharts(filteredData);
        }}
        
        function updateCharts(filteredData) {{
            // Update uptime chart
            uptimeChart.data.datasets[0].data = filteredData.timeline.map(d => ({{
                x: timestampToMs(timestampToUTC(d.timestamp)),
                y: d.successful_sites
            }}));
            uptimeChart.data.datasets[1].data = filteredData.timeline.map(d => ({{
                x: timestampToMs(timestampToUTC(d.timestamp)),
                y: d.failed_sites
            }}));
            uptimeChart.update();
            
            // Update response time chart
            const newResponseTimeDatasets = Object.keys(filteredData.response_times).map((siteName, index) => {{
                const colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1', '#20c997', '#fd7e14', '#e83e8c'];
                return {{
                    label: siteName,
                    data: filteredData.response_times[siteName].map(d => ({{
                        x: timestampToMs(timestampToUTC(d.timestamp)),
                        y: d.response_time
                    }})),
                    borderColor: colors[index % colors.length],
                    backgroundColor: colors[index % colors.length] + '20',
                    tension: 0.4
                }};
            }});
            
            responseTimeChart.data.datasets = newResponseTimeDatasets;
            responseTimeChart.update();
        }}
        
        // Uptime Chart with linear time scale
        const uptimeCtx = document.getElementById('uptimeChart').getContext('2d');
        uptimeChart = new Chart(uptimeCtx, {{
            type: 'line',
            data: {{
                datasets: [{{
                    label: 'Successful Sites',
                    data: dashboardData.timeline.map(d => ({{
                        x: timestampToMs(timestampToUTC(d.timestamp)),
                        y: d.successful_sites
                    }})),
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4,
                    fill: true
                }}, {{
                    label: 'Failed Sites',
                    data: dashboardData.timeline.map(d => ({{
                        x: timestampToMs(timestampToUTC(d.timestamp)),
                        y: d.failed_sites
                    }})),
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    tension: 0.4,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Website Status Over Time',
                        font: {{
                            size: 16
                        }}
                    }},
                    legend: {{
                        position: 'top'
                    }},
                    tooltip: {{
                        callbacks: {{
                            title: function(context) {{
                                return new Date(context[0].parsed.x).toLocaleString();
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        type: 'linear',
                        title: {{
                            display: true,
                            text: 'Time'
                        }},
                        ticks: {{
                            maxTicksLimit: 8,
                            callback: function(value) {{
                                return formatTime(value);
                            }}
                        }}
                    }},
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 1
                        }},
                        title: {{
                            display: true,
                            text: 'Number of Sites'
                        }}
                    }}
                }},
                interaction: {{
                    intersect: false,
                    mode: 'index'
                }}
            }}
        }});
        
        // Response Time Chart with linear time scale
        const responseTimeCtx = document.getElementById('responseTimeChart').getContext('2d');
        const responseTimeDatasets = Object.keys(dashboardData.response_times).map((siteName, index) => {{
            const colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1', '#20c997', '#fd7e14', '#e83e8c'];
            return {{
                label: siteName,
                data: dashboardData.response_times[siteName].map(d => ({{
                    x: timestampToMs(timestampToUTC(d.timestamp)),
                    y: d.response_time
                }})),
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '20',
                tension: 0.4
            }};
        }});
        
        responseTimeChart = new Chart(responseTimeCtx, {{
            type: 'line',
            data: {{
                datasets: responseTimeDatasets
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Response Times Over Time',
                        font: {{
                            size: 16
                        }}
                    }},
                    legend: {{
                        position: 'top'
                    }},
                    tooltip: {{
                        callbacks: {{
                            title: function(context) {{
                                return new Date(context[0].parsed.x).toLocaleString();
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        type: 'linear',
                        title: {{
                            display: true,
                            text: 'Time'
                        }},
                        ticks: {{
                            maxTicksLimit: 8,
                            callback: function(value) {{
                                return formatTime(value);
                            }}
                        }}
                    }},
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Response Time (seconds)'
                        }}
                    }}
                }},
                interaction: {{
                    intersect: false,
                    mode: 'index'
                }}
            }}
        }});

        // Initialize and apply filters
        initializeFilters();
        applyFilters();
    </script>
</body>
    """

    html_template_end = """
</html>
    """
    
    # Load current status to check for failures
    current_failed_sites = 0
    alert_section = ""
    if current_status:
        current_failed_sites = current_status.get('summary', {}).get('failed_sites', 0)
        if current_failed_sites > 0:
            alert_section = f'<div class="alert alert-danger">⚠️ {current_failed_sites} website(s) are currently down!</div>'
        else:
            alert_section = '<div class="alert alert-success">✅ All websites are operational</div>'
    
    # Calculate summary statistics
    websites = dashboard_data.get('websites', {})
    total_websites = len(websites)
    
    if total_websites > 0:
        overall_uptime = sum(site['uptime_percentage'] for site in websites.values()) / total_websites
        overall_status_class = 'success' if overall_uptime >= 99 else 'warning' if overall_uptime >= 95 else 'danger'
    else:
        overall_uptime = 0
        overall_status_class = 'danger'
    
    # Calculate average response time from recent data
    timeline = dashboard_data.get('timeline', [])
    avg_response_time = 0
    if timeline:
        recent_times = [entry['average_response_time'] for entry in timeline[-10:] if entry['average_response_time'] > 0]
        avg_response_time = round(sum(recent_times) / len(recent_times) * 1000, 0) if recent_times else 0
    
    total_checks = sum(len(site['checks']) for site in websites.values())
    total_entries = len(timeline)
    
    # Generate website list HTML
    website_list_html = ""
    for site in websites.values():
        recent_check = site['checks'][-1] if site['checks'] else None
        status_class = "" if site['current_status'] == 'up' else "down"
        uptime = site['uptime_percentage']
        uptime_class = 'uptime-excellent' if uptime >= 99 else 'uptime-good' if uptime >= 95 else 'uptime-poor'
        
        response_time_text = ""
        if site['last_response_time']:
            response_time_text = f"<div class=\"response-time\">Last: {site['last_response_time']}s</div>"
        
        website_list_html += f"""
        <div class="website-item {status_class}">
            <div class="website-info">
                <strong>{site['name']}</strong><br>
                <small><a href="{site['url']}">{site['url']}</a></small>
            </div>
            <div class="website-metrics">
                <div>
                    <span class="uptime-badge {uptime_class}">{uptime}% uptime</span>
                    {response_time_text}
                </div>
            </div>
        </div>
        """
    
    # Format the template
    html_body_content = html_template_body.format(
        last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        alert_section=alert_section,
        total_websites=total_websites,
        overall_uptime=round(overall_uptime, 1),
        overall_status_class=overall_status_class,
        avg_response_time=int(avg_response_time),
        total_checks=total_checks,
        total_entries=total_entries,
        website_list_html=website_list_html,
        dashboard_data_json=json.dumps(dashboard_data)
    )

    html_content = html_template_start + html_template_head + html_body_content + html_template_end
    
    return html_content


def main():
    """Generate the dashboard"""
    print("📊 Generating monitoring dashboard...")
    
    # Load historical data
    historical_data = load_historical_data()
    current_status = load_current_status()
    
    if not historical_data:
        print("No historical data found. Run monitoring first.")
        # Create a minimal dashboard indicating no data
        minimal_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Website Monitoring Dashboard</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>🔍 Website Monitoring Dashboard</h1>
            <p>No monitoring data available yet.</p>
            <p>The dashboard will be populated after the first monitoring run.</p>
        </body>
        </html>
        """
        
        dashboard_file = os.path.join(os.path.dirname(__file__), 'dashboard.html')
        with open(dashboard_file, 'w') as f:
            f.write(minimal_html)
        
        print(f"📄 Minimal dashboard created: {dashboard_file}")
        return
    
    # Process data
    dashboard_data = generate_dashboard_data(historical_data)
    
    # Generate HTML
    html_content = generate_html_dashboard(dashboard_data, current_status)
    
    # Save dashboard
    dashboard_file = os.path.join(os.path.dirname(__file__), 'dashboard.html')
    with open(dashboard_file, 'w') as f:
        f.write(html_content)
    
    print(f"✅ Dashboard generated: {dashboard_file}")


if __name__ == '__main__':
    main()
