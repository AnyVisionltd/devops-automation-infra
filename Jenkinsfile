#!/usr/bin/env groovy
def remote = [:]

pipeline {
    environment {
        GIT_REPO_NAME = 'devops-automation-infra'
        GIT_CREDS = credentials('av-jenkins-reader')
        TEST_TARGET_BRANCH = 'master'
        EMAIL_TO = 'peterm@anyvision.co'
        KVM_MACHINE_IP = '192.168.70.35'
        KVM_MACHINE_CREDS = credentials("office-il-servers")
    }
    agent {
        label 'iloffice'
    }
    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 4, unit: 'HOURS')
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr:'50'))
    }
    parameters {
        string(name: 'AUTOMATION_INFRA_BRANCH', defaultValue: 'master', description: 'The automation_infra branch to include in this pipeline')
        string(name: 'CORE_PRODUCT_BRANCH', defaultValue: 'development', description: 'The core-product branch to include in this pipeline')
    }
    stages {
        stage ('Clone the automation_infra repo') {
            steps {
                checkout changelog: false, poll: false, scm: [
                    $class: 'GitSCM',
                    branches: [[name: params.AUTOMATION_INFRA_BRANCH ]],
                    extensions: [[$class: 'RelativeTargetDirectory',
                       relativeTargetDir: 'automation_infra/']],
                    userRemoteConfigs: [[credentialsId: 'av-jenkins-reader', url: "https://github.com/AnyVisionltd/automation-infra.git"]]
                ]
            }
        }
        stage ('Clone the core-product repo') {
            steps {
                checkout changelog: false, poll: false, scm: [
                    $class: 'GitSCM',
                    branches: [[name: params.CORE_PRODUCT_BRANCH ]],
                    extensions: [[$class: 'RelativeTargetDirectory',
                       relativeTargetDir: 'core_product/']],
                    userRemoteConfigs: [[credentialsId: 'av-jenkins-reader', url: "https://github.com/AnyVisionltd/core-product.git"]]
                ]
            }
        }
        stage ('Set Remote connection to KVM machine') {
            steps {
                script {
                    remote.name = "kvm-machine"
                    remote.host = "${env.KVM_MACHINE_IP}"
                    remote.allowAnyHosts = true
                    remote.user = "${env.KVM_MACHINE_CREDS_USR}"
                    remote.password = "${env.KVM_MACHINE_CREDS_PSW}"
                }
            }
        }
        stage('Run unit tests') {
            steps {
                script {
                    sh "echo 'Not yet implemented!'"
                }
            }
        }
        stage('Create VM for executing tests upon') {
            stages {
                stage('Spin up VM') {
                    steps {
                        script {
                            env.vminfo = sshCommand (
                                remote: remote,
                                command: '/home/user/automation-infra/hypervisor_cli.py --allocator=localhost:8080 create --image=ubuntu-compose_v2 --cpu=10 --ram=20 --size=150 --gpus=1 --networks bridge'
                            )
                            env.vmip = sh (
                                script: "echo '${env.vminfo}' | jq  .info.net_ifaces[0].ip",
                                returnStdout: true
                            ).trim()
                        }
                    }
                }
                stage('Create the hardware.yaml') {
                    steps {
                        sh (
                          script: "make -f ./automation_infra/Makefile-env set-connection-file HOST_IP=${env.vmip} USERNAME=root PASS=root CONN_FILE_PATH=${WORKSPACE}/hardware.yaml && cat ${WORKSPACE}/hardware.yaml"
                        )
                    }
                }
                stage('Send core-product to VM and run docker-compose up') {
                    steps {
                        script {
                            timeout(10) {
                                waitUntil {
                                    def resp = sh script: "nc -w 1 -z ${env.vmip} 22", returnStatus: true
                                    return resp == 0
                                }
                            }
                        }
                        sh """
                           ssh-keygen -R ${env.vmip} || true
                           ssh-keyscan -H ${env.vmip} >> ~/.ssh/known_hosts
                           sshpass -p root scp -r core_product root@${env.vmip}:
                           sshpass -p root ssh root@${env.vmip} 'docker-compose -f ./core_product/docker-compose/docker-compose-core-gpu.yml up -d'
                        """
                    }
                }
                stage('Run integration tests') {
                    steps {
                        sh (
                            script: "cd ./automation_infra/ && MOUNT_PATH=${WORKSPACE} PYTHONPATH=../automation/:. ./containerize.sh 'cat ${WORKSPACE}/hardware.yaml && PYTHONPATH=../automation/:. python3 -m pytest -p pytest_automation_infra ${WORKSPACE}/automation/devops_automation_infra/tests/docker_tests/ --hardware ${WORKSPACE}/hardware.yaml'"
                        )
                    }
                }
            }
        }
    } // end of stages
    post {
        always {
            script {
                vmname = sh (
                    script: "echo '${env.vminfo}' | jq .info.name",
                    returnStdout: true
                ).trim()
                sshCommand (
                    remote: remote,
                    command: "/home/user/automation-infra/hypervisor_cli.py --allocator=localhost:8080 delete --name ${vmname}"
                )
            }
            archiveArtifacts artifacts: '**/logs/**/*', fingerprint: true
            cleanWs()
        }
        failure {
            echo "${currentBuild.result}, exiting now..."
            mail to: "${EMAIL_TO}",
                 bcc: '',
                 cc: '',
                 charset: 'UTF-8',
                 from: '',
                 mimeType: 'text/html',
                 replyTo: '',
                 subject: "${currentBuild.result}: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                 body: "<b>Jenkins Job status:</b><br><br>" +
                        "Project: ${env.JOB_NAME}<br>" +
                        "Build Number: # ${env.BUILD_NUMBER}<br>" +
                        "Build Duration: ${currentBuild.durationString}<br>" +
                        "build url: ${env.BUILD_URL}<br>" +
                        "Build Log:<br>${currentBuild.rawBuild.getLog(50).join("<br>")}<br><br>" +
                        "<img class='cartoon' src='https://jenkins.io/images/226px-Jenkins_logo.svg.png' width='42' height='42' align='middle'/><br>"
        }
    }
}
