#!/bin/bash
source ~/venvs/berrymetre/bin/activate
cd ~/BerryMetre/BerryMetrePythonReceiver
python BerryMetrePythonReceiver.py > /dev/null 2>&1
