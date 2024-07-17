FROM harbor.tzpassport.com/ops/s2i-python:3.10.10
COPY . /opt/app-root/src
USER root
RUN cd /opt/app-root/src && sh ./build.sh && rm -rf /tmp/* && chmod +x /opt/app-root/src/start.sh
WORKDIR /opt/app-root
CMD ["/opt/app-root/src/start.sh"]