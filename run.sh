#!/bin/bash

gnome-terminal --title="Simulation" --geometry 60x25+0+0 -e "python3 simulation.py"

for i in {1..20} 
do
	port=$((5010+$i))
	gnome-terminal --title="Cliente $i" -e "python3 client.py -p $port -r 4950 -t 420"
done