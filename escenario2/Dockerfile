FROM node:18-alpine

RUN apk add --no-cache bash python3

RUN npm install -g --unsafe-perm node-red

WORKDIR /data

ENV FLOWS=/data/flows.json
ENV NODE_RED_ENABLE_PROJECTS=false
EXPOSE 1880

CMD ["node-red", "--userDir", "/data", "flows.json"]
