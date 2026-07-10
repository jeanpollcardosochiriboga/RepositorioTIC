FROM nodered/node-red:4.1.10

USER root
RUN apk add --no-cache openssh-client sshpass
USER node-red
RUN cd /usr/src/node-red && npm install --no-audit --no-fund node-red-dashboard
