FROM docker.io/debian:9.3-slim

RUN apt-get update \
&& apt-get install -y python3-pip python3-venv \
&& useradd -ms /bin/bash cc

USER cc

ENV PATH="/home/cc/.local/bin:${PATH}"
ENV PYTHONPATH="/home/cc/.local/lib/python3.5/site-packages/"

RUN pip3 install --no-input --user poetry

ADD --chown=cc:cc . /opt/cc-core

# install cc-core
RUN cd /opt/cc-core \
&& poetry build --format=wheel \
&& pip3 install --no-input --user dist/*.whl
