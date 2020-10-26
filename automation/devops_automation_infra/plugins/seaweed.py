import logging
import tempfile

from infra.model import plugins
from pytest_automation_infra import helpers
from botocore.exceptions import ClientError
import boto3
import os
import io

from automation_infra.plugins.resource_manager import ResourceManager


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
        weed_shell = "weed shell -filer seaweedfs-filer:8888"

        def weed_cmd(cmd):
            return " | ".join([f"echo {cmd}", weed_shell])

        weed_delete_cmd = " | ".join([
            weed_cmd("bucket.list"),
            "grep -Eo '\\S+$'",
            "sed 's|^|bucket.delete -name |'",
            "tr '\\n' ';'",
            weed_shell
        ])

        weed_delete_cmd = "; ".join([
            weed_cmd("lock"),
            weed_delete_cmd,
            weed_cmd("unlock")
        ])

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


    def deploy_resource_to_s3(self, resource_path, s3_path):
        bucket = "automation_infra"
        file_bytes = self._host.ResourceManager.get_raw_resource(resource_path)
        file_obj = io.BytesIO(file_bytes)
        self.upload_fileobj(file_obj, bucket, s3_path)
        return f'{bucket}/{s3_path}'

    def download_resource_from_s3(self, bucket, s3_path, local_folder):
        self.download_to_filesystem(s3_path, local_folder, bucket)

    def deploy_multiple_resources_to_s3(self, aws_file_list, aws_folder, s3_folder):
        resources_s3_list = []
        for resource in aws_file_list:
            resources_s3_list.append(
            self.deploy_resource_to_s3(os.path.join(aws_folder, resource), os.path.join(s3_folder, resource)))
        return resources_s3_list


plugins.register('Seaweed', Seaweed)
