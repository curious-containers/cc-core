FROM docker.io/debian:9.5-slim

RUN apt-get update \
&& apt-get install -y curl python3-pip python3-venv \
&& useradd -ms /bin/bash cc

USER cc

ENV PATH="/home/cc/.local/bin:/home/cc/.poetry/bin:${PATH}"
ENV PYTHONPATH="/home/cc/.local/lib/python3.5/site-packages/"

RUN mkdir -p /home/cc/.local/bin && \
ln -s $(which python3) /home/cc/.local/bin/python && \
curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

ADD --chown=cc:cc . /opt/cc-core

# install cc-core
RUN cd /opt/cc-core \
&& poetry build --format=wheel \
&& pip3 install --no-input --user dist/*.whl
