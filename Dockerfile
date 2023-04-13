FROM python:slim
FROM nvidia/opengl:1.2-glvnd-devel-ubuntu18.04
RUN apt-get update && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends \
    git \
    wget \
    g++ \
    ca-certificates \
    libx11-6 \
    libgl1 \
    libxrender1 \
  && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-latest-Linux-x86_64.sh -b \
    && rm -f Miniconda3-latest-Linux-x86_64.sh \
    && echo "Running $(conda --version)" && \
    conda init bash && \
    . /root/.bashrc && \
    conda update conda && \
    conda create -n python-app && \
    conda activate python-app && \
    conda install python=3.11 pip

RUN mkdir /GV \
    && cd /GV \
    && git init \
    && git remote add origin https://github.com/GeoverseGit/ProjectG.git \
    && git fetch --all \
    && git reset --hard origin/master

RUN /bin/bash -c "source activate python-app && pip install vtk trame"

RUN echo 'conda activate python-app \n \
alias gv-para="python main.py"' >> /root/.bashrc
ENTRYPOINT []
WORKDIR /GV
CMD ["/bin/bash", "-c", "source activate python-app && python main.py --port 1234 --host 0.0.0.0"]
