FROM python:3.8-alpine
COPY build/requirements.txt /.
RUN apk add python3-dev
RUN apk add libffi-dev
RUN apk add openssl-dev
RUN apk add build-base
RUN pip3 install -r /requirements.txt
ADD .jupiter /cosmos/jupiter
ADD bin /cosmos/sirius/bin
ADD lib /cosmos/sirius/lib
ADD api /cosmos/sirius/api
ADD __init__.py /cosmos/sirius/__init__.py
ADD config /cosmos/sirius/config
RUN touch /cosmos/__init__.py
ENV PYTHONPATH /cosmos
WORKDIR /cosmos/sirius
CMD ["python3", "bin/app.py"]
#CMD tail -f /dev/null
