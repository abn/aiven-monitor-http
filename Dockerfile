FROM docker.io/python:3.7

RUN pip install --upgrade pip poetry

RUN install -d /opt/source
ADD . /opt/source/

WORKDIR /opt/source

RUN poetry build -f wheel -v -n


FROM docker.io/python:3.7

COPY --from=0 /opt/source/dist/*.whl /tmp/.

RUN pip install --prefer-binary /tmp/*.whl

ENTRYPOINT ["aiven-monitor", "http"]

CMD ["--help"]