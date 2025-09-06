from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import csv
import os

app = Flask(__name__)
CORS(app)

# -----------------------
# Graph class
# -----------------------
class Graph:
    def __init__(self):
        self.vertexData = {}      # city -> index
        self.adjMatrix = []       # adjacency matrix of dicts
        self.coordinates = {}     # city -> (lat, lon)

    def addVertex(self, city, lat=None, lon=None):
        if city not in self.vertexData:
            idx = len(self.vertexData)
            self.vertexData[city] = idx
            self.coordinates[city] = (lat, lon)
            for row in self.adjMatrix:
                row.append(None)
            self.adjMatrix.append([None] * len(self.vertexData))

    def addEdge(self, src, dest, dist, time, cost):
        i, j = self.vertexData[src], self.vertexData[dest]
        self.adjMatrix[i][j] = {"distance": dist, "time": time, "cost": cost}
        self.adjMatrix[j][i] = {"distance": dist, "time": time, "cost": cost}

    def loadFromCSV(self, filename):
        with open(filename, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                src = row["source"]
                dest = row["target"]
                dist = float(row["distance_km"])
                time = float(row["time_hr"])
                cost = float(row["cost_usd"])
                src_lat = float(row["source_lat"])
                src_lon = float(row["source_lon"])
                dest_lat = float(row["target_lat"])
                dest_lon = float(row["target_lon"])

                self.addVertex(src, src_lat, src_lon)
                self.addVertex(dest, dest_lat, dest_lon)
                self.addEdge(src, dest, dist, time, cost)

    def dijkstras(self, startCity, endCity, mode="shortest"):
        n = len(self.vertexData)
        cities = list(self.vertexData.keys())
        dis = [float('inf')] * n
        pred = [-1] * n
        visited = [0] * n

        startIndex = self.vertexData[startCity]
        endIndex = self.vertexData[endCity]
        dis[startIndex] = 0

        for _ in range(n):
            minDist = float('inf')
            u = -1
            for i in range(n):
                if not visited[i] and dis[i] <= minDist:
                    minDist = dis[i]
                    u = i
            if u == -1:
                break
            visited[u] = 1
            for v in range(n):
                edge = self.adjMatrix[u][v]
                if edge and not visited[v]:
                    if mode == "shortest":
                        weight = edge["distance"]
                    elif mode == "fastest":
                        weight = edge["time"]
                    elif mode == "cheapest":
                        weight = edge["cost"]
                    else:
                        weight = edge["distance"]

                    if dis[u] + weight < dis[v]:
                        dis[v] = dis[u] + weight
                        pred[v] = u

        path = []
        current = endIndex
        while current != -1:
            path.append(cities[current])
            current = pred[current]
        path.reverse()

        total_distance, total_time, total_cost = 0, 0, 0
        for i in range(len(path) - 1):
            u = self.vertexData[path[i]]
            v = self.vertexData[path[i+1]]
            edge = self.adjMatrix[u][v]
            total_distance += edge["distance"]
            total_time += edge["time"]
            total_cost += edge["cost"]

        return {
            "path": path,
            "distance": total_distance,
            "time": total_time,
            "cost": total_cost
        }

# -----------------------
# Load graph
# -----------------------
g = Graph()
g.loadFromCSV(os.path.join(os.path.dirname(os.path.abspath(__file__)), "routes.csv"))

# -----------------------
# Flask API
# -----------------------
@app.route("/cities")
def get_cities():
    return jsonify([
        {"name": city, "lat": g.coordinates[city][0], "lon": g.coordinates[city][1]}
        for city in g.vertexData
    ])

@app.route("/shortest-path", methods=["POST"])
def shortest_path():
    data = request.json
    src = data.get("source")
    dest = data.get("destination")
    mode = data.get("mode", "shortest")
    if src not in g.vertexData or dest not in g.vertexData:
        return jsonify({"error": "Invalid city names"}), 400

    result = g.dijkstras(src, dest, mode)
    path_coords = [
        {"city": c, "lat": g.coordinates[c][0], "lon": g.coordinates[c][1]}
        for c in result["path"]
    ]
    return jsonify({
        "path": [c["city"] for c in path_coords],
        "coords": path_coords,
        "distance": result["distance"],
        "time": result["time"],
        "cost": result["cost"]
    })

# -----------------------
# Serve frontend
# -----------------------
@app.route("/")
def serve_frontend():
    return send_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend.html"))

# -----------------------
# Run Flask
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
