pipeline {
  agent any
  stages {
    stage('Test') {
      post {
        cleanup {
          echo 'Cleanup...'
          sh 'docker-compose down -v --rmi all && rm docker-compose.yml'
        }

      }
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
    }

    stage('Build') {
      environment {
        PYTHON_VERSION = credentials('python-version')
      }
      steps {
        echo 'Building..'
        script {
          dockerInstanceDjango = docker.build("winnerokay/sna-app", '-t latest --build-arg PYTHON_VERSION=$PYTHON_VERSION ./adminpage')
          dockerInstanceNginx = docker.build("winnerokay/sna-app-nginx", '-t latest ./nginx')
        }

      }
    }

    stage('Migrate') {
      environment {
        ENV_FILE = credentials('production-envfile')
      }
      steps {
        echo 'Making migrations to the db...'
        sh ' docker run --env-file $ENV_FILE -e POSTGRES_SERVER=$(getent hosts db_server | awk \'{ print $1 }\') winnerokay/sna-app:latest bash -c "python manage.py makemigrations && python manage.py migrate"'
      }
    }

    stage('Push to registry') {
      environment {
        registryCredentialSet = 'dockerhub'
      }
      steps {
        echo 'Publishing....'
        script {
          docker.withRegistry('', registryCredentialSet){
            dockerInstanceDjango.push("${env.GIT_COMMIT}")
            dockerInstanceDjango.push("latest")
            dockerInstanceNginx.push("${env.GIT_COMMIT}")
            dockerInstanceNginx.push("latest")
          }
        }

      }
    }

    stage('Deploy') {
      environment {
        ansibleInventoryFile = credentials('ansible-inventory-web')
        productionEnvfile = credentials('production-envfile')
      }
      steps {
        echo 'Deploying...'
        sh 'ls -la'
        ansiblePlaybook(
          playbook: "deploy_web.yml",
          inventory: "$ansibleInventoryFile",
          extras: '-e envfilePath=$productionEnvfile'
        )
      }
    }

  }
}
