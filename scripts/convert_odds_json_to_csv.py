#!/usr/bin/env python3
"""Convert odds JSON to CSV format for easy lookup."""

import json
import csv
from pathlib import Path
from datetime import datetime


def convert_odds_to_csv(json_path: str, csv_path: str):
    """Convert odds JSON file to CSV format.
    
    Args:
        json_path: Path to input JSON file
        csv_path: Path to output CSV file
    """
    # Load JSON data
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Prepare CSV rows
    rows = []
    
    for game in data:
        game_id = game['id']
        commence_time = game['commence_time']
        home_team = game['home_team']
        away_team = game['away_team']
        
        # Parse date for better readability
        game_date = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
        game_date_str = game_date.strftime('%Y-%m-%d %H:%M')
        
        # Process each bookmaker
        for bookmaker in game['bookmakers']:
            bookmaker_name = bookmaker['title']
            
            # Initialize odds variables
            home_moneyline = away_moneyline = None
            home_spread = away_spread = None
            home_spread_price = away_spread_price = None
            over_total = under_total = None
            over_price = under_price = None
            total_points = None
            
            # Extract odds from markets
            for market in bookmaker['markets']:
                if market['key'] == 'h2h':
                    # Moneyline odds
                    for outcome in market['outcomes']:
                        if outcome['name'] == home_team:
                            home_moneyline = outcome['price']
                        elif outcome['name'] == away_team:
                            away_moneyline = outcome['price']
                
                elif market['key'] == 'spreads':
                    # Spread odds
                    for outcome in market['outcomes']:
                        if outcome['name'] == home_team:
                            home_spread = outcome.get('point')
                            home_spread_price = outcome['price']
                        elif outcome['name'] == away_team:
                            away_spread = outcome.get('point')
                            away_spread_price = outcome['price']
                
                elif market['key'] == 'totals':
                    # Over/Under totals
                    for outcome in market['outcomes']:
                        if outcome['name'] == 'Over':
                            over_price = outcome['price']
                            total_points = outcome.get('point')
                        elif outcome['name'] == 'Under':
                            under_price = outcome['price']
            
            # Create row
            row = {
                'game_id': game_id,
                'game_date': game_date_str,
                'home_team': home_team,
                'away_team': away_team,
                'bookmaker': bookmaker_name,
                'home_moneyline': home_moneyline,
                'away_moneyline': away_moneyline,
                'home_spread': home_spread,
                'home_spread_price': home_spread_price,
                'away_spread': away_spread,
                'away_spread_price': away_spread_price,
                'total_points': total_points,
                'over_price': over_price,
                'under_price': under_price,
            }
            rows.append(row)
    
    # Write to CSV
    if rows:
        fieldnames = rows[0].keys()
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"✓ Converted {len(data)} games with {len(rows)} bookmaker entries")
        print(f"✓ CSV saved to: {csv_path}")
    else:
        print("No data to write")


if __name__ == '__main__':
    # Define paths
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    json_path = project_dir / 'data' / 'odds.json'
    csv_path = project_dir / 'data' / 'odds.csv'
    
    # Convert
    convert_odds_to_csv(str(json_path), str(csv_path))
