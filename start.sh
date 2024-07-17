#!/bin/bash

bash load_model.sh

export LD_LIBRARY_PATH=`python3 -c 'import os; import nvidia.cublas.lib; import nvidia.cudnn.lib; print(os.path.dirname(nvidia.cublas.lib.__file__) + ":" + os.path.dirname(nvidia.cudnn.lib.__file__))'`
cd ~/
uvicorn app.main:app --host 0.0.0.0 --port 8080
