# 1. Base Image: Use a lightweight Python version
# "slim" variants are much smaller and safer for production
FROM python:3.11-slim

# 2. Set Environment Variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files to disc
# PYTHONUNBUFFERED: Ensures logs are flushed immediately (crucial for container logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Set Work Directory
# This creates /code inside the container and sets it as the default dir
WORKDIR /code

# 4. Install Dependencies
# We copy requirements first to leverage Docker's layer caching.
# If requirements.txt hasn't changed, Docker won't re-run pip install.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 5. Copy Application Code
# This copies your local 'app' folder into '/code/app' inside the container
COPY ./app ./app

# 6. Expose the Port
# This documents that the container listens on port 8000
EXPOSE 8000

# 7. Start the Application
# "app.main:app" tells uvicorn to look in the 'app' folder, 'main' file, for the 'app' object
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]