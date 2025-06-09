dwani.ai - gh200 Setup

```bash
export API_KEY_SECRET="dwani-mobile-app-some-sercwer234"
export CHAT_RATE_LIMIT="100/minute"
export DWANI_API_BASE_URL_PDF="http://127.0.0.1:7861"
export DWANI_API_BASE_URL_VISION="http://127.0.0.1:7861"
export DWANI_API_BASE_URL_LLM="http://127.0.0.1:7861"
export DWANI_API_BASE_URL_TTS="http://127.0.0.1:7864"
export DWANI_API_BASE_URL_ASR="http://127.0.0.1:7863"
export DWANI_API_BASE_URL_TRANSLATE="http://127.0.0.1:7862"
export DWANI_API_BASE_URL_S2S="http://127.0.0.1:7861"
export SPEECH_RATE_LIMIT="5/minute"
export ENCRYPTION_KEY="tetegdgfdgfdfgdfgdfg"
export DEFAULT_ADMIN_USER="adminsdfsdf"
export DEFAULT_ADMIN_PASSWORD="dwani-987-123234fsfsfsfsfd"

export HF_TOKEN='hf_this_is_not_a_secret__this_gaganyatri'
```
---


pip install torch==2.7.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

- ### API server 
  - https://github.com/dwani-ai/dwani-api-server
```bash
git clone https://github.com/dwani-ai/dwani-api-server
cd dwani-api-server

python -m venv --system-site-packages venv

source venv/bin/activate

pip install -r requirements.txt


python src/server/main.py --host  0.0.0.0 --port 8888
```

----

- ### ASR - Automatic Speech Recognition / Speech to Text
    - https://github.com/dwani-ai/asr-indic-server.git
```bash
git clone https://github.com/dwani-ai/asr-indic-server.git
cd asr-indic-server
    
python -m venv --system-site-packages venv
source venv/bin/activate

pip install -r requirements.txt


python src/server/asr_api.py --host 0.0.0.0 --port 7863 --device cuda

```
----

- ### Translate
- https://github.com/dwani-ai/indic-translate-server.git
```bash
git clone https://github.com/dwani-ai/indic-translate-server.git
cd indic-translate-server

python -m venv --system-site-packages venv

source venv/bin/activate
pip install --upgrade pip setuptools wheel packaging cython

pip install torch==2.7.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt

python src/server/translate_api.py --host 0.0.0.0 --port 7862 --device cuda
```

--- 
- ### Documents 
  - https://github.com/dwani-ai/docs-indic-server.git
```bash
git clone https://github.com/dwani-ai/docs-indic-server.git
cd docs-indic-server

python -m venv --system-site-packages venv

source venv/bin/activate

pip install -r requirements.txt
pip install "numpy<2.0"

python src/server/docs_api.py  --host 0.0.0.0 --port 7861
```

- Dependencies
  - decord

```bash
cd
mkdir external
cd external
git clone --recursive https://github.com/dmlc/decord

cd decord

mkdir build && cd build

cmake .. -DUSE_CUDA=0 -DCMAKE_BUILD_TYPE=Release

make

cd ../python
python3 setup.py install --user
pip install "numpy<2.0"

```
<!-- 
// pwd=$PWD
// echo "PYTHONPATH=$PYTHONPATH:$pwd" >> ~/.bashrc
// source ~/.bashrc
### option 2: install with setuptools
-->

- olmocr

```bash
cd ../../
git clone  https://github.com/allenai/olmocr.git

cd olmocr

pip install --upgrade pip setuptools wheel packaging

 // copy ppyproject.toml
pip install -e .
cd ../../dwani_org/gh-200-docs-indic-server/
pip install "numpy<2.0"
```
in olmocr :  pyproject.toml - remove sql-kernem and sglang
set python version to 3.10
<!--

diff --git a/pyproject.toml b/pyproject.toml
index 0eec834..431216f 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -17,7 +17,7 @@ classifiers = [
 authors = [
     {name = "Allen Institute for Artificial Intelligence", email = "jakep@allenai.org"}
 ]
-requires-python = ">=3.11"git 
+requires-python = ">=3.10"
 dependencies = [
   "cached-path",
   "smart_open",
@@ -50,8 +50,6 @@ Changelog = "https://github.com/allenai/olmocr/blob/main/CHANGELOG.md"
 
 [project.optional-dependencies]
 gpu = [
-    "sgl-kernel==0.0.3.post1",
-    "sglang[all]==0.4.2",
 ]
 
 dev = [
 -->

 --

- ### TTS - Text to Speech 
- https://github.com/dwani-ai/tts-indic-server
```bash
git clone https://github.com/dwani-ai/tts-indic-server
cd tts-indic-server


python -m venv  venv
source venv/bin/activate
pip install wheel packaging

pip install -r requirements.txt

 pip uninstall torch torchaudio torchvision

pip install torch==2.7.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

python src/gh200/main.py --host 0.0.0.0 --port 7864 --config config_two
```


