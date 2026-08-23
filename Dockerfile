FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends bluez dbus \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY kingsmith_walkingpad ./kingsmith_walkingpad
RUN pip install --no-cache-dir .

EXPOSE 8080
ENV WALKINGPAD_HOST=0.0.0.0
ENV WALKINGPAD_PORT=8080

# --demo is the safe default in containers without a radio.
# Override the command to pass --address AA:BB:CC:DD:EE:FF on a host with BLE.
CMD ["sh", "-c", "walkingpad serve --host ${WALKINGPAD_HOST} --port ${WALKINGPAD_PORT} --demo"]
