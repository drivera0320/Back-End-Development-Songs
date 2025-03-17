from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

@app.route("/health", methods=["GET"])
def health():
    return {"status":"OK"}, 200

@app.route("/count", methods=["GET"])
def count():
    count = db.songs.count_documents({})
    return jsonify({"count": count}), 200

@app.route("/song", methods=["GET"])
def songs():
    try:
        list_songs = list(db.songs.find({}))
        return json_util.dumps({"songs": list_songs}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/song/<id>", methods=["GET"])
def get_song_by_id(id):
    try:
        song = db.songs.find_one({"id": int(id)})
        if not song:
            return jsonify({"message": f"song with id '{id}' not found"}), 400
        return json_util.dumps(song), 200

    except Exception as e:
        print(f"Error fetching song with id {id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/song", methods=["POST"])
def create_song():
    try:
        song_data = request.get_json()
        
        if not song_data or "id" not in song_data:
            return jsonify({"error": "Missing 'id' in request body"}), 400

        song_id = int(song_data["id"])

        if db.songs.find_one({"id": song_id}):
            return jsonify({"Message": f"song with id {song_id} already present"}), 302
        
        result = db.songs.insert_one(song_data)

        return jsonify({"inserted_id": str(result.inserted_id)}), 201

    except ValueError:
        return jsonify({"error": "Invalid ID format. Must be an integer."}), 400
    except Exception as e:
        print(f"Error creating song with id {id}: {e}")
        return jsonify({"error": str(e)}), 500
            

@app.route("/song/<id>", methods=["PUT"])
def update_song(id):
    try:
        song_id = int(id)
        update_data = request.get_json()

        if not update_data:
            return jsonify({"error": "No JSON payload provided"}), 400

        result = db.songs.update_one(
            {"id": song_id},          # Filter
            {"$set": update_data}     # Update
        )
        
        if result.matched_count == 0:
            return jsonify({"message": "song not found"}), 404
        
        updated_song = db.songs.find_one({"id": song_id})

        if "_id" in updated_song:
            updated_song["_id"] = str(updated_song["_id"])

        return jsonify(updated_song), 200

    except ValueError:
        return jsonify({"error": "Invalid ID format. Must be an integer."}), 400
    except Exception as e:
        print(f"Error creating song with id {id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    try:
        result = db.songs.delete_one({"id": id})

        if result.deleted_count == 0:
            return jsonify({"message": "song not found"}), 404

        return '', 204

    except Exception as e:
        print(f"Error deleting song with id {id}: {e}")
        return jsonify({"error": str(e)}), 500

