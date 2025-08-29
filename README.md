# Canary

Website health monitor using GitHub Actions as cloud hosting provider

## License

Canary is made available free of charge under the Affero GPL v3 license (or any later version, at your option). See `LICENSE.txt` for the full license text.

## Features

Canary was developed by prioritizing a few key aspects:

### Down Detection

Monitors the list of websites provided repeatedly at a defined interval, and sends an alert email if any outages are detected.

### Offsite Monitoring

Since this was developed to monitor the health of websites being run on-premesis and alert in the case of downtime due to power outages, an offsite location was needed for the runtime. 

### No Installation or Maintenance

I wanted to experiment with this "cloud computing" idea, since renting a new offsite VPS might be prohibitively expensive and I didn't want to build a web app which would be always-online just to occasionally ping a few websites and possibly send an email.

### No New Subscriptions or Trials

Since I was already paying for a Github subscription and not using my Github Actions minutes for anything, this seemed a more appealing solution than a trial for AWS or Azure. Due to the way Github Actions runners are apportioned, cron tasks don't always execute with specific precision, but that is considered an acceptable drawback for this project.

### Metrics Dashboard

In order to analyze trends in the downtime of these sites, a small amount of data is stored with each run (using Github Actions cache) containing the response time and up/down status of each website checked. Each run generates an HTML dashboard using ChartJS to render and filter the data.

## How to Use

Getting Canary up and running takes only a few steps, since it runs entirely on Github Actions runners:

1. Fork and configure Canary
2. Set appropriate cron settings for your use case
3. Set repository secrets for SMTP (optional)
4. View results via Github Actions

You will need SMTP credentials in order for the alert emails to be sent. If these are not provided (via secrets), you will not receive email alerts.

It is **highly recommended** to use a Private repository for this program, otherwise your list of websites to check, and the email your alerts are being sent to, will both be visible to the public.

### Fork and configure Canary

First, start by creating your own fork of the repository. You will need this so that you can input your own SMTP secrets.

Then, edit the file [config/websites.json](config/websites.json) according to the following schema:

```JSON
{
    "websites": [
        {
            "name": "Friendly Name",
            "url": "http//example.url.goes.here",
            "timeout": 10,
            "expected_status": 200,
            "content_keywords": []
        },
        ...
    ],
    "notification": {
        "email": "email.to.send.alerts.to@your.email.provider",
        "subject_prefix": "[WEBSITE ALERT]"
    },
    "settings": {
        "retry_attempts": 2,
        "retry_delay": 5,
        "user_agent": "Canary/1.0"
    }
}
```

Each object in the `websites` list will be checked. Canary will wait up to `timeout` seconds for a response, and will confirm that the returned status matches `expected_status`.

*Optionally, you can populate `content_keywords` with a list of phrases to check for, and if any of those phrases were not found (case insensitive) in the returned content from the specified `url`, then this will be considered a "down" condition.*

The `email` in the `notification` section is the email you want your alerts sent to. This is used by the script when building the alert email, and if you want to include a `subject_prefix` so you can filter the incoming email at this address for specific notifications, that can be updated here.

The only other application-specific settings are the `retry_attempts`, which is the number of times Canary will retry if the `timeout` is reached for that site; the `retry_delay`, which is the number of seconds Canary will wait before retrying; and the `user_agent`, which is sent in the header of each request. You can set a custom user agent here if you want to implement any sort of packet filtering or header-based whitelisting for this utility.

### Set appropriate cron settings for your use case

The [.github/workflows/monitor.yml](.github/workflows/monitor.yml) file contains the information for the Github Actions pipeline to execute the script. One of the very first things in this file is the `cron` settings:

```yml
name: Canary

on:
  schedule:
    # Run every 15 minutes
    - cron: '*/15 * * * *'
```

This is what makes the program run automatically. This setting will control how often your sites are checked, and thus, how quickly you get alerted when a down condition happens.

**Caution:** Depending on the number of sites being checked, the number of timeouts/retries, and this cron setting, this will all add up to your total Github Actions usage. Be very mindful of this if your Github plan only includes a certain total of minutes, since Github will round up to the nearest whole minute on each Action's runtime! ([source](https://docs.github.com/en/billing/reference/actions-minute-multipliers)) You can estimate how many minutes this program will use each month by taking the average runtime (rounded up to the nearest whole minute) and multiplying it by the cron frequency. So, assuming a cron of 15 minutes, average runtime of 20 seconds, and a 30-day month:

```
30*24*(60/15) = 2880 minutes/month
```

If we instead change the cron to run every 20 minutes instead of every 15:

```
30*24*(60/20) = 2160 minutes/month
```

Your cron should be set to an amount which doesn't consume too much of your available Github Actions minutes each month, but still frequent enough that you can be notified in a timely manner when outages occur. Please take time to adjust these settings appropriately to avoid unexpected billing for overages.

### Set repository secrets for SMTP

Since you have forked this repository, you can set secrets for your fork which are only accessible in your forked repository. In the Settings panel for this repository, set the following secrets to your SMTP credentials:

* `SMTP_SERVER`
* `SMTP_PORT`
* `SMTP_USERNAME`
* `SMTP_PASSWORD`

These are passed into the script as environment variables so the script can send the alert email if any mismatches to `expected_status` or `content_keywords` are detected.

### View results via Github Actions

Now that everything is set up, you can see the output of the program in the Actions tab of your forked repository once it's triggered. You can either wait until cron triggers it, or you can trigger it manually from the Actions tab by selecting the specific workflow.

Clicking an Action will show the status summary, including the websites and response times for that specific run. If you download and open the .zip file containing the `dashboard.html` file, you will see the ChartJS implementation showing data from the past 24 hours by default. Resetting the time filter on the dashboard will allow you to see all data from the last 500 runs.
