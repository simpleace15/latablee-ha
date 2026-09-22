ARG BUILD_FROM=ghcr.io/home-assistant/base:3.19

FROM ${BUILD_FROM}

# jq for reading /data/options.json (bashio needs hassio_api; jq does not)
RUN apk add --no-cache nginx jq

COPY run.sh /run.sh
COPY nginx.conf /etc/nginx/latablee.conf
RUN chmod a+x /run.sh

LABEL \
    io.hass.type="app" \
    io.hass.arch="aarch64,amd64,armv7"

CMD [ "/run.sh" ]