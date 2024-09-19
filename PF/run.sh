#!/bin/bash

# Check if the number of terminals is provided as an argument
if [ -z "$2" ]; then
  echo "Usage: $0 <number_of_terminals> <local_IP>"
  exit 1
fi

# Number of additional terminals to open
NUM_TERMINALS=$1
# Local IP
LOCALIP=$2

# Open the first terminal with the initial command
gnome-terminal -- bash -c "python3 node.py -p 8000 -s 7000; exec bash"

# Open subsequent terminals with incremented ports and seeds
for i in $(seq 1 $NUM_TERMINALS)
do
  port=$((8000 + i))
  seed=$((7000 + i))
  gnome-terminal -- bash -c "python3 node.py -p $port -s $seed -a $LOCALIP:7000; exec bash"
done
