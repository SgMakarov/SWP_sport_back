pipeline {
  agent any
  stages {
    stage('Test') {
      steps {
        echo 'Testing..'
        sh '''
          ln -s docker-compose-test.yml docker-compose.yml
          echo "Building test images..."
          docker-compose build --no-cache
          docker-compose up -d
          echo "Waiting for database to go up..."
          docker-compose exec -T adminpanel bash -c "while !</dev/tcp/db/5432; do sleep 1; done;"  
          echo "Making migrations..."
          docker-compose exec -T adminpanel python manage.py makemigrations
          docker-compose exec -T adminpanel python manage.py migrate
          echo "Running tests..."
          docker-compose exec -T adminpanel pytest
          echo "done"
          '''
      }
      post {
        cleanup {
          echo 'Cleanup...'
          sh 'docker-compose down -v --rmi all && rm docker-compose.yml'
        }
      }
    }

    stage('Build') {
      environment {
        PYTHON_VERSION = credentials('python-version')
      }
      steps {
        echo 'Building..'
        script {
          dockerInstanceDjango = docker.build("winnerokay/sna-app", '--build-arg PYTHON_VERSION=$PYTHON_VERSION ./adminpage')
	  dockerInstanceNginx = docker.build("winnerokay/sna-app-nginx", './nginx')
        }
      }
    }
    
    stage('Migrate'){
      steps {
        echo 'Making migrations to the db...' 
      }
    }
    
    stage('Push to registry') {
      environment {
        registryCredentialSet = 'dockerhub'
      }
      steps {
        echo 'Publishing....'
        script{
          docker.withRegistry('', registryCredentialSet){
            dockerInstanceDjango.push("${env.BUILD_NUMBER}")
            dockerInstanceDjango.push("latest")
	    dockerInstanceNginx.push("${env.BUILD_NUMBER}")
            dockerInstanceNginx.push("latest")
          }
        }
      }
    }
    
    stage('Deploy'){
      steps {
        echo 'Deploying...'
      }
    }
  }
}
