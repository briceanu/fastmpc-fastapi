import boto3
from botocore.exceptions import ClientError
import json


def get_secret():
    """
    Retrieve and return a secret from AWS Secrets Manager.

    This function connects to AWS Secrets Manager in the specified region,
    retrieves the secret with the name 'learn', and parses it as a JSON object.

    Returns:
        dict: The secret data as a Python dictionary.

    Raises:
        botocore.exceptions.ClientError: If there is an error retrieving the secret.

    Notes:
        - The AWS credentials (access key, secret key, and session token if any)
          are automatically obtained from the environment, IAM role, or AWS config.
        - Ensure that the secret stored in AWS Secrets Manager is in valid JSON format
          so that `json.loads` can parse it correctly.
    """
    secret_name = "rent-car-app"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']
    secrets = json.loads(secret)
    return secrets
