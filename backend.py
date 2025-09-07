from flask import Flask, jsonify, request, send_from_directory
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
                cost = float(row.get("cost_inr", 0))  # numeric only

                src_lat = float(row["source_lat"])
                src_lon = float(row["source_lon"])
                dest_lat = float(row["target_lat"])
                dest_lon = float(row["target_lon"])

                self.addVertex(src, src_lat, src_lon)
                self.addVertex(dest, dest_lat, dest_lon)
                self.addEdge(src, dest, dist, time, cost)

    # -----------------------
    # Dijkstra's algorithm
    # -----------------------
    def dijkstras(self, startCity, endCity, mode="shortest"):
        n = len(self.vertexData)
        cities = list(self.vertexData.keys())
        dis = [float('inf')] * n
        pred = [-1] * n
        visited = [0] * n

        startIndex = self.vertexData[startCity]
        endIndex = self.vertexData[endCity]
        dis[startIndex] = 0

        weightKey = {"shortest":"distance","fastest":"time","cheapest":"cost"}.get(mode, "distance")

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
                    weight = edge[weightKey]
                    if dis[u] + weight < dis[v]:
                        dis[v] = dis[u] + weight
                        pred[v] = u

        path = []
        current = endIndex
        while current != -1:
            path.append(cities[current])
            current = pred[current]
        path.reverse()

        if not path or path[0] != startCity:
            return {"path": [], "distance": 0, "time": 0, "cost": 0}

        total_distance, total_time, total_cost = 0, 0, 0
        for i in range(len(path)-1):
            u = self.vertexData[path[i]]
            v = self.vertexData[path[i+1]]
            edge = self.adjMatrix[u][v]
            total_distance += edge["distance"]
            total_time += edge["time"]
            total_cost += edge["cost"]

        # cost is numeric only
        return {"path": path, "distance": total_distance, "time": total_time, "cost": total_cost}

# -----------------------
# Load graphs
# -----------------------
globalGraph = Graph()
globalGraph.loadFromCSV("routes.csv")       # INR numeric

domesticGraph = Graph()
domesticGraph.loadFromCSV("routes_india.csv")  # INR numeric

# -----------------------
# Flask API
# -----------------------
@app.route("/cities")
def get_cities():
    scope = request.args.get("scope", "global")
    graph = globalGraph if scope=="global" else domesticGraph
    result = []
    for city in graph.vertexData:
        lat, lon = graph.coordinates[city]
        result.append({"name": city, "lat": lat, "lon": lon})
    return jsonify(result)

@app.route("/shortest-path", methods=["POST"])
def shortest_path():
    data = request.json
    src = data.get("source")
    dest = data.get("destination")
    mode = data.get("mode", "shortest")
    scope = data.get("scope", "global")

    graph = globalGraph if scope=="global" else domesticGraph

    if src not in graph.vertexData or dest not in graph.vertexData:
        return jsonify({"error":"Invalid city names"}), 400

    result = graph.dijkstras(src, dest, mode)
    if not result["path"]:
        return jsonify({"error":"No path found"}), 400

    return jsonify(result)

# -----------------------
# Serve frontend
# -----------------------
@app.route("/")
def serve_frontend():
    return send_from_directory(os.getcwd(), "frontend.html")

# -----------------------
# Run Flask
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
