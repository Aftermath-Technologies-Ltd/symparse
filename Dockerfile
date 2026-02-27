FROM ollama/ollama:latest

# Install python and necessary build dependencies
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv git libre2-dev

WORKDIR /app

# Create a virtual environment and install symparse
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project files
COPY . /app
RUN pip install setuptools wheel pybind11
# Install without build isolation to use system libre2
RUN CFLAGS="-I$(python -c 'import pybind11; print(pybind11.get_include())')" pip install google-re2==1.0.0 --no-build-isolation
RUN pip install .

# Script to start ollama, pull gemma3:1b, and wait for tail -f ready state
RUN echo '#!/bin/bash\n\
ollama serve &\n\
sleep 5\n\
ollama pull gemma3:1b\n\
echo "Ready! You can now pipe logs into symparse."\n\
tail -f /dev/null' > /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
