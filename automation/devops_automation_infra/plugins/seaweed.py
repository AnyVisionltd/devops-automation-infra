import logging
import tempfile

from infra.model import plugins
from pytest_automation_infra import helpers
from botocore.exceptions import ClientError
import boto3
import os
from automation_infra.utils import waiter
from devops_automation_infra.plugins.resource_manager import ResourceManager


class Seaweed(ResourceManager):
    def __init__(self, host):
        super().__init__(host)
        self._host = host
        self.DNS_NAME = 'seaweedfs-s3-localnode.tls.ai' if not helpers.is_k8s(self._host.SshDirect) else 'seaweedfs-s3.default.svc.cluster.local'
        self.filer_host = 'seaweedfs-filer-localnode.tls.ai' if not helpers.is_k8s(self._host.SshDirect) else 'seaweedfs-filer.default.svc.cluster.local'
        self.filer_port = 8888
        self.PORT = 8333

    @property
    def tunnel(self):
        return self._host.TunnelManager.get_or_create(self.DNS_NAME, self.DNS_NAME, self.PORT)

    @property
    def client(self):
        if self._client is None:
            self._client = self._s3_client()
        return self._client

    @property
    def resource(self):
        if self._resource is None:
            self._resource = self._s3_resource()
        return self._resource

    @property
    def remote_endpoint(self):
        return f'http://{self.DNS_NAME}:{self.PORT}'

    def _endpoint_uri(self):
        host, port = self.tunnel.host_port
        return f'http://{host}:{port}'

    def _s3_client(self):
        return boto3.client('s3', endpoint_url=self._endpoint_uri(),
                          aws_secret_access_key='any',
                          aws_access_key_id='any')

    def _s3_resource(self):
        return boto3.resource('s3', endpoint_url=self._endpoint_uri(),
                          aws_secret_access_key='any',
                          aws_access_key_id='any')

    def ping(self):
        self.get_all_buckets()

    def reset_state(self, keys={}):
        all_buckets = self.get_all_buckets()
        if len(all_buckets) > 0:
            logging.debug(f"reset seaweedfs state")
            for bucket in all_buckets:
                if bucket.name != 'static':
                    self.delete_bucket(bucket.name)

    def clear_buckets(self):
        weed_shell = "weed shell "

        def weed_cmd(cmd):
            return " | ".join([f"echo {cmd}", weed_shell])

        weed_delete_cmd = " | ".join([
            weed_cmd("s3.bucket.list"),
            "grep -v 'seaweedfs-master:9333'",
            "tr -d '>'",
            "sed '/^[[:space:]]*$/d'",
            "sed 's/^ *//'",
            "xargs -I{} echo -e 'lock\\n;s3.bucket.delete' -name={};\\nunlock\\n'",
            weed_shell
        ])
       
        logging.info(f"weed_delete_cmd: {weed_delete_cmd}")
        self._host.Docker.run_cmd_in_service('_seaweedfs-master_', weed_delete_cmd)

    def verify_functionality(self):
        try:
            self.delete_bucket("test_bucket")
        except ClientError as e:
            pass  # doesnt exist
        self.create_bucket("test_bucket")
        f = tempfile.NamedTemporaryFile(delete=True)
        f.write("content".encode())
        f.flush()
        self.upload_fileobj(f, "test_bucket", "temp/test.tmp")
        bucket_files = self.get_bucket_files('test_bucket')
        assert bucket_files == ['temp/test.tmp'], f'bucket files: {bucket_files}'

        self.clear_buckets()
        assert not self.file_exists('test_bucket', 'temp/test.tmp'), "buckets not cleared properly"

        logging.info(f"<<<<<<<<<<<<<SEAWEED PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>>")

    def http_direct_path(self, stream_s3_path):
        return os.path.join(f"http://{self.filer_host}:{self.filer_port}/buckets", stream_s3_path.replace('s3:///', ''))

    def deploy_resource_to_s3(self, resource_path, s3_path, chunk_size=100 * 1024 * 1024):
        bucket = "automation_infra"
        aws_s3_client = self._host.ResourceManager.client
        uploader = self.client.create_multipart_upload(Bucket=bucket, Key=s3_path)
        s3_object = aws_s3_client.get_object(Bucket="anyvision-testing", Key=resource_path)
        # Lets do 4MB chunks
        s3_data_stream = s3_object['Body'].iter_chunks(chunk_size=chunk_size)

        parts = []
        for i, chunk in enumerate(s3_data_stream):
            part = self.client.upload_part(Bucket=bucket, Key=s3_path,
                                       PartNumber=i, UploadId=uploader['UploadId'],
                                       Body=chunk)
            parts.append({"PartNumber": i, "ETag": part["ETag"]})

        result = self.client.complete_multipart_upload(Bucket=bucket,
                                                       Key=s3_path,
                                                       UploadId=uploader['UploadId'],
                                                       MultipartUpload={"Parts": parts})
        logging.debug(f"upload result to {bucket}/{s3_path} is {result}")
        return f'{bucket}/{s3_path}'

    def download_resource_from_s3(self, bucket, s3_path, local_folder):
        self.download_to_filesystem(s3_path, local_folder, bucket)

    def delete_resource_from_s3(self, bucket, s3_path):
        self.delete_file(bucket, s3_path)

    def deploy_multiple_resources_to_s3(self, aws_file_list, aws_folder, s3_folder):
        resources_s3_list = []
        for resource in aws_file_list:
            resources_s3_list.append(
            self.deploy_resource_to_s3(os.path.join(aws_folder, resource), os.path.join(s3_folder, resource)))
        return resources_s3_list

    def stop_service(self):
        self._host.Docker.stop_container("seaweedfs")
        self._host.Docker.wait_container_down("seaweedfs")

    def start_service(self):
        self._host.Docker.start_container("seaweedfs")
        self._host.Docker.wait_container_up("seaweedfs")
        waiter.wait_nothrow(self.ping, timeout=30)

    def service_running(self):
        return self._host.Docker.is_container_up("seaweedfs")


plugins.register('Seaweed', Seaweed)
