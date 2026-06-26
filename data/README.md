# MuleShield AI Data Directory

## Overview
This directory contains the training dataset for the MuleShield AI fraud detection system.

## Required File
- **DataSet.csv**: The anonymized banking transaction dataset (9,082 rows × 3,924 features)

## Setup Instructions

1. **Copy the dataset to this directory:**
   ```bash
   cp /path/to/DataSet.csv ./data/DataSet.csv
   ```

2. **Verify the file exists:**
   ```bash
   ls -lh data/DataSet.csv
   ```

3. **Start the system:**
   ```bash
   docker compose up --build
   ```

The training pipeline will automatically detect and use this file during the initial model training.

## File Format
- CSV format with header row
- 9,082 rows (transactions)
- 3,924 columns (anonymized features F1-F3924)
- Label column: F610 (fraud indicator)

## Security Note
This directory is mounted as **read-only** in Docker containers to prevent accidental modification of the source dataset.

## Volume Mounting
In docker-compose.yml:
```yaml
volumes:
  - ./data:/data:ro  # ro = read-only
```
