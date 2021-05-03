import boto3
import os

def create_aws_s3_connection():
    _is_aws_cred_path_exists()
    s3 = boto3.client('s3')  # Configure locally access keys on local machine in ~/.aws, this will use them
    return s3

def _is_aws_cred_path_exists():
    if not os.path.exists(f'{os.path.expanduser("~")}/.aws'):
        raise FileNotFoundError("Missing aws credentials in ~/.aws folder")
