#!/usr/bin/env python3
"""
Website monitoring script for GitHub Actions
Checks configured websites and sends email alerts on failures
"""

import json
import os
import sys
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

def get_cache_dir():
    """Get cache directory path"""
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def load_config():
    """Load configuration from JSON file"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'websites.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

def load_historical_data():
    """Load existing historical data from cache"""
    cache_dir = get_cache_dir()
    historical_file = os.path.join(cache_dir, 'monitoring_history.json')
    
    if os.path.exists(historical_file):
        try:
            with open(historical_file, 'r') as f:
                data = json.load(f)
                print(f"📚 Loaded {len(data)} historical entries from cache")
                return data
        except Exception as e:
            print(f"Warning: Could not load historical data: {e}")
    
    print("📚 No historical data found in cache, starting fresh")
    return []


def save_historical_data(historical_data, new_entry):
    """Save updated historical data to cache"""
    try:
        cache_dir = get_cache_dir()
        
        # Add new entry
        historical_data.append(new_entry)
        
        # Keep only last 500 entries
        # GitHub Actions cache has size limits, so we keep it smaller
        if len(historical_data) > 500:
            historical_data = historical_data[-500:]
            print(f"📦 Trimmed historical data to last 500 entries")
        
        # Save to cache
        historical_file = os.path.join(cache_dir, 'monitoring_history.json')
        with open(historical_file, 'w') as f:
            json.dump(historical_data, f, indent=2)
        
        print(f"💾 Saved historical data to cache ({len(historical_data)} total entries)")
        return True
        
    except Exception as e:
        print(f"Error saving historical data: {e}")
        return False


def save_current_status(results):
    """Save current status for quick access"""
    try:
        cache_dir = get_cache_dir()
        
        status_data = {
            'timestamp': datetime.now().isoformat(),
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'summary': {
                'total_sites': len(results),
                'successful_sites': len([r for r in results if r['success']]),
                'failed_sites': len([r for r in results if not r['success']]),
                'average_response_time': calculate_average_response_time(results)
            },
            'sites': {
                result['name']: {
                    'status': 'up' if result['success'] else 'down',
                    'response_time': result.get('response_time'),
                    'status_code': result.get('status_code'),
                    'error': result.get('error'),
                    'url': result['url']
                }
                for result in results
            }
        }
        
        status_file = os.path.join(cache_dir, 'current_status.json')
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
            
        print(f"📊 Saved current status to cache")
        return True
        
    except Exception as e:
        print(f"Error saving current status: {e}")
        return False

def check_website(website_config, user_agent):
    """Check a single website and return result"""
    url = website_config['url']
    name = website_config['name']
    timeout = website_config.get('timeout', 10)
    expected_status = website_config.get('expected_status', 200)
    content_keywords = website_config.get('content_keywords', [])
    
    print(f"Checking {name} ({url})...")
    
    result = {
        'name': name,
        'url': url,
        'timestamp': datetime.now().isoformat(),
        'success': False,
        'status_code': None,
        'response_time': None,
        'error': None
    }
    
    try:
        headers = {
            'User-Agent': user_agent
        }
        
        start_time = time.time()
        response = requests.get(url, timeout=timeout, headers=headers)
        end_time = time.time()
        
        result['status_code'] = response.status_code
        result['response_time'] = round(end_time - start_time, 2)
        
        # Check status code
        if response.status_code != expected_status:
            result['error'] = f"Expected status {expected_status}, got {response.status_code}"
            return result
            
        # Check content if required
        if len(content_keywords) > 0:
            content = response.text.lower()
            missing_keywords = [kw for kw in content_keywords if kw.lower() not in content]
            if missing_keywords:
                result['error'] = f"Missing keywords in content: {', '.join(missing_keywords)}"
                return result
        
        result['success'] = True
        print(f"✓ {name} OK ({result['response_time']}s)")
        
    except requests.exceptions.Timeout:
        result['error'] = f"Timeout after {timeout} seconds"
        print(f"✗ {name} TIMEOUT")
        
    except requests.exceptions.ConnectionError:
        result['error'] = "Connection error - site may be down"
        print(f"✗ {name} CONNECTION ERROR")
        
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"
        print(f"✗ {name} ERROR: {str(e)}")
    
    return result


def retry_check(website_config, max_retries, retry_delay, user_agent):
    """Check website with retry logic"""
    for attempt in range(max_retries + 1):
        if attempt > 0:
            print(f"  Retry {attempt}/{max_retries} after {retry_delay}s...")
            time.sleep(retry_delay)
            
        result = check_website(website_config, user_agent)
        if result['success']:
            return result
            
    return result


def calculate_average_response_time(results):
    """Calculate average response time for successful checks"""
    successful_times = [r['response_time'] for r in results if r['success'] and r['response_time']]
    return round(sum(successful_times) / len(successful_times), 2) if successful_times else 0


def calculate_uptime_stats(historical_data, hours=24):
    """Calculate uptime statistics for the last N hours"""
    if not historical_data:
        return {}
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    stats = {}
    for entry in historical_data:
        try:
            entry_time = datetime.fromisoformat(entry['timestamp'])
            if entry_time < cutoff_time:
                continue
        except:
            continue
            
        for result in entry['results']:
            site_name = result['name']
            if site_name not in stats:
                stats[site_name] = {'total': 0, 'successful': 0}
            
            stats[site_name]['total'] += 1
            if result['success']:
                stats[site_name]['successful'] += 1
    
    # Calculate percentages
    uptime_percentages = {}
    for site_name, data in stats.items():
        if data['total'] > 0:
            uptime_percentages[site_name] = round((data['successful'] / data['total']) * 100, 2)
        else:
            uptime_percentages[site_name] = 0
    
    return uptime_percentages


def write_github_summary(results, failed_checks):
    """Write status summary to GitHub Actions summary"""
    github_summary_file = os.getenv('GITHUB_STEP_SUMMARY')
    if not github_summary_file:
        return
    
    try:
        with open(github_summary_file, 'a') as f:
            f.write("# 🔍 Website Monitoring Report\n\n")
            
            # Overall status
            if failed_checks:
                f.write(f"## ⚠️ Status: {len(failed_checks)} site{'s' if len(failed_checks)>1 else ''} down\n\n")
            else:
                f.write("## ✅ Status: All systems operational\n\n")
            
            # Summary table
            f.write("| Website | Link | Status | Response Time | Error |\n")
            f.write("|---------|------|--------|---------------|-------|\n")
            
            for result in results:
                status_icon = "✅" if result['success'] else "❌"
                response_time = f"{result['response_time']}s" if result['response_time'] else "N/A"
                error = result.get('error', '').replace('|', '\\|') if result.get('error') else "None"
                
                f.write(f"| {result['name']} | [{result['url']}]({result['url']}) | {status_icon} | {response_time} | {error} |\n")
            
            f.write(f"\n📅 Last check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            
    except Exception as e:
        print(f"Warning: Could not write GitHub summary: {e}")


def send_email_alert(failed_checks, config):
    """Send email alert for failed checks"""
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    if not all([smtp_server, smtp_username, smtp_password]):
        print("Error: Email configuration missing in environment variables")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = config['notification']['email']
        
        subject_prefix = config['notification'].get('subject_prefix', '[WEBSITE ALERT]')
        if len(failed_checks) == 1:
            msg['Subject'] = f"{subject_prefix} {failed_checks[0]['name']} is down"
        else:
            msg['Subject'] = f"{subject_prefix} {len(failed_checks)} websites are down"
        
        # Create email body
        body = "Website monitoring alert:\n\n"
        
        for check in failed_checks:
            body += f"❌ {check['name']}\n"
            body += f"   URL: {check['url']}\n"
            body += f"   Time: {check['timestamp']}\n"
            body += f"   Error: {check['error']}\n"
            if check['status_code']:
                body += f"   Status Code: {check['status_code']}\n"
            if check['response_time']:
                body += f"   Response Time: {check['response_time']}s\n"
            body += "\n"
        
        body += f"Check performed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        body += "This alert was sent by Canary via GitHub Actions"
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        
        print(f"✓ Alert email sent to {config['notification']['email']}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to send email alert: {e}")
        return False


def main():
    """Main function"""
    print("Starting website monitoring...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Load configuration
    config = load_config()
    historical_data = load_historical_data()
    
    # Get settings
    settings = config.get('settings', {})
    retry_attempts = settings.get('retry_attempts', 2)
    retry_delay = settings.get('retry_delay', 5)
    user_agent = settings.get('user_agent', requests.utils.default_headers())
    
    # Check all websites
    results = []
    failed_checks = []
    
    for website in config['websites']:
        result = retry_check(website, retry_attempts, retry_delay, user_agent)
        results.append(result)
        
        if not result['success']:
            failed_checks.append(result)

    # Create monitoring entry
    monitoring_entry = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_sites': len(results),
            'successful_sites': len([r for r in results if r['success']]),
            'failed_sites': len([r for r in results if not r['success']]),
            'average_response_time': calculate_average_response_time(results)
        },
        'results': results,
        'metadata': {
            'run_id': os.getenv('GITHUB_RUN_ID', 'local'),
            'run_number': os.getenv('GITHUB_RUN_NUMBER', '0'),
            'workflow': os.getenv('GITHUB_WORKFLOW', 'local-test')
        }
    }

    # Save data to cache
    save_historical_data(historical_data, monitoring_entry)
    save_current_status(results)
    
    # Calculate uptime statistics
    uptime_stats = calculate_uptime_stats(historical_data + [monitoring_entry], hours=24)
    
    # Summary
    total_sites = len(results)
    failed_sites = len(failed_checks)
    successful_sites = total_sites - failed_sites
    
    print(f"\n--- Summary ---")
    print(f"Total sites checked: {total_sites}")
    print(f"Successful: {successful_sites}")
    print(f"Failed: {failed_sites}")
    print(f"Historical entries: {len(historical_data)+1}")

    if uptime_stats:
        print(f"\n--- 24h Uptime ---")
        for site_name, uptime in uptime_stats.items():
            print(f"{site_name}: {uptime}%")
    
    # Send alerts if there are failures
    if failed_checks:
        print(f"\n🚨 Sending alert for {len(failed_checks)} failed sites...")
        send_email_alert(failed_checks, config)
        # Write status to GitHub Actions summary
        write_github_summary(results, failed_checks)
        # Don't exit with error - we want the job to succeed
        print(f"⚠️ Monitoring completed with {len(failed_checks)} failures")
    else:
        print(f"\n✅ All sites are operational!")
        write_github_summary(results, failed_checks)
    

if __name__ == '__main__':
    main()
