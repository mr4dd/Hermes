# Hermes

Hermes is an automated image processing pipeline that uses Large Multimodal Models (LMM) to analyze images, generate detailed text descriptions, and store high-dimensional embeddings in a local database for semantic search capabilities.

## Overview

The system performs the following workflow:

1. Scans a specified directory for images.
2. Generates a SHA-256 hash for each file to ensure unique identification.
3. Utilizes Ollama to generate detailed descriptive text for every image.
4. Stores these descriptions and hashes in an SQLite database.
5. Automatically generates vector embeddings for all stored descriptions to facilitate similarity search.

## Features

- Multimodal processing via Ollama.
- Automatic batching and transaction management for database integrity.
- Progress tracking using tqdm for large datasets.
- Vector embedding generation for efficient retrieval.
- Customizable system prompts for description generation.

## Requirements

- Python 3.x
- Ollama installed on the host machine.

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/mr4dd/Hermes
    cd Hermes
    ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run Hermes:

    ```bash
    python src/main.py --database <path_to_db> --dir <path_to_images> --model <model_name>
    ```

## Configuration

The system uses environment variables for configuration. You can set these in a `.env` file or directly in your shell environment:

- `SYSTEM_PROMPT`: The instructions given to the model (e.g., "describe what's in the image in as much detail as possible").

### Arguments:

- `--database`: The file path for the SQLite database (e.g., `data.db`).
- `--dir`: The directory containing images to be processed and indexed.
- `--model`: The name of the LLM as specified in ollama's model list.

## Data Structure

The system populates two primary tables in the SQLite database:

1. **classifications**: Stores `filename`, `hash` (SHA256), and the generated `description`.
2. **embeddings**: Stores the vector embeddings corresponding to each entry in the classification table.

## Licence

This project is licensed under [AGPL-3.0 License](LICENSE.md)