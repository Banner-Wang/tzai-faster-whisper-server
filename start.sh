#!/bin/bash

export LD_LIBRARY_PATH=`python3 -c 'import os; import nvidia.cublas.lib; import nvidia.cudnn.lib; print(os.path.dirname(nvidia.cublas.lib.__file__) + ":" + os.path.dirname(nvidia.cudnn.lib.__file__))'`

cd ~/

model_name=${MODEL_NAME}

# 判断MODEL_NAME是否为空或者不包含finetune字符串
if [ -z "$model_name" ] || [[ ! $model_name =~ finetune ]]; then
  echo "MODEL_NAME is empty or does not contain finetune string, continue..."
else
  echo "Executing bash load_model.sh..."
  bash load_model.sh
fi

echo "Starting uvicorn server..."
uvicorn app.main:app --host 0.0.0.0 --port 8080
