pipeline {
    agent none
    triggers {
        // Needs Cron. FIXME the expression below shouldn't trigger until 2044. Needs to be altered after MVP. 
        cron('0 0 29 2 1')
    }
    environment {
        IMAGE_NAME = 'box-cron'
    }
    stages {
        stage('Test Deploy') {
            agent {
                label 'podman'
            }
            stages{
                stage('Build') {
                    steps {
                        script {
                            if (currentBuild.getBuildCauses('com.cloudbees.jenkins.GitHubPushCause').size() || currentBuild.getBuildCauses('jenkins.branch.BranchIndexingCause').size()) {
                               scmSkip(deleteBuild: true, skipPattern:'.*\\[ci skip\\].*')
                            }
                        }
                        echo "NODE_NAME = ${env.NODE_NAME}"
                        sh 'podman build -t localhost/$IMAGE_NAME --pull --force-rm --no-cache .'
                        
                     }
                }
                stage('Test') {
                    steps {
                        sh 'podman run -it --rm --pull=never localhost/$IMAGE_NAME which python'
                        sh 'podman run -it --rm --pull=never localhost/$IMAGE_NAME python -c "import requests; from boxsdk import JWTAuth, Client"'
                        sh 'podman run -it --rm --pull=never -v $PWD:/var/tmp:z localhost/$IMAGE_NAME python test_file.py'
                        // sh 'podman run -it --rm --pull=never -v $PWD:/var/tmp:z localhost/$IMAGE_NAME python box_export.py'
                        sh 'podman run -it --rm --pull=never -v $PWD:/var/tmp:z localhost/$IMAGE_NAME python box_transfer.py'
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'test_write.csv, box_export.csv, csvStatusInactive.csv, outputLog.csv'
                            sh 'podman rmi -i localhost/$IMAGE_NAME || true'
                        }
                    }
                }
                stage('Deploy') {
                    when { branch 'main' }
                    steps {
                        // Launch python code here to run a sync. 
                        echo "Placeholder text for running sync"
                    }
                }
            }
        }
    }
    post {
        success {
            slackSend(channel: '#infrastructure-build', username: 'jenkins', color: 'good', message: "Build ${env.JOB_NAME} ${env.BUILD_NUMBER} just finished successfull! (<${env.BUILD_URL}|Details>)")
           slackSend(channel: '#project-pit-box', username: 'jenkins', color: 'good', message: "Build ${env.JOB_NAME} ${env.BUILD_NUMBER} just finished successfull! (<${env.BUILD_URL}|Details>)")
        }
        failure {
            slackSend(channel: '#project-pit-box', username: 'jenkins', color: 'danger', message: "Uh Oh! Build ${env.JOB_NAME} ${env.BUILD_NUMBER} had a failure! (<${env.BUILD_URL}|Find out why>).")
            slackSend(channel: '#infrastructure-build', username: 'jenkins', color: 'danger', message: "Uh Oh! Build ${env.JOB_NAME} ${env.BUILD_NUMBER} had a failure! (<${env.BUILD_URL}|Find out why>).")
        }
    }
}

