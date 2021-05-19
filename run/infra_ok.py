#! /usr/bin/env python3

from pathlib import Path
import subprocess
import time


def check_output(command):
    subprocess.run(command, shell=True, stdout=subprocess.PIPE, check=True, input="")

def check_environment():
    start = time.time()
    gravity_doesnt_exist = False
    try:
        check_output('gravity status')
    except subprocess.CalledProcessError as e:
        gravity_doesnt_exist = True
        assert e.returncode == 127, \
            "Gravity exists on machine.. please purge from machine before resuming"
    assert gravity_doesnt_exist, "Gravity exists on machine.. please purge from machine before resuming"

    docker_config_json = Path.joinpath(Path.home(), '.docker/config.json')
    assert docker_config_json.exists(), \
        "Please get docker login credentials from https://anyvision.atlassian.net/wiki/spaces/INTEGRATION/pages/752321438/Software+Installation+from+scratch"

    certificate_dir = Path.joinpath(Path.home(), '.habertest')
    assert Path.exists(certificate_dir) and \
           {f.name for f in certificate_dir.glob('*')} == {'habertest.crt', 'habertest.key'}, \
        "Please download certificates from https://anyvision.atlassian.net/wiki/spaces/PROD/pages/2266464264/Run+test+with+cloud+provisioner"

    aws_dir = Path.joinpath(Path.home(), '.aws')
    
    assert Path.exists(aws_dir) and {'config', 'credentials'}.issubset({f.name for f in aws_dir.glob('*')}), \
        f"aws credentials dont exist in {Path.home()}.aws directory. Please get config and credential files"

    if not Path.exists(Path.joinpath(Path.home(), '.ssh', 'anyvision-devops.pem')):
        print(f'WARNING: anyvision-devops.pem doesnt exist in {Path.joinpath(Path.home(), ".ssh")} folder, '
              f'you will need it to ssh to provisioned HUT machines. Speak with devops to get it.')

    try:
        check_output('docker login https://gcr.io')
    except subprocess.CalledProcessError:
        print("Cant successfully login to docker. config.json:\n\n")
        with open(docker_config_json, "r") as f:
            print(f.read())
            
    try:
        check_output("aws s3 ls anyvision-testing")
    except subprocess.CalledProcessError:
        print(f"Couldn't connect to aws s3, check you have aws configured properly in {aws_dir} folder")

    duration = time.time() - start
    print(f"pre-flight duration: {duration}")


if __name__ == '__main__':
    check_environment()
