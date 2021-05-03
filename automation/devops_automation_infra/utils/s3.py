import os

def download_file_to_filesystem(boto3_client, remote_path, local_dir=".", bucketname="anyvision-testing"):
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    local_file_path = os.path.join(local_dir, os.path.basename(remote_path))
    boto3_client.download_file(bucketname, remote_path, local_file_path)
    return local_file_path

def download_files_to_filesystem(boto3_client, remote_files, local_dir=".", bucketname="anyvision-testing"):
    for file in remote_files:
        download_file_to_filesystem(boto3_client, file, local_dir, bucketname)