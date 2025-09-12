#!/bin/bash

set -e

# Template variables
SECRET_NAME="${secret_name}"
AWS_REGION="${region}"

echo "Starting SageMaker notebook instance lifecycle configuration..."

# Install database connectivity packages
sudo -u ec2-user -i <<'EOF'
source /home/ec2-user/anaconda3/bin/activate python3
pip install --upgrade psycopg2-binary sqlalchemy pandas boto3
EOF

# Create a simple database connection helper
cat > /home/ec2-user/SageMaker/db_connection.py <<'PYTHON_SCRIPT'
import boto3
import json
from sqlalchemy import create_engine
import pandas as pd

def get_db_connection():
    """Get database connection using credentials from Secrets Manager."""
    client = boto3.client('secretsmanager', region_name='${region}')
    response = client.get_secret_value(SecretId='${secret_name}')
    creds = json.loads(response['SecretString'])

    connection_string = (
        f"postgresql://{creds['username']}:{creds['password']}@"
        f"{creds['host']}:{creds['port']}/{creds['database']}"
    )
    return create_engine(connection_string)

def query(sql):
    """Execute a query and return results as pandas DataFrame."""
    engine = get_db_connection()
    return pd.read_sql(sql, engine)

print("Database connection helper loaded. Usage: from db_connection import query")
PYTHON_SCRIPT

chown ec2-user:ec2-user /home/ec2-user/SageMaker/db_connection.py

echo "SageMaker notebook startup completed!"
