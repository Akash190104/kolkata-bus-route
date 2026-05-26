#!/usr/bin/env python3
"""
Interactive Geocoding Helper for Kolkata Bus Route
--------------------------------------------------
Identifies popular stops without geocoded coordinates, opens map searches in the browser,
parses pasted coordinates/URLs, updates build.py, and rebuilds project data.
"""
import os
import sys
import json
import re
import subprocess
import webbrowser
import urllib.parse

def extract_coordinates(text):
    text = text.strip()
    if not text:
        return None
    
    # 1. Google maps URL @lat,lng
    gmaps_match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", text)
    if gmaps_match:
        return float(gmaps_match.group(1)), float(gmaps_match.group(2))
        
    # 2. General URL query parameter like q=lat,lng or query=lat,lng
    query_match = re.search(r"[?&](?:q|query|loc|location)=(-?\d+\.\d+),(-?\d+\.\d+)", text)
    if query_match:
        return float(query_match.group(1)), float(query_match.group(2))

    # 3. Path segments with coordinates: /search/lat,lng or /place/lat,lng
    path_match = re.search(r"/(?:search|place|maps)/(-?\d+\.\d+),\+?(-?\d+\.\d+)", text)
    if path_match:
        return float(path_match.group(1)), float(path_match.group(2))
        
    # 4. Standard coords matching: Lat, Lng
    coords_match = re.search(r"(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)", text)
    if coords_match:
        return float(coords_match.group(1)), float(coords_match.group(2))
        
    # 5. Space separated: Lat Lng
    space_match = re.search(r"(-?\d+\.\d+)\s+(-?\d+\.\d+)", text)
    if space_match:
        lat, lng = float(space_match.group(1)), float(space_match.group(2))
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return lat, lng
            
    return None

def self_test():
    test_cases = [
        ("22.5807963, 88.2616239", (22.5807963, 88.2616239)),
        ("  -22.58,   -88.26   ", (-22.58, -88.26)),
        ("https://www.google.com/maps/place/Santragachi+Junction/@22.5807963,88.2616239,15z/data=!4m6!", (22.5807963, 88.2616239)),
        ("https://www.google.com/maps/@22.123,88.456,12z", (22.123, 88.456)),
        ("https://www.openstreetmap.org/search?query=22.789,88.987", (22.789, 88.987)),
        ("22.1234 88.5678", (22.1234, 88.5678)),
    ]
    for text, expected in test_cases:
        res = extract_coordinates(text)
        if not res or abs(res[0] - expected[0]) > 1e-6 or abs(res[1] - expected[1]) > 1e-6:
            raise AssertionError(f"Self-test failed for '{text}'. Expected {expected}, got {res}")

def update_build_py(stop_name, lat, lng):
    with open("build.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    target = "HUB = {"
    if target not in content:
        print("Error: Could not find 'HUB = {' in build.py")
        return False
    
    # Format the entry to match existing structure
    entry = f'\n  "{stop_name}":[{lat:.4f},{lng:.4f}],'
    
    new_content = content.replace(target, target + entry, 1)
    
    with open("build.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    return True

def main():
    self_test()
    
    if not os.path.exists("busdata.json"):
        print("busdata.json not found. Running build.py to generate it first...")
        subprocess.run([sys.executable, "build.py"], check=True)
        
    with open("busdata.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    stops = data.get("stops", [])
    un_geocoded = [s for s in stops if s.get("lat") is None]
    
    if not un_geocoded:
        print("All stops are already geocoded! Nothing to do.")
        return
        
    print(f"Found {len(un_geocoded)} un-geocoded stops out of {len(stops)} total stops.\n")
    
    # Specific stop geocoding search loop
    while True:
        print("Do you want to geocode a specific stop? Type in the name or press enter")
        specific_stop = input("> ").strip()
        if not specific_stop:
            break
            
        # Search all stops in the dataset
        matches = [s for s in stops if specific_stop.lower() in s["name"].lower()]
        if not matches:
            print(f"No stops found matching '{specific_stop}'. Please try again.\n")
            continue
            
        selected_stop = None
        if len(matches) == 1:
            selected_stop = matches[0]
        else:
            print(f"Found {len(matches)} matching stops:")
            limit = 15
            for i, match in enumerate(matches[:limit]):
                status = "geocoded" if match.get("lat") is not None else "missing coords"
                print(f"  {i+1}) {match['name']} ({match['routes']} routes, {status})")
            if len(matches) > limit:
                print(f"  ... and {len(matches) - limit} more matching stops.")
                
            while True:
                choice = input(f"Select a stop number (1-{min(len(matches), limit)}) or press Enter to search again: ").strip()
                if not choice:
                    break
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < min(len(matches), limit):
                        selected_stop = matches[idx]
                        break
                    else:
                        print("Invalid selection.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            
        if selected_stop:
            name = selected_stop["name"]
            status_text = "geocoded" if selected_stop.get("lat") is not None else "missing coords"
            print(f"\nGeocoding selected stop: '{name}' ({selected_stop['routes']} routes, status: {status_text})")
            
            # Build search query for Kolkata location
            query = f"Kolkata {name}"
            gmaps_url = f"https://www.google.com/maps/search/{urllib.parse.quote_plus(query)}"
            osm_url = f"https://www.openstreetmap.org/search?query={urllib.parse.quote_plus(query)}"
            
            print(f"  Google Maps: {gmaps_url}")
            print(f"  OpenStreetMap: {osm_url}")
            
            try:
                webbrowser.open(gmaps_url)
            except Exception as e:
                print(f"  (Could not open browser: {e})")
                
            while True:
                ans = input("  Paste coordinates or URL (or Enter to cancel): ").strip()
                if not ans:
                    print("  Cancelled.\n")
                    break
                
                coords = extract_coordinates(ans)
                if coords:
                    lat, lng = coords
                    print(f"  Parsed coordinates: Lat: {lat:.6f}, Lng: {lng:.6f}")
                    
                    if update_build_py(name, lat, lng):
                        print("  Updated build.py with new coordinates.")
                        try:
                            print("  Rebuilding project data...")
                            subprocess.run([sys.executable, "build.py"], check=True)
                            print("  Successfully rebuilt and updated HTML files!\n")
                            # Reload stops data
                            with open("busdata.json", "r", encoding="utf-8") as f:
                                data = json.load(f)
                            stops = data.get("stops", [])
                            # Also update un_geocoded so the standard flow doesn't repeat this stop
                            un_geocoded = [s for s in stops if s.get("lat") is None]
                        except subprocess.CalledProcessError as e:
                            print(f"  Warning: build.py failed after update: {e}\n")
                    break
                else:
                    print("  Invalid coordinates or URL format. Please try again.")

    if not un_geocoded:
        print("All stops are already geocoded! Nothing to do.")
        return

    print("Starting interactive geocoding for remaining stops. For each stop, a browser tab will open.")
    print("Copy the coordinates or URL and paste here. Press Enter to skip, 'q' to quit.\n")
    
    for idx, stop in enumerate(un_geocoded):
        name = stop["name"]
        routes_count = stop["routes"]
        
        print(f"[{idx+1}/{len(un_geocoded)}] Stop: '{name}' ({routes_count} routes)")
        
        # Build search query for Kolkata location
        query = f"Kolkata {name}"
        gmaps_url = f"https://www.google.com/maps/search/{urllib.parse.quote_plus(query)}"
        osm_url = f"https://www.openstreetmap.org/search?query={urllib.parse.quote_plus(query)}"
        
        print(f"  Google Maps: {gmaps_url}")
        print(f"  OpenStreetMap: {osm_url}")
        
        try:
            webbrowser.open(gmaps_url)
        except Exception as e:
            print(f"  (Could not open browser: {e})")
            
        while True:
            ans = input("  Paste coordinates or URL (or Enter to skip, 'q' to quit): ").strip()
            if not ans:
                print("  Skipped.\n")
                break
            if ans.lower() == 'q':
                print("Exiting.")
                return
                
            coords = extract_coordinates(ans)
            if coords:
                lat, lng = coords
                print(f"  Parsed coordinates: Lat: {lat:.6f}, Lng: {lng:.6f}")
                
                if update_build_py(name, lat, lng):
                    print("  Updated build.py with new coordinates.")
                    try:
                        print("  Rebuilding project data...")
                        subprocess.run([sys.executable, "build.py"], check=True)
                        print("  Successfully rebuilt and updated HTML files!\n")
                        # Reload stops data
                        with open("busdata.json", "r", encoding="utf-8") as f:
                            data = json.load(f)
                        stops = data.get("stops", [])
                    except subprocess.CalledProcessError as e:
                        print(f"  Warning: build.py failed after update: {e}\n")
                break
            else:
                print("  Invalid coordinates or URL format. Please try again.")

if __name__ == "__main__":
    main()
