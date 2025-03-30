FROM python:3.9-alpine

WORKDIR /app

# Install required packages for compiling Python packages
RUN apk add --no-cache gcc musl-dev jpeg-dev zlib-dev libjpeg

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py .
COPY config/ app/config
COPY templates /app/templates
COPY static /app/static

# 设置容器时间，有的容器时区与我们的时区不同，可能会带来麻烦
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone 

# Expose port for web access
EXPOSE 8080

# Create necessary directories
RUN mkdir -p /app/buspic /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the web server
CMD ["python", "webserver.py"] 