ARG sourceimage=freqtradeorg/freqtrade
ARG sourcetag=develop
FROM ${sourceimage}:${sourcetag}

# Install dependencies
COPY requirements-plot.txt /panther/

RUN pip install -r requirements-plot.txt --user --no-cache-dir
