import math
from typing import List, Dict, Any, Tuple
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in kilometers."""
    radius = 6371.0  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(radius * c, 2)

def optimize_refill_route(atms_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Optimize replenishment route starting from Depot, visiting all ATMs, and returning to Depot using Google OR-Tools."""
    if not atms_data:
        return {
            "route": ["Central Cash Depot", "Central Cash Depot"],
            "steps": [
                {"step": 1, "title": "Start at Central Cash Depot", "atm_id": None, "location": "Depot", "leg_distance_km": 0.0},
                {"step": 2, "title": "Return to Central Cash Depot", "atm_id": None, "location": "Depot", "leg_distance_km": 0.0}
            ],
            "total_distance_km": 0.0,
            "estimated_time_mins": 0,
            "atms_count": 0
        }

    # Calculate Depot location at centroid of ATMs with small offset for realism
    avg_lat = sum(a["latitude"] for a in atms_data) / len(atms_data)
    avg_lon = sum(a["longitude"] for a in atms_data) / len(atms_data)
    depot = {
        "atm_id": "DEPOT",
        "title": "Central Cash Depot",
        "location": "Regional Currency Vault",
        "latitude": round(avg_lat + 0.02, 4),
        "longitude": round(avg_lon + 0.02, 4),
    }

    locations = [depot] + atms_data
    n_nodes = len(locations)

    # Build integer distance matrix in decameters (10m units) for OR-Tools solver
    distance_matrix = []
    distance_matrix_km = []
    for i in range(n_nodes):
        row_int = []
        row_km = []
        for j in range(n_nodes):
            if i == j:
                row_int.append(0)
                row_km.append(0.0)
            else:
                dist = haversine_distance_km(
                    locations[i]["latitude"], locations[i]["longitude"],
                    locations[j]["latitude"], locations[j]["longitude"]
                )
                row_km.append(dist)
                row_int.append(int(dist * 100))
        distance_matrix.append(row_int)
        distance_matrix_km.append(row_km)

    # Set up OR-Tools Routing Model
    manager = pywrapcp.RoutingIndexManager(n_nodes, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    solution = routing.SolveWithParameters(search_parameters)

    # Construct ordered route steps
    steps = []
    route_labels = []
    total_km = 0.0
    step_num = 1

    if solution:
        index = routing.Start(0)
        prev_node = 0
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            loc = locations[node_index]
            leg_dist = distance_matrix_km[prev_node][node_index]
            total_km += leg_dist

            if node_index == 0:
                title = "Depot (Start: Regional Currency Vault)"
                route_labels.append("Depot")
            else:
                title = f"{loc['atm_id']} - {loc.get('city', '')} ({loc.get('site_type', 'Branch')})"
                route_labels.append(loc["atm_id"])

            steps.append({
                "step": step_num,
                "title": title,
                "atm_id": loc["atm_id"] if node_index != 0 else None,
                "location": loc.get("location") or loc.get("city", "Depot"),
                "leg_distance_km": round(leg_dist, 2)
            })
            step_num += 1
            prev_node = node_index
            index = solution.Value(routing.NextVar(index))

        # Final return to Depot
        leg_dist = distance_matrix_km[prev_node][0]
        total_km += leg_dist
        route_labels.append("Depot")
        steps.append({
            "step": step_num,
            "title": "Depot (Return: Regional Currency Vault)",
            "atm_id": None,
            "location": "Depot",
            "leg_distance_km": round(leg_dist, 2)
        })
    else:
        # Fallback sequential order if solver fails
        route_labels = ["Depot"] + [a["atm_id"] for a in atms_data] + ["Depot"]
        prev_lat, prev_lon = depot["latitude"], depot["longitude"]
        steps.append({
            "step": 1,
            "title": "Depot (Start)",
            "atm_id": None,
            "location": "Depot",
            "leg_distance_km": 0.0
        })
        for idx, a in enumerate(atms_data, start=2):
            leg = haversine_distance_km(prev_lat, prev_lon, a["latitude"], a["longitude"])
            total_km += leg
            steps.append({
                "step": idx,
                "title": f"{a['atm_id']} - {a.get('city', '')}",
                "atm_id": a["atm_id"],
                "location": a.get("city", "City"),
                "leg_distance_km": leg
            })
            prev_lat, prev_lon = a["latitude"], a["longitude"]
        leg = haversine_distance_km(prev_lat, prev_lon, depot["latitude"], depot["longitude"])
        total_km += leg
        steps.append({
            "step": len(atms_data) + 2,
            "title": "Depot (Return)",
            "atm_id": None,
            "location": "Depot",
            "leg_distance_km": leg
        })

    # Estimate travel time: 35 km/h driving speed + 15 mins cash replenishment per ATM
    driving_minutes = int((total_km / 35.0) * 60)
    service_minutes = len(atms_data) * 15
    total_time_mins = driving_minutes + service_minutes

    return {
        "route": route_labels,
        "steps": steps,
        "total_distance_km": round(total_km, 1),
        "estimated_time_mins": total_time_mins,
        "atms_count": len(atms_data)
    }
