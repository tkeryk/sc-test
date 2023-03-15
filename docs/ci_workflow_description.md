## Countinuous Integration for SAI Challenger 
(short description) 

CI created using github workflows and intended to verify docker build process after changes that are made to the Dockerfiles, source code or configuration files of SAI-Challenger.

CI involves checking the following configurations and their corresponding docker images:

|   | Mode               |Docker Images                                            |
|:--|:-------------------|:--------------------------------------------------------|
| 1 | standalone         | dockerfiles/Dockerfile,\<TARGET\>Dockerfile             |
| 2 | standalone-thrift  | dockerfiles/Dockerfile,\<TARGET\>Dockerfile.saithrift   |
| 3 | client             | dockerfiles/Dockerfile.client                           |
| 4 | client-thrift      | dockerfiles/Dockerfile.client, /dockerfiles/Dockerfile. saithrift-client |
| 5 | server             | dockerfiles/Dockerfile.server,\<TARGET\>Dockerfile      |


To minimize the duration of the CI pipeline, reuse docker images can be used. For example, testing the standalone and standalone-thrift variants involves using the same basic sc-base image.

|   | Base Dockerfile          | Base image  | Child Dockerfile    |Child Image    |
|:--|:-------------------------|:------------|:--------------------|:----------------------------------|
|   |dockerfiles/Dockerfile    | sc-base     |\<TARGET\>/Dockerfile|sc-\<TARGET\>                      |
|   |dockerfiles/Dockerfile    | sc-base     |\<TARGET\>/Dockerfile.saithrift|sc-thrift-\<TARGET\>               | 
|   |dockerfiles/Dockerfile.client| sc-client|dockerfiles/Dockerfile.saithrift-client|sc-thrift-client  |
|   |dockerfiles/Dockerfile.server| sc-server-base|\<TARGET\>/Dockerfile.server|sc-server-\<TARGET\>               |

CI execution is started by a trigger that is triggered by a pull-request (PR) if the proposed in PR changes may affect docker images. Pull request can be created to any branch. CI execution will triggered if changes have occurred in the following files or folders:
- '.github/workflows/sc-docker-images-bldr.yml'- 'dockerfiles/Dockerfile'
- 'dockerfiles/Dockerfile.client'
- 'dockerfiles/Dockerfile.saithrift-client'
- 'dockerfiles/Dockerfile.server'
- 'npu/broadcom/trident2/saivs/Dockerfile.saithrift'
- 'npu/broadcom/trident2/saivs/Dockerfile'
- 'npu/broadcom/trident2/saivs/Dockerfile.server'
- 'common/'
- 'cli/'
- 'scripts/'
- 'configs/'
- 'setup.py'
- 'build.sh'
- '.dockerignore'

Pull request operations that can tigger CI execution:

- open PR 
- reopen PR
- update PR

Github has a limit on simultaneous job - 20. To minimize the usage of CI pipeline resources, it is proposed not to run all CI jobs for create all docker images, but only those that may be affected by software changes by grouping them with the following SAI-Challenger modes:
- standalone
- client
- server

Thus, we will have the following files in .github/workflows:
- sc-docker-standalone-bldr.yml - used 2 jobs (for sai interface: redis, thrift)
- sc-docker-client-bldr.yml  - used 2 jobs (for sai interface: redis, thrift)
- sc-docker-server-bldr.yml  - used 1 job  (for sai interface: redis)

Also we can built redis and thrift image in one job successively to reuse base docker images 

Using this approach, we can provide simultaneous launch of CI for 4-20 newly created PRs

Estimated duration of CI - 25 minutes.

Example of workflow file:

```sh
name: sc-docker-client-bldr

on:
  pull_request:
    branches: [ "**" ]
    paths:
      - '.github/workflows/sc-docker-client-bldr.yml'
      - 'dockerfiles/Dockerfile.client'
      - 'dockerfiles/Dockerfile.saithrift-client'
      - 'common/'
      - 'cli/'
      - 'scripts/'
      - 'configs/'
      - 'setup.py'
      - 'build.sh'
      - '.dockerignore'
  
jobs: 
  build-sc-client-thrift:
    name: Build SAI Challenger client thrift image
    runs-on: ubuntu-20.04
    steps:
    - uses: actions/checkout@v3
    - name: submodules update
      run: git submodule update --init
    - name: build client docker image
      run: ./build.sh -i client
    - name: build client thrift docker image
      run: ./build.sh -i client -s thrift
```