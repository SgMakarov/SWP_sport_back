pipeline {
  agent any
  stages {
    stage('Build') {
      steps {
        echo 'Building..'
      }
    }

    stage('Test') {
      agent {
        docker {
          image 'docker/compose'
        }

      }
      steps {
        echo 'Testing..'
        sh 'docker-compose --version'
      }
    }

    stage('Deploy') {
      steps {
        echo 'Deploying....'
      }
    }

  }
}