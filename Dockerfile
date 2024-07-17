# 使用官方的 Python 3.10 Slim 镜像作为基础镜像
FROM python:3.10-slim-bookworm

# 设置环境变量，指定用户的主目录和更新 PATH 环境变量
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# 切换到 root 用户
USER root

# 设置工作目录
WORKDIR $HOME

RUN bash build.sh

RUN bash load_model.sh

# 复制应用代码到容器内，并将所有权设置为 root
COPY --chown=root . $HOME

CMD ["bash", "start.sh"]