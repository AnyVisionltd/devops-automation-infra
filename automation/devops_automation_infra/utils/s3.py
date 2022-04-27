import os
from automation_infra.utils import concurrently
from functools import partial
import logging
from devops_automation_infra.utils import aws_s3


def clear_bucket(boto3_client, bucket_name):
    boto3_client.delete_bucket(Bucket=bucket_name)


def file_exists(boto3_client, bucket_name, file_name):
    try:
        boto3_client.get_object(Bucket=bucket_name, Key=file_name)
    except Exception:
        return False
    else:
        return True


def file_content(boto3_client, bucket_name, key):
    res = boto3_client.get_object(Bucket=bucket_name, Key=key)
    assert res['ResponseMetadata']['HTTPStatusCode'] == 200
    return res['Body'].read()


def bulk_upload_to_seaweed_from_s3(boto3_client, aws_folder, images_name):
    resources_s3_list = []
    for image in images_name:
        resources_s3_list.append(
            upload_to_seaweed_from_s3(boto3_client, aws_folder, image))
    return resources_s3_list


def upload_to_seaweed_from_s3(boto3_client, aws_folder, image_name, chunk_size=100 * 1024 * 1024):
    resource_path = os.path.join(aws_folder, image_name)
    bucket = "automation_infra"
    aws_s3_client = aws_s3.create_aws_s3_connection()
    uploader = boto3_client.create_multipart_upload(Bucket=bucket, Key=image_name)
    s3_object = aws_s3_client.get_object(Bucket="anyvision-testing", Key=resource_path)
    # Lets do 4MB chunks
    s3_data_stream = s3_object['Body'].iter_chunks(chunk_size=chunk_size)

    parts = []
    for i, chunk in enumerate(s3_data_stream):
        part = boto3_client.upload_part(Bucket=bucket, Key=resource_path,
                                        PartNumber=i, UploadId=uploader['UploadId'],
                                        Body=chunk)
        parts.append({"PartNumber": i, "ETag": part["ETag"]})

    result = boto3_client.complete_multipart_upload(Bucket=bucket,
                                                    Key=resource_path,
                                                    UploadId=uploader['UploadId'],
                                                    MultipartUpload={"Parts": parts})
    logging.debug(f"upload result to {bucket}/{resource_path} is {result}")
    return f'{bucket}/{resource_path}'


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


def get_bucket_key_from_path(path):
    full_path = path.replace('s3://', '/')
    start = 1
    bucket_key_separator = full_path.find('/', start)
    bucket = full_path[start: bucket_key_separator]
    key = full_path[bucket_key_separator + 1:]
    return bucket, key
