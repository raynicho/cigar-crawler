# Project Name

A Python-based cigar data scraper and MongoDB data pipeline.  
Scrapes cigar brand pages, writes JSON data, and stores results in MongoDB.

## Table of Contents

1. [Overview](#overview)  
2. [Prerequisites](#prerequisites)  
3. [Installation](#installation)  
   - [Install Python 3.10+ (macOS/Linux)](#install-python-310-macoslinux)  
   - [Set Up a Virtual Environment (Optional)](#set-up-a-virtual-environment-optional)  
   - [Install Dependencies](#install-dependencies)  
4. [Run MongoDB via Docker](#run-mongodb-via-docker)  
5. [Run the Scraping Script](#run-the-scraping-script)  
6. [Refresh the MongoDB (Optional)](#refresh-the-mongodb-optional)
7. [Connect & Query Mongo with `mongosh`](#connect--query-mongo-with-mongosh)
8. [FAQ & Troubleshooting](#faq--troubleshooting)

---

## Overview

This project automates:

1. **Scraping** [https://www.cigarpage.com/brands](https://www.cigarpage.com/brands) and various brand pages to collect cigar data.  
2. **Saving** HTML for debugging in `html_debug/` and JSON output in `brand_data/`.  
3. **Storing** the final data in a local MongoDB instance, which runs inside a Docker container.

You can extend or customize the brand scraping list, concurrency settings, or the MongoDB pipeline as needed.

---

## Prerequisites

- **macOS or Linux** (the steps below assume a Unix-like shell).
- **Python** 3.10+ (some libraries may break on older versions).
- **Docker** (to run MongoDB easily).
- **Chrome** installed (or a Chromium-based browser), because the scraping script uses [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected_chromedriver).

---

## Installation

### Install Python 3.10+ (macOS/Linux)

**macOS**  
- Via [Homebrew](https://brew.sh/):
  ```bash
  brew install python@3.11
  ```

***Linux (Ubuntu/Debian)***

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip
```

Check:

```bash
python3 --version
```

Should be >= 3.10.

### Set Up a Virtual Environment (Optional)

Create a virtual environment named venv:

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

### Install Dependencies

Inside the project folder (with venv activated if you use one), run:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If you don’t have a requirements.txt or want to install manually:

```bash
pip install \
  undetected-chromedriver \
  selenium \
  beautifulsoup4 \
  requests \
  ...
```

Note: If you plan to use concurrency, concurrent.futures is part of the Python standard library (no separate install needed).

## Run MongoDB via Docker

Install Docker (macOS: Docker Desktop; Linux: see official Docker docs).

Start Docker (macOS: launch Docker Desktop, wait until “Docker is running”).

Pull & run Mongo:

```bash
docker run --name mymongo -p 27017:27017 -d mongo:latest
```

Container name: mymongo
Exposes port 27017 on localhost
Check if Mongo is running:

```bash
docker ps
```

You should see mymongo listed.

## Run the Scraping Script

For example, if your Python script is named main.py:

Make sure you have Chrome installed and Docker container mymongo running.

Run:

```bash
python main.py
```

or, if it has a shebang and is executable:

```bash
./main.py
```

What it does:

Creates multiple Selenium drivers (using undetected-chromedriver).
Visits https://www.cigarpage.com/brands, scrolls to load brand links.
Filters brand links (e.g., “Arturo Fuente”, “Drew Estate”).
For each brand, spawns a thread, saves HTML in html_debug/, and writes JSON in brand_data/.


## Refresh the MongoDB (Optional)

(Optional) You might then import the JSON into Mongo manually or via a separate script.

If you have a script (e.g., refresh_db.sh or refresh_db.py) that:

Clears out the existing data in your MongoDB collections.
Re-imports all JSON from brand_data/*.json.
Example refresh_db.sh usage:

Make it executable:

```bash
chmod +x refresh_db.sh
```

Run:

```bash
./refresh_db.sh
```

It might do something like:

```
mongosh to delete all documents in cigarsDB.cigars.
docker cp JSON files to the container.
mongoimport each file.
```

## Connect & Query Mongo with `mongosh`

Once your Docker container (mymongo) is running MongoDB, you can:

Enter the container (where mongosh is available by default in newer images) or install mongosh on your host machine.

If you want to run queries from inside the container:

bash
Copy code
docker exec -it mymongo bash

Now inside the container:

mongosh

If you installed mongosh on your host (and the container port is published):

```bash
mongosh "mongodb://localhost:27017"
```

Switch to the cigarsDB database:

```js
use cigarsDB
```

```js
show collections
db.cigars.count()
```

Find one document:

```js
db.cigars.findOne()
```

This returns a single random cigar document (so you can see field names).

Search by brand name (e.g. partial match "Hemingway"):

```js
db.cigars.find({ Name: /Hemingway/i }).pretty()
```

The `/Hemingway/i` is a regular expression for case-insensitive matching in the Name field.
You can also filter by price, pack, etc., depending on your data structure.

Use these queries to validate your data imports and quickly inspect results. If you see no data, confirm your import steps or check for errors.

## FAQ & Troubleshooting

Q1: I get FileNotFoundError: /Users/.../undetected_chromedriver/...

This can happen if undetected-chromedriver can’t properly download or patch ChromeDriver on macOS (especially Apple Silicon).
Solution: Provide a manually downloaded ChromeDriver to uc.Chrome(driver_executable_path="...").
Q2: I get bash: mongo: command not found

Newer official Mongo Docker images might only have mongosh or none of the old CLI tools.
Solution: Use mongosh instead of mongo, or install the needed tools in the container.
Q3: The data never shows up in cigarsDB.cigars

Possibly missing --jsonArray in mongoimport, or your JSON is empty.
Solution: Double-check the JSON file format, import logs, and confirm no errors reported.
Q4: Cloudflare blocks me

The site might detect automation if you run too many parallel requests quickly.
Solution: Increase wait times, reduce MAX_THREADS, or use a rotating proxy.
