#!/usr/bin/env bash
#
# refresh_db.sh
#
# Deletes all documents in a specific collection (preserving the DB),
# then re-imports JSON from host to Mongo container using mongosh.

########################
# CONFIGURATION
########################

# Name or ID of your running MongoDB container
CONTAINER_NAME="mymongo"

# Name of the MongoDB database you want to refresh
DB_NAME="cigarsDB"

# Name of the collection to re-import
COLLECTION_NAME="cigars"

# Local path on your HOST containing JSON files (e.g., page_1.json, page_2.json, etc.)
DATA_FOLDER="brand_data"

########################
# STEP 1: CLEAR THE COLLECTION
########################

echo "=== Deleting all documents from $DB_NAME.$COLLECTION_NAME (keeping the DB itself) ==="
docker exec -i "$CONTAINER_NAME" bash -c "\
  mongosh --eval '
      use $DB_NAME;
      db.$COLLECTION_NAME.deleteMany({});
      print(\"Deleted all docs from $DB_NAME.$COLLECTION_NAME\");
  '
"
echo "=== Done. All documents deleted from $DB_NAME.$COLLECTION_NAME. ==="

########################
# STEP 2: RE-IMPORT JSON
########################

echo "=== Re-importing JSON files from host ($DATA_FOLDER) to container ($CONTAINER_NAME) ==="

for json_file in "$DATA_FOLDER"/*.json; do
  if [[ -f "$json_file" ]]; then
    echo ">>> Found JSON file: $json_file"
    filename="$(basename "$json_file")"

    # Copy the file into the container's /tmp/ directory
    docker cp "$json_file" "$CONTAINER_NAME":/tmp/

    # Use 'mongosh' to run 'mongoimport' inside the container
    echo ">>> Importing $filename into $DB_NAME.$COLLECTION_NAME ..."
    docker exec -i "$CONTAINER_NAME" bash -c "\
      mongoimport --db $DB_NAME --collection $COLLECTION_NAME --file /tmp/$filename --jsonArray
    "
    echo ">>> Finished importing $filename."
  fi
done

echo "=== All JSON files imported successfully! ==="
