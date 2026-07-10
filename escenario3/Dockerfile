FROM node:18-alpine

RUN apk add --no-cache bash python3

RUN npm install -g --unsafe-perm node-red && \
    cd /usr/local/lib/node_modules/node-red && \
    npm install --unsafe-perm node-red-dashboard

WORKDIR /data

ENV FLOWS=/data/flows.json
ENV NODE_RED_ENABLE_PROJECTS=false
EXPOSE 1880

CMD ["node-red", "--userDir", "/data", "flows.json"]
