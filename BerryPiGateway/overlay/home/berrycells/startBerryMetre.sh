#!/bin/bash
source ~/venvs/berrymetre/bin/activate
cd ~/BerryMetre/BerryMetrePythonReceiver
python BerryMetrePythonReceiver.py >> berrymetre.log 2>&1
