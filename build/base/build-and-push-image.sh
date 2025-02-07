#!/bin/bash
tag=V`date +%Y%m%d`
echo "Image will be tagged: $tag"

docker build --no-cache -t amunn/searchlight-base .
docker push amunn/searchlight-base:$tag
