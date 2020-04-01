from infra.model import plugins
from automation_infra.plugins.base_plugin import TunneledPlugin
from pytest_automation_infra import helpers
from botocore.exceptions import ClientError
import boto3
import os


class Seaweed(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self.DNS_NAME = 'seaweedfs-s3-localnode.tls.ai' if not helpers.is_k8s(self._host.SshDirect) else 'seaweedfs-s3.default.svc.cluster.local'
        self.PORT = 8333
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = self._s3_client()
        return self._client

    def _s3_client(self):
        self.start_tunnel(self.DNS_NAME, self.PORT)
        s3_endpoint_url = f'http://localhost:{self.local_bind_port}'
        s3 = boto3.client('s3', endpoint_url=s3_endpoint_url,
                          aws_secret_access_key='any',
                          aws_access_key_id='any')
        return s3

    def get_bucket_files(self, bucket_name, recursive=True):
        return self.get_files_by_prefix(bucket_name, '', recursive)

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
        for obj in resp['Contents']:
            result.append(obj['Key'])
        return result


plugins.register('Seaweed', Seaweed)
