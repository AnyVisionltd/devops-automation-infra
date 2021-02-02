#!/usr/bin/env groovy
String cron_string = BRANCH_NAME == "master" ? "H H(0-4) * * *" : ""

pipeline {
    environment {
        GIT_REPO_NAME = 'devops-automation-infra'
        GIT_CREDS = credentials('av-jenkins-reader')
        HABERTEST_HEARTBEAT_SERVER='https://heartbeat-server.tls.ai'
        HABERTEST_PROVISIONER='https://provisioner.tls.ai'
        HABERTEST_SSL_CERT='$HOME/.habertest/habertest.crt'
        HABERTEST_SSL_KEY='$HOME/.habertest/habertest.key'

    }
    agent {
        label 'automation'
    }
    libraries {
        lib('pipeline-library')
    }
    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 4, unit: 'HOURS')
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr:'50'))
    }
    triggers {
        cron(cron_string)
        issueCommentTrigger('^\\/rebuild')
    }
    parameters {
        string(name: 'AUTOMATION_INFRA_BRANCH', defaultValue: 'master', description: 'The automation_infra branch to include in this pipeline')
    }
    stages {
        stage ('Git') {
            steps {
                cleanWs()
                script {
                    coreLib.repoInit("https://${GIT_CREDS_USR}:${GIT_CREDS_PSW}@github.com/AnyVisionltd/core-manifest.git", "automation")
                }
            }
        }
        stage ('Build automation proxy container') {
            steps{
                dir ('automation-infra'){
                    sh(script: "make push-automation-proxy")
                }
            }
        }
        stage('Run integration tests') {
            steps {
                dir ('automation-infra'){
                    sh (
                        script: "./run/env_vars.sh --install ../devops-automation-infra/automation/devops_automation_infra/tests/docker_tests/ --num-parallel 5"
                    )
                }
            }
        }
    } // end of stages
    post {
        success {
            cleanWs()
        }
        always {
            dir (env.GIT_REPO_NAME) {
                script {
                    coreLib.notification()
                }
            }
        }
    }
}
