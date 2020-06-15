import logging
import tempfile

from infra.model import plugins
from automation_infra.plugins.base_plugin import TunneledPlugin
from pytest_automation_infra import helpers
from botocore.exceptions import ClientError
import boto3
import os


class Seaweed(object):
    def __init__(self, host):
        self._host = host
        self.DNS_NAME = 'seaweedfs-s3-localnode.tls.ai' if not helpers.is_k8s(self._host.SshDirect) else 'seaweedfs-s3.default.svc.cluster.local'
        self.filer_host = 'seaweedfs-filer-localnode.tls.ai' if not helpers.is_k8s(self._host.SshDirect) else 'seaweedfs-filer.default.svc.cluster.local'
        self.filer_port = 8888
        self.PORT = 8333
        self._client = None
        self._resource = None


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

    def get_bucket_files(self, bucket_name, recursive=True):
        return self.get_files_by_prefix(bucket_name, '', recursive)

    def get_all_buckets(self):
        return list(self.resource.buckets.all())

    def get_files_by_prefix(self, bucket_name, prefix, recursive=True):
        res = self.client.list_objects(Bucket=bucket_name, Prefix=prefix)
        res_code = res['ResponseMetadata']['HTTPStatusCode']
        assert res_code == 200
        files = [x['Key'] for x in res.get('Contents', [])]
        if not recursive:
            return files
        for x in res.get('CommonPrefixes', []):
            prefix = x['Prefix']
            files.extend(self.get_files_by_prefix(bucket_name, prefix))
        return files

    def create_bucket(self, bucket_name):
        res = self.client.create_bucket(Bucket=bucket_name)
        res_code = res['ResponseMetadata']['HTTPStatusCode']
        assert res_code == 200

    def delete_bucket(self, bucket_name):
        res = self.client.delete_bucket(Bucket=bucket_name)
        res_code = res['ResponseMetadata']['HTTPStatusCode']
        assert res_code == 204

    def upload_file_to_bucket(self, src_file_path, dst_bucket, ds_file_name):
        res = self.client.upload_file(src_file_path, dst_bucket, ds_file_name)
        assert res is None

    def upload_fileobj(self, file_obj, dst_bucket, dst_filepath):
        res = self.client.upload_fileobj(file_obj, dst_bucket, dst_filepath)
        assert res is None

    def upload_files_from(self, path, dst_bucket):
        self.create_bucket(dst_bucket)
        src_files = os.listdir(path)
        dst_files = self.get_bucket_files(dst_bucket)
        missing_files = [item for item in src_files if item not in dst_files]
        for _file in missing_files:
            self.upload_file_to_bucket(path + _file, dst_bucket, _file)

    def file_exists(self, bucket_name, file_name):
        try:
            self.client.head_object(Bucket=bucket_name, Key=file_name)
        except ClientError:
            return False
        else:
            return True
        
    def file_content(self, bucket_name, key):
        res = self.client.get_object(Bucket=bucket_name, Key=key)
        assert res['ResponseMetadata']['HTTPStatusCode'] == 200
        return res['Body'].read()

    def check_video_path(self, bucket_name, key):
        res = self.client.get_object(Bucket=bucket_name, Key=key)
        assert res['ResponseMetadata']['HTTPStatusCode'] == 200
        return res

    def get_files_in_dir(self, bucket_name, dir_path):
        result = []
        resp = self.client.list_objects_v2(Bucket=bucket_name, Prefix=dir_path, Delimiter='/')
        if 'Contents' not in resp.keys():
            return
        return [obj['Key'] for obj in resp['Contents']]

    def delete_file(self, bucket_name, file_name):
        self.client.delete_object(Bucket=bucket_name, Key=file_name)
        assert not self.file_exists(bucket_name, file_name)

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


plugins.register('Seaweed', Seaweed)
