FROM python:3.9.7-slim
# copio todo menos el config.ini
COPY server/main.py /
COPY server/common /common
COPY server/tests /tests
RUN python -m unittest tests/test_common.py
ENTRYPOINT ["/bin/sh"]
