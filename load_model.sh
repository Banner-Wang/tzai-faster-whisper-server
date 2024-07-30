#!/bin/bash

set -euo pipefail

log() {
  # This function is from espnet
  local fname=${BASH_SOURCE[1]##*/}
  echo -e "$(date '+%Y-%m-%d %H:%M:%S') (${fname}:${BASH_LINENO[0]}:${FUNCNAME[1]}) $*"
}

verify_md5() {
    local file_path="$1"
    local md5="$2"

    if [ ! -f "$file_path" ]; then
        log "File not found: $file_path"
        return 1
    fi

    computed_md5=$(md5sum "$file_path" | awk '{print $1}')
    
    if [ "$computed_md5" == "$md5" ]; then
        log "MD5 check passed for $file_path"
        return 0
    else
        log "MD5 check failed for $file_path"
        log "Expected: $md5"
        log "Computed: $computed_md5"
        return 1
    fi
}


download_model() {
    local model_name="$1"
    local model_dir="$2"
    local nfs_model_dir="$3"
    local s3_model_dir="$4"
    local s3_base_url="$5"
    local md5="$6"

    model_tar_name="${model_dir}/${model_name}.tar.gz"

    if [ -f "$nfs_model_dir" ]; then
        log "Using NFS model"
        cp "$nfs_model_dir" "${model_dir}"
    elif [ -f "$s3_model_dir" ]; then
        log "Using S3 model"
        cp "$s3_model_dir" "${model_dir}"
    else
        s3_file_url="${s3_base_url}${s3_model_dir#/s3mnt/}"
        log "Downloading model from S3： $s3_file_url"
        curl -L "$s3_file_url" -o "${model_tar_name}"
    fi

    if [ -n "$md5" ] && verify_md5 "${model_tar_name}" "$md5"; then
        file_type=$(file --mime-type -b "${model_tar_name}")

        case $file_type in
            application/x-gzip)
                log "Extracting gzip compressed tar archive..."
                tar -xzvf "${model_tar_name}" -C "$model_dir" && rm -rf "${model_tar_name}"
                ;;
            application/x-tar)
                log "Extracting uncompressed tar archive..."
                tar -xvf "${model_tar_name}" -C "$model_dir" && rm -rf "${model_tar_name}"
                ;;
            *)
                log "Unsupported file type: $file_type"
                exit 1
                ;;
        esac

        log "Model download success"
    else
      log "Model download failed"
      exit 1
    fi
}

get_model() {
    log "Download model"
    download_model "$model_name" "$app_dir" "$nfs_model_dir" "$s3_model_dir" "$s3_base_url" "$md5"
}


# Read input parameters
model_name=$MODEL_NAME

app_dir=$(pwd)  # Model storage directory
env_file=${app_dir}/app/.env

sed -i "s/^ASR_ENGINE=.*$/ASR_ENGINE=\"finetune_whisper\"/" ${env_file}

# 更新 .env 文件中的 WHISPER_ASR_MODEL 值
sed -i "s/^WHISPER_ASR_MODEL=.*$/WHISPER_ASR_MODEL=\"${model_name}\"/" ${env_file}

CURRENT_WHISPER_ASR_MODEL=$(grep "^WHISPER_ASR_MODEL" ${env_file} | cut -d'=' -f2 | tr -d '"')

if [ "$CURRENT_WHISPER_ASR_MODEL" != "$model_name" ]; then
  log "Error: WHISPER_ASR_MODEL was not updated correctly."
  exit 1
else
  log "WHISPER_ASR_MODEL updated successfully to $CURRENT_WHISPER_ASR_MODEL."
fi

# 下载model对应的config.json文件
if [ -f "config.json" ]; then
    log "config.json exists, remove"
    rm config.json
fi

wget http://svrgit.dingtone.xyz/aibasic/asr-models/-/raw/main/asr/${model_name}/config.json
if [ $? -ne 0 ]; then
    log "Error: Download config.json failed."
    exit 1
fi

config=$(cat ${app_dir}/config.json)


s3_base_url=$(echo "$config" | jq -r '.s3_base_url')
s3_model_dir=$(echo "$config" | jq -r '.s3_model_dir')
nfs_model_dir=$(echo "$config" | jq -r '.nfs_model_dir')
md5=$(echo "$config" | jq -r '.md5')

# Check and download or update the model
get_model