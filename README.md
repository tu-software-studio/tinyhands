# Dream Suite

Love Justice International

![Codeship Status](https://app.codeship.com/projects/79c5fb20-1e83-0132-0c4f-7a12a542bc63/status?branch=master)

# Setup

## Docker

1. Make sure you install Docker [here](https://www.docker.com/) and docker-compose by executing: `sudo pip install docker-compose`
2. Clone the repository and cd into it
3. execute the `setup.sh` script in the root of the repo (this might take a few minutes)
4. run `docker-compose up -d` to start running the project
5. The created local.env file may need some secrets before the project will run. Ask for the secrets from whoever is helping you get started
6. If all of the steps were successful, you can find the application running on [port 80 on localhost](http://localhost).
7. If you can't figure this out, contact Austin Munn.

## Running on Pycharm in Windows
This assumes that you have the database set up already and have been working with the docker containers before.
I will enhance this guide with a more complete set-up process from a clean machine at a later date.
1. Install Python 3.12 on your Windows machine
2. Make a new Python Interpreter with a Virtual Environment (venv) using Python 3.12 
3. Under Tools -> Python Integrated Tools specify your requirements.txt as build\base\requirements.txt
4. Install C++ build tools (for face recognition dependencies)
   1. Download and run CMake Windows 64bit installer https://cmake.org/download/
   2. Verify `cmake` works in terminal (may need to restart PC)
   3. Download and install Visual Studio C++ Build tools via Microsoft Visual Studio Installer - https://visualstudio.microsoft.com/visual-cpp-build-tools/
   4. Choose Desktop Development with C++ (2 GB download, have good internet!)
5. Navigate to build\base\requirements.txt and click the yellow banner "Install Dependencies" (must finish indexing if you restarted)
6. Go into the Python Interpreter from step 2, hit the plus button and choose opencv-python, check specify version at 3.4.18.65
7. Make a Pycharm run configuration for docker compose for 'docker compose up' on service 'db'
8. Make a Pycharm run configuration for python with script pointed at manage.py 
   1. params: `runserver 9001 --settings dreamsuite.settings.local`
   2. working directory: application
   3. Modify Options -> Before Launch -> Run another configuration -> configuration from last step
9. Make sure Docker Desktop is running
10. Add the following to your local.env
    1. DREAMSUITE_LOG=./log/dreamsuite.log 
    2. DB_HOST=localhost 
    3. DB_PORT=7654
11. Launch the configuration from step 8
12. Visit localhost:9001/api/me/ and verify you get some page with "Authentication credentials were not provided"
13. Use postman to hit the endpoint that you want

## Installing Sanitized Test Data

execute `docker-compose run --rm web sh /data/bin/install_test_db.sh`

The sanitized database has two accounts preconfigured for testing both of which have the password 'pass'

- test_sup@example.com - is a super user account
- test1 - is a user account

## Installing Production Backup Data

1. Ask someone for a backup or use `sftp <your_ssh_username>@<server_name>` from the directory you want it in if you have ssh access
2. get db_restore.sh file from someone and run it

## Docker/Docker-Compose Cheat Sheet

- `docker-compose up -d` Turn on all of the containers listed in the docker-compose.yml file
- `docker-compose run --rm <container-name> bash` open a bash session inside a copy of the container
- `docker-compose kill <container name>*` Turn off the running containers
- `docker-compose rm <container name>*` Delete the containers
- `docker-compose run <container-name> <command>` Run a command inside of a copy of a container
- `docker-compose build` - rebuild the containers specified in the docker-compose.yml file
- `docker stop $(docker ps -a -q)` - stop all running containers on machine
- `docker rm $(docker ps -a -q)` - remove all containers on machine
- `docker exec -it <container-id> bash` - run an interactive shell inside the actual running container

## Some useful :commands on server
- export DREAMSUITE_TAG=`cat /home/thi/tinyhands/dreamsuite_tag`
- sudo DREAMSUITE_TAG=$DREAMSUITE_TAG docker-compose run -d --rm web ./manage.py backupAttachmentsToCloud -d 2024-10-01
- sudo DREAMSUITE_TAG=$DREAMSUITE_TAG docker-compose run --rm web bash
- ./manage.py backupAttachmentsToCloud -d 2024-10-01 -p /data/media
- docker exec -it web ./manage.py indicatorHistory --start 202405

## Some useful :commands on local
- python ./manage.py formLatest --settings dreamsuite.settings.local

# local.env and common.env files

In the root project directory there are three files used that contain environment variables. These files are used inside of the containers. If you look at the docker-compose.yml file you can see that these are imported into all of the containers.

- common.env file: This is for key-value pairs that are okay to be public knowledge. That way we can share their values.
- local.env file: This is for key-value pairs that should not be known to the public. Think passwords, secret keys, other stuff you don't want the world knowing about (Since one day it would be nice to make this an open-source project). Since we do not want these being released, this is not tracked in the repository.
- local.env.dist: This is where you put the keys that should go into the local.env file. In this file the format should be `<key>=`. This way we know what environment variables need to exist/be set to run the project, but we are not putting the actual values in version control

# Testing

## Django Unit Tests:

Execute the `./manage.py test` command in a new container. eg. `docker-compose run web ./manage.py test`

## Deployment Process

### Building containers

I have created a build script to automate the build process of docker-containers. Just run the script and manually check to see if there were any problems in the build process. Note that at the end, it provides a build number with which the images have been tagged. This version number is automatically put into a file called dreamsuite_tag in the root of the repository as well so that you do not have to remember it.

execute: `./build-containers.sh`

### Pushing containers

There is a push containers script in the root of the repository. This script takes in a version number as the 1st argument and pushes the containers to DockerHub with the specified tag. The following command pushes the docker containers with the tag number that was generated by the build-containers script.

`` ./push-containers.sh `cat dreamsuite_tag` ``

### Refreshing certificate

As of 2023-02-06, we are not using certbot automatic Lets Encrypt refreshing, 
and instead manually refreshing the certificate every 90 days.

To do this:
    - https://punchsalad.com/ssl-certificate-generator/, fill out and download file
    - put file with same name on server in tinyhands/data/certbot/www/.well-known/acme-challenge
    - verify that the link works, if it doesn't:

        docker restart nginx
        (wait for 'nginx' to appear in terminal)
        docker exec -it nginx /bin/bash
        cd /var/www/certbot/.well-known/acme-challenge
        (verify that file is in that folder)
        (test url on website provided)

After that:
    - cd tinyhands/certs/
    - vim fullchain.pem and replace it with top (text above CRT + CA bundle button)
    - vim privkey.pem and replace it with bottom (text above private key button)
    - docker restart nginx
