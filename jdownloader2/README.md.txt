Docker Image Update
Because features are added, issues are fixed, or simply because a new version of the containerized application is integrated, the Docker image is regularly updated. Different methods can be used to update the Docker image.

The system used to run the container may have a built-in way to update containers. If so, this could be your primary way to update Docker images.

An other way is to have the image be automatically updated with Watchtower. Whatchtower is a container-based solution for automating Docker image updates. This is a "set and forget" type of solution: once a new image is available, Watchtower will seamlessly perform the necessary steps to update the container.

Finally, the Docker image can be manually updated with these steps:

Fetch the latest image:
=======================
docker pull jlesage/jdownloader-2

Stop the container:
===================
docker stop jdownloader-2

Remove the container:
=====================
docker rm jdownloader-2