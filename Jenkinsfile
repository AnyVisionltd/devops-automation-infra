#!/usr/bin/env groovy
def remote = [:]

pipeline {
    environment {
        GIT_REPO_NAME = 'devops-automation-infra'
        GIT_CREDS = credentials('av-jenkins-reader')
        TEST_TARGET_BRANCH = 'master'
        EMAIL_TO = 'orielh@anyvision.co'
        HABERTEST_HEARTBEAT_SERVER='https://heartbeat-server.tls.ai'
        HABERTEST_PROVISIONER='https://provisioner.tls.ai'
        HABERTEST_SSL_CERT='$HOME/.habertest/habertest.crt'
        HABERTEST_SSL_KEY='$HOME/.habertest/habertest.key'

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
    triggers {
        issueCommentTrigger('^\\/rebuild')
    }
    parameters {
        string(name: 'AUTOMATION_INFRA_BRANCH', defaultValue: 'master', description: 'The automation_infra branch to include in this pipeline')
    }
    stages {
        stage ('Clone the automation_infra repo') {
            steps {
                script {
                    if (env.CHANGE_BRANCH) {
                      def buildNumber = env.BUILD_NUMBER as int
                      echo "Aborting previous build: ${buildNumber - 1}"
                      if (buildNumber > 1) milestone(buildNumber - 1)
                      milestone(buildNumber)
                    }
                }
                script {
                    sh "rm devops-automation-infra automation-infra -rf"
                    sh "mkdir devops-automation-infra && mv -t devops-automation-infra automation Jenkinsfile"
                }
                checkout changelog: false, poll: false, scm: [
                    $class: 'GitSCM',
                    branches: [[name: params.AUTOMATION_INFRA_BRANCH ]],
                    extensions: [[$class: 'RelativeTargetDirectory',
                       relativeTargetDir: 'automation-infra/']],
                    userRemoteConfigs: [[credentialsId: 'av-jenkins-reader', url: "https://github.com/AnyVisionltd/automation-infra.git"]]
                ]
                sh "echo finished cloning successfully"
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
                //dir ('automation-infra'){
                    sh (
                        script: "cd automation-infra && ./run/env_vars.sh -p devops_product_manager ../devops-automation-infra/automation/devops_automation_infra/tests/docker_tests/ --log-cli-level info"
                    )
                //}
            }
        }
    } // end of stages
    post {
        always {
            archiveArtifacts artifacts: '**/logs/**/*', fingerprint: true
            echo "post build stage :)"
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
