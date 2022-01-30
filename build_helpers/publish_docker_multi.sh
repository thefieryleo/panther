#!/bin/sh

# The below assumes a correctly setup docker buildx environment

# Replace / with _ to create a valid tag
TAG=$(echo "${BRANCH_NAME}" | sed -e "s/\//_/g")
TAG_PLOT=${TAG}_plot
TAG_PI="${TAG}_pi"

PI_PLATFORM="linux/arm/v7"
echo "Running for ${TAG}"
CACHE_IMAGE=pantherorg/panther_cache
CACHE_TAG=${CACHE_IMAGE}:${TAG_PI}_cache

# Add commit and commit_message to docker container
echo "${GITHUB_SHA}" > panther_commit

if [ "${GITHUB_EVENT_NAME}" = "schedule" ]; then
    echo "event ${GITHUB_EVENT_NAME}: full rebuild - skipping cache"
    # Build regular image
    docker build -t panther:${TAG} .
    # Build PI image
    docker buildx build \
        --cache-to=type=registry,ref=${CACHE_TAG} \
        -f docker/Dockerfile.armhf \
        --platform ${PI_PLATFORM} \
        -t ${IMAGE_NAME}:${TAG_PI} --push .
else
    echo "event ${GITHUB_EVENT_NAME}: building with cache"
    # Build regular image
    docker pull ${IMAGE_NAME}:${TAG}
    docker build --cache-from ${IMAGE_NAME}:${TAG} -t panther:${TAG} .

    # Pull last build to avoid rebuilding the whole image
    # docker pull --platform ${PI_PLATFORM} ${IMAGE_NAME}:${TAG}
    docker buildx build \
        --cache-from=type=registry,ref=${CACHE_TAG} \
        --cache-to=type=registry,ref=${CACHE_TAG} \
        -f docker/Dockerfile.armhf \
        --platform ${PI_PLATFORM} \
        -t ${IMAGE_NAME}:${TAG_PI} --push .
fi

if [ $? -ne 0 ]; then
    echo "failed building multiarch images"
    return 1
fi
# Tag image for upload and next build step
docker tag panther:$TAG ${CACHE_IMAGE}:$TAG

docker build --cache-from panther:${TAG} --build-arg sourceimage=${CACHE_IMAGE} --build-arg sourcetag=${TAG} -t panther:${TAG_PLOT} -f docker/Dockerfile.plot .

docker tag panther:$TAG_PLOT ${CACHE_IMAGE}:$TAG_PLOT

# Run backtest
docker run --rm -v $(pwd)/config_examples/config_bittrex.example.json:/panther/config.json:ro -v $(pwd)/tests:/tests panther:${TAG} backtesting --datadir /tests/testdata --strategy-path /tests/strategy/strats/ --strategy StrategyTestV2

if [ $? -ne 0 ]; then
    echo "failed running backtest"
    return 1
fi

docker images

docker push ${CACHE_IMAGE}
docker push ${CACHE_IMAGE}:$TAG_PLOT
docker push ${CACHE_IMAGE}:$TAG


docker images

if [ $? -ne 0 ]; then
    echo "failed building image"
    return 1
fi
