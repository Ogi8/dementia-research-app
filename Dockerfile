FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./
COPY .python-version ./

# Install dependencies using uv
RUN uv sync --no-dev

# Copy application code
COPY app ./app
COPY static ./static

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
