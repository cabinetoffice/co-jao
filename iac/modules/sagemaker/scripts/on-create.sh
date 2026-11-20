#!/bin/bash

set -e

# Template variables
IDLE_TIME="${idle_time}"

echo "Setting up auto-stop for idle notebook instances..."

# Only set up auto-stop if idle_time is greater than 0
if [ "${idle_time}" -gt "0" ]; then
    # Create a simple auto-stop script
    cat > /home/ec2-user/SageMaker/auto-stop-idle.sh <<'SCRIPT'
#!/bin/bash
# Simple auto-stop script - checks if Jupyter has active kernels
# If no kernels are running for IDLE_TIME minutes, stop the instance

IDLE_TIME=${idle_time}
TIMESTAMP_FILE="/home/ec2-user/SageMaker/.last_activity"

# Check if any Jupyter kernels are running
if pgrep -f "jupyter-kernel" > /dev/null; then
    echo "$(date): Kernels active" >> /home/ec2-user/SageMaker/auto-stop.log
    date +%s > $TIMESTAMP_FILE
else
    # No kernels running, check how long idle
    if [ -f "$TIMESTAMP_FILE" ]; then
        LAST_ACTIVITY=$(cat $TIMESTAMP_FILE)
        CURRENT_TIME=$(date +%s)
        IDLE_SECONDS=$((CURRENT_TIME - LAST_ACTIVITY))
        IDLE_MINUTES=$((IDLE_SECONDS / 60))

        echo "$(date): Idle for $IDLE_MINUTES minutes" >> /home/ec2-user/SageMaker/auto-stop.log

        if [ $IDLE_MINUTES -ge $IDLE_TIME ]; then
            echo "$(date): Stopping instance due to inactivity" >> /home/ec2-user/SageMaker/auto-stop.log
            sudo shutdown -h now
        fi
    else
        # First time with no activity
        date +%s > $TIMESTAMP_FILE
    fi
fi
SCRIPT

    chmod +x /home/ec2-user/SageMaker/auto-stop-idle.sh

    # Create cron job to run every 5 minutes
    (crontab -u ec2-user -l 2>/dev/null || true; echo "*/5 * * * * /home/ec2-user/SageMaker/auto-stop-idle.sh") | crontab -u ec2-user -

    echo "Auto-stop configured for ${idle_time} minutes of inactivity"
else
    echo "Auto-stop is disabled (idle_time = 0)"
fi

# Set proper permissions
chown -R ec2-user:ec2-user /home/ec2-user/SageMaker/

echo "Lifecycle configuration completed!"
