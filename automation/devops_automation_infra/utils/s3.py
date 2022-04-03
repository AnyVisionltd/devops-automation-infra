import os
import boto3
from automation_infra.utils import concurrently
from functools import  partial

def clear_bucket(boto3_client, bucket_name):
    boto3_client.delete_bucket(Bucket=bucket_name)

def file_exists(boto3_client, bucket_name,file_name):
    try:
        boto3_client.get_object(Bucket=bucket_name, Key=file_name)
    except Exception :
        return False
    else:
        return True

def clear_all_buckets(boto3_client):
    bucket_names = [bucket['Name'] for bucket in boto3_client.list_buckets()['Buckets']]
    jobs = {f"delete-job-{bucket}": partial(boto3_client.delete_bucket, Bucket=bucket) for bucket in bucket_names}
    if len(jobs) > 0:
        concurrently.run(jobs)

def download_file_to_filesystem(boto3_client, remote_path, local_dir=".", bucketname="anyvision-testing"):
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    local_file_path = os.path.join(local_dir, os.path.basename(remote_path))
    boto3_client.download_file(bucketname, remote_path, local_file_path)
    return local_file_path


def download_files_to_filesystem(boto3_client, remote_files, local_dir=".", bucketname="anyvision-testing"):
    for file in remote_files:
        download_file_to_filesystem(boto3_client, file, local_dir, bucketname)